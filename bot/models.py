"""
Multi-tier Model Abstraction
─────────────────────────────
Centralized AI model selection. Three tiers — fast / balanced / premium —
mapped to env-configurable model IDs. Default to Gemini lineup (2.5 Flash + 3.1 Pro).

Swap to Claude later by changing env vars:
  MODEL_PREMIUM=claude-opus-4-7
  MODEL_BALANCED=claude-sonnet-4-6
  MODEL_FAST=claude-haiku-4-5-20251001

Tier guidance (em đã consult anh — Phase 1):
  - fast: classification, extraction, intent routing, OCR. <2s latency, high freq.
  - balanced: coach steps, OKR synthesis, playbook gen. 2-5s, medium freq.
  - premium: strategic synthesis, delegation coach, crisis advisor, weekly story. 5-15s ok.
"""

import json
import logging
import os
import time
from typing import Any

import google.generativeai as genai

logger = logging.getLogger(__name__)


# ─── Tier → model ID mapping (env-overridable) ──────────────────────────────

MODEL_FAST     = os.getenv("MODEL_FAST",     "gemini-2.5-flash")
MODEL_BALANCED = os.getenv("MODEL_BALANCED", "gemini-3.1-pro")
MODEL_PREMIUM  = os.getenv("MODEL_PREMIUM",  "gemini-3.1-pro")

TIER_MODELS = {
    "fast":     MODEL_FAST,
    "balanced": MODEL_BALANCED,
    "premium":  MODEL_PREMIUM,
}

# Token caps per tier (tune for latency/cost)
TIER_DEFAULT_TOKENS = {
    "fast":     1200,
    "balanced": 2400,
    "premium":  4000,
}

# Default temperatures (premium runs hotter for nuanced reasoning)
TIER_DEFAULT_TEMP = {
    "fast":     0.15,
    "balanced": 0.25,
    "premium":  0.35,
}


# ─── Safety (uniform across tiers) ──────────────────────────────────────────

_SAFETY = [
    {"category": c, "threshold": "BLOCK_NONE"}
    for c in [
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    ]
]


# ─── Lazy init Gemini ───────────────────────────────────────────────────────

_initialized = False


def _ensure_init() -> None:
    global _initialized
    if _initialized:
        return
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — model calls will fail.")
    else:
        genai.configure(api_key=api_key)
    _initialized = True


# ─── Model cache ────────────────────────────────────────────────────────────

_model_cache: dict[tuple, genai.GenerativeModel] = {}


def get_model(
    tier: str = "fast",
    system: str | None = None,
    json_mode: bool = True,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> tuple[genai.GenerativeModel, str]:
    """
    Return cached Gemini model for the requested tier + system instruction.
    Returns (model, model_name).
    """
    _ensure_init()

    if tier not in TIER_MODELS:
        logger.warning(f"Unknown tier '{tier}', falling back to 'fast'.")
        tier = "fast"

    model_name = TIER_MODELS[tier]
    temp = TIER_DEFAULT_TEMP[tier] if temperature is None else temperature
    max_tok = TIER_DEFAULT_TOKENS[tier] if max_output_tokens is None else max_output_tokens

    key = (model_name, system or "", json_mode, round(temp, 2), max_tok)
    if key in _model_cache:
        return _model_cache[key], model_name

    config = genai.GenerationConfig(
        response_mime_type="application/json" if json_mode else None,
        temperature=temp,
        max_output_tokens=max_tok,
    )

    kwargs = {
        "model_name": model_name,
        "generation_config": config,
        "safety_settings": _SAFETY,
    }
    if system:
        kwargs["system_instruction"] = system

    model = genai.GenerativeModel(**kwargs)
    _model_cache[key] = model
    return model, model_name


# ─── Telemetry-wrapped call ─────────────────────────────────────────────────

def call_tier(
    tier: str,
    prompt: str | list,
    system: str | None = None,
    json_mode: bool = True,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    retries: int = 1,
    label: str = "call",
) -> dict | str | None:
    """
    Call the model for `tier` with telemetry (latency + model name in logs).

    Returns:
      - dict (parsed JSON) if json_mode=True and parse succeeds
      - raw text str if json_mode=False
      - None on hard failure
    """
    model, model_name = get_model(
        tier=tier, system=system, json_mode=json_mode,
        temperature=temperature, max_output_tokens=max_output_tokens,
    )

    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            resp = model.generate_content(prompt)
            elapsed = time.time() - t0
            text = resp.text or ""

            usage = getattr(resp, "usage_metadata", None)
            in_tok = getattr(usage, "prompt_token_count", "?") if usage else "?"
            out_tok = getattr(usage, "candidates_token_count", "?") if usage else "?"
            logger.info(
                f"[ai/{tier}] {model_name} {label} {elapsed:.2f}s "
                f"in={in_tok} out={out_tok}"
            )

            if not json_mode:
                return text
            try:
                return json.loads(text)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"[ai/{tier}] JSON parse failed: {e} — text head: {text[:120]}")
                if attempt < retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                return None
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"[ai/{tier}] {model_name} {label} FAILED {elapsed:.2f}s — {e}")
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
            else:
                return None
    return None


def tier_info() -> dict:
    """Return current tier → model mapping (for /health + debugging)."""
    return dict(TIER_MODELS)
