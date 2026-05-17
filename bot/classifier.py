"""
Classifier — Gemini-powered task classification, deadline extraction, and smart routing.

Architecture:
- _classify_model: basic classify + deadline (no system context, lightweight)
- _router_model: full routing with team context cached in system instruction
  → extracts assignee, OKR ref, scope check, breakdown from a single call
"""

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
    max_output_tokens=1200,
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
    model_name="gemini-2.0-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
)

# Router model — system context loaded once and cached by Gemini API
_router_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
    system_instruction=_ROUTER_SYSTEM,
)

_vision_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
)

ROUTER_PROMPT = """
Phân tích task text sau và trả về JSON với đúng cấu trúc này:

{
  "is_task": true/false,
  "summary": "tóm tắt task ngắn gọn dưới 100 ký tự",
  "assignee_name": "Họ tên đầy đủ hoặc tên thường dùng | null nếu không rõ",
  "assignee_email": "email@ahamove.com | null nếu không rõ",
  "assignee_confidence": 0.0-1.0,
  "deadline_raw": "chuỗi deadline gốc từ text | null",
  "deadline_iso": "YYYY-MM-DD | null",
  "priority": "P0|P1|P2|P3",
  "category": "fill_rate|supply|retention|b2b|expansion|cost|tech|other",
  "okr_ref": "ví dụ O1.1 | null nếu không liên quan OKR",
  "okr_action_id": "ví dụ 1.1.1 | null",
  "in_scope": true/false,
  "scope_note": "giải thích ngắn tại sao in/out scope",
  "breakdown": ["bước 1...", "bước 2...", "bước 3..."] hoặc [] nếu task đơn giản,
  "confidence": 0.0-1.0
}

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
