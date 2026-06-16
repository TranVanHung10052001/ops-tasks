"""
Natural-Language Intent Router — phân loại tin nhắn user thành intent + entities,
sử dụng Gemini với team_context cached. Trả về intent + entities cho bot.py
để execute action tương ứng.
"""

import logging
import re
from datetime import datetime
from pathlib import Path

from models import call_tier

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
INTENT_PROMPT = (PROMPTS_DIR / "intent.md").read_text(encoding="utf-8")
TEAM_CONTEXT = (PROMPTS_DIR / "team_context.md").read_text(encoding="utf-8")


SYSTEM = f"""
Bạn là intent classifier cho bot Telegram của team Ops Truck Ahamove.

{INTENT_PROMPT}

---

Context team (dùng để resolve tên người, OKR ref, team keyword):

{TEAM_CONTEXT}

TODAY = {datetime.now().strftime("%Y-%m-%d (%A)")}
""".strip()


VALID_INTENTS = {
    "ASSIGN_TASK", "REASSIGN_TASK", "UPDATE_DEADLINE", "UPDATE_PRIORITY",
    "MARK_DONE", "CANCEL_TASK", "SNOOZE_TASK", "BLOCK_TASK",
    "QUERY_MY_TASKS", "QUERY_TEAM_TASKS", "QUERY_TODAY", "QUERY_OKR",
    "SUGGEST_DELEGATE", "VIEW_SCOPE", "VIEW_PLAYBOOK", "COACH_TASK",
    "HELP", "SMALLTALK", "CREATE_TASK", "UNCLEAR",
}


# Regex fallbacks for common patterns — fast path before AI call
_TASK_ID_RE = re.compile(r"#?\s*(?:task\s+)?(\d{1,5})\b", re.IGNORECASE)
_DONE_RE = re.compile(r"\b(done|xong|hoàn\s*thành|xong\s*rồi)\b", re.IGNORECASE)
_CANCEL_RE = re.compile(r"\b(cancel|huỷ|hủy|drop|bỏ)\b", re.IGNORECASE)
_SNOOZE_RE = re.compile(r"\b(snooze|hoãn|dời|lùi)\b.*?(\d+)\s*(h|d|ngày|giờ)", re.IGNORECASE)
_PRIORITY_RE = re.compile(r"\b(P[0-3])\b")
_HELP_RE = re.compile(r"^\s*(/?help|/start|\?|menu|hướng\s*dẫn|bot\s*có\s*gì)\s*$", re.IGNORECASE)


def _try_fast_path(text: str) -> dict | None:
    """Quick regex matches for unambiguous patterns to save AI call."""
    text_lower = text.strip().lower()
    if not text_lower:
        return None

    if _HELP_RE.match(text):
        return {"intent": "HELP", "confidence": 0.99, "entities": {}, "reasoning": "fast-path help"}

    # MARK_DONE: must have task_id + done keyword
    task_match = _TASK_ID_RE.search(text)
    if task_match and _DONE_RE.search(text) and len(text) < 60:
        return {
            "intent": "MARK_DONE",
            "confidence": 0.95,
            "entities": {"task_id": int(task_match.group(1))},
            "reasoning": "fast-path: task_id + done keyword",
        }

    return None


def route_intent(text: str, user_context: dict | None = None) -> dict:
    """
    Classify the user's message into an intent + entities.

    Args:
        text: raw message from user
        user_context: optional {role, full_name, team} to bias intent
                      (e.g. only Manager/TL can trigger ASSIGN)

    Returns dict:
        {
            intent: str (one of VALID_INTENTS),
            confidence: float,
            entities: dict,
            reasoning: str,
            clarify: str | None,
        }
    """
    text = (text or "").strip()
    if not text:
        return {"intent": "UNCLEAR", "confidence": 0.0, "entities": {}, "reasoning": "empty"}

    # Fast path
    fast = _try_fast_path(text)
    if fast:
        return _normalize(fast)

    # AI path — fast tier (intent routing high-frequency, low complexity)
    prompt = f"User message: \"\"\"{text}\"\"\""
    if user_context:
        prompt += f"\nUser context: role={user_context.get('role')}, name={user_context.get('full_name')}, team={user_context.get('team')}"

    result = call_tier(
        "fast",
        prompt,
        system=SYSTEM,
        label="intent_route",
        temperature=0.1,
        max_output_tokens=600,
        retries=1,
    )
    if not result:
        return {
            "intent": "UNCLEAR",
            "confidence": 0.0,
            "entities": {},
            "reasoning": "AI call failed",
            "clarify": "Bot không xử lý được tin nhắn. Thử lại hoặc gõ /help.",
        }

    return _normalize(result)


def _normalize(result: dict) -> dict:
    intent = result.get("intent", "UNCLEAR")
    if intent not in VALID_INTENTS:
        intent = "UNCLEAR"

    entities = result.get("entities") or {}
    # Coerce task_id to int when possible
    tid = entities.get("task_id")
    if isinstance(tid, str):
        try:
            entities["task_id"] = int(tid)
        except (ValueError, TypeError):
            entities["task_id"] = None

    return {
        "intent": intent,
        "confidence": float(result.get("confidence", 0.5)),
        "entities": entities,
        "reasoning": result.get("reasoning", ""),
        "clarify": result.get("clarify"),
    }
