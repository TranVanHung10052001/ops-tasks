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
    get_task, block_task, list_auto_created_today, list_team_tasks,
)
from roles import MANAGER, TEAM_LEAD, can_see_team
import templates as tpl

logger = logging.getLogger(__name__)

QUIET_START = int(os.getenv("QUIET_HOURS_START", "22"))
QUIET_END   = int(os.getenv("QUIET_HOURS_END", "6"))
MANAGER_ID  = int(os.getenv("MANAGER_CHAT_ID", "0"))

P_EMOJI = tpl.PRIORITY_ICON


def _is_quiet() -> bool:
    h = datetime.now().hour
    if QUIET_START > QUIET_END:
        return h >= QUIET_START or h < QUIET_END
    return QUIET_START <= h < QUIET_END


def _fmt(task: dict, show_assignee: bool = False) -> str:
    """Delegate to templates design system."""
    return tpl.fmt_task_line(task, show_assignee=show_assignee)


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
    await app.bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")


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
            chat_id=MANAGER_ID, text=msg, parse_mode="HTML"
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
                    msg = tpl.msg_reminder_deadline(task, hours)
                    await app.bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
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
                    msg = tpl.msg_overdue(task, hrs_over)
                    await app.bot.send_message(chat_id=uid, text=msg)
                    increment_reminder(task["id"])

        except Exception as e:
            logger.error(f"deadline_check_all failed for {uid}: {e}")


# ─── Daily AI auto-assign digest (17:00) ─────────────────────────────────────

async def auto_digest_manager(app):
    """
    17:00 daily — list mọi task bot tự tạo (source='ai_auto') trong ngày,
    gửi cho manager kèm inline button reassign per-task.
    Im lặng nếu không có task auto-tạo nào trong ngày.
    """
    if _is_quiet() or not MANAGER_ID:
        return

    tasks = list_auto_created_today()
    if not tasks:
        logger.info("auto_digest_manager: no auto-created tasks today")
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    msg = tpl.msg_auto_digest_manager(tasks)
    # 1 reassign button per task (cap 8 to keep keyboard readable)
    rows = []
    for t in tasks[:8]:
        rows.append([
            InlineKeyboardButton(
                f"↗ #{t['id']} → {t.get('assignee_name','?')}",
                callback_data=f"digest_reassign:{t['id']}",
            ),
        ])
    kb = InlineKeyboardMarkup(rows) if rows else None

    try:
        await app.bot.send_message(
            chat_id=MANAGER_ID, text=msg,
            parse_mode="HTML", reply_markup=kb,
        )
        logger.info("auto_digest_manager: sent %d auto-created tasks", len(tasks))
    except Exception as e:
        logger.error(f"auto_digest_manager failed: {e}")


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
            stats      = get_team_stats()
            members    = list_team_by_person()
            all_ov     = get_all_overdue_tasks()
            # Top pending across all team — for tomorrow's Q1/Q2 preview
            all_pending = list_team_tasks(statuses=["pending", "accepted"], limit=50)
            msg = tpl.msg_eod_manager(
                stats=stats,
                members=members,
                overdue_tasks=all_ov,
                top_pending=all_pending,
            )
            await app.bot.send_message(chat_id=MANAGER_ID, text=msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"manager eod digest failed: {e}")


