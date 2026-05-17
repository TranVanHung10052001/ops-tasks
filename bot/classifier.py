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
