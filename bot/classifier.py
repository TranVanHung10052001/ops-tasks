"""
Classifier — Gemini-powered task classification, deadline extraction, and smart routing.

Architecture:
- _classify_model: basic classify + deadline (no system context, lightweight)
- _router_model: full routing with team context cached in system instruction
  → extracts assignee, OKR ref, scope check, breakdown from a single call
"""

import re as _re
import warnings
warnings.simplefilter("ignore", FutureWarning)

import google.generativeai as genai
import json
import os
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

PROMPTS_DIR = Path(__file__).parent / "prompts"
CLASSIFY_PROMPT = (PROMPTS_DIR / "classify.md").read_text(encoding="utf-8")
EXTRACT_PROMPT  = (PROMPTS_DIR / "extract.md").read_text(encoding="utf-8")

# System context: loaded once, cached by Gemini between calls
_TEAM_CONTEXT    = (PROMPTS_DIR / "team_context.md").read_text(encoding="utf-8")
_OKR_CONTEXT     = (PROMPTS_DIR / "okr_truck_ops.md").read_text(encoding="utf-8")
_ROUTER_SYSTEM   = f"""
Bạn là AI assistant cho team Ops Truck của Ahamove. Nhiệm vụ: phân tích task text và
trả về JSON routing hoàn chỉnh dựa trên team context và OKR Q2/2026 bên dưới.

{_TEAM_CONTEXT}

---

{_OKR_CONTEXT}

---

NGUYÊN TẮC ROUTING:
1. Detect assignee từ tên, nickname, role hint, OKR keyword, location keyword
2. Nếu task text có từ "HAN/Hà Nội" → ưu tiên Thống/Thương/Toàn
3. Nếu task text có từ "SGN/HCM/Sài Gòn" → ưu tiên Thành/Phú/Chiến
4. Nếu task text có từ "B2B/vendor/hợp đồng" → ưu tiên Khánh/Ngân/Hùng
5. Nếu task text có từ "tỉnh/KCN/expansion" → ưu tiên Khâm
6. Map task sang OKR action gần nhất (nếu có) — dùng id từ OKR tree
7. Chỉ đề xuất breakdown nếu task phức tạp (>1 bước rõ ràng)
8. Confidence: 0.9+ = chắc chắn, 0.7-0.9 = khá chắc, <0.7 = không rõ

TODAY = {datetime.now().strftime("%Y-%m-%d (%A)")}
""".strip()

JSON_CONFIG = genai.GenerationConfig(
    response_mime_type="application/json",
    temperature=0.15,
    max_output_tokens=2000,
)

SAFETY = [
    {"category": c, "threshold": "BLOCK_NONE"}
    for c in [
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    ]
]

# Lightweight model — no system context, used for classify + deadline only
_classify_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
)

# Router model — system context loaded once and cached by Gemini API
_router_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
    system_instruction=_ROUTER_SYSTEM,
)

_vision_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
)

ROUTER_PROMPT = """
Phân tích task text sau và trả về JSON với đúng cấu trúc này:

{
  "is_task": true/false,
  "summary": "Động từ + Đối tượng + Context (ai/ở đâu/về gì). VD: 'Theo dõi FR Core HAN tuần 22 với Thương' | tối đa 100 ký tự",
  "assignee_name": "Họ tên đầy đủ hoặc tên thường dùng | null nếu không rõ",
  "assignee_email": "email@ahamove.com | null nếu không rõ",
  "assignee_confidence": 0.0-1.0,
  "deadline_raw": "chuỗi deadline gốc từ text | null",
  "deadline_iso": "YYYY-MM-DDTHH:MM:SS | null",
  "priority": "P0|P1|P2|P3",
  "category": "ops|report|meeting|vendor|admin|data|other",
  "estimated_minutes": <số phút ước tính thực tế — tối thiểu 15, meeting thường 60, report 90-120>,
  "okr_ref": "O1|O2|O3|O4 | null nếu không liên quan OKR rõ ràng",
  "okr_action_id": "ví dụ O1.1 | null",
  "in_scope": true/false,
  "scope_note": "giải thích ngắn tại sao in/out scope",
  "breakdown": [...],
  "confidence": 0.0-1.0
}

**BREAKDOWN RULES — quan trọng nhất:**
- Để `[]` nếu task đơn giản (1 hành động rõ ràng, ≤15 phút)
- Dùng 2–5 bước nếu task phức tạp hoặc có nhiều giai đoạn
- Mỗi bước PHẢI cụ thể và actionable: Động từ + Đối tượng + Nguồn/Tool cụ thể
  ✅ "Vào Redash > Fill Rate dashboard > filter KCN VSIP, pull số liệu tuần hiện tại"
  ✅ "So sánh với target O1: FR EXP ≥65% (baseline ~55%) — note gap nếu có"
  ✅ "Liên hệ Khâm (khamnd@ahamove.com) qua Telegram xác nhận nguyên nhân supply gap"
  ❌ "Kiểm tra tình hình" / "Liên hệ liên quan" / "Xem xét vấn đề"

- Khi task liên quan OKR, nhúng số liệu thực vào bước:
  * O1 Fill Rate: target Core ≥68% (baseline 60.5%), EXP ≥65% (baseline ~55%), Long Haul ≥70%, SME ≥65% (baseline 17%)
  * O2 Supply: KCN BDG live 30/04, LAN Hub live 15/05; Shift Model ≥100 drivers; Decal target 1,900; Retention D30 ≥70%
  * O3 Cost/SLA: COGS GXT target 75K/kiện (đang ~80K), Vendor B2B target 11 (đang 8), 1st PU On-Time ≥80% (baseline 47.6%)
  * O4 Tech: Dynamic Pricing 100% research, Vehicle Classification 60%, AI Bot 40% auto

- Khi task liên quan người cụ thể, nêu tên + email hoặc kênh liên lạc:
  * FR data HAN → Thương (thuonglth@ahamove.com)
  * FR SGN / SLA SGN → Thành (thanhtq@ahamove.com) hoặc Phú (phutn@ahamove.com)
  * KCN / expansion / EXP → Khâm (khamnd@ahamove.com)
  * Vendor B2B / hợp đồng → Khánh (khanhlv@ahamove.com) hoặc Ngân (Nganntk1@ahamove.com)
  * COGS GXT / planning HAN → Thống (thonglhn@ahamove.com)
  * Driver retention HAN → Toàn (toanpt@ahamove.com) | SGN → Chiến (chienpd@ahamove.com)

Ví dụ breakdown tốt cho "Check fill rate VSIP tuần này và báo cáo":
[
  "Vào Redash > Fill Rate EXP dashboard > filter KCN VSIP, lấy số tuần hiện tại (MTD + W/W)",
  "So sánh với target O1: FR EXP ≥65% (baseline ~55%) — highlight gap nếu dưới target",
  "Liên hệ Khâm (khamnd@) qua Telegram xác nhận nguyên nhân nếu có supply gap",
  "Tổng hợp vào báo cáo FR tuần → gửi cho Huy (huyle@) trước EOD"
]

TASK TEXT:
"""


def _safe_call(model, prompt: str, retries: int = 2) -> dict:
    for attempt in range(retries + 1):
        try:
            resp = model.generate_content(prompt)
            return json.loads(resp.text)
        except Exception as e:
            if attempt < retries:
                time.sleep(1.5 ** attempt)
            else:
                logger.error(f"Gemini call failed after {retries} retries: {e}")
                return {}
    return {}


def classify_text(text: str) -> dict:
    """Lightweight classify — no team context. Returns basic task fields."""
    prompt = CLASSIFY_PROMPT + "\n\n" + text
    result = _safe_call(_classify_model, prompt)
    return {
        "is_task":           result.get("is_task", False),
        "summary":           result.get("summary", text[:100]),
        "deadline_raw":      result.get("deadline_raw"),
        "priority":          result.get("priority", "P3"),
        "category":          result.get("category", "other"),
        "estimated_minutes": result.get("estimated_minutes", 30),
        "confidence":        result.get("confidence", 0.5),
    }


def extract_deadline(text: str) -> dict:
    """Extract deadline ISO from raw text."""
    today = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
    prompt = EXTRACT_PROMPT.replace("{today}", today) + "\n\n" + text
    result = _safe_call(_classify_model, prompt)
    return {
        "deadline_iso":   result.get("deadline_iso"),
        "confidence":     result.get("confidence", "low"),
        "interpretation": result.get("interpretation", ""),
    }


def route_task(text: str) -> dict:
    """
    Full routing pipeline with team context (cached system instruction).
    Single Gemini call → returns assignee, OKR ref, scope, breakdown.

    Returns dict with keys:
      is_task, summary, assignee_name, assignee_email, assignee_confidence,
      deadline_iso, priority, category, okr_ref, okr_action_id,
      in_scope, scope_note, breakdown, confidence
    """
    result = _safe_call(_router_model, ROUTER_PROMPT + text)

    if not result:
        # Fallback to basic classify
        basic = classify_text(text)
        return {**basic, "assignee_name": None, "assignee_email": None,
                "assignee_confidence": 0.0, "deadline_iso": None,
                "okr_ref": None, "okr_action_id": None,
                "in_scope": True, "scope_note": "", "breakdown": []}

    return {
        "is_task":              result.get("is_task", False),
        "summary":              result.get("summary", text[:100]),
        "assignee_name":        result.get("assignee_name"),
        "assignee_email":       result.get("assignee_email"),
        "assignee_confidence":  float(result.get("assignee_confidence", 0.0)),
        "deadline_raw":         result.get("deadline_raw"),
        "deadline_iso":         result.get("deadline_iso"),
        "priority":             result.get("priority", "P2"),
        "category":             result.get("category", "other"),
        "estimated_minutes":    int(result.get("estimated_minutes", 30)),
        "okr_ref":              result.get("okr_ref"),
        "okr_action_id":        result.get("okr_action_id"),
        "in_scope":             result.get("in_scope", True),
        "scope_note":           result.get("scope_note", ""),
        "breakdown":            result.get("breakdown", []),
        "confidence":           float(result.get("confidence", 0.5)),
    }


def full_pipeline(text: str) -> dict:
    """
    Legacy pipeline — classify + deadline only (no team context).
    Kept for backward compat with scheduler briefings.
    """
    classified = classify_text(text)
    if not classified.get("is_task"):
        return classified

    if classified.get("deadline_raw"):
        deadline_data = extract_deadline(classified["deadline_raw"])
        classified["deadline_iso"]        = deadline_data.get("deadline_iso")
        classified["deadline_confidence"] = deadline_data.get("confidence")
    else:
        classified["deadline_iso"]        = None
        classified["deadline_confidence"] = "none"

    return classified


def coach_task(
    task_summary: str,
    okr_ref: str | None = None,
    okr_action_id: str | None = None,
    breakdown: list | None = None,
    priority: str = "P2",
    deadline_iso: str | None = None,
    assignee_name: str | None = None,
) -> dict:
    """
    Generate AI coaching guide for a specific task.
    Returns: {why_matters, steps, watch_out, tips, estimated_minutes}
    """
    context_parts = []
    if okr_ref:
        context_parts.append(f"OKR: {okr_ref}" + (f" (action {okr_action_id})" if okr_action_id else ""))
    if priority:
        context_parts.append(f"Priority: {priority}")
    if deadline_iso:
        context_parts.append(f"Deadline: {deadline_iso}")
    if assignee_name:
        context_parts.append(f"Assignee: {assignee_name}")
    if breakdown:
        context_parts.append("Breakdown gợi ý: " + " | ".join(breakdown))

    prompt = f"""Bạn là AI coach cho team Truck Ops Ahamove. Phân tích task sau và trả về JSON hướng dẫn thực tế.

TASK: {task_summary}
CONTEXT: {", ".join(context_parts) if context_parts else "Không có thêm context"}

Trả về JSON với cấu trúc:
{{
  "why_matters": "Tại sao task này quan trọng với team/OKR (1-2 câu súc tích)",
  "steps": ["Bước 1 cụ thể...", "Bước 2...", "Bước 3..."],
  "watch_out": ["Rủi ro/blockers cần lưu ý 1", "Rủi ro 2"],
  "tips": "Mẹo hoặc shortcut để làm nhanh hơn (1 câu)",
  "estimated_minutes": <số phút ước tính thực tế>
}}

Yêu cầu: steps phải cụ thể, actionable, phù hợp với nghiệp vụ logistics/truck ops. Tối đa 5 steps.
"""
    result = _safe_call(_router_model, prompt)
    if not result:
        return {
            "why_matters": "Task quan trọng cho OKR team.",
            "steps": breakdown or ["Thực hiện task theo mô tả."],
            "watch_out": [],
            "tips": "",
            "estimated_minutes": 30,
        }
    return {
        "why_matters":        result.get("why_matters", ""),
        "steps":              result.get("steps", breakdown or []),
        "watch_out":          result.get("watch_out", []),
        "tips":               result.get("tips", ""),
        "estimated_minutes":  result.get("estimated_minutes", 30),
    }


def recommend_now(
    pending_tasks: list[dict],
    user_name: str = "",
) -> dict:
    """
    Given a user's pending tasks + current time, pick THE single task they should
    do right now and explain why in 1 sentence.

    Scoring lens the AI should use (built into prompt):
    - Deadline urgency (overdue > today > tomorrow > >2d)
    - OKR weight (tasks with okr_ref outrank generic tasks)
    - Priority (P0 always wins, P1 > P2 > P3)
    - Time-of-day fit: P0/deep-work AM, meetings/coordination PM, admin EOD
    - Blocker chain: tasks others are waiting on first

    Returns: {task_id, reason, alternative_task_id, alternative_reason}
    """
    if not pending_tasks:
        return {"task_id": None, "reason": "Không có task nào đang pending."}

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d %H:%M (%A)")
    hour = now.hour
    period = (
        "đầu giờ sáng (deep work)" if 7 <= hour < 11
        else "trưa (medium energy)" if 11 <= hour < 13
        else "chiều (coordination)" if 13 <= hour < 17
        else "cuối ngày (wrap up)" if 17 <= hour < 20
        else "ngoài giờ"
    )

    # Compact task list for prompt
    task_lines = []
    for t in pending_tasks[:15]:  # cap at 15 to control token cost
        meta = t.get("classifier_meta") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        okr = meta.get("okr_ref", "") if isinstance(meta, dict) else ""
        dl = t.get("deadline", "")
        dl_short = dl[:16] if dl else "no-deadline"
        task_lines.append(
            f"#{t['id']} [{t.get('priority','P3')}] {t.get('summary','')[:80]} | "
            f"dl={dl_short} | okr={okr or '—'} | cat={t.get('category','other')}"
        )
    tasks_text = "\n".join(task_lines)

    prompt = f"""User: {user_name or '?'}
NOW: {today_str} — {period}

PENDING TASKS:
{tasks_text}

Pick THE single task this user should do RIGHT NOW (1 task only).

Criteria (decreasing priority):
1. P0 + overdue → always wins
2. Deadline ≤ 4h từ now → escalate
3. OKR-linked (có okr_ref) > ad-hoc
4. Time-of-day fit: AM=deep work / heavy analysis, PM=coordination/meeting, EOD=admin
5. Nếu nhiều task tương đương → chọn task có deadline gần nhất

Return JSON:
{{
  "task_id": <id của task chọn>,
  "reason": "1 câu (≤20 từ) giải thích vì sao chọn task này — bám vào OKR/deadline cụ thể",
  "alternative_task_id": <id task thứ 2 nên cân nhắc, hoặc null>,
  "alternative_reason": "1 câu ngắn nói vì sao đó là backup, hoặc null"
}}
"""
    result = _safe_call(_router_model, prompt)
    if not result:
        # Fallback: rule-based pick
        sorted_t = sorted(pending_tasks, key=lambda t: (
            _PRIORITY_RANK_LOCAL.get(t.get("priority", "P3"), 3),
            t.get("deadline") or "9999",
        ))
        first = sorted_t[0]
        return {
            "task_id": first["id"],
            "reason": f"Priority {first.get('priority','P3')} với deadline sớm nhất.",
            "alternative_task_id": sorted_t[1]["id"] if len(sorted_t) > 1 else None,
            "alternative_reason": None,
        }

    return {
        "task_id": result.get("task_id"),
        "reason": result.get("reason", ""),
        "alternative_task_id": result.get("alternative_task_id"),
        "alternative_reason": result.get("alternative_reason"),
    }


_PRIORITY_RANK_LOCAL = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def weekly_summary(done_tasks: list, pending_tasks: list, overdue_tasks: list,
                   period_label: str = "") -> dict:
    """
    AI-generated weekly report highlights.
    Returns: {headline, highlights, risks, next_week_focus}
    """
    done_text = "\n".join(
        f"- {t.get('summary', '')[:80]} [{t.get('assignee_name', '?')}]"
        for t in done_tasks[:20]
    ) or "(không có)"

    overdue_text = "\n".join(
        f"- {t.get('summary', '')[:60]} [{t.get('assignee_name', '?')}] deadline={t.get('deadline', '?')[:10]}"
        for t in overdue_tasks[:10]
    ) or "(không có)"

    prompt = f"""Bạn là AI analyst cho team Truck Ops Ahamove. Phân tích performance tuần và trả về JSON báo cáo.

TUẦN: {period_label}
DONE ({len(done_tasks)} tasks):
{done_text}

OVERDUE ({len(overdue_tasks)} tasks):
{overdue_text}

ĐANG PENDING: {len(pending_tasks)} tasks

Trả về JSON:
{{
  "headline": "Tóm tắt 1 câu về tuần này (tone: factual, không hype)",
  "highlights": ["Điểm nổi bật 1", "Điểm nổi bật 2", "Điểm nổi bật 3"],
  "risks": ["Rủi ro/cần chú ý 1", "Rủi ro 2"],
  "next_week_focus": "Khuyến nghị ưu tiên tuần sau (1-2 câu)"
}}
"""
    result = _safe_call(_router_model, prompt)
    if not result:
        return {
            "headline": f"Tuần {period_label}: {len(done_tasks)} done, {len(overdue_tasks)} overdue.",
            "highlights": [],
            "risks": [f"{len(overdue_tasks)} tasks quá hạn cần xử lý."] if overdue_tasks else [],
            "next_week_focus": "Tập trung giảm overdue và đảm bảo deadline tuần tới.",
        }
    return {
        "headline":        result.get("headline", ""),
        "highlights":      result.get("highlights", []),
        "risks":           result.get("risks", []),
        "next_week_focus": result.get("next_week_focus", ""),
    }


# ─── NL Intent Classification ─────────────────────────────────────────────────
# Regex fast-paths (zero AI cost) for the most common operator commands.

_RE_NL_DONE = _re.compile(
    r'(?:xong|done|hoàn\s*thành|đánh\s*dấu\s*xong)\s*(?:task)?\s*#?(\d+)'
    r'|'
    r'(?:task)?\s*#?(\d+)\s+(?:xong|done|hoàn\s*thành)',
    _re.IGNORECASE | _re.UNICODE,
)
_RE_NL_DEADLINE = _re.compile(
    r'task\s+#?(\d+)\s+(?:deadline|hạn|dl)[:\s]+(.+?)$',
    _re.IGNORECASE | _re.UNICODE,
)
_RE_NL_REASSIGN = _re.compile(
    r'(?:giao|chuyển|move|đổi)\s+task\s+#?(\d+)\s+(?:cho|sang|→|->)\s+(.+)',
    _re.IGNORECASE | _re.UNICODE,
)
_RE_NL_QUERY_PERSON = _re.compile(
    r'([\w\s]{3,20}?)\s+(?:đang\s+làm\s+gì|có\s+(?:task|việc)\s+gì|đang\s+bận\s+gì)',
    _re.IGNORECASE | _re.UNICODE,
)
_RE_NL_BRIEF = _re.compile(
    r'\b(?:brief|tổng\s*hợp|status\s+team|báo\s*cáo\s+nhanh|daily\s*brief|check\s+team)\b',
    _re.IGNORECASE | _re.UNICODE,
)

_NL_INTENT_PROMPT = """Phân tích câu lệnh tiếng Việt từ manager ops Ahamove.

recent_task_id = {recent_task_id}

Trả về JSON:
{{
  "intent": "update_deadline|reassign|mark_done|query_task|query_person|brief|unknown",
  "task_id": <int hoặc null — dùng recent_task_id nếu text có "cái đó/vừa tạo/task vừa rồi/nó">,
  "assignee_hint": "tên người để reassign hoặc null",
  "deadline_raw": "chuỗi deadline thô hoặc null",
  "person_hint": "tên người cần query hoặc null",
  "confidence": 0.0-1.0
}}

Rules:
- update_deadline: "task X deadline Y", "task X hạn Y", "đổi deadline task X sang Y"
- reassign: "giao/chuyển task X cho/sang Y"
- mark_done: "task X xong", "xong task X", "#X done"
- query_task: "task X là gì", "task X status", "check task X"
- query_person: "Y đang làm gì", "check Y", "task của Y", "Y bận gì"
- brief: muốn tổng hợp tình hình team
- unknown: chitchat, câu hỏi, hoặc tạo task mới

TODAY = {today}

INPUT: """


def nl_intent(text: str, recent_task_id: int | None = None) -> dict:
    """
    Parse NL command → structured intent. Regex fast-paths first, Gemini fallback.

    Returns dict with keys: intent, task_id?, assignee_hint?, deadline_raw?,
    person_hint?, confidence.
    Intents: update_deadline | reassign | mark_done | query_task |
             query_person | brief | unknown
    """
    # ── Regex fast-paths (zero cost) ──────────────────────────────────────────
    m = _RE_NL_DONE.search(text)
    if m:
        tid = m.group(1) or m.group(2)
        return {"intent": "mark_done", "task_id": int(tid), "confidence": 0.95}

    m = _RE_NL_DEADLINE.search(text)
    if m:
        return {
            "intent":       "update_deadline",
            "task_id":      int(m.group(1)),
            "deadline_raw": m.group(2).strip(),
            "confidence":   0.93,
        }

    m = _RE_NL_REASSIGN.search(text)
    if m:
        return {
            "intent":        "reassign",
            "task_id":       int(m.group(1)),
            "assignee_hint": m.group(2).strip(),
            "confidence":    0.93,
        }

    if _RE_NL_BRIEF.search(text):
        return {"intent": "brief", "confidence": 0.92}

    m = _RE_NL_QUERY_PERSON.search(text)
    if m:
        return {"intent": "query_person", "person_hint": m.group(1).strip(), "confidence": 0.87}

    # ── Gemini fallback for ambiguous NL ──────────────────────────────────────
    today = datetime.now().strftime("%Y-%m-%d (%A)")
    prompt = _NL_INTENT_PROMPT.format(
        recent_task_id=recent_task_id if recent_task_id else "null",
        today=today,
    ) + text
    result = _safe_call(_classify_model, prompt)
    if not result:
        return {"intent": "unknown", "confidence": 0.0}
    return {
        "intent":        result.get("intent", "unknown"),
        "task_id":       result.get("task_id"),
        "assignee_hint": result.get("assignee_hint"),
        "deadline_raw":  result.get("deadline_raw"),
        "person_hint":   result.get("person_hint"),
        "confidence":    float(result.get("confidence", 0.5)),
    }


def image_pipeline(image_bytes: bytes) -> dict:
    """OCR + route from screenshot (Zalo, email, etc.)."""
    import PIL.Image
    import io

    prompt = (
        "Đây là screenshot từ ứng dụng nhắn tin hoặc email. "
        "Hãy OCR nội dung văn bản, sau đó phân loại và routing.\n\n"
        + ROUTER_PROMPT
    )
    try:
        img = PIL.Image.open(io.BytesIO(image_bytes))
        resp = _router_model.generate_content([prompt, img])
        result = json.loads(resp.text)
        return {
            "is_task":             result.get("is_task", False),
            "summary":             result.get("summary", ""),
            "assignee_name":       result.get("assignee_name"),
            "assignee_email":      result.get("assignee_email"),
            "assignee_confidence": float(result.get("assignee_confidence", 0.0)),
            "deadline_iso":        result.get("deadline_iso"),
            "priority":            result.get("priority", "P3"),
            "category":            result.get("category", "other"),
            "okr_ref":             result.get("okr_ref"),
            "in_scope":            result.get("in_scope", True),
            "breakdown":           result.get("breakdown", []),
            "confidence":          float(result.get("confidence", 0.5)),
        }
    except Exception as e:
        logger.error(f"image_pipeline failed: {e}")
        return {"is_task": False, "summary": "", "confidence": 0.0}
