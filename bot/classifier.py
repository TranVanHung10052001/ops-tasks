"""
Classifier — Gemini-powered task classification and deadline extraction.
Simplified for team use: no personal OKR mapping until Excel is provided.
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

JSON_CONFIG = genai.GenerationConfig(
    response_mime_type="application/json",
    temperature=0.2,
    max_output_tokens=1000,
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

_classify_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
)

_vision_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=JSON_CONFIG,
    safety_settings=SAFETY,
)


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
    """
    Returns:
      is_task, summary, deadline_raw, priority, category,
      estimated_minutes, confidence
    """
    prompt = CLASSIFY_PROMPT + "\n\n" + text
    result = _safe_call(_classify_model, prompt)

    return {
        "is_task":            result.get("is_task", False),
        "summary":            result.get("summary", text[:100]),
        "deadline_raw":       result.get("deadline_raw"),
        "priority":           result.get("priority", "P3"),
        "category":           result.get("category", "other"),
        "estimated_minutes":  result.get("estimated_minutes", 30),
        "confidence":         result.get("confidence", 0.5),
    }


def extract_deadline(text: str) -> dict:
    """
    Returns: deadline_iso (str or None), confidence (str), interpretation (str)
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
    prompt = EXTRACT_PROMPT.replace("{today}", today) + "\n\n" + text
    result = _safe_call(_classify_model, prompt)

    return {
        "deadline_iso":    result.get("deadline_iso"),
        "confidence":      result.get("confidence", "low"),
        "interpretation":  result.get("interpretation", ""),
    }


def image_pipeline(image_bytes: bytes) -> dict:
    """OCR + classify from screenshot (Zalo, email, etc.)."""
    import PIL.Image
    import io

    prompt = (
        "Đây là screenshot từ ứng dụng nhắn tin hoặc email. "
        "Hãy OCR nội dung và phân loại có phải task không.\n\n"
        + CLASSIFY_PROMPT
    )
    try:
        img = PIL.Image.open(io.BytesIO(image_bytes))
        resp = _vision_model.generate_content([prompt, img])
        result = json.loads(resp.text)
        return {
            "is_task":           result.get("is_task", False),
            "summary":           result.get("summary", ""),
            "deadline_raw":      result.get("deadline_raw"),
            "priority":          result.get("priority", "P3"),
            "category":          result.get("category", "other"),
            "estimated_minutes": result.get("estimated_minutes", 30),
            "confidence":        result.get("confidence", 0.5),
        }
    except Exception as e:
        logger.error(f"image_pipeline failed: {e}")
        return {"is_task": False, "summary": "", "confidence": 0.0}


def full_pipeline(text: str) -> dict:
    """Classify + extract deadline in sequence."""
    classified = classify_text(text)
    if not classified.get("is_task"):
        return classified

    if classified.get("deadline_raw"):
        deadline_data = extract_deadline(classified["deadline_raw"])
        classified["deadline_iso"] = deadline_data.get("deadline_iso")
        classified["deadline_confidence"] = deadline_data.get("confidence")
    else:
        classified["deadline_iso"] = None
        classified["deadline_confidence"] = "none"

    return classified
