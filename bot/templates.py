"""
Message Templates — Truck Ops Telegram Bot
Chuẩn hoá toàn bộ tin nhắn theo Design System.

Icon Legend:
  STATUS:   ● done  ◐ doing  ○ todo  ⊘ cancel  ◌ blocked
  PRIORITY: ■ P0  ▪ P1  ▫ P2  □ P3  ◌ P4
  ACTIONS:  ▸ open  ● confirm  ↗ transfer  ✕ cancel
  TRENDS:   ▲ up  ▼ down  ━ stable
  AI:       ⊙ Trợ lý điều vận
  TIME:     ◷ time  ⊡ date  ‼ urgent
"""

from datetime import datetime

# ─── Design tokens ────────────────────────────────────────────────────────────

DIV_STRONG = "═════════════════════════════"
DIV_LIGHT  = "─────────────────────────"
AI_SIG     = "⊙ Trợ lý điều vận"

PRIORITY_ICON  = {"P0": "■", "P1": "▪", "P2": "▫", "P3": "□", "P4": "◌"}
PRIORITY_LABEL = {
    "P0": "KHẨN CẤP", "P1": "CAO",
    "P2": "TRUNG BÌNH", "P3": "THẤP", "P4": "KHI RẢNH",
}
STATUS_ICON = {
    "todo": "○", "pending": "○",
    "doing": "◐", "in_progress": "◐",
    "done": "●",
    "cancel": "⊘", "cancelled": "⊘",
    "blocked": "◌",
}

# ─── Eisenhower Matrix — Urgent × Important ──────────────────────────────────
# Eisenhower (1954) × Covey Q2-focus × color psychology (🔴 urgent, ⚪ defer)
# Urgent = deadline ≤ 24h HOẶC P0 · Important = P0/P1 HOẶC OKR ref

_URGENT_HOURS    = 24
_IMPORTANT_PRIOS = {"P0", "P1"}

EISENHOWER = {
    "Q1": {"icon": "🔴", "label": "Làm ngay",      "note": "Gấp + Quan trọng"},
    "Q2": {"icon": "🟡", "label": "Lên kế hoạch",  "note": "Quan trọng, chưa gấp"},
    "Q3": {"icon": "🟠", "label": "Uỷ quyền",      "note": "Gấp, ít quan trọng"},
    "Q4": {"icon": "⚪", "label": "Xem lại",        "note": "Không gấp, ít quan trọng"},
}


def eisenhower_quadrant(task: dict) -> str:
    """
    Phân loại task vào 1 trong 4 ô Eisenhower (Q1–Q4).

    Urgency   = deadline ≤ _URGENT_HOURS giờ  HOẶC  priority P0
    Importance = priority P0/P1  HOẶC  có OKR ref
    """
    import json as _j
    now = datetime.now()
    p   = task.get("priority", "P3")

    # ── Urgency ───────────────────────────────────────────────────────────────
    urgent = (p == "P0")          # P0 luôn khẩn cấp theo định nghĩa
    if not urgent:
        dl_raw = task.get("deadline") or task.get("deadline_iso")
        if dl_raw:
            try:
                dl = datetime.fromisoformat(dl_raw).replace(tzinfo=None)
                hours_left = (dl - now).total_seconds() / 3600
                urgent = 0 < hours_left <= _URGENT_HOURS
            except (ValueError, TypeError):
                pass

    # ── Importance ────────────────────────────────────────────────────────────
    important = p in _IMPORTANT_PRIOS
    if not important:
        # Check OKR alignment in classifier_meta or top-level field
        try:
            meta = task.get("classifier_meta") or {}
            if isinstance(meta, str):
                meta = _j.loads(meta)
            if meta.get("okr_ref") or meta.get("okr_tag"):
                important = True
        except Exception:
            pass
        if not important and task.get("okr_ref"):
            important = True

    # ── Matrix ────────────────────────────────────────────────────────────────
    if urgent and important:
        return "Q1"
    if not urgent and important:
        return "Q2"
    if urgent and not important:
        return "Q3"
    return "Q4"


def eisenhower_icon(task: dict) -> str:
    """Trả về colored circle emoji cho task."""
    return EISENHOWER[eisenhower_quadrant(task)]["icon"]


CAT_LABEL = {
    "fill_rate": "Fill Rate",
    "supply":    "Supply",
    "cost":      "Cost",
    "b2b":       "B2B",
    "expansion": "Expansion",
    "retention": "Retention",
    "tech":      "Tech",
    "report":    "Report",
    "vendor":    "Vendor",
    "meeting":   "Họp",
    "ops":       "Vận hành",
    "admin":     "Admin",
    "other":     "Khác",
}

# Color-coded priorities (more glanceable than geometric icons)
PRIORITY_EMOJI = {
    "P0": "🔴", "P1": "🔴",
    "P2": "🟡",
    "P3": "⚪", "P4": "⚪",
}

# OKR theme labels — expand "O3" → "O3 Cost/SLA" for readability
OKR_LABEL = {
    "O1": "Fill Rate",
    "O2": "Supply",
    "O3": "Cost/SLA",
    "O4": "Tech",
}


# ─── Name + label cleaners ────────────────────────────────────────────────────

import re as _re

# Keep ASCII + Vietnamese letters + common name punctuation. Drops emoji,
# kaomoji art like "(つ◉ヮ◉)つ", and any other non-name decorations.
_NAME_KEEP_RE = _re.compile(r"[^a-zA-ZÀ-ỹ\s\-'\.]")


def _clean_name(name: str | None) -> str:
    """Strip emoji art / decorations from a Telegram display name."""
    if not name:
        return ""
    cleaned = _NAME_KEEP_RE.sub("", str(name))
    cleaned = " ".join(cleaned.split())  # collapse whitespace
    return cleaned or str(name).strip()  # fallback if everything stripped


def _okr_label(okr_ref: str | None) -> str:
    """Expand 'O3' → 'O3 Cost/SLA', 'O1.2' → 'O1.2 Fill Rate'.
    Returns empty string if okr_ref falsy."""
    if not okr_ref:
        return ""
    base = okr_ref.split(".")[0].upper().strip()
    theme = OKR_LABEL.get(base)
    return f"{okr_ref} {theme}" if theme else okr_ref


def _deadline_urgency(deadline_iso: str | None) -> str:
    """Return short urgency chip if deadline < 24h. Empty otherwise.
    Examples: '🔥 Còn 3h', '🔥 Còn 45p', '⚠️ Còn 18h'."""
    if not deadline_iso:
        return ""
    try:
        dl = datetime.fromisoformat(deadline_iso).replace(tzinfo=None)
    except (ValueError, TypeError):
        return ""
    secs = (dl - datetime.now()).total_seconds()
    if secs <= 0:
        return ""
    h = secs / 3600
    if h < 1:
        return f"🔥 Còn {int(secs / 60)}p"
    if h < 4:
        return f"🔥 Còn {int(h)}h"
    if h < 24:
        return f"⚠️ Còn {int(h)}h"
    return ""


# ─── Markdown helpers ─────────────────────────────────────────────────────────

def _md(text: str) -> str:
    """Escape HTML special chars for Telegram HTML parse_mode."""
    import html as _html
    return _html.escape(str(text))


# ─── Time helpers ──────────────────────────────────────────────────────────────

def _fmt_time(dt: datetime) -> str:
    """HH:MM"""
    return dt.strftime("%H:%M")


def _fmt_date(dt: datetime) -> str:
    """DD·MM"""
    return dt.strftime("%d·%m")


def _time_until(dt: datetime) -> str:
    """'còn Xh Ym' hoặc 'còn Xp'"""
    delta = dt - datetime.now()
    secs = delta.total_seconds()
    if secs <= 0:
        return "đã qua"
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    if h > 0:
        return f"còn {h}h {m:02d}p" if m else f"còn {h}h"
    return f"còn {m}p"


def _time_over(dt: datetime) -> str:
    """'trễ Xh' hoặc 'trễ X ngày'"""
    delta = datetime.now() - dt
    secs = delta.total_seconds()
    h = int(secs // 3600)
    d = delta.days
    if d >= 1:
        return f"trễ {d} ngày"
    return f"trễ {h}h"


_DOW = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _deadline_line(deadline_iso: str | None, verbose: bool = False) -> str:
    """One-line deadline chip with day-of-week.
    verbose=True thêm '(còn N ngày/h)' — dùng cho task card, không dùng cho list rows.
    """
    if not deadline_iso:
        return ""
    try:
        dl    = datetime.fromisoformat(deadline_iso).replace(tzinfo=None)
        now   = datetime.now()
        delta = dl - now
        secs  = delta.total_seconds()
        dow   = _DOW[dl.weekday()]
        t     = _fmt_time(dl)
        d     = dl.strftime("%d/%m")

        if secs < 0:
            return f"⚠️ {_time_over(dl)}"
        elif secs < 3600:
            mins = int(secs / 60)
            return f"🔴 Còn {mins}p · {t}"
        elif secs < 4 * 3600:
            h = int(secs / 3600)
            suffix = f" (còn {h}h)" if verbose else ""
            return f"⏰ Hôm nay {t}{suffix}"
        elif dl.date() == now.date():
            h = int(secs / 3600)
            suffix = f" (còn {h}h)" if verbose else ""
            return f"⏰ Hôm nay {t}{suffix}"
        elif delta.days == 1:
            suffix = " (còn 1 ngày)" if verbose else ""
            return f"⏰ Mai {dow} · {t}{suffix}"
        else:
            suffix = f" (còn {delta.days} ngày)" if verbose else ""
            return f"📅 {dow} {d} · {t}{suffix}"
    except (ValueError, TypeError):
        return ""


# ─── Task inline format (list rows) ──────────────────────────────────────────

def fmt_task_line(
    task: dict,
    show_assignee: bool = False,
    show_quadrant: bool = True,
) -> str:
    """
    Compact single-line: `🔴 ▪ #42 Tên task  ◷ còn 3h`
    show_quadrant=False để ẩn Eisenhower icon.
    """
    p    = task.get("priority", "P3")
    icon = PRIORITY_ICON.get(p, "□")
    q_prefix = eisenhower_icon(task) + " " if show_quadrant else ""
    line = f"{q_prefix}{icon} <code>#{task['id']}</code> {task.get('summary','')[:60]}"
    if show_assignee and task.get("assignee_name"):
        short = task["assignee_name"].split()[-1]
        line += f"  [{short}]"
    dl = _deadline_line(task.get("deadline") or task.get("deadline_iso"))
    if dl:
        line += f"  {dl}"
    return line


# ─── 2.1 / 2.2  Task được giao ────────────────────────────────────────────────

def msg_task_new(task: dict, assigned_by_name: str = "") -> str:
    """Tin nhắn khi task mới được giao tới member — Layer 1 coaching.

    Render quick-start steps (breakdown từ classifier_meta) ngay trong card.
    Nếu assignee muốn hướng dẫn sâu hơn → bấm nút '🎓 Hướng dẫn chi tiết'
    (Layer 2 — gắn ngoài bởi caller).
    """
    p       = task.get("priority", "P3")
    icon    = PRIORITY_ICON.get(p, "□")
    cat     = CAT_LABEL.get(task.get("category", "other"), "Khác")
    dl      = _deadline_line(task.get("deadline"))

    meta_parts = [f"{icon} {p}", cat]
    if dl:
        meta_parts.append(dl)
    if assigned_by_name:
        meta_parts.append(f"từ {assigned_by_name}")

    # Extract OKR ref + breakdown from classifier_meta
    okr_ref = ""
    breakdown: list = []
    try:
        import json as _j
        meta = task.get("classifier_meta") or {}
        if isinstance(meta, str):
            meta = _j.loads(meta)
        if isinstance(meta, dict):
            okr_ref = meta.get("okr_ref") or meta.get("okr_tag") or task.get("okr_ref", "")
            breakdown = meta.get("breakdown") or []
    except Exception:
        pass

    _q_task = {"priority": p, "deadline": task.get("deadline"), "okr_ref": okr_ref}
    q_icon  = eisenhower_icon(_q_task)

    lines = [
        f"📬 <b>Task mới · {p}</b>",
        "",
        f"{q_icon} <code>#{task['id']}</code> <b>{_md(task.get('summary', ''))}</b>",
        "",
        "  ·  ".join(meta_parts),
    ]
    if okr_ref:
        lines.append(f"🎯 OKR · {okr_ref}")

    # Manager's own guidance — overrides generic AI coaching when Huy edited it.
    mnote = task.get("manager_note")
    if not mnote and isinstance(meta, dict):
        mnote = meta.get("manager_note")
    if mnote:
        who = assigned_by_name or "quản lý"
        lines += ["", f"📝 <b>Hướng dẫn từ {_md(who)}:</b>", _md(str(mnote))]

    # Layer 1 coaching — concise steps inline (3-5 bullets from AI breakdown)
    if breakdown:
        lines += ["", "📋 <b>Bắt đầu thế nào:</b>"]
        for step in breakdown[:5]:
            lines.append(f"▸ {_md(str(step))}")

    lines += [
        "",
        f"<code>/done {task['id']}</code> xong · <code>/snooze {task['id']} 2h</code> hoãn · "
        f"<code>/coach {task['id']}</code> hướng dẫn",
    ]

    return "\n".join(lines)


# ─── 2.3  Confirm nhận task ───────────────────────────────────────────────────

def msg_task_accepted(task: dict) -> str:
    """Xác nhận đã nhận task."""
    dl = _deadline_line(task.get("deadline"))
    dl_part = f"\n{dl}" if dl else ""
    return (
        f"● Đã nhận\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"<code>#{task['id']}</code> {task.get('summary','')[:70]}"
        f"{dl_part}"
    )


# ─── 2.5  Chuyển task ────────────────────────────────────────────────────────

def msg_task_transferred(task: dict, from_name: str, to_name: str, reason: str = "") -> str:
    reason_line = f"\nLý do: {reason}" if reason else ""
    return (
        f"↗ Đã chuyển\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"<code>#{task['id']}</code>\n"
        f"<code>{from_name}</code> → <code>{to_name}</code>"
        f"{reason_line}"
    )


# ─── 2.7  Assigner xác nhận giao task ───────────────────────────────────────

def msg_assign_confirm(task_id: int, assignee_name: str, result: dict) -> str:
    """Gửi lại cho người giao sau khi task được tạo thành công."""
    p        = result.get("priority", "P2")
    p_emoji  = PRIORITY_EMOJI.get(p, "⚪")
    cat      = CAT_LABEL.get(result.get("category", "other"), "Khác")
    summary  = result.get("summary", "") or "(chưa có nội dung)"
    dl       = _deadline_line(result.get("deadline_iso"))
    dl_urg   = _deadline_urgency(result.get("deadline_iso"))
    okr_lbl  = _okr_label(result.get("okr_ref"))
    conf     = result.get("assignee_confidence", result.get("confidence", 0))
    conf_str = f"  ·  AI {int(conf*100)}%" if conf else ""
    est      = result.get("estimated_minutes") or 0
    clean    = _clean_name(assignee_name)

    # Eisenhower quadrant icon for the task title
    _q_task = {
        "priority": p,
        "deadline": result.get("deadline_iso"),
        "okr_ref":  result.get("okr_ref", ""),
    }
    q_icon = eisenhower_icon(_q_task)

    meta_parts = [f"{p_emoji} {p}", cat]
    if dl:
        meta_parts.append(dl)  # _deadline_line already includes ⏰/🔴/📅 icon
    if okr_lbl:
        meta_parts.append(f"🎯 {okr_lbl}")

    lines = [
        f"● <b>Task #{task_id}</b> → <b>{_md(clean)}</b>{conf_str}",
        DIV_LIGHT,
        "",
        f"{q_icon} <b>{_md(summary)}</b>",
        "",
        "  ·  ".join(meta_parts),
    ]

    # Estimated time + deadline urgency on a second meta-row
    extras = []
    if est:
        extras.append(f"⏱ ~{est} phút")
    if dl_urg:
        extras.append(dl_urg)
    if extras:
        lines.append("  ·  ".join(extras))

    steps = result.get("breakdown", [])
    if steps:
        lines += ["", "📋 <b>Đề xuất các bước:</b>"]
        for s in steps[:5]:
            lines.append(f"▸ {_md(str(s))}")

    return "\n".join(lines)


def msg_auto_assigned(
    task_id: int, assignee_name: str, result: dict, undo_window_min: int = 60,
) -> str:
    """
    Bot tự tạo task → 1-line confirmation gửi cho manager.
    Đi kèm inline keyboard [↶ Undo] [↗ Đổi người] bên ngoài.
    """
    p        = result.get("priority", "P2")
    icon     = PRIORITY_ICON.get(p, "□")
    summary  = (result.get("summary") or "")[:80]
    dl       = _deadline_line(result.get("deadline_iso"))
    okr      = result.get("okr_ref", "")
    conf     = int(result.get("assignee_confidence", 0) * 100)

    bits = [f"{icon} {p}"]
    if dl:
        bits.append(dl)
    if okr:
        bits.append(f"OKR {okr}")

    return (
        f"🤖 <b>Auto</b> <code>#{task_id}</code> → <b>{_md(assignee_name)}</b> (AI {conf}%)\n"
        f"{_md(summary)}\n"
        f"{'  ·  '.join(bits)}\n"
        f"<i>Undo trong {undo_window_min}p nếu sai.</i>"
    )


def msg_coach_detail(task: dict, coach: dict) -> str:
    """
    Layer 2 — chi tiết coaching cho assignee sau khi bấm '🎓 Hướng dẫn chi tiết'.

    `task`  : dict từ DB (cần id, summary, priority, deadline)
    `coach` : output của classifier.coach_task()
              {why_matters, steps, watch_out, tips, contacts, estimated_minutes}
    """
    tid     = task.get("id", "?")
    summary = task.get("summary", "")[:90]
    p       = task.get("priority", "P3")
    icon    = PRIORITY_ICON.get(p, "□")
    est     = coach.get("estimated_minutes") or task.get("estimated_minutes") or 0

    lines = [
        f"🎓 <b>Hướng dẫn chi tiết — Task #{tid}</b>",
        DIV_LIGHT,
        f"{icon} {p} · <b>{_md(summary)}</b>",
    ]
    if est:
        lines.append(f"<i>~{est} phút</i>")

    why = coach.get("why_matters", "").strip()
    if why:
        lines += ["", "💡 <b>Tại sao quan trọng</b>", _md(why)]

    steps = coach.get("steps") or []
    if steps:
        lines += ["", f"📋 <b>{len(steps)} bước cụ thể</b>"]
        for i, s in enumerate(steps[:6], 1):
            lines.append(f"{i}. {_md(str(s))}")

    watch = coach.get("watch_out") or []
    if watch:
        lines += ["", "⚠️ <b>Watch out</b>"]
        for w in watch[:4]:
            lines.append(f"• {_md(str(w))}")

    tips = coach.get("tips", "").strip()
    if tips:
        lines += ["", f"💎 <b>Tip</b>: {_md(tips)}"]

    contacts = coach.get("contacts") or []
    if contacts:
        lines += ["", "📎 <b>Cần hỗ trợ</b>"]
        for c in contacts[:4]:
            if not isinstance(c, dict):
                continue
            name = c.get("name", "?")
            email = c.get("email", "")
            when = c.get("when", "")
            line = f"• <b>{_md(name)}</b>"
            if email:
                line += f" (<code>{_md(email)}</code>)"
            if when:
                line += f" — {_md(when)}"
            lines.append(line)

    lines += [
        "",
        f"<i><code>/done {tid}</code> xong · <code>/snooze {tid} 2h</code> hoãn</i>",
    ]
    return "\n".join(lines)


def msg_auto_digest_manager(tasks: list[dict]) -> str:
    """
    17h daily digest gửi cho manager — list tất cả task bot tự tạo trong ngày,
    grouped by assignee. Mỗi task hiển thị id, summary ngắn, OKR ref, deadline.
    Inline buttons reassign per-task được thêm ngoài (do scheduler tạo).
    """
    if not tasks:
        return "🤖 <b>Auto-digest hôm nay</b>\n\nKhông có task nào bot tự tạo."

    # Group by assignee
    by_person: dict[str, list[dict]] = {}
    for t in tasks:
        name = t.get("assignee_name") or "?"
        by_person.setdefault(name, []).append(t)

    today = datetime.now().strftime("%d/%m")
    lines = [
        f"🤖 <b>Auto-digest {today}</b> — {len(tasks)} task bot tự tạo",
        DIV_LIGHT,
    ]

    for person, items in by_person.items():
        lines.append(f"\n<b>{_md(person)}</b> ({len(items)})")
        for t in items[:5]:
            p_icon = PRIORITY_ICON.get(t.get("priority", "P3"), "□")
            summary = (t.get("summary") or "")[:55]
            dl = _deadline_line(t.get("deadline")) if t.get("deadline") else ""
            okr = t.get("classifier_meta", {})
            okr_ref = ""
            if isinstance(okr, dict):
                okr_ref = okr.get("okr_ref", "") or ""
            elif isinstance(okr, str):
                try:
                    import json as _j
                    okr_ref = _j.loads(okr).get("okr_ref", "") or ""
                except Exception:
                    pass
            extras = []
            if dl:
                extras.append(dl)
            if okr_ref:
                extras.append(f"OKR {okr_ref}")
            extra_str = "  ·  " + "  ·  ".join(extras) if extras else ""
            lines.append(f"  {p_icon} <code>#{t['id']}</code> {_md(summary)}{extra_str}")

    lines.append(
        f"\n<i>Bấm nút bên dưới để giao lại nếu sai person.</i>"
        f"\n<i>Dùng <code>/undo &lt;id&gt;</code> để hủy hẳn.</i>"
    )
    return "\n".join(lines)


def msg_ai_route_card(result: dict, assigner_name: str = "") -> str:
    """AI đề xuất người nhận — kèm inline keyboard bên ngoài."""
    p        = result.get("priority", "P2")
    icon     = PRIORITY_ICON.get(p, "□")
    cat      = CAT_LABEL.get(result.get("category", "other"), "Khác")
    summary  = result.get("summary", "") or "(chưa có nội dung)"
    assignee = result.get("assignee_name", "?")
    dl       = _deadline_line(result.get("deadline_iso"))
    okr      = result.get("okr_ref", "")
    in_scope = result.get("in_scope", True)
    conf     = int(result.get("assignee_confidence", 0) * 100)
    steps    = result.get("breakdown", [])

    meta_parts = [f"{icon} {p}", cat]
    if dl:
        meta_parts.append(dl)
    if okr:
        meta_parts.append(f"OKR {okr}")

    scope_line = (
        "" if in_scope
        else f"\n▲ {result.get('scope_note', 'Ngoài scope thông thường')}"
    )
    step_block = ""
    if steps:
        step_block = "\n\ngợi ý:\n" + "\n".join(
            f"{i}. {s}" for i, s in enumerate(steps[:3], 1)
        )

    note = result.get("manager_note")
    note_block = f"\n\n📝 <b>Ghi chú:</b> {_md(str(note))}" if note else ""
    header = "✏️ <b>Đã sửa</b>" if result.get("edited") else f"🤖 <b>AI đề xuất · {conf}%</b>"

    return (
        f"{header}\n"
        f"\n"
        f"<b>{_md(summary)}</b>\n"
        f"\n"
        f"→ <b>{_md(assignee)}</b>\n"
        + "  ·  ".join(meta_parts)
        + scope_line
        + step_block
        + note_block
        + "\n\n<i>Sửa nội dung / ghi chú / ưu tiên / deadline bằng nút bên dưới trước khi giao.</i>"
    )


# ─── 2.8  Tạo task nhanh ─────────────────────────────────────────────────────

_ADHOC_CATS = {"ops", "admin", "meeting", "vendor", "other"}
_ADHOC_CAP  = int(__import__("os").getenv("ADHOC_CAP", "15"))


def msg_task_created(
    task_id: int,
    result: dict,
    text: str,
    assignee_name: str = "",
    is_self: bool = True,
    adhoc_ratio: dict | None = None,
) -> str:
    """Xác nhận tạo task — rich card layout."""
    p        = result.get("priority", "P3")
    p_emoji  = PRIORITY_EMOJI.get(p, "⚪")
    cat      = CAT_LABEL.get(result.get("category", "other"), "Khác")
    conf     = result.get("confidence", result.get("classifier_confidence", 0))
    conf_str = f"AI {int(conf * 100)}%" if conf else ""
    summary  = result.get("summary") or text[:120]
    dl       = _deadline_line(result.get("deadline_iso"), verbose=True)
    dl_urg   = _deadline_urgency(result.get("deadline_iso"))
    est      = result.get("estimated_minutes") or 0
    okr_lbl  = _okr_label(result.get("okr_ref"))
    steps    = result.get("breakdown", [])

    name             = _clean_name(assignee_name) or "?"
    assignee_display = f"{name} (self)" if is_self else name
    if conf_str:
        assignee_display += f" · {conf_str}"

    # Eisenhower quadrant icon — hiện trên card để member biết ưu tiên ngay
    _q_task = {
        "priority": p,
        "deadline": result.get("deadline_iso"),
        "okr_ref":  result.get("okr_ref", ""),
    }
    q_icon = eisenhower_icon(_q_task)

    # ── Meta row 1: priority + category + OKR ──
    meta_parts = [f"{p_emoji} {p}", cat]
    if okr_lbl:
        meta_parts.append(f"🎯 {okr_lbl}")

    # ── Meta row 2: time + deadline + urgency ──
    time_parts = []
    if est:
        time_parts.append(f"⏱ ~{est} phút")
    if dl:
        time_parts.append(dl)  # _deadline_line already includes icon
    if dl_urg:
        time_parts.append(dl_urg)

    lines = [
        f"✅ <b>Task #{task_id}</b>",
        DIV_LIGHT,
        "",
        f"{q_icon} <b>{_md(summary)}</b>",
        "",
        "  ·  ".join(meta_parts),
    ]
    if time_parts:
        lines.append("  ·  ".join(time_parts))
    lines.append(f"👤 {_md(assignee_display)}")

    if steps:
        lines += ["", "📋 <b>Đề xuất các bước:</b>"]
        for s in steps[:5]:
            lines.append(f"▸ {_md(str(s))}")

    if adhoc_ratio and adhoc_ratio.get("ratio_pct", 0) > _ADHOC_CAP:
        r = adhoc_ratio["ratio_pct"]
        lines += ["", f"⚠️ <i>Ad-hoc tuần này: {r}% (vượt cap {_ADHOC_CAP}%)</i>"]

    return "\n".join(lines)


# ─── 2.9  Done confirm ─────────────────────────────────────────────────────────

def msg_task_done(task: dict, next_task: dict | None = None) -> str:
    """Xác nhận task hoàn thành."""
    tid     = task.get("id", "?")
    summary = task.get("summary", "")[:70]

    next_block = ""
    if next_task:
        p  = next_task.get("priority", "P3")
        dl = _deadline_line(next_task.get("deadline"))
        dl_part = f"  {dl}" if dl else ""
        next_block = (
            f"\nTASK TIẾP THEO\n"
            f"{PRIORITY_ICON.get(p,'□')} <code>#{next_task['id']}</code> "
            f"{next_task.get('summary','')[:55]}{dl_part}\n"
        )

    return (
        f"● Hoàn thành\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"<code>#{tid}</code> {summary}"
        f"{next_block}"
    )


# ─── 3.1 / 3.3  Reminders ────────────────────────────────────────────────────

def msg_reminder_deadline(task: dict, hours_left: float) -> str:
    """Nhắc deadline sắp tới."""
    tid     = task.get("id", "?")
    summary = task.get("summary", "")[:100]
    p       = task.get("priority", "P3")
    icon    = PRIORITY_ICON.get(p, "□")
    dl      = _deadline_line(task.get("deadline"))

    if hours_left <= 0.25:
        header = f"🔴 <b>Còn {int(hours_left * 60)}p</b>"
    elif hours_left <= 4:
        header = f"🔴 <b>Còn {int(hours_left)}h</b>"
    elif hours_left <= 28:
        header = "⏰ <b>Deadline hôm nay / mai</b>"
    else:
        header = "📅 <b>Nhắc trước 3 ngày</b>"

    return (
        f"{header}\n"
        f"\n"
        f"{icon} <code>#{tid}</code> <b>{_md(summary)}</b>\n"
        f"{dl}\n"
        f"\n"
        f"<code>/done {tid}</code> xong · <code>/snooze {tid} 2h</code> hoãn"
    )


def msg_overdue(task: dict, hours_over: float) -> str:
    """Task quá hạn."""
    tid     = task.get("id", "?")
    summary = task.get("summary", "")[:70]
    p       = task.get("priority", "P3")
    icon    = PRIORITY_ICON.get(p, "□")
    divider = DIV_STRONG if p in ("P0", "P1") else DIV_LIGHT
    over_str = f"{int(hours_over)}h" if hours_over < 48 else f"{int(hours_over // 24)} ngày"

    return (
        f"{icon} QUÁ HẠN\n"
        f"{divider}\n"
        f"\n"
        f"<code>#{tid}</code> {summary}\n"
        f"\n"
        f"Trễ: {over_str}\n"
        f"\n"
        f"<code>/done {tid}</code> xong · <code>/snooze {tid} 4h</code> xin gia hạn"
    )


def msg_assigner_alert(
    assignee_name: str,
    task: dict,
    hours_over: float | None = None,
    hours_left: float | None = None,
) -> str:
    """Nhắc NGƯỜI GIAO khi việc họ giao cho người khác sắp trễ / đã trễ.

    Dùng cho scheduler 'nhắc 2 chiều' — manager/TL biết việc mình delegate đang
    có nguy cơ rớt mà không cần hỏi tay từng người."""
    tid     = task.get("id", "?")
    summary = task.get("summary", "")[:70]
    p       = task.get("priority", "P3")
    icon    = PRIORITY_ICON.get(p, "□")
    who     = _md((assignee_name or "?").strip())

    if hours_over is not None and hours_over > 0:
        over_str = f"{int(hours_over)}h" if hours_over < 48 else f"{int(hours_over // 24)} ngày"
        divider  = DIV_STRONG if p in ("P0", "P1") else DIV_LIGHT
        return (
            f"⚠ <b>Việc bạn giao đang TRỄ</b>\n"
            f"{divider}\n"
            f"\n"
            f"{icon} <code>#{tid}</code> {_md(summary)}\n"
            f"Người làm: <b>{who}</b> · trễ {over_str}\n"
            f"\n"
            f"<code>/assign</code> giao lại · nhắc <b>{who}</b> hoặc gỡ vướng giúp."
        )

    # Sắp tới hạn (chưa trễ)
    left = hours_left if hours_left is not None else 0
    left_str = f"{int(left * 60)}p" if left < 1 else f"{int(left)}h"
    return (
        f"⏰ <b>Việc bạn giao sắp tới hạn</b>\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"{icon} <code>#{tid}</code> {_md(summary)}\n"
        f"Người làm: <b>{who}</b> · còn {left_str}\n"
        f"\n"
        f"Theo dõi giúp để không rớt."
    )


def msg_stalled(task: dict) -> str:
    """Task không có update trong N ngày."""
    tid     = task.get("id", "?")
    summary = task.get("summary", "")[:70]
    return (
        f"◌ Chưa có cập nhật\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"<code>#{tid}</code> {summary}\n"
        f"\n"
        f"Task im lặng. Cần gì không?\n"
        f"Reply hoặc <code>/done {tid}</code>"
    )


# ─── 4.1  Morning briefing Manager ────────────────────────────────────────────

def msg_morning_manager(
    manager_name: str,
    stats: dict,
    members: list[dict],
    overdue_tasks: list[dict],
) -> str:
    """Manager digest 08:00."""
    now    = datetime.now()
    wday   = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"][now.weekday()]
    date_s = _fmt_date(now)

    active  = stats.get("active", 0)
    done_t  = stats.get("done_today", 0)
    overdue = stats.get("overdue", 0)
    blocked = stats.get("blocked", 0)
    summary = f"{active} task · {done_t} xong · {overdue} trễ · {blocked} blocked"

    member_rows = []
    for m in members:
        ov = m.get("overdue_count", 0)
        ac = m.get("active_count", 0)
        bl = m.get("blocked_count", 0)
        ind = "▲" if ov > 0 else ("━" if ac > 7 else "·")
        row = f"{ind} {m['full_name']} — {ac} task"
        if ov:
            row += f", {ov} trễ"
        if bl:
            row += f", {bl} blocked"
        member_rows.append(row)

    overdue_block = ""
    if overdue_tasks:
        rows = [fmt_task_line(t, show_assignee=True) for t in overdue_tasks[:5]]
        overdue_block = "\nCẦN XỬ LÝ\n" + "\n".join(rows) + "\n"

    return (
        f"{AI_SIG} · BÁO CÁO SÁNG\n"
        f"{wday} {date_s}\n"
        f"{DIV_STRONG}\n"
        f"\n"
        f"Chào sáng, {manager_name}.\n"
        f"\n"
        f"TỔNG QUAN\n"
        f"{summary}\n"
        f"\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"TEAM\n"
        + "\n".join(member_rows)
        + f"\n"
        f"{overdue_block}"
        f"{DIV_LIGHT}\n"
        f"/team · /pending · /assign"
    )


# ─── 4.2  Morning briefing Member ─────────────────────────────────────────────

def msg_morning_member(
    name: str,
    overdue_tasks: list[dict],
    top_tasks: list[dict],
    okr_note: str = "",
) -> str:
    """
    Member briefing 08:00 — task list grouped by Eisenhower quadrant.
    overdue_tasks: list from get_overdue_tasks_for_user()
    top_tasks    : list from get_top_tasks_for_user() — today's priority tasks
    """
    now    = datetime.now()
    wday   = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"][now.weekday()]
    date_s = _fmt_date(now)

    all_tasks = list(overdue_tasks) + list(top_tasks)

    if not all_tasks:
        return (
            f"{AI_SIG} · {wday} {date_s}\n"
            f"{DIV_STRONG}\n"
            f"\n"
            f"Chào sáng, {name}.\n"
            f"\n"
            f"Queue trống — không có task nào hôm nay.\n"
            f"/add <nội dung> để tạo task mới."
        )

    # Force overdue → Q1
    overdue_ids = {t["id"] for t in overdue_tasks}
    groups = _group_by_quadrant(all_tasks)
    for q in ("Q2", "Q3", "Q4"):
        moved    = [t for t in groups[q] if t["id"] in overdue_ids]
        kept     = [t for t in groups[q] if t["id"] not in overdue_ids]
        groups["Q1"] = moved + groups["Q1"]
        groups[q]    = kept

    q1_n = len(groups["Q1"])
    q2_n = len(groups["Q2"])

    lines = [
        f"☀️ <b>{wday} {date_s}</b>",
        "",
        f"Chào sáng, <b>{name}</b>.",
        "",
    ]

    # Quick summary line
    summary_parts = []
    if q1_n:
        summary_parts.append(f"🔴 {q1_n} cần làm ngay")
    if q2_n:
        summary_parts.append(f"🟡 {q2_n} lên kế hoạch")
    for q in ("Q3", "Q4"):
        n = len(groups[q])
        if n:
            summary_parts.append(f"{EISENHOWER[q]['icon']} {n} {EISENHOWER[q]['label'].lower()}")
    if summary_parts:
        lines.append("  ·  ".join(summary_parts))
        lines.append("")

    lines.append(DIV_LIGHT)
    lines.append("")

    # Quadrant sections — Q1 & Q2 always shown; Q3/Q4 only if non-empty
    for q in ("Q1", "Q2", "Q3", "Q4"):
        block = _quadrant_block(q, groups[q], max_tasks=4)
        if block:
            lines.append(block)
            lines.append("")

    if okr_note:
        lines += [DIV_LIGHT, "", okr_note, ""]

    lines += [DIV_LIGHT, "<code>/done &lt;id&gt;</code> · <code>/snooze &lt;id&gt; 2h</code> · <code>/today</code>"]
    return "\n".join(lines)


# ─── 4.3  Evening summary Member ──────────────────────────────────────────────

def _progress_bar(done: int, total: int, width: int = 8) -> str:
    if total == 0:
        return "░" * width
    filled = max(0, min(width, round(done / total * width)))
    return "█" * filled + "░" * (width - filled)


def msg_evening_member(
    name: str,
    done_count: int,
    total_count: int,
    pending_tomorrow: list[dict],
) -> str:
    now  = datetime.now()
    wday = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"][now.weekday()]
    pct  = int(done_count / total_count * 100) if total_count else 0
    bar  = _progress_bar(done_count, total_count)

    # Contextual note based on completion rate
    if total_count == 0:
        note = "Hôm nay không có task — nghỉ ngơi tốt! 🙌"
    elif pct >= 80:
        note = f"Tốt lắm! Hoàn thành {pct}% task hôm nay 💪"
    elif pct >= 50:
        note = f"Xong {pct}% — còn {total_count - done_count} task chuyển sang mai."
    else:
        note = f"Hôm nay bận — {total_count - done_count} task còn lại, ưu tiên Q1 sáng sớm nhé."

    lines = [
        f"🌇 <b>{wday} {now.strftime('%d/%m')} · {now.strftime('%H:%M')}</b>",
        "",
        f"<b>{name.split()[0]}</b> · {note}",
        "",
        f"Hôm nay: <code>{bar}</code> {done_count}/{total_count} task",
    ]

    if pending_tomorrow:
        lines += ["", "📋 <b>Ngày mai:</b>"]
        for t in pending_tomorrow[:4]:
            lines.append(fmt_task_line(t))
        lines.append("")
        lines.append("<i>/done &lt;id&gt; · /snooze &lt;id&gt; 2h · /today</i>")

    return "\n".join(lines)


# ─── 4.4  EOD Team (Manager) ─────────────────────────────────────────────────

def msg_eod_manager(
    stats: dict,
    members: list[dict],
    overdue_tasks: list[dict],
    top_pending: list[dict] | None = None,
) -> str:
    """
    Manager nhận cuối ngày — team health + member status + tomorrow preview.
    stats        = get_team_stats()
    members      = list_team_by_person()
    overdue_tasks= list of overdue task dicts (all team)
    top_pending  = top Q1/Q2 tasks pending (optional, for tomorrow preview)
    """
    now        = datetime.now()
    wday       = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","CN"][now.weekday()]
    done_today = stats.get("done_today", 0)
    active     = stats.get("active", 0)
    overdue    = stats.get("overdue", 0)
    total      = done_today + active
    bar        = _progress_bar(done_today, total)

    # Health signal
    if overdue == 0 and done_today >= active:
        health = "✅ Team on track"
    elif overdue <= 2:
        health = f"⚠️ {overdue} task trễ — cần theo dõi"
    else:
        health = f"🔴 {overdue} task trễ — cần can thiệp ngay"

    lines = [
        f"🌇 <b>EOD Report · {wday} {now.strftime('%d/%m')} · {now.strftime('%H:%M')}</b>",
        "",
        health,
        f"<code>{bar}</code> {done_today} xong · {active} đang chạy" + (f" · ‼️ {overdue} trễ" if overdue else ""),
        "",
        DIV_LIGHT,
        "",
        "👥 <b>Team hôm nay</b>",
    ]

    # Per-member status — one per line, readable
    for m in members:
        a   = m.get("active_count", 0)
        od  = m.get("overdue_count", 0)
        dt  = m.get("done_today", 0)
        name = m.get("full_name", "?").split()[-1]

        if od >= 2:
            status_icon = "🔴"
        elif od == 1:
            status_icon = "🟠"
        elif dt > 0 and a == 0:
            status_icon = "✅"
        elif dt > 0:
            status_icon = "🟡"
        else:
            status_icon = "⚪"

        parts = [f"{status_icon} <b>{name}</b>"]
        if dt:
            parts.append(f"✅{dt}")
        if a:
            parts.append(f"🔄{a}")
        if od:
            parts.append(f"‼️{od} trễ")
        if dt == 0 and a == 0:
            parts.append("<i>(không có task)</i>")
        lines.append("  ".join(parts))

    # Overdue section
    if overdue_tasks:
        lines += ["", DIV_LIGHT, "", f"‼️ <b>Cần xử lý sáng mai ({len(overdue_tasks)})</b>"]
        for t in overdue_tasks[:6]:
            lines.append(fmt_task_line(t, show_assignee=True))

    # Tomorrow's top priorities (Q1/Q2 tasks pending)
    if top_pending:
        q1q2 = [t for t in top_pending
                if eisenhower_quadrant(t) in ("Q1", "Q2")][:5]
        if q1q2:
            lines += ["", DIV_LIGHT, "", "📋 <b>Ưu tiên sáng mai</b>"]
            for t in q1q2:
                lines.append(fmt_task_line(t, show_assignee=True))

    lines += ["", DIV_LIGHT, "/brief · /team · /pending"]
    return "\n".join(lines)


# ─── Eisenhower grouping helper ───────────────────────────────────────────────

def _group_by_quadrant(tasks: list[dict]) -> dict[str, list[dict]]:
    """Group tasks list into {Q1: [...], Q2: [...], Q3: [...], Q4: [...]}."""
    groups: dict[str, list[dict]] = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    for t in tasks:
        groups[eisenhower_quadrant(t)].append(t)
    return groups


def _quadrant_block(q: str, tasks: list[dict], max_tasks: int = 6) -> str:
    """Single quadrant section: header + task rows."""
    if not tasks:
        return ""
    meta  = EISENHOWER[q]
    n     = len(tasks)
    extra = f" +{n - max_tasks}" if n > max_tasks else ""
    rows  = [fmt_task_line(t, show_quadrant=False) for t in tasks[:max_tasks]]
    return (
        f"{meta['icon']} {meta['label']} ({n}{extra})\n"
        + "\n".join(rows)
    )


def msg_mytasks(name: str, tasks: list[dict]) -> str:
    """All pending tasks for a user, grouped by Eisenhower quadrant (Q1→Q4).

    Replaces the old flat list — surfaces what to do FIRST instead of a wall."""
    n = len(tasks)
    if n == 0:
        return (
            f"✓ <b>{name.split()[0]}</b> — sạch bảng!\n"
            f"{DIV_LIGHT}\n\nKhông có task pending. "
            f"Gõ <code>/add &lt;nội dung&gt;</code> để tạo task mới."
        )

    groups = _group_by_quadrant(tasks)
    lines = [
        f"📋 <b>Task của {name.split()[0]}</b> — {n} pending",
        DIV_LIGHT,
    ]
    for q in ("Q1", "Q2", "Q3", "Q4"):
        block = _quadrant_block(q, groups[q])
        if block:
            lines += ["", block]
    lines += [
        "",
        "<i>👉 /now để bot chọn việc nên làm trước · "
        "/done &lt;id&gt; · /snooze &lt;id&gt; 2h</i>",
    ]
    return "\n".join(lines)


def msg_my_stats(
    name: str,
    done_week: int,
    pending: int,
    overdue: int,
    top_tasks: list[dict] | None = None,
) -> str:
    """Personal weekly stats with a visual progress bar + next-up preview."""
    total = done_week + pending
    pct   = int(done_week / total * 100) if total else 0
    bar   = _progress_bar(done_week, total)

    if total == 0:
        note = "Chưa có task tuần này."
    elif overdue > 0:
        note = f"⚠ {overdue} task quá hạn — ưu tiên giải tỏa trước."
    elif pct >= 80:
        note = f"💪 Tiến độ tốt — {pct}% tuần này."
    else:
        note = f"Còn {pending} task pending — gõ /now để chọn việc tiếp theo."

    lines = [
        f"📊 <b>Thống kê · {name.split()[0]}</b>",
        DIV_LIGHT,
        "",
        f"Tuần này: <code>{bar}</code> {done_week}/{total} ({pct}%)",
        f"● {done_week} hoàn thành   ○ {pending} pending"
        + (f"   ‼ {overdue} quá hạn" if overdue else ""),
        "",
        f"<i>{note}</i>",
    ]

    if top_tasks:
        lines += ["", "🎯 <b>Nên làm tiếp:</b>"]
        for t in top_tasks[:3]:
            lines.append(fmt_task_line(t))

    return "\n".join(lines)


def _period_label(days: int) -> str:
    if days >= 360:
        return f"{round(days / 365)} năm" if days >= 365 else "~1 năm"
    if days >= 28:
        return f"{round(days / 30)} tháng"
    if days >= 7:
        return f"{round(days / 7)} tuần"
    return f"{days} ngày"


def msg_member_performance(name: str, perf: dict) -> str:
    """Báo cáo hiệu suất 1 thành viên trong khoảng `days` — dùng cho /perf + đánh giá.

    Pyramid: chấm điểm tổng trước, chi tiết sau. Số liệu đều từ data thật."""
    days   = perf.get("days", 30)
    period = _period_label(days)
    done   = perf.get("done", 0)
    on_pct = perf.get("on_time_pct")
    comp   = perf.get("completion_pct")

    # Đánh giá nhanh (chỉ khi đủ data)
    if done == 0:
        verdict = "Chưa có task hoàn thành trong kỳ — chưa đủ data để đánh giá."
    elif on_pct is not None and on_pct >= 85 and done >= 5:
        verdict = f"💪 Đáng tin — đúng hạn {on_pct}%, hoàn thành {done} task."
    elif on_pct is not None and on_pct < 60:
        verdict = f"⚠ Đúng hạn chỉ {on_pct}% — cần xem lại tải việc / deadline."
    else:
        verdict = f"Ổn định — {done} task xong trong {period}."

    def _v(x, suffix=""):
        return f"{x}{suffix}" if x is not None else "—"

    cyc = perf.get("avg_cycle_h")
    cyc_str = (f"{cyc}h" if cyc is not None and cyc < 48
               else (f"{round(cyc / 24, 1)} ngày" if cyc is not None else "—"))
    hrs = round(perf.get("actual_minutes", 0) / 60, 1)

    lines = [
        f"📈 <b>Hiệu suất · {_md(name)}</b>",
        f"<i>Kỳ: {period} gần nhất</i>",
        DIV_STRONG,
        "",
        f"<i>{verdict}</i>",
        "",
        "<b>Throughput</b>",
        f"  · Hoàn thành: <b>{done}</b> / giao {perf.get('assigned', 0)} "
        + (f"({comp}%)" if comp is not None else ""),
        f"  · P0 xong: {perf.get('p0_done', 0)}   · P1 xong: {perf.get('p1_done', 0)}",
        f"  · Giờ ghi nhận: {hrs}h",
        "",
        "<b>Đúng hạn</b>",
        f"  · On-time: <b>{_v(on_pct, '%')}</b> "
        + f"({perf.get('on_time', 0)}/{perf.get('with_deadline', 0)} task có deadline)",
        f"  · Trễ hạn: {perf.get('late', 0)}",
        f"  · Cycle-time TB: {cyc_str}",
        "",
        "<b>Hiện tại</b>",
        f"  · Đang làm: {perf.get('active', 0)}   · Quá hạn: {perf.get('overdue', 0)}",
        "",
        "<b>Kỷ luật</b>",
        f"  · Hoãn (defer): {perf.get('defer_total', 0)}   "
        f"· Bị nhắc: {perf.get('reminder_total', 0)}   "
        f"· Từ chối: {perf.get('declined', 0)}",
    ]
    return "\n".join(lines)


# ─── 6.1  /today ──────────────────────────────────────────────────────────────

def msg_now_recommendation(
    primary_task: dict,
    primary_reason: str,
    alternative_task: dict | None = None,
    alternative_reason: str | None = None,
) -> str:
    """
    /now — AI chọn 1 task để user làm ngay + lý do, kèm 1 alternative nếu có.
    Inline keyboard [Done] [Snooze] gắn ngoài bởi caller.
    """
    p = primary_task.get("priority", "P3")
    icon = PRIORITY_ICON.get(p, "□")
    summary = _md(primary_task.get("summary", ""))
    dl = _deadline_line(primary_task.get("deadline"), verbose=True)
    est = primary_task.get("estimated_minutes") or 0

    meta = primary_task.get("classifier_meta") or {}
    if isinstance(meta, str):
        try:
            import json as _j
            meta = _j.loads(meta)
        except Exception:
            meta = {}
    okr = meta.get("okr_ref", "") if isinstance(meta, dict) else ""

    bits = [f"{icon} {p}"]
    if est:
        bits.append(f"~{est}p")
    if dl:
        bits.append(dl)
    if okr:
        bits.append(f"OKR {okr}")

    lines = [
        f"🎯 <b>Làm ngay:</b> <code>#{primary_task['id']}</code>",
        f"<b>{summary}</b>",
        f"{'  ·  '.join(bits)}",
        "",
        f"<i>💡 {_md(primary_reason)}</i>",
    ]

    if alternative_task:
        alt_p = alternative_task.get("priority", "P3")
        alt_icon = PRIORITY_ICON.get(alt_p, "□")
        lines += [
            "",
            f"Backup: {alt_icon} <code>#{alternative_task['id']}</code> "
            f"{_md(alternative_task.get('summary','')[:60])}",
        ]
        if alternative_reason:
            lines.append(f"<i>{_md(alternative_reason)}</i>")

    return "\n".join(lines)


def msg_today(name: str, overdue_tasks: list[dict], today_tasks: list[dict]) -> str:
    """
    Task list grouped by Eisenhower quadrant.
    Overdue tasks force-classified as Q1 (they were already urgent+missed).
    """
    now   = datetime.now()
    wday  = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"][now.weekday()]
    date_s = _fmt_date(now)

    all_tasks = list(overdue_tasks) + list(today_tasks)

    if not all_tasks:
        return (
            f"⊡ {wday} {date_s} · {name}\n"
            f"{DIV_LIGHT}\n"
            f"\n"
            f"Queue trống. Không có task nào hôm nay.\n"
            f"\n"
            f"+ <code>/add &lt;nội dung&gt;</code> để tạo task mới"
        )

    # Overdue tasks → always Q1 (already missed deadline = maximum urgency)
    for t in overdue_tasks:
        t["_force_q1"] = True  # marker, not persisted

    groups = _group_by_quadrant(all_tasks)

    # Overdue: move to Q1 regardless of calculated quadrant
    if overdue_tasks:
        overdue_ids = {t["id"] for t in overdue_tasks}
        for q in ("Q2", "Q3", "Q4"):
            moved    = [t for t in groups[q] if t["id"] in overdue_ids]
            kept     = [t for t in groups[q] if t["id"] not in overdue_ids]
            groups["Q1"] = moved + groups["Q1"]
            groups[q]    = kept

    total = len(all_tasks)
    q1_n  = len(groups["Q1"])

    lines = [
        f"⊡ {wday} {date_s} · {name}",
        f"{DIV_LIGHT}",
        f"",
        f"{total} task  ·  " + (f"🔴 {q1_n} cần làm ngay" if q1_n else "Không có task khẩn cấp"),
        f"",
    ]

    # Q1 first, then Q2, Q3 — Q4 last (deprioritize)
    for q in ("Q1", "Q2", "Q3", "Q4"):
        block = _quadrant_block(q, groups[q])
        if block:
            lines.append(block)
            lines.append("")

    lines += [DIV_LIGHT, "<code>/done &lt;id&gt;</code> · <code>/snooze &lt;id&gt; 2h</code> · <code>/add mới</code>"]
    return "\n".join(lines)


# ─── 6.3  /done response ──────────────────────────────────────────────────────

def msg_done_quick(task_id: int, summary: str) -> str:
    """Xác nhận done nhanh, trước khi hỏi thời gian."""
    return (
        f"● Xong\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"<code>#{task_id}</code> {summary[:70]}\n"
        f"\n"
        f"Mất bao lâu?"
    )



# ─── 7.x  AI response wrapper ─────────────────────────────────────────────────

def msg_ai_response(answer_text: str, tools_used: list[str] | None = None) -> str:
    """Wrap smart_agent answer với AI signature line."""
    now = datetime.now()
    tools_str = f" · {', '.join(tools_used)}" if tools_used else ""
    footer = f"\n{DIV_LIGHT}\n{AI_SIG} · ◷ {now.strftime('%H:%M')}{tools_str}"
    return answer_text + footer


def msg_ai_thinking() -> str:
    return f"{AI_SIG}\n{DIV_LIGHT}\n\n◐ Đang phân tích..."



# ─── 9.x  Errors & system ────────────────────────────────────────────────────

def msg_error(error_type: str, reason: str, suggestion: str = "") -> str:
    sug_line = f"\n{suggestion}" if suggestion else ""
    return (
        f"✕ {error_type}\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"{reason}"
        f"{sug_line}"
    )


def msg_confirm(action: str, detail: str, next_hint: str = "") -> str:
    next_line = f"\n{next_hint}" if next_hint else ""
    return (
        f"● {action}\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"{detail}"
        f"{next_line}"
    )


def msg_warning(warn_type: str, what: str, action: str = "") -> str:
    action_line = f"\n{action}" if action else ""
    return (
        f"▲ {warn_type}\n"
        f"{DIV_LIGHT}\n"
        f"\n"
        f"{what}"
        f"{action_line}"
    )


# ─── 5.x  /brief — Team status snapshot ──────────────────────────────────────

def msg_brief_team(
    stats: dict,
    members: list[dict],
    cat_counts: dict[str, int],
    p0_tasks: list[dict],
    all_tasks: list[dict] | None = None,
) -> str:
    """
    /brief response cho manager/TL.
    stats         = get_team_stats() dict
    members       = list_team_by_person() list
    cat_counts    = {category: count} of pending tasks
    p0_tasks      = list of P0 task dicts (max shown: 5)
    all_tasks     = full pending task list (optional) → shows Eisenhower matrix
    """
    now        = datetime.now()
    active     = stats.get("active", 0)
    done_today = stats.get("done_today", 0)
    overdue    = stats.get("overdue", 0)
    blocked    = stats.get("blocked", 0)

    # ── header ──
    lines = [
        f"{AI_SIG} · BRIEF TEAM",
        f"◷ {now.strftime('%H:%M')}  ⊡ {now.strftime('%d/%m')}",
        DIV_LIGHT,
        "",
        f"TỔNG QUAN",
        f"● {active} đang chạy   ◷ {done_today} xong hôm nay   "
        f"{'‼ ' if overdue else ''}{overdue} trễ"
        + (f"   ◌ {blocked} blocked" if blocked else ""),
        "",
    ]

    # ── per-member row (compact 2-column grid) ──
    lines.append("THÀNH VIÊN")
    member_rows = []
    for m in members:
        a = m.get("active_count", 0)
        od = m.get("overdue_count", 0)
        dt = m.get("done_today", 0)
        last = m.get("full_name", "?").split()[-1]

        # choose icon by workload severity
        if od > 2:
            icon = "■"   # critical
        elif od > 0:
            icon = "▪"   # warning
        elif a > 6:
            icon = "▫"   # busy
        else:
            icon = "○"   # normal

        cell = f"{icon} {last}  {a}t"
        if od:
            cell += f" ‼{od}"
        if dt:
            cell += f" ●{dt}"
        member_rows.append(cell)

    # pair members into 2-column layout
    for i in range(0, len(member_rows), 2):
        left  = member_rows[i]
        right = member_rows[i + 1] if i + 1 < len(member_rows) else ""
        lines.append(f"{left:<28}{right}")

    # ── category breakdown ──
    cat_order = ["fill_rate", "supply", "b2b", "expansion",
                 "cost", "retention", "tech", "ops", "other"]
    cat_visible = [(c, cat_counts[c]) for c in cat_order if c in cat_counts]
    # also include any cats not in order
    extra = [(c, n) for c, n in cat_counts.items() if c not in cat_order]
    cat_visible += extra

    if cat_visible:
        lines.append("")
        lines.append("THEO CATEGORY")
        for cat, count in cat_visible:
            label = CAT_LABEL.get(cat, cat)
            lines.append(f"  · {label}: {count}")

    # ── Eisenhower matrix summary (nếu có all_tasks) ──
    if all_tasks:
        groups = _group_by_quadrant(all_tasks)
        q_counts = {q: len(v) for q, v in groups.items() if v}
        if q_counts:
            lines.append("")
            lines.append("MA TRẬN EISENHOWER")
            for q in ("Q1", "Q2", "Q3", "Q4"):
                n = len(groups[q])
                if n:
                    meta = EISENHOWER[q]
                    lines.append(f"  {meta['icon']} {meta['label']} ({n})  · {meta['note']}")

    # ── P0 block ──
    if p0_tasks:
        lines.append("")
        lines.append(f"🔴 Làm ngay — {len(p0_tasks)} task khẩn cấp:")
        for t in p0_tasks[:5]:
            lines.append(fmt_task_line(t, show_assignee=True))

    # ── footer ──
    lines += [
        "",
        DIV_LIGHT,
        "/team chi tiết · /assign · /pending",
    ]

    return "\n".join(lines)


