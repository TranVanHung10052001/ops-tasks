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

logger = logging.getLogger(__name__)

QUIET_START = int(os.getenv("QUIET_HOURS_START", "22"))
QUIET_END   = int(os.getenv("QUIET_HOURS_END", "6"))
MANAGER_ID  = int(os.getenv("MANAGER_CHAT_ID", "0"))

P_EMOJI = {"P0": "🔴", "P1": "🟡", "P2": "🟢", "P3": "🔵"}


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
    overdue  = get_overdue_tasks_for_user(user_id)
    top3     = get_top_tasks_for_user(user_id, limit=3)

    now = datetime.now()
    weekday = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"][now.weekday()]

    roast = get_morning_roast(len(overdue))
    msg = f"*{weekday} {now.strftime('%d/%m')} — Xin chào {name}*\n_{roast}_\n\n"

    if overdue:
        msg += f"⚠️ *Quá hạn ({len(overdue)}):*\n"
        for t in overdue[:4]:
            msg += f"  {_fmt(t)}\n"
        msg += "\n"

    if top3:
        msg += f"📋 *Ưu tiên hôm nay:*\n"
        for t in top3:
            msg += f"  {_fmt(t)}\n"
        msg += "\n"

    if not overdue and not top3:
        msg += "Queue sạch. Tốt.\n\n"

    msg += "/mytasks · /done <id> · /snooze <id> 2h"

    await app.bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")


# ─── Manager team digest (8:30) ───────────────────────────────────────────────

async def manager_team_digest(app):
    """Send team-wide status digest to manager at 8:30."""
    if _is_quiet() or not MANAGER_ID:
        return

    members = list_team_by_person()
    stats   = get_team_stats()
    overdue_all = get_all_overdue_tasks()

    now = datetime.now()
    roast = get_manager_morning_roast(stats["overdue"], stats["active"])

    msg = (
        f"*Team digest — {now.strftime('%d/%m %H:%M')}*\n"
        f"_{roast}_\n\n"
        f"{stats['active']} active · {stats['done_today']} done · "
        f"{stats['overdue']} overdue · {stats['blocked']} blocked\n\n"
    )

    for m in members:
        active  = m.get("active_count", 0)
        overdue = m.get("overdue_count", 0)
        blocked = m.get("blocked_count", 0)

        if overdue > 0:
            ind = "🔴"
        elif active > 8:
            ind = "🟡"
        else:
            ind = "🟢"

        line = f"{ind} *{m['full_name']}* — {active} task"
        if overdue:
            line += f", {overdue} trễ"
        if blocked:
            line += f", {blocked} blocked"
        msg += line + "\n"

    if overdue_all:
        msg += f"\n⚠️ *Overdue cần chú ý:*\n"
        for t in overdue_all[:5]:
            msg += f"  {_fmt(t, show_assignee=True)}\n"

    msg += "\n/team chi tiết · /assign giao việc mới"

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

                if 0 <= hours <= 4 and rc < 3:
                    msg = f"🔥 *Hôm nay deadline:*\n  {_fmt(task)}\n\n/done {task['id']} khi xong"
                elif 20 <= hours <= 28 and rc < 2:
                    msg = f"⏰ *Mai phải xong:*\n  {_fmt(task)}"
                elif 68 <= hours <= 76 and rc < 1:
                    msg = f"📋 *Còn 3 ngày:*\n  {_fmt(task)}"

                if msg:
                    await app.bot.send_message(
                        chat_id=uid, text=msg, parse_mode="Markdown"
                    )
                    increment_reminder(task["id"])

            # Overdue check
            overdue = get_overdue_tasks_for_user(uid)
            for task in overdue:
                if task.get("reminder_count", 0) >= 5:
                    continue
                try:
                    dl = datetime.fromisoformat(task["deadline"]).replace(tzinfo=None)
                    hrs_over = (now - dl).total_seconds() / 3600
                except (ValueError, TypeError):
                    continue

                if hrs_over % 4 < 0.5:
                    roast = get_overdue_roast(hrs_over)
                    await app.bot.send_message(
                        chat_id=uid,
                        text=f"⚠️ *Task #{task['id']} overdue*\n  {_fmt(task)}\n\n_{roast}_",
                        parse_mode="Markdown",
                    )
                    increment_reminder(task["id"])

        except Exception as e:
            logger.error(f"deadline_check_all failed for {uid}: {e}")


# ─── EOD recap (18:00) ────────────────────────────────────────────────────────

async def eod_recap_all(app):
    if _is_quiet():
        return

    users = list_users(approved_only=True)
    for u in users:
        uid = u["telegram_id"]
        try:
            from store import get_user_stats
            s = get_user_stats(uid)
            overdue = get_overdue_tasks_for_user(uid)

            if s["pending"] == 0 and not overdue:
                continue  # Nothing to report

            roast = get_eod_roast(s["done_week"], s["pending"], s["overdue"])
            msg = (
                f"*EOD — {u['full_name']}*\n_{roast}_\n\n"
                f"✓ {s['done_week']} done tuần này · ⏳ {s['pending']} pending"
            )
            if overdue:
                msg += f"\n\n⚠️ *Cần xử lý sáng mai:*\n"
                for t in overdue[:3]:
                    msg += f"  {_fmt(t)}\n"

            await app.bot.send_message(chat_id=uid, text=msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"eod_recap failed for {uid}: {e}")

    # Manager gets team EOD
    if MANAGER_ID:
        try:
            stats = get_team_stats()
            msg = (
                f"*EOD Team — {datetime.now().strftime('%d/%m')}*\n\n"
                f"✓ {stats['done_today']} done hôm nay · "
                f"⏳ {stats['active']} active · "
                f"⚠️ {stats['overdue']} overdue\n\n"
                f"/team để xem chi tiết"
            )
            await app.bot.send_message(
                chat_id=MANAGER_ID, text=msg, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"manager eod digest failed: {e}")


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

            emoji = P_EMOJI.get(task.get("priority", "P3"), "⚪")
            defers = f" (hoãn {task['defer_count']}x)" if task.get("defer_count", 0) else ""
            msg = (
                f"⏸ *Task #{task['id']} — im {days} ngày{defers}*\n"
                f"{emoji} {task['summary'][:80]}\n\nĐang bị gì vậy?"
            )
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
