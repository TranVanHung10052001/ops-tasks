"""
Bot Handlers — Multi-user team task bot.
Roles: manager / team_lead / employee.
"""

import logging
import io
import os
import re
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from store import (
    get_user, register_user, approve_user, reject_user,
    set_user_role, list_users, list_pending_approval, touch_user,
    add_task, get_task, list_user_tasks, list_user_today_tasks,
    list_team_tasks, list_team_by_person, get_team_stats, get_user_stats,
    mark_done, cancel_task, start_task, return_to_pool, snooze_task, block_task, unblock_task,
    update_task_deadline, set_actual_minutes, increment_reminder,
    increment_defer, get_overdue_tasks_for_user, get_stalled_tasks_for_user,
    get_top_tasks_for_user, get_member_performance,
    log_action,
    get_user_by_name, get_user_by_email, find_users_by_name, reassign_task,
    get_adhoc_ratio_this_week,
    claim_preseeded_user, find_preseeded_by_name,
)
from roles import (
    MANAGER, TEAM_LEAD, EMPLOYEE, ROLE_LABELS, MANAGER_CHAT_ID,
    is_manager, is_team_lead, can_assign, can_see_team,
    can_approve_users, can_see_task,
)
from classifier import (
    extract_deadline, route_task, recommend_now, coach_task,
)
import templates as tpl

logger = logging.getLogger(__name__)


async def _ai(fn, *args, **kwargs):
    """Run a blocking Gemini call in a thread so it never freezes the event loop.

    The classifier functions (route_task, recommend_now, coach_task,
    extract_deadline) call model.generate_content() synchronously and can block
    1–5s. Running them inline in an async handler stalls the bot for ALL users.
    Wrapping every call in run_in_executor keeps the loop responsive.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

# ─── Persisted state (survives bot restarts via SQLite) ──────────────────────
# Replaces in-memory dicts so callback state doesn't get wiped on Railway redeploy
from store import PersistedDict as _PersistedDict

DEADLINE_TTL = 300  # 5 minutes

# {chat_id: True} — waiting for user's full name input
_pending_name = _PersistedDict("name", ttl_seconds=1800)

# {chat_id: {classified_task_data}} — forward-to-assign flow step 1
_pending_assign_who = _PersistedDict("assign_who", ttl_seconds=1800)

# {chat_id: {task_data, assignee_id}} — waiting for deadline after assignee picked
_pending_assign_deadline = _PersistedDict("assign_deadline", ttl_seconds=DEADLINE_TTL)

# {chat_id: (task_id, ts)} — waiting for deadline on self-created task
_pending_deadline = _PersistedDict("deadline", ttl_seconds=DEADLINE_TTL)

# {chat_id: {routed task data}} — waiting for manager to confirm AI routing
_pending_confirm = _PersistedDict("confirm", ttl_seconds=1800)

# ─── Deadline-reply heuristic ─────────────────────────────────────────────────
# Only treat incoming text as a deadline answer when it is SHORT (≤ 6 words)
# AND contains a Vietnamese date/time token.  Anything longer is almost certainly
# a new task message, not a deadline reply — fixes the "task 2 silently dropped"
# bug where extract_deadline() consumed a task description as a deadline.
_DEADLINE_TOKEN_RE = re.compile(
    r'\b('
    r't[2-8]'               # t2-t8 (thứ)
    r'|thứ\s*[2-8hai ba tư năm sáu bảy]+'
    r'|mai|ngày\s*mai|hôm\s*nay'
    r'|sáng|chiều|tối|trưa|đêm'
    r'|\d{1,2}\s*h\s*\d{0,2}'  # 5h, 17h30
    r'|\d{1,2}:\d{2}'          # 17:30
    r'|\d{1,2}/\d{1,2}'        # 31/05
    r'|cuối\s*tuần|cuối\s*ngày|cuối\s*tháng'
    r'|tuần\s*(này|sau|tới)'
    r'|tháng\s*(này|sau)'
    r'|eod|eow|asap'
    r'|trước\s*\d'             # trước 5pm
    r')',
    re.IGNORECASE,
)


def _is_deadline_reply(text: str) -> bool:
    """Return True iff text looks like a pure deadline response (≤ 8 words + date token).

    Cap raised 6→8: Vietnamese deadline replies like "trước 5h chiều thứ 6 tuần này"
    run to 7 words and were being misread as new tasks."""
    return len(text.split()) <= 8 and bool(_DEADLINE_TOKEN_RE.search(text))

# {chat_id: task_id} — last task touched/created in this session (NL follow-up context)
_last_task: dict[int, int] = {}

# {task_id: created_at} — bot-auto-created tasks (source=ai_auto), tracked for /undo window
_auto_created: dict[int, datetime] = {}

# ─── Auto-decision config (env-tunable) ───────────────────────────────────────
AUTO_DECISION_THRESHOLD    = float(os.getenv("AUTO_DECISION_THRESHOLD", "0.85"))
AUTO_DECISION_MAX_PRIORITY = os.getenv("AUTO_DECISION_MAX_PRIORITY", "P2").upper()
AUTO_DECISION_UNDO_WINDOW  = int(os.getenv("AUTO_DECISION_UNDO_WINDOW_MIN", "60"))

# P0/P1 are higher-stakes than P2/P3 — bot only auto-creates priorities >= MAX_PRIORITY.
# Rank: lower = more urgent/important. P2 (rank 2) and P3 (rank 3) eligible when max=P2.
_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _is_auto_eligible(routed: dict) -> bool:
    """Return True iff a routed task qualifies for auto-creation (no manager click)."""
    if not routed.get("is_task"):
        return False
    if not routed.get("assignee_name"):
        return False
    if float(routed.get("assignee_confidence", 0)) < AUTO_DECISION_THRESHOLD:
        return False
    pri = routed.get("priority", "P3")
    max_rank = _PRIORITY_RANK.get(AUTO_DECISION_MAX_PRIORITY, 2)
    if _PRIORITY_RANK.get(pri, 3) < max_rank:
        return False  # P0/P1 always need confirm
    return True

# ─── UI constants ─────────────────────────────────────────────────────────────

# Legacy emoji map — chỉ dùng trong _fmt_task (list view)
# Các message quan trọng đã chuyển sang templates.py
P_EMOJI = {"P0": "■", "P1": "▪", "P2": "▫", "P3": "□"}
CAT_EMOJI = {
    "fill_rate": "◈", "supply": "◈", "retention": "◈",
    "b2b": "◈", "expansion": "◈", "cost": "◈", "tech": "◈",
    "ops": "◈", "report": "◈", "meeting": "◈",
    "vendor": "◈", "admin": "◈", "data": "◈",
    "other": "◈",
}

EMPLOYEE_KEYBOARD = ReplyKeyboardMarkup(
    [["▸ Task của tôi", "▸ Hôm nay"], ["▸ Thống kê"]],
    resize_keyboard=True,
    input_field_placeholder="Forward tin nhắn · /add · /done <id>",
)

MANAGER_KEYBOARD = ReplyKeyboardMarkup(
    [["▸ Team", "▸ Task của tôi"], ["▸ Giao việc AI", "▸ Thống kê"]],
    resize_keyboard=True,
    input_field_placeholder="Forward tin nhắn để giao · /assign · /ask",
)


def _get_keyboard(user: dict) -> ReplyKeyboardMarkup:
    if can_see_team(user):
        return MANAGER_KEYBOARD
    return EMPLOYEE_KEYBOARD


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _deadline_str(deadline_iso: str | None) -> str:
    """Return compact deadline string with urgency indicator."""
    if not deadline_iso:
        return ""
    try:
        dl = datetime.fromisoformat(deadline_iso).replace(tzinfo=None)
        delta = dl - datetime.now()
        secs = delta.total_seconds()
        if secs < 0:
            days_late = abs(delta.days)
            hrs_late = abs(secs) / 3600
            return f"‼ trễ {days_late}n" if days_late >= 1 else f"‼ trễ {hrs_late:.0f}h"
        elif delta.days == 0:
            hrs = secs / 3600
            return f"⏰ còn {hrs:.0f}h" if hrs < 6 else f"hôm nay {dl.strftime('%H:%M')}"
        elif delta.days == 1:
            return f"ngày mai {dl.strftime('%H:%M')}"
        elif delta.days <= 4:
            return f"còn {delta.days}n ({dl.strftime('%d/%m')})"
        else:
            return dl.strftime('%d/%m')
    except (ValueError, TypeError):
        return ""


def _fmt_task(task: dict, show_assignee: bool = False) -> str:
    """Compact single-line format for lists — delegates to templates."""
    return tpl.fmt_task_line(task, show_assignee=show_assignee)


def _fmt_task_card(task: dict, show_assignee: bool = True) -> str:
    """Rich card — delegates to templates (used for task notifications)."""
    return tpl.msg_task_new(task, assigned_by_name="")


def _task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Done",  callback_data=f"done:{task_id}"),
            InlineKeyboardButton("◷ 2h",   callback_data=f"snooze:{task_id}:2h"),
            InlineKeyboardButton("◷ 1d",   callback_data=f"snooze:{task_id}:1d"),
            InlineKeyboardButton("✕ Drop", callback_data=f"cancel:{task_id}"),
        ],
        [InlineKeyboardButton("🎓 Hướng dẫn chi tiết", callback_data=f"coach:{task_id}")],
    ])


def _duration_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("<30ph", callback_data=f"dur:{task_id}:20"),
            InlineKeyboardButton("1-2h", callback_data=f"dur:{task_id}:90"),
            InlineKeyboardButton("Cả ngày", callback_data=f"dur:{task_id}:480"),
        ],
        [InlineKeyboardButton("Bỏ qua", callback_data=f"dur:{task_id}:0")],
    ])


def _assignee_keyboard(users: list[dict], task_key: str) -> InlineKeyboardMarkup:
    """Build inline keyboard to pick assignee, max 2 per row."""
    buttons = []
    row = []
    for u in users[:10]:
        active = u.get("active_count", 0)
        label = f"{u['full_name']} ({active})"
        btn = InlineKeyboardButton(label, callback_data=f"pick:{u['telegram_id']}:{task_key}")
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def _is_expired(ts: datetime) -> bool:
    return (datetime.now() - ts).total_seconds() > DEADLINE_TTL


async def _notify_manager(app, text: str, parse_mode: str = "HTML"):
    """Send a message to manager."""
    try:
        await app.bot.send_message(
            chat_id=MANAGER_CHAT_ID, text=text, parse_mode=parse_mode
        )
    except Exception as e:
        logger.error(f"notify_manager failed: {e}")


async def _require_approved(update: Update) -> dict | None:
    """Return user dict if approved, else reply and return None."""
    uid = update.effective_user.id
    user = get_user(uid)
    if not user:
        await update.message.reply_text(
            "Bạn chưa đăng ký. Gõ /start để bắt đầu."
        )
        return None
    if not user["is_approved"]:
        await update.message.reply_text(
            "Tài khoản đang chờ Manager duyệt. Vui lòng đợi."
        )
        return None
    touch_user(uid)
    return user


# ─── Registration flow ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    tg_user = update.effective_user

    user = get_user(uid)
    if user and user["is_approved"]:
        kb = _get_keyboard(user)
        await update.message.reply_text(
            f"Chào {user['full_name']}! Bot đang hoạt động.",
            reply_markup=kb,
        )
        return

    if user and not user["is_approved"]:
        # Allow re-entering name while waiting for approval (typo fix)
        _pending_name[uid] = True
        await update.message.reply_text(
            f"Tài khoản <b>{user['full_name']}</b> đang chờ duyệt.\n\n"
            "Nếu bạn nhập sai tên, gõ <b>họ tên đầy đủ</b> lại để cập nhật:",
            parse_mode="HTML",
        )
        return

    # New user — auto-register manager if chat_id matches env
    if uid == MANAGER_CHAT_ID:
        username = tg_user.username or ""
        full_name = tg_user.full_name or "Manager"
        register_user(uid, username, full_name)
        approve_user(uid)
        set_user_role(uid, MANAGER)
        await update.message.reply_text(
            f"Chào anh/chị <b>{full_name}</b>! Đã xác nhận Manager.\n\n"
            "Dùng /help để xem hướng dẫn.",
            parse_mode="HTML",
            reply_markup=MANAGER_KEYBOARD,
        )
        return

    # New employee — ask for name
    _pending_name[uid] = True
    await update.message.reply_text(
        "Chào bạn! Bot quản lý task của team Ahamove Truck Ops.\n\n"
        "Vui lòng nhập <b>họ tên đầy đủ</b> của bạn:",
        parse_mode="HTML",
    )


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle name input during registration. Returns True if consumed."""
    uid = update.effective_user.id
    if uid not in _pending_name:
        return False

    full_name = update.message.text.strip()
    if len(full_name) < 2:
        await update.message.reply_text("Tên quá ngắn. Vui lòng nhập lại họ tên đầy đủ:")
        return True

    _pending_name.pop(uid)
    tg_user = update.effective_user
    username = tg_user.username or ""

    # ── Pre-seeded account claim ──────────────────────────────────────────
    # Check if this name matches a pre-seeded team member record.
    # If so, "claim" it: swap placeholder ID → real Telegram ID, skip approval.
    try:
        claimed = claim_preseeded_user(uid, username, full_name)
    except Exception as e:
        logger.error(f"claim_preseeded_user failed for {uid}: {e}", exc_info=True)
        claimed = None
    if claimed:
        role  = claimed.get("role", "employee")
        team  = claimed.get("team") or ""
        grade = claimed.get("grade") or ""
        kb    = _get_keyboard(claimed)
        team_str  = f" · {team}" if team else ""
        grade_str = f" ({grade})" if grade else ""
        await update.message.reply_text(
            f"Xin chào <b>{claimed['full_name']}</b>{grade_str}! ✅\n"
            f"Tài khoản đã được xác nhận tự động{team_str}.\n\n"
            "Gõ /help để xem các lệnh, hoặc forward tin nhắn để tạo task.",
            parse_mode="HTML",
            reply_markup=kb,
        )
        # Notify manager of claim (info only, no approval needed)
        uname_str = f" (@{username})" if username else ""
        await _notify_manager(
            context.application,
            f"✅ <b>{claimed['full_name']}</b>{uname_str} đã kích hoạt tài khoản "
            f"({team}{grade_str}).\nID: <code>{uid}</code>",
        )
        return True
    # ── End claim flow ────────────────────────────────────────────────────

    registered = register_user(uid, username, full_name)
    if not registered:
        # Already exists — try claim flow again first, else update the name
        # (user might be re-typing because they realized name was wrong)
        from store import update_user_name
        try:
            update_user_name(uid, full_name)
        except Exception:
            pass
        await update.message.reply_text(
            f"Đã cập nhật tên: <b>{full_name}</b>\n\n"
            "Đang chờ Manager duyệt.",
            parse_mode="HTML",
        )
        # Re-notify manager with new name
        try:
            approve_kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✓ Duyệt", callback_data=f"approve:{uid}"),
                InlineKeyboardButton("✕ Từ chối", callback_data=f"reject:{uid}"),
            ]])
            uname_str = f" (@{username})" if username else ""
            await context.application.bot.send_message(
                chat_id=MANAGER_CHAT_ID,
                text=f"✏️ <b>Đã cập nhật tên:</b> {full_name}{uname_str}\nID: <code>{uid}</code>\n\nDuyệt?",
                parse_mode="HTML",
                reply_markup=approve_kb,
            )
        except Exception:
            pass
        return True

    await update.message.reply_text(
        f"Đã ghi nhận: <b>{full_name}</b>\n\n"
        "Vui lòng đợi Manager duyệt tài khoản. "
        "Bot sẽ thông báo khi được duyệt.\n\n"
        "<i>Nhập sai tên? Gõ /start để nhập lại.</i>",
        parse_mode="HTML",
    )

    # Notify manager
    approve_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Duyệt", callback_data=f"approve:{uid}"),
        InlineKeyboardButton("✕ Từ chối", callback_data=f"reject:{uid}"),
    ]])
    uname_str = f" (@{username})" if username else ""
    try:
        await context.application.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=f"👤 <b>Đăng ký mới:</b> {full_name}{uname_str}\nID: <code>{uid}</code>\n\nDuyệt?",
            parse_mode="HTML",
            reply_markup=approve_kb,
        )
    except Exception as e:
        logger.error(f"Failed to notify manager of new registration: {e}")

    return True


# ─── Command Handlers ─────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    personal = (
        "<b>Task cá nhân:</b>\n"
        "• <code>/add &lt;mô tả&gt;</code> — tạo task cho bản thân\n"
        "• <code>/mytasks</code> — danh sách task của bạn\n"
        "• <code>/today</code> — task hôm nay + overdue\n"
        "• <code>/done &lt;id&gt;</code> — đánh dấu xong\n"
        "• <code>/snooze &lt;id&gt; 2h|1d</code> — hoãn lại\n"
        "• <code>/cancel &lt;id&gt;</code> — huỷ task\n"
        "• <code>/stats</code> — thống kê tuần này\n"
        "• <code>/perf [ngày]</code> — hiệu suất của bạn (vd /perf 365)\n"
        "• <code>/coach &lt;id&gt;</code> — AI hướng dẫn cách làm task\n"
    )

    # Employee: can /assign upward to manager (request task)
    if user.get("role") == EMPLOYEE:
        personal += (
            "\n<b>Gửi yêu cầu lên sếp:</b>\n"
            "• <code>/assign &lt;mô tả&gt;</code> — gửi task lên Manager (request)\n"
            "• <code>/assign @manager &lt;mô tả&gt;</code> — chỉ định Manager/TL cụ thể\n"
        )

    manager_cmds = ""
    if can_see_team(user):
        manager_cmds = (
            "\n<b>Team (Manager/TL):</b>\n"
            "• <code>/assign @user &lt;mô tả&gt;</code> — giao task cho người khác\n"
            "• <code>/team</code> — dashboard toàn team\n"
            "• <code>/pending</code> — task chưa được nhận\n"
            "• <code>/perf @user [ngày]</code> — hiệu suất 1 thành viên\n"
        )
    if is_manager(user):
        manager_cmds += (
            "• <code>/approve &lt;id&gt;</code> — duyệt user mới\n"
            "• <code>/users</code> — danh sách team\n"
            "• <code>/setrole @user &lt;role&gt; [team]</code> — cấp quyền\n"
        )

    await update.message.reply_text(
        "📖 <b>Hướng dẫn sử dụng</b>\n\n"
        + personal + manager_cmds +
        "\n<b>Tạo task nhanh:</b> Forward tin nhắn bất kỳ vào đây → bot tự classify.",
        parse_mode="HTML",
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a task for yourself."""
    user = await _require_approved(update)
    if not user:
        return

    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Cú pháp: <code>/add &lt;mô tả task&gt;</code>\n"
            "Ví dụ: <code>/add Gửi báo cáo tuần trước 5pm</code>",
            parse_mode="HTML",
        )
        return

    # Use full route_task (team context) instead of basic classify
    result = await _ai(route_task, text)
    uid = user["telegram_id"]

    # High-confidence assignee detected → suggest re-routing to that person
    assignee_conf = result.get("assignee_confidence", 0)
    detected_name = result.get("assignee_name")
    if assignee_conf >= 0.78 and detected_name and can_assign(user):
        # Store in pending_confirm for manager to confirm or self-keep
        _pending_confirm[uid] = {"task_text": text, "routed": result, "ts": datetime.now()}
        # AI route card + [Assign] [Giữ] buttons
        await update.message.reply_text(
            tpl.msg_ai_route_card(result),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"● Giao {detected_name.split()[-1]}", callback_data="confirm_assign"),
                InlineKeyboardButton("○ Giữ cho mình", callback_data="self_keep"),
            ]]),
        )
        return

    # Create for self
    task_id = add_task(
        raw_message=text,
        summary=result.get("summary", text[:100]),
        assignee_id=uid,
        assigned_by=uid,
        team=user.get("team"),
        source="manual",
        sender=user["full_name"],
        deadline=result.get("deadline_iso"),
        deadline_confidence=result.get("deadline_confidence"),
        priority=result.get("priority", "P3"),
        category=result.get("category", "other"),
        estimated_minutes=result.get("estimated_minutes", 30),
        classifier_meta=result,
        visibility="private" if not can_see_team(user) else "team",
    )
    _last_task[uid] = task_id

    adhoc = get_adhoc_ratio_this_week(uid)
    msg = tpl.msg_task_created(
        task_id, result, text,
        assignee_name=user["full_name"].split()[0],
        is_self=True,
        adhoc_ratio=adhoc,
    )
    if not result.get("deadline_iso"):
        _pending_deadline[update.effective_chat.id] = (task_id, datetime.now())
        msg += "\n\n⏰ <i>Deadline? Gõ T6 17h, mai 9h, hoặc /skip</i>"

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=_task_keyboard(task_id))
    log_action(uid, "add_task", "task", task_id, result.get("summary", ""))


async def cmd_mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    tasks = list_user_tasks(user["telegram_id"], status="pending", limit=30)
    if not tasks:
        await update.message.reply_text(
            tpl.msg_mytasks(user["full_name"], []), parse_mode="HTML"
        )
        return

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🎯 Làm ngay", callback_data="now"),
        InlineKeyboardButton("⊡ Hôm nay", callback_data="show_today"),
    ]])
    await update.message.reply_text(
        tpl.msg_mytasks(user["full_name"], tasks),
        parse_mode="HTML",
        reply_markup=kb,
    )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    tasks = list_user_today_tasks(user["telegram_id"])
    overdue = [t for t in tasks if t.get("deadline") and
               datetime.fromisoformat(t["deadline"]).replace(tzinfo=None) < datetime.now()]
    today_tasks = [t for t in tasks if t not in overdue]

    msg = tpl.msg_today(user["full_name"], overdue, today_tasks)
    await update.message.reply_text(msg, parse_mode="HTML")


async def _compute_now(user: dict) -> tuple[str, InlineKeyboardMarkup | None, int | None]:
    """Core /now logic — returns (message_text, keyboard, primary_task_id).

    Shared by the /now command and the inline 🎯 Làm ngay button so both render
    identically. primary_task_id is None when there's nothing to recommend."""
    pending = list_user_tasks(user["telegram_id"], status="pending", limit=20)
    if not pending:
        return (
            "○ Queue sạch — không có task nào pending.\n"
            "Gõ /today để xem task hôm nay, hoặc /mytasks tất cả.",
            None, None,
        )

    rec = await _ai(recommend_now, pending, user_name=user["full_name"].split()[0])
    if not rec.get("task_id"):
        return (
            tpl.msg_error("AI không chọn được task", rec.get("reason", "Thử /today để xem list.")),
            None, None,
        )

    by_id = {t["id"]: t for t in pending}
    primary = by_id.get(rec["task_id"]) or pending[0]  # fall back if AI hallucinated id
    alt = by_id.get(rec.get("alternative_task_id")) if rec.get("alternative_task_id") else None

    msg = tpl.msg_now_recommendation(
        primary_task=primary,
        primary_reason=rec.get("reason", ""),
        alternative_task=alt,
        alternative_reason=rec.get("alternative_reason"),
    )
    return msg, _task_keyboard(primary["id"]), primary["id"]


async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    AI picks THE single task user should do right now from their pending list.
    Bám vào: deadline urgency, OKR weight, priority, time-of-day fit.
    """
    user = await _require_approved(update)
    if not user:
        return

    await update.message.reply_chat_action("typing")
    msg, kb, task_id = await _compute_now(user)
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)
    if task_id:
        log_action(user["telegram_id"], "now", "task", task_id)


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    if not context.args:
        await update.message.reply_text("Cú pháp: <code>/done &lt;id&gt;</code>", parse_mode="HTML")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID phải là số.")
        return

    task = get_task(task_id)
    if not task or not can_see_task(user, task):
        await update.message.reply_text(f"Không tìm thấy task #{task_id}.")
        return

    if mark_done(task_id):
        msg = tpl.msg_done_quick(task_id, task.get("summary", ""))
        await update.message.reply_text(msg, parse_mode="HTML",
                                        reply_markup=_duration_keyboard(task_id))
        log_action(user["telegram_id"], "done", "task", task_id)

        # Notify assigner if different from doer
        if task.get("assigned_by") and task["assigned_by"] != user["telegram_id"]:
            try:
                notify = tpl.msg_confirm(
                    "Task hoàn thành",
                    f"<code>{user['full_name']}</code> vừa xong:\n<i>{task['summary'][:70]}</i>",
                )
                await context.bot.send_message(
                    chat_id=task["assigned_by"],
                    text=notify,
                    parse_mode="HTML",
                )
            except Exception:
                pass
    else:
        await update.message.reply_text(
            tpl.msg_error("Không thể đánh dấu xong",
                          f"Task #{task_id} không tồn tại hoặc đã xong."),
            parse_mode="HTML",
        )


async def cmd_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    if len(context.args) < 2:
        await update.message.reply_text("Cú pháp: <code>/snooze &lt;id&gt; 2h|1d</code>", parse_mode="HTML")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID phải là số.")
        return

    delta_str = context.args[1].lower()
    now = datetime.now()
    if delta_str.endswith("h"):
        until = now + timedelta(hours=float(delta_str[:-1]))
    elif delta_str.endswith("d"):
        until = now + timedelta(days=float(delta_str[:-1]))
    else:
        await update.message.reply_text("Dùng <code>2h</code>, <code>4h</code>, <code>1d</code>, <code>2d</code>.", parse_mode="HTML")
        return

    task = get_task(task_id)
    if not task or not can_see_task(user, task):
        await update.message.reply_text(f"Không tìm thấy task #{task_id}.")
        return

    snooze_task(task_id, until.isoformat())
    await update.message.reply_text(
        tpl.msg_confirm(
            "Đã hoãn",
            f"<code>#{task_id}</code> {task.get('summary','')[:60]}\n"
            f"◷ Đến {until.strftime('%d/%m %H:%M')}",
            next_hint=f"<code>/done {task_id}</code> khi xong sớm hơn",
        ),
        parse_mode="HTML",
    )
    increment_defer(task_id)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    if not context.args:
        await update.message.reply_text("Cú pháp: <code>/cancel &lt;id&gt;</code>", parse_mode="HTML")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID phải là số.")
        return

    task = get_task(task_id)
    if not task or not can_see_task(user, task):
        await update.message.reply_text(f"Không tìm thấy task #{task_id}.")
        return

    if cancel_task(task_id):
        await update.message.reply_text(
            tpl.msg_confirm("Đã huỷ", f"<code>#{task_id}</code> {task.get('summary','')[:60]}"),
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            tpl.msg_error("Không thể huỷ", f"Task #{task_id} không tồn tại hoặc đã xong."),
            parse_mode="HTML",
        )


async def cmd_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Layer 2 coaching: `/coach <task_id>` — gen hướng dẫn chi tiết
    (why_matters, steps, watch_out, tips, contacts) cho assignee.
    """
    user = await _require_approved(update)
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Cú pháp: <code>/coach &lt;task_id&gt;</code>\nVD: <code>/coach 45</code>",
            parse_mode="HTML",
        )
        return

    try:
        task_id = int(context.args[0].lstrip("#"))
    except ValueError:
        await update.message.reply_text("Task ID phải là số.")
        return

    task = get_task(task_id)
    if not task:
        await update.message.reply_text(f"Task #{task_id} không tồn tại.")
        return
    if not can_see_task(user, task):
        await update.message.reply_text("Bạn không có quyền xem task này.")
        return

    await update.message.reply_chat_action("typing")

    import json as _j
    meta = task.get("classifier_meta") or {}
    if isinstance(meta, str):
        try:
            meta = _j.loads(meta)
        except Exception:
            meta = {}

    coach = await _ai(
        coach_task,
        task_summary=task.get("summary", ""),
        okr_ref=meta.get("okr_ref") if isinstance(meta, dict) else None,
        okr_action_id=meta.get("okr_action_id") if isinstance(meta, dict) else None,
        breakdown=meta.get("breakdown") if isinstance(meta, dict) else None,
        priority=task.get("priority", "P2"),
        deadline_iso=task.get("deadline"),
        assignee_name=user["full_name"],
        raw_message=task.get("raw_message"),
    )

    msg = tpl.msg_coach_detail(task, coach)
    if len(msg) > 4000:
        msg = msg[:3900] + "\n…(rút gọn)"
    await update.message.reply_text(
        msg, parse_mode="HTML", reply_markup=_task_keyboard(task_id)
    )
    log_action(user["telegram_id"], "coach", "task", task_id)


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manager rút lại 1 task bot tự tạo (source='ai_auto') trong cửa sổ UNDO_WINDOW phút.
    Cú pháp: /undo <task_id>
    """
    user = await _require_approved(update)
    if not user or not can_assign(user):
        if user:
            await update.message.reply_text("Chỉ Manager / Team Lead mới dùng được /undo.")
        return

    if not context.args:
        await update.message.reply_text("Cú pháp: <code>/undo &lt;task_id&gt;</code>", parse_mode="HTML")
        return

    try:
        task_id = int(context.args[0].lstrip("#"))
    except ValueError:
        await update.message.reply_text("Task ID phải là số.")
        return

    task = get_task(task_id)
    if not task:
        await update.message.reply_text(f"Task #{task_id} không tồn tại.")
        return

    # Verify undo window: prefer in-memory _auto_created, fall back to DB created_at
    created_at = _auto_created.get(task_id)
    if not created_at:
        try:
            ts_str = task.get("created_at") or ""
            created_at = datetime.fromisoformat(ts_str.replace("Z", "")).replace(tzinfo=None)
        except (ValueError, TypeError):
            created_at = None

    if created_at:
        elapsed_min = (datetime.now() - created_at.replace(tzinfo=None)).total_seconds() / 60
        if elapsed_min > AUTO_DECISION_UNDO_WINDOW:
            await update.message.reply_text(
                f"⏰ Task #{task_id} đã quá cửa sổ undo "
                f"({AUTO_DECISION_UNDO_WINDOW} phút, đã trôi {int(elapsed_min)}p).\n"
                f"Dùng <code>/cancel {task_id}</code> để huỷ hẳn nếu cần.",
                parse_mode="HTML",
            )
            return

    # Only allow undo on tasks bot created (source='ai_auto') or via assigner path
    if task.get("source") not in ("ai_auto", "ai_route", "assign_pick", "assign_cmd"):
        await update.message.reply_text(
            f"Task #{task_id} không phải do bot tự tạo — dùng <code>/cancel {task_id}</code> thay.",
            parse_mode="HTML",
        )
        return

    cancel_task(task_id)
    _auto_created.pop(task_id, None)
    log_action(user["telegram_id"], "undo", "task", task_id)

    await update.message.reply_text(
        tpl.msg_confirm("Đã undo", f"<code>#{task_id}</code> {task.get('summary','')[:60]}"),
        parse_mode="HTML",
    )

    # Notify assignee — they shouldn't keep working on this
    if task.get("assignee_id") and task["assignee_id"] != user["telegram_id"]:
        try:
            await context.bot.send_message(
                chat_id=task["assignee_id"],
                text=f"⏪ Manager đã rút lại task <code>#{task_id}</code> <i>{task.get('summary','')[:60]}</i> — không cần làm nữa.",
                parse_mode="HTML",
            )
        except Exception:
            pass


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    s = get_user_stats(user["telegram_id"])
    top = get_top_tasks_for_user(user["telegram_id"], limit=3)
    msg = tpl.msg_my_stats(
        name=user["full_name"],
        done_week=s.get("done_week", 0),
        pending=s.get("pending", 0),
        overdue=s.get("overdue", 0),
        top_tasks=top,
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_perf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /perf [@username] [days] — báo cáo hiệu suất dài hạn để đánh giá.
      /perf            → của chính mình, 30 ngày
      /perf 365        → của mình, cả năm
      /perf @huy 90    → của Huy, 90 ngày (chỉ Manager/TL xem người khác)
    """
    user = await _require_approved(update)
    if not user:
        return

    args = list(context.args) if context.args else []
    target = user
    days = 30

    # Tách @username và số ngày khỏi args (thứ tự bất kỳ)
    username = None
    for a in args:
        if a.startswith("@"):
            username = a[1:]
        elif a.isdigit():
            days = max(1, min(int(a), 1095))  # cap 3 năm

    if username:
        if not can_see_team(user):
            await update.message.reply_text(
                "Chỉ Manager/TL mới xem hiệu suất người khác. "
                "Gõ <code>/perf</code> để xem của bạn.",
                parse_mode="HTML",
            )
            return
        from store import get_user_by_username
        target = get_user_by_username(username)
        if not target:
            await update.message.reply_text(
                f"Không tìm thấy @{username}. Gõ /users để xem danh sách."
            )
            return

    perf = get_member_performance(target["telegram_id"], days=days)
    await update.message.reply_text(
        tpl.msg_member_performance(target["full_name"], perf),
        parse_mode="HTML",
    )
    log_action(user["telegram_id"], "perf", "user", target["telegram_id"], f"{days}d")


async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending deadline prompt."""
    uid = update.effective_chat.id
    if uid in _pending_deadline:
        _pending_deadline.pop(uid)
        await update.message.reply_text("Bỏ qua deadline. Task đã lưu không có deadline.")
    else:
        await update.message.reply_text("Không có deadline nào đang chờ.")


# ─── Manager / TL commands ────────────────────────────────────────────────────

async def cmd_assign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /assign @username <task description> [due:<date>] [P1]
    If no @username, start guided flow.
    """
    user = await _require_approved(update)
    if not user or not can_assign(user):
        if user:
            await update.message.reply_text("Bạn không có quyền giao task.")
        return

    args_text = " ".join(context.args) if context.args else ""

    # Check if @username is provided
    match = re.match(r"@(\S+)\s+(.*)", args_text.strip())
    if match:
        username, task_text = match.group(1), match.group(2).strip()
        assignee = None
        # Try to find by username in DB
        from store import get_user_by_username
        assignee = get_user_by_username(username)
        if not assignee:
            await update.message.reply_text(
                f"Không tìm thấy @{username} trong hệ thống.\n"
                "Dùng /users để xem danh sách."
            )
            return
        # Permission: employee can only assign upward (to manager/TL) or self
        from roles import can_assign_to
        if not can_assign_to(user, assignee):
            await update.message.reply_text(
                "Nhân viên chỉ có thể giao task lên cho Manager/TL (request) "
                "hoặc cho chính mình. Để giao cho đồng nghiệp, hãy nhờ sếp."
            )
            return
        await _do_assign_with_text(update, context, user, assignee, task_text)
        return

    # No @username — start guided flow
    if not args_text:
        # Totally guided: ask for task description first
        _pending_assign_who[update.effective_chat.id] = {"waiting_desc": True}
        await update.message.reply_text(
            "Nhập mô tả task cần giao:"
        )
        return

    # Has description but no assignee — try smart route first
    await update.message.reply_text("⏳ Đang phân tích...")
    routed = await _ai(route_task, args_text)

    # Employee path: auto-route to their manager (upward request) — skip picker
    if user.get("role") == EMPLOYEE:
        from store import get_user as _get_user
        mgr_id = user.get("reports_to") or MANAGER_CHAT_ID
        manager = _get_user(mgr_id) if mgr_id else None
        if not manager:
            await update.message.reply_text(
                "Chưa biết Manager của bạn là ai. Liên hệ admin để cấu hình."
            )
            return
        await _do_assign_with_text(update, context, user, manager, args_text)
        return

    if routed.get("assignee_confidence", 0) >= 0.75 and routed.get("assignee_name"):
        await _show_confirm_card(update, context, user, args_text, routed)
    else:
        await _show_assignee_picker(update, context, user, args_text, routed)


async def _do_assign_with_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    assigner: dict, assignee: dict, task_text: str,
):
    """Create task and notify assignee directly."""
    result = await _ai(route_task, task_text)
    task_id = add_task(
        raw_message=task_text,
        summary=result.get("summary", task_text[:100]),
        assignee_id=assignee["telegram_id"],
        assigned_by=assigner["telegram_id"],
        team=assignee.get("team"),
        source="assign_cmd",
        sender=assigner["full_name"],
        deadline=result.get("deadline_iso"),
        deadline_confidence=result.get("deadline_confidence"),
        priority=result.get("priority", "P2"),
        category=result.get("category", "other"),
        estimated_minutes=result.get("estimated_minutes", 30),
        classifier_meta=result,
    )

    # Confirm to assigner — rich card
    await update.message.reply_text(
        tpl.msg_assign_confirm(task_id, assignee["full_name"], result),
        parse_mode="HTML",
    )

    # DM to assignee — task_new card
    accept_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Nhận việc", callback_data=f"accept:{task_id}"),
            InlineKeyboardButton("✗ Từ chối", callback_data=f"decline:{task_id}"),
        ],
        [InlineKeyboardButton("🎓 Hướng dẫn chi tiết", callback_data=f"coach:{task_id}")],
    ])
    task_dict = {
        "id":       task_id,
        "summary":  result.get("summary", task_text[:100]),
        "priority": result.get("priority", "P2"),
        "deadline": result.get("deadline_iso"),
        "category": result.get("category", "other"),
        "classifier_meta": result,
    }
    try:
        await context.bot.send_message(
            chat_id=assignee["telegram_id"],
            text=tpl.msg_task_new(task_dict, assigned_by_name=assigner["full_name"]),
            parse_mode="HTML",
            reply_markup=accept_kb,
        )
    except Exception as e:
        logger.error(f"Failed to DM assignee {assignee['telegram_id']}: {e}")

    log_action(assigner["telegram_id"], "assign", "task", task_id,
               f"→ {assignee['full_name']}")


async def _show_confirm_card(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    assigner: dict, task_text: str, routed: dict,
):
    """
    Show AI-routed task confirm card when assignee detected with high confidence.
    Manager taps [✅ Assign] to confirm or [✏️ Đổi người] to open picker.
    """
    uid = update.effective_chat.id
    _pending_confirm[uid] = {
        "task_text": task_text,
        "routed": routed,
        "ts": datetime.now(),
    }
    logger.info(f"_show_confirm_card stored _pending_confirm[{uid}] for chat={update.effective_chat.id}")

    assignee_name = routed.get("assignee_name", "?")

    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"● Assign {assignee_name.split()[-1]}",
                                 callback_data="confirm_assign"),
            InlineKeyboardButton("↗ Đổi người", callback_data="change_assignee"),
        ],
        [InlineKeyboardButton("⊘ Huỷ", callback_data="cancel_assign")],
    ])

    await update.message.reply_text(
        tpl.msg_ai_route_card(routed, assigner_name=assigner.get("full_name", "")),
        parse_mode="HTML",
        reply_markup=confirm_kb,
    )


async def _show_assignee_picker(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    assigner: dict, task_text: str, result: dict,
):
    """Show team members as inline buttons to pick assignee."""
    team_members = list_team_by_person()
    # Exclude manager and unapproved
    team_members = [u for u in team_members
                    if u["telegram_id"] != assigner["telegram_id"]]

    if not team_members:
        await update.message.reply_text(
            "Team chưa có thành viên. Dùng /users để kiểm tra."
        )
        return

    # Store pending state — use truncated task text as key
    task_key = str(hash(task_text))[:8]
    _pending_assign_who[update.effective_chat.id] = {
        "task_text": task_text,
        "result": result,
        "ts": datetime.now(),
    }

    p       = result.get("priority", "P2")
    icon    = tpl.PRIORITY_ICON.get(p, "□")
    summary = result.get("summary", task_text[:80])

    msg = (
        f"{icon} {p} — {summary}\n"
        f"{tpl.DIV_LIGHT}\n"
        f"Giao cho ai?"
    )

    # Build assignee buttons showing workload
    buttons = []
    row = []
    for u in team_members[:8]:
        overdue = u.get("overdue_count", 0)
        active = u.get("active_count", 0)
        suffix = " ‼" if overdue > 0 else ""
        label = f"{u['full_name']} ({active}){suffix}"
        btn = InlineKeyboardButton(
            label, callback_data=f"pick:{u['telegram_id']}"
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await update.message.reply_text(
        msg, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _auto_create_and_assign(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    assigner: dict, task_text: str, routed: dict,
) -> bool:
    """
    Bot tự tạo task + DM cho assignee. Manager nhận 1-line confirmation kèm undo button.
    Returns True if successfully auto-created; False if fell back (caller should CONFIRM).
    """
    # Resolve assignee — by email first, then by name (route_task gives both)
    assignee = None
    if routed.get("assignee_email"):
        assignee = get_user_by_email(routed["assignee_email"])
    if not assignee and routed.get("assignee_name"):
        assignee = get_user_by_name(routed["assignee_name"])
    if not assignee:
        # Can't resolve user in DB → caller will fall back to confirm card
        return False

    # Workload guard: don't silently auto-dump onto someone already drowning.
    # If the assignee has >2 overdue tasks, fall back to confirm so the manager
    # sees the load and can rebalance instead of auto-creating.
    try:
        overdue_n = len(get_overdue_tasks_for_user(assignee["telegram_id"]))
    except Exception:
        overdue_n = 0
    if overdue_n > 2:
        logger.info(
            f"auto-dispatch skipped: {assignee['full_name']} has {overdue_n} overdue → confirm"
        )
        return False

    task_id = add_task(
        raw_message=task_text,
        summary=routed.get("summary", task_text[:100]),
        assignee_id=assignee["telegram_id"],
        assigned_by=assigner["telegram_id"],
        team=assignee.get("team"),
        source="ai_auto",              # flagged for daily digest + /undo whitelist
        sender=assigner["full_name"],
        deadline=routed.get("deadline_iso"),
        priority=routed.get("priority", "P2"),
        category=routed.get("category", "other"),
        estimated_minutes=routed.get("estimated_minutes", 30),
        classifier_meta=routed,
    )

    _auto_created[task_id] = datetime.now()
    log_action(assigner["telegram_id"], "ai_auto", "task", task_id,
               f"→ {assignee['full_name']} (conf={routed.get('assignee_confidence',0):.2f})")

    # 1-line confirmation to manager + undo/reassign buttons
    mgr_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"↶ Undo", callback_data=f"undo:{task_id}"),
        InlineKeyboardButton(f"↗ Đổi người", callback_data=f"digest_reassign:{task_id}"),
    ]])
    await update.message.reply_text(
        tpl.msg_auto_assigned(task_id, assignee["full_name"], routed, AUTO_DECISION_UNDO_WINDOW),
        parse_mode="HTML",
        reply_markup=mgr_kb,
    )

    # DM to assignee (same shape as confirm-flow)
    accept_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Nhận việc", callback_data=f"accept:{task_id}"),
            InlineKeyboardButton("✗ Từ chối",  callback_data=f"decline:{task_id}"),
        ],
        [InlineKeyboardButton("🎓 Hướng dẫn chi tiết", callback_data=f"coach:{task_id}")],
    ])
    task_dict = {
        "id":              task_id,
        "summary":         routed.get("summary", task_text[:100]),
        "priority":        routed.get("priority", "P2"),
        "deadline":        routed.get("deadline_iso"),
        "category":        routed.get("category", "other"),
        "classifier_meta": routed,
    }
    try:
        await context.bot.send_message(
            chat_id=assignee["telegram_id"],
            text=tpl.msg_task_new(task_dict, assigned_by_name=assigner["full_name"]),
            parse_mode="HTML",
            reply_markup=accept_kb,
        )
    except Exception as e:
        logger.error(f"Auto-assign DM to {assignee['telegram_id']} failed: {e}")

    return True


async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manager/TL team dashboard."""
    user = await _require_approved(update)
    if not user or not can_see_team(user):
        if user:
            await update.message.reply_text("Chỉ Manager và Team Lead mới xem được team dashboard.")
        return

    members   = list_team_by_person()
    stats     = get_team_stats()
    all_tasks = list_team_tasks(statuses=["pending"])

    cat_counts: dict[str, int] = {}
    for t in all_tasks:
        cat = t.get("category", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    p0_tasks = [t for t in all_tasks if t.get("priority") == "P0"]

    await update.message.reply_text(
        tpl.msg_brief_team(stats=stats, members=members,
                           cat_counts=cat_counts, p0_tasks=p0_tasks,
                           all_tasks=all_tasks),
        parse_mode="HTML",
    )


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show unaccepted/unstarted assigned tasks."""
    user = await _require_approved(update)
    if not user or not can_assign(user):
        return

    tasks = list_team_tasks(statuses=["pending"])
    if not tasks:
        await update.message.reply_text("Không có task pending trong team.")
        return

    lines = [f"<b>Pending — team</b> ({len(tasks)} task)\n"]
    for t in tasks[:20]:
        lines.append(_fmt_task(t, show_assignee=True))

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manager approves pending users: /approve <telegram_id>"""
    user = await _require_approved(update)
    if not user or not can_approve_users(user):
        if user:
            await update.message.reply_text("Chỉ Manager mới approve được.")
        return

    if not context.args:
        pending = list_pending_approval()
        if not pending:
            await update.message.reply_text("Không có tài khoản nào chờ duyệt.")
            return
        lines = ["<b>Chờ duyệt:</b>\n"]
        for u in pending:
            uname = f" @{u['username']}" if u.get("username") else ""
            lines.append(f"• {u['full_name']}{uname} — <code>/approve {u['telegram_id']}</code>")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID không hợp lệ.")
        return

    if approve_user(target_id):
        target = get_user(target_id)
        name = target["full_name"] if target else str(target_id)
        await update.message.reply_text(f"✓ Đã duyệt tài khoản: <b>{name}</b>", parse_mode="HTML")
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✓ Tài khoản của bạn đã được duyệt!\n\nGõ /help để xem hướng dẫn.",
                reply_markup=EMPLOYEE_KEYBOARD,
            )
        except Exception:
            pass
        log_action(user["telegram_id"], "approve_user", "user", target_id)
    else:
        await update.message.reply_text("Không tìm thấy user này.")


async def cmd_debug_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dump all pending_actions rows for current user — diagnose 'Phiên hết hạn'."""
    user = await _require_approved(update)
    if not user:
        return
    uid = update.effective_chat.id
    from store import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT kind, expires_at, length(payload) as len "
            "FROM pending_actions WHERE uid = ?",
            (uid,),
        ).fetchall()
    if not rows:
        await update.message.reply_text(
            f"Không có pending state cho uid={uid}.\n"
            f"Effective chat id: <code>{update.effective_chat.id}</code>\n"
            f"Effective user id: <code>{update.effective_user.id}</code>",
            parse_mode="HTML",
        )
        return
    lines = [f"<b>Pending state cho uid={uid}</b>"]
    for r in rows:
        lines.append(f"• <code>{r['kind']}</code> · expires {r['expires_at']} · {r['len']}B")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all team members."""
    user = await _require_approved(update)
    if not user or not can_see_team(user):
        return

    members = list_users(approved_only=True)
    if not members:
        await update.message.reply_text("Team chưa có thành viên.")
        return

    lines = [f"<b>Team ({len(members)} người)</b>\n"]
    for m in members:
        role_str = ROLE_LABELS.get(m["role"], m["role"])
        uname = f" @{m['username']}" if m.get("username") else ""
        team_str = f" [{m['team']}]" if m.get("team") else ""
        lines.append(f"• {m['full_name']}{uname}{team_str} — {role_str}")

    pending = list_pending_approval()
    if pending:
        lines.append(f"\n⏳ <b>Chờ duyệt: {len(pending)} người</b> — /approve để duyệt")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_setrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /setrole @username <role> [team_name]
    role: manager | tl | employee
    """
    user = await _require_approved(update)
    if not user or not can_approve_users(user):
        if user:
            await update.message.reply_text("Chỉ Manager mới cấp quyền được.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Cú pháp: <code>/setrole @user &lt;manager|tl|employee&gt; [team]</code>\n"
            "Ví dụ: <code>/setrole @nam tl B2B_Vendor</code>",
            parse_mode="HTML",
        )
        return

    username = context.args[0].lstrip("@")
    role_input = context.args[1].lower()
    team_name = context.args[2] if len(context.args) > 2 else None

    role_map = {"manager": MANAGER, "tl": TEAM_LEAD, "team_lead": TEAM_LEAD,
                "employee": EMPLOYEE, "nv": EMPLOYEE}
    role = role_map.get(role_input)
    if not role:
        await update.message.reply_text(
            "Role không hợp lệ. Dùng: manager / tl / employee"
        )
        return

    from store import get_user_by_username
    target = get_user_by_username(username)
    if not target:
        await update.message.reply_text(f"Không tìm thấy @{username}.")
        return

    set_user_role(target["telegram_id"], role, team=team_name)
    role_label = ROLE_LABELS.get(role, role)
    await update.message.reply_text(
        f"✓ @{username} — {role_label}" + (f" [{team_name}]" if team_name else ""),
        parse_mode="HTML",
    )
    log_action(user["telegram_id"], "set_role", "user", target["telegram_id"],
               f"{role} team={team_name}")


# ─── Message handlers ─────────────────────────────────────────────────────────

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded messages and direct text."""
    # ── Registration flow MUST run before require_approved ────────────────
    # Unregistered users are not yet in the DB; they need to be able to type
    # their name as the second step of the /start flow. If we call
    # _require_approved first, they get blocked and can never finish registration.
    if await handle_name_input(update, context):
        return

    user = await _require_approved(update)
    if not user:
        return

    text = update.message.text or update.message.caption or ""
    if not text:
        return

    uid = update.effective_chat.id

    # Check pending deadline input
    # GUARD: only consume text as a deadline reply when it is short (≤ 6 words)
    # AND contains a date/time token.  Long/complex text is a new task — clear
    # the prompt and fall through so the task gets created normally.
    if uid in _pending_deadline:
        task_id_dl, ts_dl = _pending_deadline[uid]
        if _is_expired(ts_dl):
            _pending_deadline.pop(uid)
        elif _is_deadline_reply(text):
            deadline_data = await _ai(extract_deadline, text)
            if deadline_data.get("deadline_iso"):
                update_task_deadline(task_id_dl, deadline_data["deadline_iso"],
                                     deadline_data.get("confidence", "asked"))
                _pending_deadline.pop(uid)
                dl = datetime.fromisoformat(deadline_data["deadline_iso"])
                await update.message.reply_text(
                    f"✓ Deadline task #{task_id_dl}: <b>{dl.strftime('%d/%m %H:%M')}</b>",
                    parse_mode="HTML",
                )
                return
            # else: not parseable — leave prompt open, fall through
        else:
            # Text is too long/complex → user sent a new task, clear the prompt
            _pending_deadline.pop(uid)

    # Check pending assign description input (guided flow)
    if uid in _pending_assign_who and _pending_assign_who[uid].get("waiting_desc"):
        _routed_desc = await _ai(route_task, text)
        _pending_assign_who[uid] = {
            "task_text": text,
            "result": _routed_desc,
            "ts": datetime.now(),
        }
        # Show assignee picker
        state = _pending_assign_who[uid]
        await _show_assignee_picker(update, context, user, text, state["result"])
        return

    # Manager forwarding external message → AUTO / CONFIRM / PICKER (3-tier)
    if can_assign(user) and update.message.forward_origin:
        await update.message.reply_text("⏳ Đang phân tích...")
        routed = await _ai(route_task, text)
        if routed.get("is_task"):
            # Tier 1: AUTO — conf ≥ 0.85 + P2/P3 + assignee resolvable in DB
            if _is_auto_eligible(routed):
                if await _auto_create_and_assign(update, context, user, text, routed):
                    return  # successfully auto-created; otherwise fall through to confirm

            # Tier 2: CONFIRM — medium confidence OR P0/P1 (high stakes)
            if routed.get("assignee_confidence", 0) >= 0.75 and routed.get("assignee_name"):
                await _show_confirm_card(update, context, user, text, routed)
            else:
                # Tier 3: PICKER — manager chooses person
                _pending_assign_who[uid] = {
                    "task_text": text,
                    "result": routed,
                    "ts": datetime.now(),
                }
                await _show_assignee_picker(update, context, user, text, routed)
        else:
            await update.message.reply_text(
                "Không phát hiện task trong tin nhắn này.\n"
                "Dùng <code>/add &lt;mô tả&gt;</code> để tạo thủ công.",
                parse_mode="HTML",
            )
        return

    # Regular text — route_task (OKR-aware) then decide: self vs. assign flow
    result = await _ai(route_task, text)
    if result.get("is_task") and result.get("confidence", 0) >= 0.6:

        # ── Manager/TL direct-text assign ──────────────────────────────────
        # e.g. "giao task cho Khánh tìm vendor Long An"
        # Same 3-tier logic as forwarded messages, applied to direct typed text.
        a_conf = result.get("assignee_confidence", 0)
        a_name = result.get("assignee_name")
        if can_assign(user) and a_name and a_conf >= 0.65:
            # Tier 1: AUTO (≥0.85 + P2/P3 + resolvable in DB)
            if _is_auto_eligible(result):
                if await _auto_create_and_assign(update, context, user, text, result):
                    return
            # Tier 2: CONFIRM card
            if a_conf >= 0.75:
                await _show_confirm_card(update, context, user, text, result)
            else:
                # Tier 3: PICKER — low-confidence assignee
                _pending_assign_who[uid] = {
                    "task_text": text, "result": result, "ts": datetime.now(),
                }
                await _show_assignee_picker(update, context, user, text, result)
            return
        # ── End direct-text assign ─────────────────────────────────────────

        # Default: create task for self
        task_id = add_task(
            raw_message=text,
            summary=result["summary"],
            assignee_id=user["telegram_id"],
            assigned_by=user["telegram_id"],
            team=user.get("team"),
            source="message",
            deadline=result.get("deadline_iso"),
            deadline_confidence=result.get("deadline_confidence"),
            priority=result.get("priority", "P3"),
            category=result.get("category", "other"),
            estimated_minutes=result.get("estimated_minutes", 30),
            classifier_meta=result,
        )

        _last_task[uid] = task_id
        adhoc = get_adhoc_ratio_this_week(uid)
        msg = tpl.msg_task_created(
            task_id, result, text,
            assignee_name=user["full_name"].split()[0],
            is_self=True,
            adhoc_ratio=adhoc,
        )
        if not result.get("deadline_iso"):
            _pending_deadline[uid] = (task_id, datetime.now())
            msg += "\n\n⏰ <i>Deadline? Gõ T6 17h, mai 9h, hoặc /skip</i>"
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=_task_keyboard(task_id))

    elif result.get("is_task"):
        # Low confidence — ask confirmation.
        # Telegram caps callback_data at 64 bytes; stuffing text[:200] there (esp.
        # multi-byte Vietnamese) overflowed → button silently broke. Stash the full
        # text + classification in _pending_confirm and pass only a short token.
        _pending_confirm[uid] = {"task_text": text, "routed": result, "ts": datetime.now()}
        confirm_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("● Lưu task", callback_data="confirm_task"),
            InlineKeyboardButton("⊘ Bỏ qua", callback_data="ignore"),
        ]])
        await update.message.reply_text(
            f"◦ Đây có phải task không?\n{result.get('summary', text[:80])}",
            reply_markup=confirm_kb,
        )
    else:
        # Not a task — gentle hint instead of silence
        await update.message.reply_text(
            "○ Không hiểu lệnh này.\n"
            "· /add <mô tả> để tạo task\n"
            "· /assign @user <mô tả> để giao task\n"
            "· /today xem task hôm nay\n"
            "· /help xem tất cả lệnh"
        )



async def _send_brief(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: dict,
) -> None:
    """Team brief snapshot: member grid + category + P0."""
    members   = list_team_by_person()
    stats     = get_team_stats()
    all_tasks = list_team_tasks(statuses=["pending"])

    cat_counts: dict[str, int] = {}
    for t in all_tasks:
        cat = t.get("category", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    p0_tasks = [t for t in all_tasks if t.get("priority") == "P0"]

    text = tpl.msg_brief_team(
        stats=stats,
        members=members,
        cat_counts=cat_counts,
        p0_tasks=p0_tasks,
        all_tasks=all_tasks,
    )
    # msg_brief_team emits HTML (<b>/<code>) — without parse_mode the tags render literally.
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/brief — Team status brief (Manager/TL only)."""
    user = await _require_approved(update)
    if not user:
        return
    if not can_see_team(user):
        await update.message.reply_text("Brief chỉ dành cho Manager/TL.")
        return
    await _send_brief(update, context, user)


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /ask <câu hỏi> — Single-prompt AI query với live team context.
    Examples:
      /ask Vì sao FR HAN giảm tuần này?
      /ask Task #5 nên giao ai phù hợp nhất?
      /ask Tuần này ai đang overload?
      /ask OKR O1.1 đang thế nào?
    """
    user = await _require_approved(update)
    if not user:
        return
    if not can_see_team(user):
        await update.message.reply_text("Tính năng AI Ask dành cho Manager/TL.")
        return

    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text(
            "<b>Hỏi AI:</b>\n"
            "<code>/ask &lt;câu hỏi&gt;</code>\n\n"
            "<b>Ví dụ:</b>\n"
            "• <code>/ask Vì sao FR HAN tuần này giảm?</code>\n"
            "• <code>/ask Task này nên giao ai?</code>\n"
            "• <code>/ask Ai đang overload?</code>\n"
            "• <code>/ask OKR O1.1 status?</code>\n"
            "• <code>/ask Tôi giữ task G4 nào không nên?</code>",
            parse_mode="HTML",
        )
        return

    msg = await update.message.reply_text(tpl.msg_ai_thinking(), parse_mode="HTML")
    try:
        from ask import ask as ai_ask
        import asyncio
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, ai_ask, question)
    except Exception as e:
        logger.error(f"cmd_ask failed: {e}", exc_info=True)
        await msg.edit_text(tpl.msg_error("AI lỗi", str(e)[:200], "Thử lại sau ít phút"), parse_mode="HTML")
        return

    if result.get("error"):
        await msg.edit_text(tpl.msg_error("AI lỗi", result["error"]), parse_mode="HTML")
        return

    answer = result.get("answer") or "(không có câu trả lời)"
    body = tpl.msg_ai_response(answer)
    if len(body) > 4000:
        body = body[:3900] + "\n…(rút gọn)"

    try:
        await msg.edit_text(body)
    except Exception as e:
        logger.error(f"cmd_ask edit failed: {e}")
    log_action(user["telegram_id"], "ask", "ai", 0, question[:80])


# ─── Keyboard text routing ────────────────────────────────────────────────────

KEYBOARD_ROUTES = {
    "▸ Hôm nay":      cmd_today,
    "▸ Task của tôi": cmd_mytasks,
    "▸ Giao việc":    cmd_assign,
    "▸ Team":         cmd_team,
}


async def handle_keyboard_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    handler = KEYBOARD_ROUTES.get(text)
    if handler:
        await handler(update, context)


# ─── Callback query handler ───────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    user = get_user(uid)

    # ── done:<id> ──
    if data.startswith("done:"):
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if not task or not can_see_task(user, task):
            await query.edit_message_text("Task không tồn tại hoặc bạn không có quyền.")
            return
        if mark_done(task_id):
            await query.edit_message_text(
                f"✓ #{task_id} done. Mất bao lâu?",
                reply_markup=_duration_keyboard(task_id),
            )
            log_action(uid, "done", "task", task_id)
            if task.get("assigned_by") and task["assigned_by"] != uid:
                try:
                    await context.bot.send_message(
                        chat_id=task["assigned_by"],
                        text=f"✓ *{user['full_name']}* xong task #{task_id}: _{task['summary'][:60]}_",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

    # ── snooze:<id>:<delta> ──
    elif data.startswith("snooze:"):
        _, task_id_str, delta_str = data.split(":")
        task_id = int(task_id_str)
        now = datetime.now()
        if delta_str.endswith("h"):
            until = now + timedelta(hours=float(delta_str[:-1]))
        else:
            until = now + timedelta(days=float(delta_str[:-1]))
        snooze_task(task_id, until.isoformat())
        await query.edit_message_text(f"◷ #{task_id} hoãn đến {until.strftime('%d/%m %H:%M')}")
        increment_defer(task_id)

    # ── cancel:<id> ──
    elif data.startswith("cancel:"):
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if not task or not can_see_task(user, task):
            await query.edit_message_text("Không có quyền.")
            return
        cancel_task(task_id)
        await query.edit_message_text(f"✕ Task #{task_id} đã huỷ.")

    # ── dur:<id>:<mins> ──
    elif data.startswith("dur:"):
        _, task_id_str, mins_str = data.split(":")
        task_id, mins = int(task_id_str), int(mins_str)
        if mins > 0:
            set_actual_minutes(task_id, mins)
        await query.edit_message_text(f"✓ Ghi nhận. Task #{task_id} hoàn thành.")

    # ── pick:<assignee_id> — manager picks assignee ──
    elif data.startswith("pick:"):
        assignee_id = int(data.split(":")[1])
        state = _pending_assign_who.get(uid)
        logger.info(f"pick uid={uid} assignee_id={assignee_id} state={'found' if state else 'NONE'} has_text={('task_text' in state) if state else 'n/a'}")
        if not state or "task_text" not in state:
            await query.edit_message_text(
                "Phiên giao việc đã hết hạn (state không tìm thấy).\n"
                "Thử lại với /assign."
            )
            return
        assignee = get_user(assignee_id)
        if not assignee:
            await query.edit_message_text("Không tìm thấy người dùng này.")
            return
        _pending_assign_who.pop(uid, None)

        # ── REASSIGN existing task (from digest) — không tạo mới, chỉ update assignee ──
        existing_id = state.get("reassign_existing")
        if existing_id:
            task = get_task(existing_id)
            if not task:
                await query.edit_message_text(f"Task #{existing_id} không còn tồn tại.")
                return
            reassign_task(existing_id, assignee["telegram_id"])
            log_action(uid, "reassign_digest", "task", existing_id,
                       f"→ {assignee['full_name']}")
            await query.edit_message_text(
                f"✓ Task #{existing_id} đã giao lại cho <b>{assignee['full_name']}</b>.",
                parse_mode="HTML",
            )
            # Notify new assignee
            try:
                await context.bot.send_message(
                    chat_id=assignee["telegram_id"],
                    text=f"📬 Bạn được giao lại task <code>#{existing_id}</code>: <i>{task.get('summary','')[:80]}</i>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
            return

        # ── CREATE new task (existing flow) ──
        task_text = state["task_text"]
        result = state.get("result") or await _ai(route_task, task_text)
        task_id = add_task(
            raw_message=task_text,
            summary=result.get("summary", task_text[:100]),
            assignee_id=assignee_id,
            assigned_by=uid,
            team=assignee.get("team"),
            source="assign_pick",
            sender=user["full_name"] if user else "Manager",
            deadline=result.get("deadline_iso"),
            deadline_confidence=result.get("deadline_confidence"),
            priority=result.get("priority", "P2"),
            category=result.get("category", "other"),
            estimated_minutes=result.get("estimated_minutes", 30),
            classifier_meta=result,
        )

        await query.edit_message_text(
            tpl.msg_assign_confirm(task_id, assignee["full_name"], result),
            parse_mode="HTML",
        )
        log_action(uid, "assign", "task", task_id, f"→ {assignee['full_name']}")

        # DM to assignee
        accept_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✓ Nhận việc", callback_data=f"accept:{task_id}"),
                InlineKeyboardButton("✗ Từ chối", callback_data=f"decline:{task_id}"),
            ],
            [InlineKeyboardButton("🎓 Hướng dẫn chi tiết", callback_data=f"coach:{task_id}")],
        ])
        assigner_name = user["full_name"] if user else "Manager"
        task_dict = {
            "id": task_id,
            "summary": result.get("summary", task_text[:100]),
            "priority": result.get("priority", "P2"),
            "deadline": result.get("deadline_iso"),
            "category": result.get("category", "other"),
            "classifier_meta": result,
        }
        try:
            await context.bot.send_message(
                chat_id=assignee_id,
                text=tpl.msg_task_new(task_dict, assigned_by_name=assigner_name),
                reply_markup=accept_kb,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to DM assignee: {e}")

    # ── accept:<task_id> — employee accepts ──
    elif data.startswith("accept:"):
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if not task:
            await query.edit_message_text("Task không còn tồn tại.")
            return
        # Actually move the task into 'in_progress' — previously the message was
        # edited but status stayed 'pending', so accept was silently a no-op.
        start_task(task_id)
        log_action(uid, "accept_task", "task", task_id)
        task = get_task(task_id) or task
        await query.edit_message_text(tpl.msg_task_accepted(task), parse_mode="HTML")
        if task.get("assigned_by"):
            receiver_name = user["full_name"] if user else "Nhân viên"
            try:
                await context.bot.send_message(
                    chat_id=task["assigned_by"],
                    text=tpl.msg_confirm(
                        "Task đã được nhận",
                        f"<code>{receiver_name}</code> nhận <code>#{task_id}</code> {task['summary'][:60]}",
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    # ── decline:<task_id> — employee declines ──
    elif data.startswith("decline:"):
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if not task:
            await query.edit_message_text("Task không còn tồn tại.")
            return
        # Return to the unassigned pool (status=pending, assignee cleared) instead
        # of cancelling — declined work shouldn't vanish; manager can /assign again.
        return_to_pool(task_id)
        log_action(uid, "decline_task", "task", task_id)
        await query.edit_message_text(
            tpl.msg_confirm("Đã từ chối", f"<code>#{task_id}</code> {task.get('summary','')[:60]} — đã trả về pool"),
            parse_mode="HTML",
        )
        if task.get("assigned_by"):
            decliner = user["full_name"] if user else "Nhân viên"
            try:
                await context.bot.send_message(
                    chat_id=task["assigned_by"],
                    text=tpl.msg_warning(
                        "Task bị từ chối",
                        f"<code>{decliner}</code> từ chối <code>#{task_id}</code>: {task['summary'][:60]}",
                        action="Đã trả về pool — giao lại cho người khác bằng /assign",
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    # ── approve:<user_id> ──
    elif data.startswith("approve:"):
        if not user or not can_approve_users(user):
            await query.answer("Không có quyền.", show_alert=True)
            return
        target_id = int(data.split(":")[1])
        if approve_user(target_id):
            target = get_user(target_id)
            name = target["full_name"] if target else str(target_id)
            await query.edit_message_text(f"✓ Đã duyệt: <b>{name}</b>", parse_mode="HTML")
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text="✓ Tài khoản đã được duyệt! Gõ /help để bắt đầu.",
                    reply_markup=EMPLOYEE_KEYBOARD,
                )
            except Exception:
                pass

    # ── reject:<user_id> ──
    elif data.startswith("reject:"):
        if not user or not can_approve_users(user):
            await query.answer("Không có quyền.", show_alert=True)
            return
        target_id = int(data.split(":")[1])
        reject_user(target_id)
        await query.edit_message_text(f"✕ Đã từ chối user {target_id}.")

    # ── block:<id>:<reason> ──
    elif data.startswith("block:"):
        parts = data.split(":")
        task_id, reason = int(parts[1]), parts[2]
        task = get_task(task_id)
        if task and can_see_task(user, task):
            block_task(task_id, reason)
            await query.edit_message_text(f"⏸ Task #{task_id} blocked: {reason}")

    # ── unblock:<id> ──
    elif data.startswith("unblock:"):
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if task and can_see_task(user, task):
            unblock_task(task_id)
            await query.edit_message_text(f"✓ Task #{task_id} unblocked — back to pending.")

    # ── coach:<id> — assignee xin Layer 2 coaching ──
    elif data.startswith("coach:"):
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if not task:
            await query.answer("Task không còn tồn tại.", show_alert=True)
            return
        if not can_see_task(user, task):
            await query.answer("Bạn không có quyền xem task này.", show_alert=True)
            return

        await query.answer("⏳ Đang gen hướng dẫn...", show_alert=False)

        # Extract OKR + breakdown from classifier_meta (parsed once)
        import json as _j
        meta = task.get("classifier_meta") or {}
        if isinstance(meta, str):
            try:
                meta = _j.loads(meta)
            except Exception:
                meta = {}

        coach = await _ai(
            coach_task,
            task_summary=task.get("summary", ""),
            okr_ref=meta.get("okr_ref") if isinstance(meta, dict) else None,
            okr_action_id=meta.get("okr_action_id") if isinstance(meta, dict) else None,
            breakdown=meta.get("breakdown") if isinstance(meta, dict) else None,
            priority=task.get("priority", "P2"),
            deadline_iso=task.get("deadline"),
            assignee_name=user["full_name"] if user else None,
            raw_message=task.get("raw_message"),
        )

        msg = tpl.msg_coach_detail(task, coach)
        # Coaching messages can be long — cap at Telegram's 4096 limit
        if len(msg) > 4000:
            msg = msg[:3900] + "\n…(rút gọn)"
        try:
            await query.edit_message_text(msg, parse_mode="HTML")
            log_action(uid, "coach", "task", task_id)
        except Exception as e:
            logger.error(f"coach edit failed: {e}")
            await context.bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")

    # ── undo:<id> — undo auto-created task within window ──
    elif data.startswith("undo:"):
        if not user or not can_assign(user):
            await query.answer("Chỉ Manager / Team Lead.", show_alert=True)
            return
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if not task:
            await query.edit_message_text(f"Task #{task_id} không còn tồn tại.")
            return
        created_at = _auto_created.get(task_id)
        if created_at:
            elapsed_min = (datetime.now() - created_at).total_seconds() / 60
            if elapsed_min > AUTO_DECISION_UNDO_WINDOW:
                await query.answer(
                    f"Đã quá cửa sổ undo ({AUTO_DECISION_UNDO_WINDOW}p).",
                    show_alert=True,
                )
                return
        cancel_task(task_id)
        _auto_created.pop(task_id, None)
        log_action(uid, "undo", "task", task_id)
        await query.edit_message_text(
            f"⏪ Đã undo task #{task_id}: <i>{task.get('summary','')[:60]}</i>",
            parse_mode="HTML",
        )
        if task.get("assignee_id") and task["assignee_id"] != uid:
            try:
                await context.bot.send_message(
                    chat_id=task["assignee_id"],
                    text=f"⏪ Manager đã rút lại task <code>#{task_id}</code> — không cần làm nữa.",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    # ── digest_reassign:<id> — manager opens picker to change assignee of an existing task ──
    elif data.startswith("digest_reassign:"):
        if not user or not can_assign(user):
            await query.answer("Chỉ Manager / Team Lead.", show_alert=True)
            return
        task_id = int(data.split(":")[1])
        task = get_task(task_id)
        if not task:
            await query.edit_message_text(f"Task #{task_id} không còn tồn tại.")
            return

        _pending_assign_who[uid] = {
            "task_text": task.get("raw_message", task.get("summary", "")),
            "result": {
                "summary":      task.get("summary", ""),
                "priority":     task.get("priority", "P2"),
                "deadline_iso": task.get("deadline"),
                "category":     task.get("category", "other"),
            },
            "ts": datetime.now(),
            "reassign_existing": task_id,
        }

        members = list_team_by_person()
        members = [m for m in members if m["telegram_id"] != uid]
        buttons, row = [], []
        for u in members[:10]:
            row.append(InlineKeyboardButton(
                u["full_name"], callback_data=f"pick:{u['telegram_id']}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        await query.edit_message_text(
            f"↗ Giao lại task <code>#{task_id}</code>: <i>{task.get('summary','')[:60]}</i>\n"
            f"Chọn người mới:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ── confirm_assign — manager confirms AI-routed assignee ──
    elif data == "confirm_assign":
        state = _pending_confirm.get(uid)
        if not state:
            await query.edit_message_text("Phiên đã hết hạn. Thử lại.")
            return
        _pending_confirm.pop(uid, None)
        routed = state["routed"]
        task_text = state["task_text"]

        # Find assignee by email or name
        assignee = None
        if routed.get("assignee_email"):
            assignee = get_user_by_email(routed["assignee_email"])
        if not assignee and routed.get("assignee_name"):
            assignee = get_user_by_name(routed["assignee_name"])

        if not assignee:
            # Fall back to picker if user not found in DB yet
            _pending_assign_who[uid] = {"task_text": task_text, "result": routed, "ts": datetime.now()}
            members = list_team_by_person()
            members = [m for m in members if m["telegram_id"] != uid]
            await query.edit_message_text(
                f"Chưa tìm thấy {routed.get('assignee_name')} trong hệ thống. Chọn người khác:",
                reply_markup=_assignee_keyboard(members, str(hash(task_text))[:8]),
            )
            return

        task_id = add_task(
            raw_message=task_text,
            summary=routed.get("summary", task_text[:100]),
            assignee_id=assignee["telegram_id"],
            assigned_by=uid,
            team=assignee.get("team"),
            source="ai_route",
            sender=user["full_name"] if user else "Manager",
            deadline=routed.get("deadline_iso"),
            priority=routed.get("priority", "P2"),
            category=routed.get("category", "other"),
            estimated_minutes=routed.get("estimated_minutes", 30),
            classifier_meta=routed,
        )

        # Confirm to manager — replace card text
        await query.edit_message_text(
            tpl.msg_assign_confirm(task_id, assignee["full_name"], routed),
            parse_mode="HTML",
        )
        log_action(uid, "assign_ai", "task", task_id, f"→ {assignee['full_name']}")

        # DM to assignee
        accept_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✓ Nhận việc", callback_data=f"accept:{task_id}"),
                InlineKeyboardButton("✗ Từ chối", callback_data=f"decline:{task_id}"),
            ],
            [InlineKeyboardButton("🎓 Hướng dẫn chi tiết", callback_data=f"coach:{task_id}")],
        ])
        task_dict = {
            "id":       task_id,
            "summary":  routed.get("summary", task_text[:100]),
            "priority": routed.get("priority", "P2"),
            "deadline": routed.get("deadline_iso"),
            "category": routed.get("category", "other"),
            "classifier_meta": routed,
        }
        sender_name = user["full_name"] if user else "Manager"
        try:
            await context.bot.send_message(
                chat_id=assignee["telegram_id"],
                text=tpl.msg_task_new(task_dict, assigned_by_name=sender_name),
                reply_markup=accept_kb,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"DM to assignee failed: {e}")

    # ── change_assignee — manager wants to override AI pick ──
    elif data == "change_assignee":
        state = _pending_confirm.get(uid)
        logger.info(f"change_assignee uid={uid} chat={query.message.chat.id if query.message else '?'} state={'found' if state else 'NONE'}")
        if not state:
            await query.edit_message_text(
                "Phiên đã hết hạn (state không tìm thấy).\n"
                "Gõ /assign lại để bắt đầu phiên mới."
            )
            return
        task_text = state["task_text"]
        routed = state["routed"]
        _pending_confirm.pop(uid, None)
        _pending_assign_who[uid] = {"task_text": task_text, "result": routed, "ts": datetime.now()}
        members = list_team_by_person()
        members = [m for m in members if m["telegram_id"] != uid]
        p       = routed.get("priority", "P2")
        icon    = tpl.PRIORITY_ICON.get(p, "□")
        summary = routed.get("summary", task_text[:60])
        await query.edit_message_text(
            f"{icon} {p} — {summary}\n{tpl.DIV_LIGHT}\nGiao cho ai?",
            reply_markup=_assignee_keyboard(members, str(hash(task_text))[:8]),
        )

    # ── cancel_assign ──
    elif data == "cancel_assign":
        _pending_confirm.pop(uid, None)
        _pending_assign_who.pop(uid, None)
        await query.edit_message_text(tpl.msg_confirm("Đã huỷ", "Không tạo task."), parse_mode="HTML")

    # ── self_keep — /add suggested assignee but user chose to keep for self ──
    elif data == "self_keep":
        state = _pending_confirm.pop(uid, None)
        if not state:
            await query.edit_message_text("Phiên đã hết hạn.")
            return
        routed   = state["routed"]
        task_txt = state["task_text"]
        task_id  = add_task(
            raw_message=task_txt,
            summary=routed.get("summary", task_txt[:100]),
            assignee_id=uid,
            assigned_by=uid,
            team=user.get("team") if user else None,
            source="manual",
            sender=user["full_name"] if user else "?",
            deadline=routed.get("deadline_iso"),
            priority=routed.get("priority", "P3"),
            category=routed.get("category", "other"),
            estimated_minutes=routed.get("estimated_minutes", 30),
            classifier_meta=routed,
            visibility="team",
        )
        _last_task[uid] = task_id
        adhoc = get_adhoc_ratio_this_week(uid)
        await query.edit_message_text(
            tpl.msg_task_created(
                task_id, routed, task_txt,
                assignee_name=user["full_name"].split()[0] if user else "?",
                is_self=True,
                adhoc_ratio=adhoc,
            ),
            parse_mode="HTML",
            reply_markup=_task_keyboard(task_id),
        )

    # ── confirm_task — user confirmed a low-confidence detected task (self-task) ──
    elif data == "confirm_task":
        state = _pending_confirm.pop(uid, None)
        if not state:
            await query.edit_message_text("Phiên đã hết hạn. Gõ lại nội dung task.")
            return
        task_text = state["task_text"]
        routed = state.get("routed", {})
        task_id = add_task(
            raw_message=task_text,
            summary=routed.get("summary", task_text[:100]),
            assignee_id=uid,
            assigned_by=uid,
            team=user.get("team") if user else None,
            source="confirm",
            sender=user["full_name"] if user else "",
            deadline=routed.get("deadline_iso"),
            priority=routed.get("priority", "P3"),
            category=routed.get("category", "other"),
            estimated_minutes=routed.get("estimated_minutes", 30),
            classifier_meta=routed,
        )
        log_action(uid, "confirm_task", "task", task_id)
        await query.edit_message_text(
            tpl.msg_task_created(
                task_id, routed, task_text,
                assignee_name=user["full_name"].split()[0] if user else "",
                is_self=True,
            ),
            parse_mode="HTML",
            reply_markup=_task_keyboard(task_id),
        )

    # ── now (🎯 Làm ngay từ /mytasks) ──
    elif data == "now":
        if not user or not user.get("is_approved"):
            await query.answer("Chưa được duyệt.", show_alert=True)
            return
        await query.message.reply_chat_action("typing")
        msg, kb, task_id = await _compute_now(user)
        await query.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)
        if task_id:
            log_action(uid, "now", "task", task_id)

    # ── show_today (⊡ Hôm nay từ /mytasks) ──
    elif data == "show_today":
        if not user or not user.get("is_approved"):
            await query.answer("Chưa được duyệt.", show_alert=True)
            return
        tasks = list_user_today_tasks(uid)
        overdue = [t for t in tasks if t.get("deadline") and
                   datetime.fromisoformat(t["deadline"]).replace(tzinfo=None) < datetime.now()]
        today_tasks = [t for t in tasks if t not in overdue]
        await query.message.reply_text(
            tpl.msg_today(user["full_name"], overdue, today_tasks),
            parse_mode="HTML",
        )

    # ── ignore ──
    elif data == "ignore":
        await query.edit_message_text("Bỏ qua.")
