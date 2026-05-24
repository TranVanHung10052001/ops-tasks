"""
Simple /ask — single-prompt Gemini call with live team context.

Replaces smart_agent.py's 2-pass reasoning (1002 LOC) for ops team of 11 people.
Pulls team workload + recent tasks + metrics into context, asks Gemini directly.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import google.generativeai as genai
import yaml

from store import (
    list_team_by_person, list_team_tasks, get_team_stats,
    get_all_overdue_tasks, get_all_metrics,
)

logger = logging.getLogger(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

_MODEL = genai.GenerativeModel("gemini-2.0-flash-exp")
_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# Simple in-memory cache for company DNA + OKR tree (5 min TTL)
_kn_cache: dict = {}
_kn_cache_ts: float = 0


def _knowledge() -> str:
    """Load minimal knowledge context (company_dna + okr_tree). 5-min cache."""
    global _kn_cache, _kn_cache_ts
    if time.monotonic() - _kn_cache_ts < 300 and _kn_cache:
        return _kn_cache.get("text", "")

    parts = []
    for fname in ("01_company_dna.yaml", "03_okr_tree.yaml"):
        f = _KNOWLEDGE_DIR / fname
        if f.exists():
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                # Keep first 2000 chars per file to control context size
                parts.append(f"### {fname}\n{json.dumps(data, ensure_ascii=False)[:2000]}")
            except Exception as e:
                logger.warning(f"knowledge load failed {fname}: {e}")
    text = "\n\n".join(parts)
    _kn_cache = {"text": text}
    _kn_cache_ts = time.monotonic()
    return text


def _live_context() -> str:
    """Pull current team state for grounding."""
    try:
        stats   = get_team_stats()
        members = list_team_by_person()
        overdue = get_all_overdue_tasks()
        recent  = list_team_tasks(statuses=["pending"])[:15]
        metrics = get_all_metrics() if callable(globals().get("get_all_metrics")) else {}

        # Compact member view
        mem_lines = []
        for m in members:
            mem_lines.append(
                f"- {m['full_name']}: {m.get('active_count',0)} active, "
                f"{m.get('overdue_count',0)} overdue, "
                f"{m.get('done_today',0)} done today"
            )

        # Compact task view
        task_lines = []
        for t in recent[:10]:
            dl = t.get("deadline", "no deadline")
            task_lines.append(
                f"- #{t['id']} [{t.get('priority','P3')}] {t.get('summary','')[:60]} "
                f"→ {t.get('assignee_name','?')} (dl: {dl})"
            )

        ov_lines = [f"- #{t['id']} {t.get('summary','')[:50]} ({t.get('assignee_name','?')})"
                    for t in overdue[:5]]

        # Metrics block
        m_lines = []
        if metrics:
            for k, v in list(metrics.items())[:12]:
                m_lines.append(f"- {k}: {v}")

        return (
            f"## TEAM STATUS ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
            f"Active: {stats.get('active',0)} · Done today: {stats.get('done_today',0)} "
            f"· Overdue: {stats.get('overdue',0)} · Blocked: {stats.get('blocked',0)}\n\n"
            f"## MEMBERS\n" + "\n".join(mem_lines) + "\n\n"
            f"## RECENT PENDING TASKS\n" + ("\n".join(task_lines) if task_lines else "(none)") + "\n\n"
            f"## OVERDUE\n" + ("\n".join(ov_lines) if ov_lines else "(none)") + "\n\n"
            f"## METRICS\n" + ("\n".join(m_lines) if m_lines else "(no live KPIs)")
        )
    except Exception as e:
        logger.error(f"live_context failed: {e}", exc_info=True)
        return "(live context unavailable)"


_SYSTEM_PROMPT = """Bạn là trợ lý điều vận cho team Truck Ops Ahamove (manager Lê Quang Huy + 10 thành viên).

Cách trả lời:
- Tiếng Việt, ngắn gọn, dùng số liệu cụ thể
- Pyramid: kết luận trước, lý do sau
- Nếu hỏi về task/người/KPI: dùng dữ liệu trong LIVE CONTEXT bên dưới
- Nếu không có data đủ: nói thẳng "chưa có data", đừng bịa
- Tối đa 6-8 dòng response, gọn
- Format: dùng bullet (·) hoặc dòng ngắn, KHÔNG dùng emoji màu (🔴🟡 v.v.)"""


def ask(question: str) -> dict:
    """
    Single-prompt /ask. Returns {answer: str, error?: str}.
    """
    q = (question or "").strip()
    if not q:
        return {"answer": "Câu hỏi trống. Thử lại với nội dung cụ thể."}
    if len(q) > 800:
        q = q[:800]

    prompt = (
        _SYSTEM_PROMPT
        + "\n\n## KNOWLEDGE\n" + _knowledge()
        + "\n\n" + _live_context()
        + f"\n\n## QUESTION\n{q}\n\n## ANSWER\n"
    )

    try:
        resp = _MODEL.generate_content(prompt)
        answer = (resp.text or "").strip()
        if not answer:
            return {"answer": "AI không có câu trả lời. Thử hỏi cụ thể hơn."}
        return {"answer": answer, "tools_used": []}
    except Exception as e:
        logger.error(f"ask() failed: {e}", exc_info=True)
        return {"answer": "", "error": str(e)[:200]}
