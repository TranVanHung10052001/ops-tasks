"""
Scheduler — per-user reminders + team digest for manager.
All jobs run async via APScheduler.
"""

import logging
import os
from datetime import datetime, timedelta

from store import (
    list_users, get_top_tasks_for_user, get_overdue_tasks_for_user,
    get_upcoming_deadlines_for_user, get_stalled_tasks_for_user,
    list_team_by_person, get_team_stats, get_all_overdue_tasks,
    unsnooze_due_tasks, increment_reminder, increment_defer,
    get_task, block_task,
)
from roles import MANAGER, TEAM_LEAD, can_see_team
from roast import (
    get_morning_roast, get_manager_morning_roast,
    get_overdue_roast, get_eod_roast,
)
import templates as tpl

logger = logging.getLogger(__name__)

QUIET_START = int(os.getenv("QUIET_HOURS_START", "22"))
QUIET_END   = int(os.getenv("QUIET_HOURS_END", "6"))
MANAGER_ID  = int(os.getenv("MANAGER_CHAT_ID", "0"))

P_EMOJI = {"P0": "🔴", "P1": "🟡", "P2": "🟢", "P3": "🔵"}

# Lazy import to avoid circular dependency
def _build_smart_reminder(task: dict, context: str = "deadline") -> str:
    try:
        from smart_agent import build_smart_reminder
        return build_smart_reminder(task, context=context)
    except Exception as e:
        logger.warning(f"smart_reminder fallback: {e}")
        return None  # Caller falls back to simple _fmt()


def _is_quiet() -> bool:
    h = datetime.now().hour
    if QUIET_START > QUIET_END:
        return h >= QUIET_START or h < QUIET_END
    return QUIET_START <= h < QUIET_END


def _fmt(task: dict, show_assignee: bool = False) -> str:
    emoji = P_EMOJI.get(task.get("priority", "P3"), "⚪")
    line = f"{emoji} #{task['id']} {task['summary'][:65]}"
    if show_assignee and task.get("assignee_name"):
        line += f" → {task['assignee_name']}"
    if task.get("deadline"):
        try:
            dl = datetime.fromisoformat(task["deadline"]).replace(tzinfo=None)
            delta = dl - datetime.now()
            if delta.total_seconds() < 0:
                line += f" ⚠️ trễ {abs(delta.total_seconds())/3600:.0f}h"
            elif delta.days == 0:
                line += f" — {delta.total_seconds()/3600:.0f}h nữa"
            elif delta.days <= 3:
                line += f" — {dl.strftime('%d/%m %H:%M')}"
            else:
                line += f" — {dl.strftime('%d/%m')}"
        except (ValueError, TypeError):
            pass
    return line


# ─── Personal briefings (8:00 for all users) ─────────────────────────────────

async def morning_briefing_all(app):
    """Send personal morning briefing to every approved user."""
    if _is_quiet():
        return

    unsnooze_due_tasks()
    users = list_users(approved_only=True)

    for u in users:
        uid = u["telegram_id"]
        if uid == MANAGER_ID:
            continue  # Manager gets special digest at 8:30
        try:
            await _send_personal_briefing(app, uid, u["full_name"])
        except Exception as e:
            logger.error(f"morning briefing failed for {uid}: {e}")


async def _send_personal_briefing(app, user_id: int, name: str):
    overdue = get_overdue_tasks_for_user(user_id)
    top3    = get_top_tasks_for_user(user_id, limit=3)
    msg = tpl.msg_morning_member(name, overdue, top3)
    await app.bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")


# ─── Manager team digest (8:30) ───────────────────────────────────────────────

async def manager_team_digest(app):
    """Send team-wide status digest to manager at 8:30."""
    if _is_quiet() or not MANAGER_ID:
        return

    members     = list_team_by_person()
    stats       = get_team_stats()
    overdue_all = get_all_overdue_tasks()

    # Build manager name from first approved user with manager role (fallback: "Manager")
    from store import list_users
    mgr_users = [u for u in list_users(approved_only=True) if u.get("telegram_id") == MANAGER_ID]
    mgr_name = mgr_users[0]["full_name"].split()[0] if mgr_users else "Manager"

    msg = tpl.msg_morning_manager(
        manager_name=mgr_name,
        stats=stats,
        members=members,
        overdue_tasks=overdue_all,
    )
    try:
        await app.bot.send_message(
            chat_id=MANAGER_ID, text=msg, parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"manager_team_digest failed: {e}")


# ─── Deadline check (every 15 min, for all users) ────────────────────────────

async def deadline_check_all(app):
    if _is_quiet():
        return

    users = list_users(approved_only=True)
    for u in users:
        uid = u["telegram_id"]
        try:
            tasks = get_upcoming_deadlines_for_user(uid, hours_ahead=72)
            now = datetime.now()
            for task in tasks:
                if not task.get("deadline"):
                    continue
                try:
                    dl = datetime.fromisoformat(task["deadline"]).replace(tzinfo=None)
                except (ValueError, TypeError):
                    continue

                delta = dl - now
                hours = delta.total_seconds() / 3600
                rc = task.get("reminder_count", 0)
                msg = None

                should_remind = False
                if 0 <= hours <= 4 and rc < 3:
                    should_remind = True
                elif 20 <= hours <= 28 and rc < 2:
                    should_remind = True
                elif 68 <= hours <= 76 and rc < 1:
                    should_remind = True

                if should_remind:
                    # Try smart reminder first, fallback to template
                    msg = _build_smart_reminder(task, context="deadline")
                    if not msg:
                        msg = tpl.msg_reminder_deadline(task, hours)
                    await app.bot.send_message(
                        chat_id=uid, text=msg, parse_mode="Markdown"
                    )
                    increment_reminder(task["id"])

            # Overdue check — smart reminder + P0 escalation
            overdue = get_overdue_tasks_for_user(uid)
            for task in overdue:
                rc_task = task.get("reminder_count", 0)
                if rc_task >= 6:
                    continue
                try:
                    dl = datetime.fromisoformat(task["deadline"]).replace(tzinfo=None)
                    hrs_over = (now - dl).total_seconds() / 3600
                except (ValueError, TypeError):
                    continue

                # Remind frequency: first 3 times every 4h, after that every 24h
                if rc_task < 3:
                    should_ping = hrs_over % 4 < 0.5
                else:
                    should_ping = hrs_over % 24 < 0.5

                if should_ping:
                    msg = _build_smart_reminder(task, context="overdue")
                    if not msg:
                        msg = tpl.msg_overdue(task, hrs_over)
                    await app.bot.send_message(
                        chat_id=uid, text=msg, parse_mode="Markdown"
                    )
                    increment_reminder(task["id"])

                    # P0 escalation: after 24h overdue + rc>=2 → alert manager too
                    if (task.get("priority") == "P0" and hrs_over >= 24
                            and rc_task == 2 and MANAGER_ID and uid != MANAGER_ID):
                        escalate_msg = (
                            f"🚨 *P0 Escalation:*\n"
                            f"Task #{task['id']} của *{task.get('assignee_name','?')}* "
                            f"đã quá hạn {int(hrs_over)}h và chưa có update.\n\n"
                            f"_{task.get('summary','')[:80]}_\n\n"
                            f"Cần can thiệp không?"
                        )
                        try:
                            await app.bot.send_message(
                                chat_id=MANAGER_ID,
                                text=escalate_msg,
                                parse_mode="Markdown",
                            )
                        except Exception as esc_e:
                            logger.error(f"P0 escalation failed: {esc_e}")

        except Exception as e:
            logger.error(f"deadline_check_all failed for {uid}: {e}")


# ─── EOD recap (18:00) ────────────────────────────────────────────────────────

async def eod_recap_all(app):
    if _is_quiet():
        return

    from store import get_user_stats, list_team_tasks
    users = list_users(approved_only=True)
    for u in users:
        uid = u["telegram_id"]
        # skip manager — gets separate team digest
        if uid == MANAGER_ID:
            continue
        try:
            s = get_user_stats(uid)
            overdue = get_overdue_tasks_for_user(uid)
            top_pending = get_top_tasks_for_user(uid, limit=3)

            if s["pending"] == 0 and not overdue:
                continue  # Nothing to report

            msg = tpl.msg_evening_member(
                name=u["full_name"],
                done_count=s.get("done_today", 0),
                total_count=s.get("done_today", 0) + s.get("pending", 0),
                pending_tomorrow=top_pending,
            )
            await app.bot.send_message(chat_id=uid, text=msg)
        except Exception as e:
            logger.error(f"eod_recap failed for {uid}: {e}")

    # Manager gets richer team EOD
    if MANAGER_ID:
        try:
            stats   = get_team_stats()
            members = list_team_by_person()
            all_ov  = get_all_overdue_tasks()
            msg = tpl.msg_eod_manager(
                stats=stats,
                members=members,
                overdue_tasks=all_ov,
            )
            await app.bot.send_message(chat_id=MANAGER_ID, text=msg)
        except Exception as e:
            logger.error(f"manager eod digest failed: {e}")


# ─── OKR Risk Intel (Mon/Wed/Fri 8:30 — Manager only) ───────────────────────

# Static OKR actions from api.py (duplicated here to avoid circular import)
# Update deadline when OKR changes
_OKR_ACTIONS = [
    ("O1.1", "FR Core ≥68%", ["1.1.1","1.1.2","1.1.3","1.1.4"]),
    ("O1.2", "FR Long Haul ≥70%", ["1.2.1","1.2.2","1.2.3","1.2.4"]),
    ("O1.3", "FR SME 100–300kg ≥65%", ["1.3.1","1.3.2","1.3.3","1.3.4"]),
    ("O2.1", "KCN BDG + LAN Hub", ["2.1.1","2.1.2","2.1.3","2.1.4","2.1.5","2.1.6"]),
    ("O2.2", "Shift Model ≥100 drivers", ["2.2.1","2.2.2","2.2.3","2.2.4","2.2.5"]),
    ("O2.4", "Driver Retention D30 70%", ["2.4.1","2.4.2","2.4.3"]),
    ("O3.1", "1st PU On-Time 80%", ["3.1.1","3.1.2","3.1.3"]),
    ("O3.2", "COGS GXT 75K/kiện", ["3.2.1","3.2.2","3.2.3","3.2.4"]),
    ("O3.3", "Vendor Truck B2B 11", ["3.3.1","3.3.2"]),
    ("O3.4", "Distribution GSV ≥4.5B", ["3.4.1","3.4.2"]),
]

_DEADLINES = {
    "1.1.1": "2026-04-29","1.1.2": "2026-04-30","1.1.3": "2026-05-27","1.1.4": "2026-04-30",
    "1.2.1": "2026-05-10","1.2.2": "2026-05-22","1.2.3": "2026-06-15","1.2.4": "2026-05-31",
    "1.3.1": "2026-05-18","1.3.2": "2026-05-22","1.3.3": "2026-05-15","1.3.4": "2026-04-30",
    "2.1.1": "2026-05-10","2.1.2": "2026-05-27","2.1.3": "2026-05-20","2.1.4": "2026-06-30",
    "2.1.5": "2026-05-27","2.1.6": "2026-05-15","2.2.1": "2026-04-22","2.2.2": "2026-04-30",
    "2.2.3": "2026-05-07","2.2.4": "2026-05-15","2.2.5": "2026-05-15","2.4.1": "2026-05-07",
    "2.4.2": "2026-05-15","2.4.3": "2026-05-31","3.1.1": "2026-04-15","3.1.2": "2026-04-30",
    "3.1.3": "2026-04-22","3.2.1": "2026-04-20","3.2.2": "2026-04-30","3.2.3": "2026-05-31",
    "3.2.4": "2026-05-31","3.3.1": "2026-05-30","3.3.2": "2026-06-15","3.4.1": "2026-04-30",
    "3.4.2": "2026-05-31",
}


async def okr_risk_intel(app):
    """
    Send OKR Risk Radar to manager Mon/Wed/Fri 8:30.
    Analyzes overdue OKR actions + team member overload → actionable suggestions.
    """
    if _is_quiet() or not MANAGER_ID:
        return

    now = datetime.now()
    weekday = now.weekday()  # 0=Mon, 1=Tue, ...
    if weekday not in (0, 2, 4):  # Mon/Wed/Fri only
        return

    # Compute OKR health
    at_risk = []
    watch = []
    on_track = []

    for kr_id, kr_label, action_ids in _OKR_ACTIONS:
        total = len(action_ids)
        overdue_count = 0
        critical_count = 0  # due in ≤ 3 days
        for aid in action_ids:
            dl_str = _DEADLINES.get(aid)
            if not dl_str:
                continue
            try:
                dl = datetime.fromisoformat(dl_str)
                delta = (dl - now).total_seconds()
                if delta < 0:
                    overdue_count += 1
                elif delta <= 3 * 86400:
                    critical_count += 1
            except (ValueError, TypeError):
                pass

        overdue_pct = overdue_count / total if total else 0
        if overdue_pct >= 0.5:
            at_risk.append((kr_id, kr_label, overdue_count, total, critical_count))
        elif overdue_pct >= 0.25 or critical_count >= 2:
            watch.append((kr_id, kr_label, overdue_count, total, critical_count))
        else:
            on_track.append((kr_id, kr_label, overdue_count, total, critical_count))

    # Team load analysis
    members = list_team_by_person()
    overloaded = [(m["full_name"], m["active_count"], m["overdue_count"])
                  for m in members if m.get("active_count", 0) > 6 or m.get("overdue_count", 0) > 2]
    underloaded = [(m["full_name"], m["active_count"])
                   for m in members if m.get("active_count", 0) <= 1 and m.get("role") != "manager"]

    # Build message
    day_str = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu"][weekday]
    lines = [
        f"{tpl.AI_SIG} · OKR Risk Radar",
        f"{day_str} {now.strftime('%d·%m')}",
        tpl.DIV_STRONG,
        "",
    ]

    if at_risk:
        lines.append("■ AT RISK — xử lý ngay")
        for kr_id, label, od, total, crit in at_risk:
            row = f"  · {kr_id} {label}: {od}/{total} overdue"
            if crit:
                row += f", {crit} sắp hết hạn"
            lines.append(row)
        lines.append("")

    if watch:
        lines.append("▪ WATCH — theo dõi")
        for kr_id, label, od, total, crit in watch:
            row = f"  · {kr_id} {label}: {od}/{total} overdue"
            if crit:
                row += f", {crit} sắp hết hạn"
            lines.append(row)
        lines.append("")

    if on_track:
        lines.append("● ON TRACK: " + " · ".join(kr for kr, *_ in on_track))
        lines.append("")

    if overloaded:
        lines.append(f"{tpl.DIV_LIGHT}")
        lines.append("▲ OVERLOAD")
        for name, active, ov in overloaded:
            lines.append(f"  · {name}: {active} active, {ov} trễ")
        lines.append("")

    if underloaded and overloaded:
        lines.append(f"Đề xuất: phân lại task sang {', '.join(n for n, _ in underloaded[:2])}")
        lines.append("")

    lines.append("/team · /assign")
    msg = "\n".join(lines)

    try:
        await app.bot.send_message(
            chat_id=MANAGER_ID, text=msg, parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"okr_risk_intel failed: {e}")


# ─── Stall check (9:00 and 15:00) ────────────────────────────────────────────

async def stall_check_all(app):
    if _is_quiet():
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    users = list_users(approved_only=True)

    for u in users:
        uid = u["telegram_id"]
        stalled = get_stalled_tasks_for_user(uid, stale_days=2)
        for task in stalled[:2]:
            try:
                created = datetime.fromisoformat(task["created_at"]).replace(tzinfo=None)
                days = (datetime.now() - created).days
            except (ValueError, TypeError):
                days = "?"

            defers = f" (hoãn {task['defer_count']}x)" if task.get("defer_count", 0) else ""
            base_msg = tpl.msg_stalled(task)
            msg = base_msg if not defers else base_msg + f"\n_{defers}_"
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🧾 Chờ chứng từ", callback_data=f"block:{task['id']}:chờ_chứng_từ"),
                    InlineKeyboardButton("👤 Chờ người", callback_data=f"block:{task['id']}:chờ_người"),
                ],
                [
                    InlineKeyboardButton("❓ Chưa rõ hướng", callback_data=f"block:{task['id']}:chưa_rõ"),
                    InlineKeyboardButton("✓ Xong rồi", callback_data=f"done:{task['id']}"),
                ],
            ])
            try:
                await app.bot.send_message(
                    chat_id=uid, text=msg,
                    parse_mode="Markdown", reply_markup=kb,
                )
                increment_defer(task["id"])
            except Exception as e:
                logger.error(f"stall_check failed for task #{task['id']}: {e}")


# ─── Weekly Friday Report (17:00 Fri) ─────────────────────────────────────────

async def weekly_report(app):
    """
    Friday 17:00 — AI-generated weekly summary sent to manager.
    Covers: done, overdue, velocity, AI highlights + next-week focus.
    """
    if _is_quiet() or not MANAGER_ID:
        return

    now = datetime.now()
    if now.weekday() != 4:  # Friday only
        return

    from store import list_team_tasks, get_team_stats
    from classifier import weekly_summary as ai_summary

    # Collect last 7 days data
    week_start = (now - timedelta(days=7)).isoformat()
    done_tasks    = list_team_tasks(statuses=["done"],    since=week_start)
    pending_tasks = list_team_tasks(statuses=["pending"])
    overdue_tasks = get_all_overdue_tasks()
    stats = get_team_stats()

    period_label = f"{(now - timedelta(days=7)).strftime('%d/%m')}–{now.strftime('%d/%m/%Y')}"

    # AI analysis
    ai = ai_summary(done_tasks, pending_tasks, overdue_tasks, period_label)

    # Build report
    msg = f"📊 *Weekly Report — Tuần {period_label}*\n\n"

    # Headline
    if ai.get("headline"):
        msg += f"_{ai['headline']}_\n\n"

    # Numbers
    msg += (
        f"*Tổng kết:*\n"
        f"  ✅ Done: *{len(done_tasks)}* tasks\n"
        f"  ⏳ Pending: *{len(pending_tasks)}* tasks\n"
        f"  🔴 Overdue: *{len(overdue_tasks)}* tasks\n"
    )

    # Team velocity (top doers)
    doer_count: dict[str, int] = {}
    for t in done_tasks:
        name = t.get("assignee_name") or "?"
        doer_count[name] = doer_count.get(name, 0) + 1
    if doer_count:
        top3 = sorted(doer_count.items(), key=lambda x: -x[1])[:3]
        msg += "\n*🏆 Top contributors:*\n"
        for name, cnt in top3:
            msg += f"  • {name}: {cnt} tasks done\n"

    # AI highlights
    if ai.get("highlights"):
        msg += "\n*💡 Highlights:*\n"
        for h in ai["highlights"][:3]:
            msg += f"  • {h}\n"

    # Risks
    if ai.get("risks"):
        msg += "\n*⚠️ Cần chú ý:*\n"
        for r in ai["risks"][:2]:
            msg += f"  • {r}\n"

    # Next week focus
    if ai.get("next_week_focus"):
        msg += f"\n*📌 Tuần tới:* _{ai['next_week_focus']}_\n"

    msg += "\n/team · /pending · /stats"

    try:
        await app.bot.send_message(
            chat_id=MANAGER_ID, text=msg, parse_mode="Markdown"
        )
        logger.info("Weekly report sent to manager")
    except Exception as e:
        logger.error(f"weekly_report failed: {e}")
