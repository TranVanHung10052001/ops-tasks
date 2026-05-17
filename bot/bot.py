"""
Bot Handlers — Multi-user team task bot.
Roles: manager / team_lead / employee.
"""

import logging
import io
import os
import re
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from store import (
    get_user, register_user, approve_user, reject_user,
    set_user_role, list_users, list_pending_approval, touch_user,
    add_task, get_task, list_user_tasks, list_user_today_tasks,
    list_team_tasks, list_team_by_person, get_team_stats, get_user_stats,
    mark_done, cancel_task, snooze_task, block_task, unblock_task,
    update_task_deadline, set_actual_minutes, increment_reminder,
    increment_defer, get_overdue_tasks_for_user, get_stalled_tasks_for_user,
    log_action,
)
from roles import (
    MANAGER, TEAM_LEAD, EMPLOYEE, ROLE_LABELS, MANAGER_CHAT_ID,
    is_manager, is_team_lead, can_assign, can_see_team,
    can_approve_users, can_see_task,
)
from classifier import full_pipeline, image_pipeline, extract_deadline, route_task, coach_task
from roast import get_done_roast, get_snooze_roast

logger = logging.getLogger(__name__)

# ─── In-memory state ─────────────────────────────────────────────────────────
# {chat_id: True} — waiting for user's full name input
_pending_name: dict[int, bool] = {}

# {manager_chat_id: {classified_task_data}} — forward-to-assign flow step 1
_pending_assign_who: dict[int, dict] = {}

# {manager_chat_id: {task_data, assignee_id}} — waiting for deadline after assignee picked
_pending_assign_deadline: dict[int, dict] = {}

# {user_chat_id: (task_id, ts)} — waiting for deadline on self-created task
_pending_deadline: dict[int, tuple] = {}

# {manager_chat_id: {routed task data}} — waiting for manager to confirm AI routing
_pending_confirm: dict[int, dict] = {}

DEADLINE_TTL = 300  # 5 minutes

# ─── UI constants ─────────────────────────────────────────────────────────────

P_EMOJI = {"P0": "🔴", "P1": "🟡", "P2": "🟢", "P3": "🔵"}
CAT_EMOJI = {
    "ops": "⚙️", "report": "📝", "meeting": "🗓",
    "vendor": "🤝", "admin": "🗂", "data": "📊", "other": "📌",
}

EMPLOYEE_KEYBOARD = ReplyKeyboardMarkup(
    [["▸ Task của tôi", "▸ Hôm nay"], ["▸ Thống kê"]],
    resize_keyboard=True,
    input_field_placeholder="Forward tin nhắn · /add · /done <id>",
)

MANAGER_KEYBOARD = ReplyKeyboardMarkup(
    [["▸ Team", "▸ Task của tôi"], ["▸ Giao việc", "▸ Thống kê"]],
    resize_keyboard=True,
    input_field_placeholder="Forward tin nhắn để giao · /assign · /team",
)


def _get_keyboard(user: dict) -> ReplyKeyboardMarkup:
    if can_see_team(user):
        return MANAGER_KEYBOARD
    return EMPLOYEE_KEYBOARD


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_task(task: dict, show_assignee: bool = False) -> str:
    emoji = P_EMOJI.get(task.get("priority", "P3"), "⚪")
    line = f"{emoji} #{task['id']} {task['summary'][:70]}"

    if show_assignee and task.get("assignee_name"):
        line += f" → {task['assignee_name']}"

    if task.get("deadline"):
        try:
            dl = datetime.fromisoformat(task["deadline"]).replace(tzinfo=None)
            delta = dl - datetime.now()
            if delta.total_seconds() < 0:
                hrs = abs(delta.total_seconds()) / 3600
                line += f" ⚠️ trễ {hrs:.0f}h"
            elif delta.days == 0:
                hrs = delta.total_seconds() / 3600
                line += f" — {hrs:.0f}h nữa"
            elif delta.days <= 3:
                line += f" — {dl.strftime('%d/%m %H:%M')}"
            else:
                line += f" — {dl.strftime('%d/%m')}"
        except (ValueError, TypeError):
            pass

    return line


def _task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Done", callback_data=f"done:{task_id}"),
        InlineKeyboardButton("◷ 2h", callback_data=f"snooze:{task_id}:2h"),
        InlineKeyboardButton("◷ 1d", callback_data=f"snooze:{task_id}:1d"),
        InlineKeyboardButton("✕ Drop", callback_data=f"cancel:{task_id}"),
    ]])


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


async def _notify_manager(app, text: str, parse_mode: str = "Markdown"):
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
        await update.message.reply_text(
            "Tài khoản của bạn đang chờ Manager duyệt. Vui lòng đợi thông báo."
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
            f"Chào anh/chị *{full_name}*! Đã xác nhận Manager.\n\n"
            "Dùng /help để xem hướng dẫn.",
            parse_mode="Markdown",
            reply_markup=MANAGER_KEYBOARD,
        )
        return

    # New employee — ask for name
    _pending_name[uid] = True
    await update.message.reply_text(
        "Chào bạn! Bot quản lý task của team Ahamove Truck Ops.\n\n"
        "Vui lòng nhập *họ tên đầy đủ* của bạn:",
        parse_mode="Markdown",
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

    registered = register_user(uid, username, full_name)
    if not registered:
        # Already exists but not approved
        await update.message.reply_text("Bạn đã đăng ký rồi, đang chờ duyệt.")
        return True

    await update.message.reply_text(
        f"Đã ghi nhận: *{full_name}*\n\n"
        "Vui lòng đợi Manager duyệt tài khoản. "
        "Bot sẽ thông báo khi được duyệt.",
        parse_mode="Markdown",
    )

    # Notify manager
    approve_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Duyệt", callback_data=f"approve:{uid}"),
        InlineKeyboardButton("✕ Từ chối", callback_data=f"reject:{uid}"),
    ]])
    uname_str = f" (@{username})" if username else ""
    await _notify_manager(
        context.application,
        f"👤 *Đăng ký mới:* {full_name}{uname_str}\n"
        f"ID: `{uid}`\n\nDuyệt tài khoản này?",
    )
    context.application.bot.send_message  # dummy to avoid unused
    try:
        await context.application.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=f"👤 *Đăng ký mới:* {full_name}{uname_str}\nID: `{uid}`\n\nDuyệt?",
            parse_mode="Markdown",
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
        "*Task cá nhân:*\n"
        "• `/add <mô tả>` — tạo task cho bản thân\n"
        "• `/mytasks` — danh sách task của bạn\n"
        "• `/today` — task hôm nay + overdue\n"
        "• `/done <id>` — đánh dấu xong\n"
        "• `/snooze <id> 2h|1d` — hoãn lại\n"
        "• `/cancel <id>` — huỷ task\n"
        "• `/stats` — thống kê tuần này\n"
        "• `/coach <id>` — AI hướng dẫn cách làm task\n"
    )

    manager_cmds = ""
    if can_see_team(user):
        manager_cmds = (
            "\n*Team (Manager/TL):*\n"
            "• `/assign @user <mô tả>` — giao task cho người khác\n"
            "• `/team` — dashboard toàn team\n"
            "• `/pending` — task chưa được nhận\n"
        )
    if is_manager(user):
        manager_cmds += (
            "• `/approve <id>` — duyệt user mới\n"
            "• `/users` — danh sách team\n"
            "• `/setrole @user <role> [team]` — cấp quyền\n"
        )

    await update.message.reply_text(
        "📖 *Hướng dẫn sử dụng*\n\n"
        + personal + manager_cmds +
        "\n*Tạo task nhanh:* Forward tin nhắn bất kỳ vào đây → bot tự classify.",
        parse_mode="Markdown",
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a task for yourself."""
    user = await _require_approved(update)
    if not user:
        return

    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Cú pháp: `/add <mô tả task>`\n"
            "Ví dụ: `/add Gửi báo cáo tuần trước 5pm`",
            parse_mode="Markdown",
        )
        return

    result = full_pipeline(text)
    uid = user["telegram_id"]

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

    summary = result.get("summary", text[:100])
    emoji = P_EMOJI.get(result.get("priority", "P3"), "⚪")
    msg = f"{emoji} *#{task_id}* {summary}"

    if result.get("deadline_iso"):
        dl = datetime.fromisoformat(result["deadline_iso"])
        msg += f"\n📅 Deadline: {dl.strftime('%d/%m %H:%M')}"
    else:
        _pending_deadline[update.effective_chat.id] = (task_id, datetime.now())
        msg += "\n\n📅 Deadline là bao giờ? (Gõ vd: *T6 17h*, *mai 9h*, hoặc /skip)"

    await update.message.reply_text(msg, parse_mode="Markdown",
                                    reply_markup=_task_keyboard(task_id))
    log_action(uid, "add_task", "task", task_id, summary)


async def cmd_mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    tasks = list_user_tasks(user["telegram_id"], status="pending", limit=30)
    if not tasks:
        await update.message.reply_text("Không có task pending. Sạch bảng!")
        return

    lines = [f"*Task của {user['full_name']}* — {len(tasks)} pending\n"]
    for t in tasks:
        lines.append(_fmt_task(t))
    lines.append("\n/done <id> · /snooze <id> 2h · /cancel <id>")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    tasks = list_user_today_tasks(user["telegram_id"])
    overdue = [t for t in tasks if t.get("deadline") and
               datetime.fromisoformat(t["deadline"]).replace(tzinfo=None) < datetime.now()]
    today_tasks = [t for t in tasks if t not in overdue]

    if not tasks:
        await update.message.reply_text("Không có task nào hôm nay.")
        return

    lines = [f"*Hôm nay — {user['full_name']}*\n"]
    if overdue:
        lines.append(f"⚠️ *Quá hạn ({len(overdue)}):*")
        for t in overdue:
            lines.append(_fmt_task(t))
        lines.append("")
    if today_tasks:
        lines.append(f"📋 *Hôm nay ({len(today_tasks)}):*")
        for t in today_tasks:
            lines.append(_fmt_task(t))

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    if not context.args:
        await update.message.reply_text("Cú pháp: `/done <id>`", parse_mode="Markdown")
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
        roast = get_done_roast()
        await update.message.reply_text(
            f"✓ *#{task_id}* done. _{roast}_\n\nMất bao lâu?",
            parse_mode="Markdown",
            reply_markup=_duration_keyboard(task_id),
        )
        log_action(user["telegram_id"], "done", "task", task_id)

        # Notify assigner if different from doer
        if task.get("assigned_by") and task["assigned_by"] != user["telegram_id"]:
            try:
                await context.bot.send_message(
                    chat_id=task["assigned_by"],
                    text=f"✓ *{user['full_name']}* vừa hoàn thành task:\n"
                         f"_{task['summary'][:80]}_",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
    else:
        await update.message.reply_text(f"Task #{task_id} không tồn tại hoặc đã xong.")


async def cmd_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    if len(context.args) < 2:
        await update.message.reply_text("Cú pháp: `/snooze <id> 2h|1d`", parse_mode="Markdown")
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
        await update.message.reply_text("Dùng `2h`, `4h`, `1d`, `2d`.", parse_mode="Markdown")
        return

    task = get_task(task_id)
    if not task or not can_see_task(user, task):
        await update.message.reply_text(f"Không tìm thấy task #{task_id}.")
        return

    snooze_task(task_id, until.isoformat())
    roast = get_snooze_roast()
    await update.message.reply_text(
        f"◷ #{task_id} hoãn đến {until.strftime('%d/%m %H:%M')}. _{roast}_",
        parse_mode="Markdown",
    )
    increment_defer(task_id)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    if not context.args:
        await update.message.reply_text("Cú pháp: `/cancel <id>`", parse_mode="Markdown")
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
        await update.message.reply_text(f"✕ Task #{task_id} đã huỷ.")
    else:
        await update.message.reply_text(f"Không thể huỷ task #{task_id}.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_approved(update)
    if not user:
        return

    s = get_user_stats(user["telegram_id"])
    await update.message.reply_text(
        f"*Thống kê — {user['full_name']}*\n\n"
        f"Tuần này: {s['done_week']} done\n"
        f"Đang pending: {s['pending']}\n"
        f"Overdue: {s['overdue']}",
        parse_mode="Markdown",
    )


async def cmd_coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /coach <task_id> — AI coaching guide for a specific task.
    Available to all team members for their own tasks; manager/TL for any task.
    """
    user = await _require_approved(update)
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Cú pháp: `/coach <id>`\n"
            "Ví dụ: `/coach 12` — AI phân tích task #12 và hướng dẫn cách làm",
            parse_mode="Markdown",
        )
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

    await update.message.reply_text("🤔 AI đang phân tích task...")

    meta = task.get("classifier_meta") or {}
    if isinstance(meta, str):
        import json as _json
        try:
            meta = _json.loads(meta)
        except Exception:
            meta = {}

    guide = coach_task(
        task_summary=task.get("summary", task.get("raw_message", "")),
        okr_ref=meta.get("okr_ref") or task.get("okr_ref"),
        okr_action_id=meta.get("okr_action_id"),
        breakdown=meta.get("breakdown") or [],
        priority=task.get("priority", "P2"),
        deadline_iso=task.get("deadline"),
        assignee_name=task.get("assignee_name"),
    )

    emoji = P_EMOJI.get(task.get("priority", "P3"), "⚪")
    summary = task.get("summary", "")
    okr_ref = meta.get("okr_ref") or task.get("okr_ref")

    lines = [
        f"{emoji} *#{task_id}* {summary[:70]}",
        "",
    ]

    if okr_ref:
        lines.append(f"🎯 *OKR {okr_ref}*")

    if guide.get("why_matters"):
        lines.append(f"📌 _{guide['why_matters']}_")

    lines.append("")
    if guide.get("steps"):
        lines.append("*Cách làm:*")
        for i, step in enumerate(guide["steps"][:5], 1):
            lines.append(f"{i}. {step}")

    if guide.get("watch_out"):
        lines.append("")
        lines.append("*⚠️ Lưu ý:*")
        for w in guide["watch_out"][:3]:
            lines.append(f"• {w}")

    if guide.get("tips"):
        lines.append("")
        lines.append(f"💡 _{guide['tips']}_")

    mins = guide.get("estimated_minutes", 0)
    if mins:
        h, m = divmod(mins, 60)
        time_str = (f"{h}h{m:02d}ph" if h else f"{m}ph")
        lines.append(f"\n⏱ Ước tính: {time_str}")

    # Action buttons
    coach_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Done", callback_data=f"done:{task_id}"),
        InlineKeyboardButton("◷ 2h", callback_data=f"snooze:{task_id}:2h"),
    ]])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=coach_kb,
    )


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
    routed = route_task(args_text)
    if routed.get("assignee_confidence", 0) >= 0.75 and routed.get("assignee_name"):
        await _show_confirm_card(update, context, user, args_text, routed)
    else:
        await _show_assignee_picker(update, context, user, args_text, routed)


async def _do_assign_with_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    assigner: dict, assignee: dict, task_text: str,
):
    """Create task and notify assignee directly."""
    result = full_pipeline(task_text)
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

    emoji = P_EMOJI.get(result.get("priority", "P2"), "⚪")
    summary = result.get("summary", task_text[:100])

    # Confirm to assigner
    msg = f"✓ Đã giao *#{task_id}* cho {assignee['full_name']}\n{emoji} _{summary}_"
    if result.get("deadline_iso"):
        dl = datetime.fromisoformat(result["deadline_iso"])
        msg += f"\n📅 {dl.strftime('%d/%m %H:%M')}"
    await update.message.reply_text(msg, parse_mode="Markdown")

    # DM to assignee
    accept_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Nhận việc", callback_data=f"accept:{task_id}"),
        InlineKeyboardButton("✗ Từ chối", callback_data=f"decline:{task_id}"),
    ]])
    assignee_msg = (
        f"📥 *{assigner['full_name']}* giao việc cho bạn:\n\n"
        f"{emoji} _{summary}_"
    )
    if result.get("deadline_iso"):
        dl = datetime.fromisoformat(result["deadline_iso"])
        assignee_msg += f"\n📅 Deadline: *{dl.strftime('%d/%m %H:%M')}*"

    try:
        await context.bot.send_message(
            chat_id=assignee["telegram_id"],
            text=assignee_msg,
            parse_mode="Markdown",
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

    priority = routed.get("priority", "P2")
    emoji = P_EMOJI.get(priority, "⚪")
    summary = routed.get("summary", task_text[:80])
    assignee_name = routed.get("assignee_name", "?")
    deadline_iso = routed.get("deadline_iso")
    okr_ref = routed.get("okr_ref")
    in_scope = routed.get("in_scope", True)
    scope_note = routed.get("scope_note", "")
    breakdown = routed.get("breakdown", [])
    confidence = int(routed.get("assignee_confidence", 0) * 100)

    # Build message
    lines = [f"📋 *{summary}*\n"]
    detail = f"👤 *{assignee_name}*  ·  {emoji} {priority}"
    if deadline_iso:
        try:
            dl = datetime.fromisoformat(deadline_iso)
            detail += f"  ·  📅 {dl.strftime('%d/%m')}"
        except (ValueError, TypeError):
            pass
    lines.append(detail)

    if okr_ref:
        lines.append(f"🎯 OKR {okr_ref}")

    scope_icon = "✅" if in_scope else "⚠️"
    lines.append(f"{scope_icon} {scope_note or ('Đúng scope' if in_scope else 'Ngoài scope')}"
                 f"  ·  AI {confidence}%")

    if breakdown:
        lines.append("\n*Gợi ý thực hiện:*")
        for i, step in enumerate(breakdown[:4], 1):
            lines.append(f"{i}. {step}")

    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ Assign cho {assignee_name.split()[-1]}",
                                 callback_data="confirm_assign"),
            InlineKeyboardButton("✏️ Đổi người", callback_data="change_assignee"),
        ],
        [InlineKeyboardButton("❌ Huỷ", callback_data="cancel_assign")],
    ])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
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

    summary = result.get("summary", task_text[:80])
    emoji = P_EMOJI.get(result.get("priority", "P2"), "⚪")

    msg = (
        f"{emoji} _{summary}_\n\n"
        f"Giao cho ai?"
    )

    # Build assignee buttons showing workload
    buttons = []
    row = []
    for u in team_members[:8]:
        overdue = u.get("overdue_count", 0)
        active = u.get("active_count", 0)
        suffix = " ⚠️" if overdue > 0 else ""
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
        msg, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manager/TL team dashboard."""
    user = await _require_approved(update)
    if not user or not can_see_team(user):
        if user:
            await update.message.reply_text("Chỉ Manager và Team Lead mới xem được team dashboard.")
        return

    members = list_team_by_person()
    stats = get_team_stats()

    now = datetime.now()
    header = (
        f"*Team Status — {now.strftime('%d/%m %H:%M')}*\n\n"
        f"{stats['active']} active  ·  "
        f"{stats['done_today']} done hôm nay  ·  "
        f"{stats['overdue']} overdue  ·  "
        f"{stats['blocked']} blocked\n"
    )

    body = []
    for m in members:
        if m.get("overdue_count", 0) > 0:
            indicator = "🔴"
        elif m.get("active_count", 0) > 8:
            indicator = "🟡"
        else:
            indicator = "🟢"

        name_str = m["full_name"]
        active = m.get("active_count", 0)
        overdue = m.get("overdue_count", 0)
        done_t = m.get("done_today", 0)

        line = f"{indicator} *{name_str}* — {active} task"
        if overdue:
            line += f", {overdue} trễ ⚠️"
        if done_t:
            line += f", {done_t} done hôm nay"

        body.append(line)

    footer = "\n\n/assign để giao task mới · /pending task chưa nhận"

    msg = header + "\n".join(body) + footer
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show unaccepted/unstarted assigned tasks."""
    user = await _require_approved(update)
    if not user or not can_assign(user):
        return

    tasks = list_team_tasks(statuses=["pending"])
    if not tasks:
        await update.message.reply_text("Không có task pending trong team.")
        return

    lines = [f"*Pending — team* ({len(tasks)} task)\n"]
    for t in tasks[:20]:
        lines.append(_fmt_task(t, show_assignee=True))

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


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
        lines = ["*Chờ duyệt:*\n"]
        for u in pending:
            uname = f" @{u['username']}" if u.get("username") else ""
            lines.append(f"• {u['full_name']}{uname} — `/approve {u['telegram_id']}`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID không hợp lệ.")
        return

    if approve_user(target_id):
        target = get_user(target_id)
        name = target["full_name"] if target else str(target_id)
        await update.message.reply_text(f"✓ Đã duyệt tài khoản: *{name}*", parse_mode="Markdown")
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


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all team members."""
    user = await _require_approved(update)
    if not user or not can_see_team(user):
        return

    members = list_users(approved_only=True)
    if not members:
        await update.message.reply_text("Team chưa có thành viên.")
        return

    lines = [f"*Team ({len(members)} người)*\n"]
    for m in members:
        role_str = ROLE_LABELS.get(m["role"], m["role"])
        uname = f" @{m['username']}" if m.get("username") else ""
        team_str = f" [{m['team']}]" if m.get("team") else ""
        lines.append(f"• {m['full_name']}{uname}{team_str} — {role_str}")

    pending = list_pending_approval()
    if pending:
        lines.append(f"\n⏳ *Chờ duyệt: {len(pending)} người* — /approve để duyệt")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


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
            "Cú pháp: `/setrole @user <manager|tl|employee> [team]`\n"
            "Ví dụ: `/setrole @nam tl B2B_Vendor`",
            parse_mode="Markdown",
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
        parse_mode="Markdown",
    )
    log_action(user["telegram_id"], "set_role", "user", target["telegram_id"],
               f"{role} team={team_name}")


# ─── Message handlers ─────────────────────────────────────────────────────────

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded messages and direct text."""
    user = await _require_approved(update)
    if not user:
        return

    text = update.message.text or update.message.caption or ""
    if not text:
        return

    # Check registration flow
    if await handle_name_input(update, context):
        return

    uid = update.effective_chat.id

    # Check pending deadline input
    if uid in _pending_deadline:
        task_id, ts = _pending_deadline[uid]
        if not _is_expired(ts):
            deadline_data = extract_deadline(text)
            if deadline_data.get("deadline_iso"):
                update_task_deadline(task_id, deadline_data["deadline_iso"],
                                     deadline_data.get("confidence", "asked"))
                _pending_deadline.pop(uid)
                dl = datetime.fromisoformat(deadline_data["deadline_iso"])
                await update.message.reply_text(
                    f"✓ Deadline task #{task_id}: *{dl.strftime('%d/%m %H:%M')}*",
                    parse_mode="Markdown",
                )
                return
        else:
            _pending_deadline.pop(uid)

    # Check pending assign description input (guided flow)
    if uid in _pending_assign_who and _pending_assign_who[uid].get("waiting_desc"):
        _pending_assign_who[uid] = {
            "task_text": text,
            "result": full_pipeline(text),
            "ts": datetime.now(),
        }
        # Show assignee picker
        state = _pending_assign_who[uid]
        await _show_assignee_picker(update, context, user, text, state["result"])
        return

    # Manager forwarding external message → smart route + confirm card / picker
    if can_assign(user) and (update.message.forward_date or update.message.forward_origin):
        await update.message.reply_text("⏳ Đang phân tích...")
        routed = route_task(text)
        if routed.get("is_task"):
            # High confidence → confirm card; low confidence → picker
            if routed.get("assignee_confidence", 0) >= 0.75 and routed.get("assignee_name"):
                await _show_confirm_card(update, context, user, text, routed)
            else:
                _pending_assign_who[uid] = {
                    "task_text": text,
                    "result": routed,
                    "ts": datetime.now(),
                }
                await _show_assignee_picker(update, context, user, text, routed)
        else:
            await update.message.reply_text(
                "Không phát hiện task trong tin nhắn này.\n"
                "Dùng `/add <mô tả>` để tạo thủ công.",
                parse_mode="Markdown",
            )
        return

    # Regular text — create task for self
    result = full_pipeline(text)
    if result.get("is_task") and result.get("confidence", 0) >= 0.6:
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

        emoji = P_EMOJI.get(result.get("priority", "P3"), "⚪")
        msg = f"{emoji} *#{task_id}* {result['summary']}"

        if result.get("deadline_iso"):
            dl = datetime.fromisoformat(result["deadline_iso"])
            msg += f"\n📅 {dl.strftime('%d/%m %H:%M')}"
        else:
            _pending_deadline[uid] = (task_id, datetime.now())
            msg += "\n\nDeadline? (Gõ vd: *T6 17h*, hoặc /skip)"

        await update.message.reply_text(
            msg, parse_mode="Markdown",
            reply_markup=_task_keyboard(task_id),
        )
    elif result.get("is_task"):
        # Low confidence — ask confirmation
        confirm_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✓ Lưu task", callback_data=f"confirm_task:{text[:200]}"),
            InlineKeyboardButton("✕ Bỏ qua", callback_data="ignore"),
        ]])
        await update.message.reply_text(
            f"Có phải task không?\n_{result.get('summary', text[:80])}_",
            parse_mode="Markdown",
            reply_markup=confirm_kb,
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot (OCR + classify)."""
    user = await _require_approved(update)
    if not user:
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await update.message.reply_text("Đang đọc ảnh...")

    result = image_pipeline(bytes(image_bytes))
    if not result.get("is_task"):
        await update.message.reply_text("Không phát hiện task trong ảnh này.")
        return

    uid = user["telegram_id"]
    task_id = add_task(
        raw_message=f"[OCR screenshot]",
        summary=result["summary"],
        assignee_id=uid,
        assigned_by=uid,
        team=user.get("team"),
        source="photo",
        deadline=result.get("deadline_iso"),
        priority=result.get("priority", "P3"),
        category=result.get("category", "other"),
        estimated_minutes=result.get("estimated_minutes", 30),
        classifier_meta=result,
    )

    emoji = P_EMOJI.get(result.get("priority", "P3"), "⚪")
    msg = f"{emoji} *#{task_id}* {result['summary']}"
    if not result.get("deadline_iso"):
        _pending_deadline[uid] = (task_id, datetime.now())
        msg += "\n\nDeadline? (/skip để bỏ qua)"

    await update.message.reply_text(msg, parse_mode="Markdown",
                                    reply_markup=_task_keyboard(task_id))


# ─── Keyboard text routing ────────────────────────────────────────────────────

KEYBOARD_ROUTES = {
    "▸ Task của tôi": cmd_mytasks,
    "▸ Hôm nay":      cmd_today,
    "▸ Thống kê":     cmd_stats,
    "▸ Team":         cmd_team,
    "▸ Giao việc":    cmd_assign,
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
                        parse_mode="Markdown",
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
        if not state or "task_text" not in state:
            await query.edit_message_text("Phiên giao việc đã hết hạn. Thử lại với /assign.")
            return
        assignee = get_user(assignee_id)
        if not assignee:
            await query.edit_message_text("Không tìm thấy người dùng này.")
            return
        _pending_assign_who.pop(uid, None)

        task_text = state["task_text"]
        result = state.get("result") or full_pipeline(task_text)
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

        emoji = P_EMOJI.get(result.get("priority", "P2"), "⚪")
        summary = result.get("summary", task_text[:80])
        await query.edit_message_text(
            f"✓ Đã giao *#{task_id}* cho {assignee['full_name']}\n{emoji} _{summary}_",
            parse_mode="Markdown",
        )
        log_action(uid, "assign", "task", task_id, f"→ {assignee['full_name']}")

        # DM to assignee
        accept_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✓ Nhận việc", callback_data=f"accept:{task_id}"),
            InlineKeyboardButton("✗ Từ chối", callback_data=f"decline:{task_id}"),
        ]])
        assigner_name = user["full_name"] if user else "Manager"
        msg = f"📥 *{assigner_name}* giao việc cho bạn:\n\n{emoji} _{summary}_"
        if result.get("deadline_iso"):
            dl = datetime.fromisoformat(result["deadline_iso"])
            msg += f"\n📅 Deadline: *{dl.strftime('%d/%m %H:%M')}*"
        try:
            await context.bot.send_message(
                chat_id=assignee_id, text=msg,
                parse_mode="Markdown", reply_markup=accept_kb,
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
        await query.edit_message_text(
            f"✓ Đã nhận task #{task_id}.\n_{task['summary'][:80]}_\n\n"
            f"/done {task_id} khi xong.",
            parse_mode="Markdown",
        )
        if task.get("assigned_by"):
            receiver_name = user["full_name"] if user else "Nhân viên"
            try:
                await context.bot.send_message(
                    chat_id=task["assigned_by"],
                    text=f"✓ *{receiver_name}* đã nhận task #{task_id}.",
                    parse_mode="Markdown",
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
        cancel_task(task_id)
        await query.edit_message_text(f"✗ Đã từ chối task #{task_id}.")
        if task.get("assigned_by"):
            decliner = user["full_name"] if user else "Nhân viên"
            try:
                await context.bot.send_message(
                    chat_id=task["assigned_by"],
                    text=f"⚠️ *{decliner}* từ chối task #{task_id}: _{task['summary'][:60]}_\n\n"
                         f"Cần giao lại cho người khác.",
                    parse_mode="Markdown",
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
            await query.edit_message_text(f"✓ Đã duyệt: *{name}*", parse_mode="Markdown")
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
            from store import get_user_by_email
            assignee = get_user_by_email(routed["assignee_email"])
        if not assignee and routed.get("assignee_name"):
            from store import get_user_by_name
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
            classifier_meta=routed,
        )

        emoji = P_EMOJI.get(routed.get("priority", "P2"), "⚪")
        summary = routed.get("summary", task_text[:80])
        okr_str = f" | 🎯 {routed['okr_ref']}" if routed.get("okr_ref") else ""
        await query.edit_message_text(
            f"✅ *#{task_id}* giao cho *{assignee['full_name']}*\n"
            f"{emoji} _{summary}_{okr_str}",
            parse_mode="Markdown",
        )
        log_action(uid, "assign_ai", "task", task_id, f"→ {assignee['full_name']}")

        # DM to assignee with OKR context
        accept_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✓ Nhận việc", callback_data=f"accept:{task_id}"),
            InlineKeyboardButton("✗ Từ chối", callback_data=f"decline:{task_id}"),
        ]])
        dm_msg = (
            f"📥 *{user['full_name'] if user else 'Manager'}* giao việc cho bạn:\n\n"
            f"{emoji} *{summary}*"
        )
        if routed.get("deadline_iso"):
            try:
                dl = datetime.fromisoformat(routed["deadline_iso"])
                dm_msg += f"\n📅 Deadline: *{dl.strftime('%d/%m')}*"
            except (ValueError, TypeError):
                pass
        if routed.get("okr_ref"):
            dm_msg += f"\n🎯 OKR: {routed['okr_ref']}"
        if routed.get("scope_note"):
            dm_msg += f"\n💡 _{routed['scope_note']}_"
        if routed.get("breakdown"):
            dm_msg += "\n\n*Gợi ý thực hiện:*\n" + "\n".join(
                f"{i}. {s}" for i, s in enumerate(routed["breakdown"][:4], 1)
            )
        try:
            await context.bot.send_message(
                chat_id=assignee["telegram_id"],
                text=dm_msg, parse_mode="Markdown", reply_markup=accept_kb,
            )
        except Exception as e:
            logger.error(f"DM to assignee failed: {e}")

    # ── change_assignee — manager wants to override AI pick ──
    elif data == "change_assignee":
        state = _pending_confirm.get(uid)
        if not state:
            await query.edit_message_text("Phiên đã hết hạn.")
            return
        task_text = state["task_text"]
        routed = state["routed"]
        _pending_confirm.pop(uid, None)
        _pending_assign_who[uid] = {"task_text": task_text, "result": routed, "ts": datetime.now()}
        members = list_team_by_person()
        members = [m for m in members if m["telegram_id"] != uid]
        emoji = P_EMOJI.get(routed.get("priority", "P2"), "⚪")
        summary = routed.get("summary", task_text[:60])
        await query.edit_message_text(
            f"{emoji} _{summary}_\n\nGiao cho ai?",
            parse_mode="Markdown",
            reply_markup=_assignee_keyboard(members, str(hash(task_text))[:8]),
        )

    # ── cancel_assign ──
    elif data == "cancel_assign":
        _pending_confirm.pop(uid, None)
        _pending_assign_who.pop(uid, None)
        await query.edit_message_text("❌ Đã huỷ.")

    # ── ignore ──
    elif data == "ignore":
        await query.edit_message_text("Bỏ qua.")
