"""
ask.py — Tool-use AI for ops queries.

Gemini function calling loop: AI tự quyết định gọi tool nào để lấy data,
rồi trả lời dựa trên kết quả thật (team workload, OKR, metrics, scope, playbooks).

7 tools:
  get_team_workload       — workload tất cả members
  get_okr_status          — tasks theo OKR ref + overdue count
  get_metrics             — live KPIs từ DB
  find_member_for_task    — gợi ý người nhận task dựa trên scope + workload
  get_member_detail       — scope + trách nhiệm + workload 1 người
  get_task_detail         — chi tiết 1 task theo ID
  search_playbooks        — tìm SOP/playbook theo từ khoá hoặc grade
"""

import json
import logging
from datetime import datetime

import google.generativeai as genai

from models import TIER_MODELS, _SAFETY, _ensure_init
from store import (
    get_task,
    get_team_stats,
    get_all_overdue_tasks,
    list_team_by_person,
    list_team_tasks,
)
import knowledge_loader as kn

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Bạn là trợ lý điều vận cho team Truck Ops Ahamove.
Manager: Lê Quang Huy (G4). Team gồm 10 thành viên G1–G3.

Nguyên tắc trả lời:
- Tiếng Việt, súc tích, dùng số liệu cụ thể từ tools
- Pyramid: kết luận trước, lý do sau
- PHẢI gọi tool để lấy data thật — KHÔNG đoán hoặc bịa số
- Nếu không có data: nói thẳng "chưa có data"
- Tối đa 8 dòng, dùng bullet (·) hoặc dòng ngắn
- Là gợi ý — manager tự quyết định"""


# ─── Tool implementations ──────────────────────────────────────────────────────

def get_team_workload() -> dict:
    """Lấy workload hiện tại của toàn team: số task active, overdue, done today cho mỗi người."""
    members = list_team_by_person()
    stats = get_team_stats()
    compact = [
        {
            "name": m["full_name"],
            "team": m.get("team", ""),
            "role": m.get("role", ""),
            "active": m.get("active_count", 0),
            "overdue": m.get("overdue_count", 0),
            "done_today": m.get("done_today", 0),
            "blocked": m.get("blocked_count", 0),
        }
        for m in members
    ]
    return {
        "summary": {
            "total_active": stats.get("active", 0),
            "total_overdue": stats.get("overdue", 0),
            "done_today": stats.get("done_today", 0),
            "blocked": stats.get("blocked", 0),
        },
        "members": compact,
    }


def get_okr_status(okr_ref: str = "") -> dict:
    """Lấy trạng thái OKR và action items. okr_ref: 'O1', 'O1.1', hoặc rỗng để lấy tất cả."""
    all_tasks = list_team_tasks(statuses=["pending", "in_progress", "blocked", "done"])
    overdue = get_all_overdue_tasks()

    if okr_ref:
        ref = okr_ref.strip().upper()
        all_tasks = [t for t in all_tasks if (t.get("okr_ref") or "").upper().startswith(ref)]
        overdue = [t for t in overdue if (t.get("okr_ref") or "").upper().startswith(ref)]

    from collections import Counter
    by_okr: Counter = Counter()
    by_status: Counter = Counter()
    for t in all_tasks:
        r = t.get("okr_ref") or "unlinked"
        by_okr[r] += 1
        by_status[t.get("status", "unknown")] += 1

    return {
        "filter": okr_ref or "all",
        "total_tasks": len(all_tasks),
        "by_status": dict(by_status),
        "by_okr": dict(by_okr.most_common(10)),
        "overdue_count": len(overdue),
        "overdue_sample": [
            {
                "id": t["id"],
                "summary": t.get("summary", "")[:60],
                "assignee": t.get("assignee_name", "?"),
                "priority": t.get("priority", ""),
                "deadline": t.get("deadline", ""),
            }
            for t in overdue[:8]
        ],
    }


def get_metrics() -> dict:
    """Lấy KPI metrics sống: fill rate, GSV, COGS, driver stats từ DB."""
    try:
        from store import get_all_metrics
        metrics = get_all_metrics()
        if not metrics:
            return {"note": "Chưa có metrics — cần kết nối Redash hoặc push qua /api/metrics/bulk."}
        return {"metrics": metrics, "count": len(metrics)}
    except ImportError:
        return {"note": "get_all_metrics chưa có trong store version này."}
    except Exception as e:
        return {"error": str(e)[:200]}


def find_member_for_task(task_description: str) -> dict:
    """Tìm thành viên phù hợp nhất để giao task dựa trên scope, grade và workload hiện tại."""
    members_load = list_team_by_person()
    scopes = kn.member_scopes().get("members", [])

    desc_lower = task_description.lower()
    load_map = {m["full_name"]: m for m in members_load}

    candidates = []
    for s in scopes:
        score = 0
        for item in s.get("owns", []):
            if any(w in desc_lower for w in item.lower().split() if len(w) > 3):
                score += 2
        for item in s.get("do_more", []):
            if any(w in desc_lower for w in item.lower().split() if len(w) > 3):
                score += 1
        if score > 0 or True:  # include all with live data
            load = load_map.get(s.get("name", ""), {})
            candidates.append({
                "name": s["name"],
                "grade": s.get("grade", ""),
                "title": s.get("title", ""),
                "scope_match_score": score,
                "active_tasks": load.get("active_count", 0),
                "overdue": load.get("overdue_count", 0),
                "owns_keywords": s.get("owns", [])[:3],
            })

    candidates.sort(key=lambda x: (-x["scope_match_score"], x["active_tasks"]))
    return {
        "task": task_description,
        "top_candidates": candidates[:5],
        "note": "Score cao + active thấp = phù hợp nhất",
    }


def get_member_detail(name: str) -> dict:
    """Lấy chi tiết scope, trách nhiệm, red flags và workload của một thành viên."""
    scope = kn.get_member_scope(name=name)
    load = next(
        (m for m in list_team_by_person() if name.lower() in m["full_name"].lower()),
        {},
    )
    if not scope:
        return {"error": f"Không tìm thấy '{name}' trong knowledge base."}
    return {
        "name": scope["name"],
        "grade": scope["grade"],
        "title": scope.get("title", ""),
        "team": scope.get("team", ""),
        "owns": scope.get("owns", []),
        "do_more": scope.get("do_more", []),
        "do_less": scope.get("do_less", []),
        "delegate_to": scope.get("delegate_to", {}),
        "red_flags": scope.get("red_flags", []),
        "active_tasks": load.get("active_count", 0),
        "overdue_tasks": load.get("overdue_count", 0),
        "done_today": load.get("done_today", 0),
    }


def get_task_detail(task_id: int) -> dict:
    """Lấy thông tin chi tiết của một task theo ID số nguyên."""
    task = get_task(task_id)
    if not task:
        return {"error": f"Không tìm thấy task #{task_id}."}
    return {
        "id": task["id"],
        "summary": task.get("summary", ""),
        "status": task.get("status", ""),
        "priority": task.get("priority", ""),
        "assignee": task.get("assignee_name", "?"),
        "deadline": task.get("deadline", ""),
        "okr_ref": task.get("okr_ref", ""),
        "category": task.get("category", ""),
        "created_at": task.get("created_at", ""),
    }


def search_playbooks(query: str = "", grade: str = "") -> dict:
    """Tìm kiếm playbook/SOP theo từ khoá hoặc grade (G1/G2/G3/G4)."""
    if query:
        results = kn.search_playbooks(query)
    elif grade:
        results = kn.playbooks_for_grade(grade.upper())
    else:
        results = kn.list_playbooks()[:12]

    return {
        "query": query or grade or "all",
        "count": len(results),
        "playbooks": [
            {
                "id": p["id"],
                "name": p["name"],
                "owner_grade": p.get("owner_grade", ""),
                "category": p.get("category", ""),
                "frequency": p.get("frequency", ""),
                "estimated_minutes": p.get("estimated_minutes", 0),
            }
            for p in results[:8]
        ],
    }


# ─── Tool dispatch ─────────────────────────────────────────────────────────────

_TOOL_FNS: dict = {
    "get_team_workload":    get_team_workload,
    "get_okr_status":       get_okr_status,
    "get_metrics":          get_metrics,
    "find_member_for_task": find_member_for_task,
    "get_member_detail":    get_member_detail,
    "get_task_detail":      get_task_detail,
    "search_playbooks":     search_playbooks,
}


def _execute_tool(name: str, args: dict) -> dict:
    fn = _TOOL_FNS.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    try:
        return fn(**args)
    except Exception as e:
        logger.error("Tool %s(%s) failed: %s", name, args, e, exc_info=True)
        return {"error": str(e)[:200]}


# ─── Lazy model init (avoid building at import time) ──────────────────────────

_ask_model = None


def _get_ask_model():
    global _ask_model
    if _ask_model is not None:
        return _ask_model
    _ensure_init()
    _ask_model = genai.GenerativeModel(
        model_name=TIER_MODELS.get("balanced", "gemini-2.5-flash"),
        system_instruction=_SYSTEM_PROMPT,
        safety_settings=_SAFETY,
        tools=list(_TOOL_FNS.values()),
        generation_config=genai.GenerationConfig(
            temperature=0.25,
            max_output_tokens=1500,
        ),
    )
    return _ask_model


# ─── Main ask() entry point ────────────────────────────────────────────────────

def ask(question: str) -> dict:
    """
    Tool-use AI query. Gemini tự quyết gọi tool nào, ta execute và trả kết quả.
    Returns {answer, tools_used, tool_results}.
    """
    q = (question or "").strip()[:800]
    if not q:
        return {"answer": "Câu hỏi trống. Thử lại nhé."}

    tools_used: list[str] = []
    tool_results: dict = {}

    try:
        model = _get_ask_model()
        chat = model.start_chat(enable_automatic_function_calling=False)

        # Add today's date to first message for temporal grounding
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M (ICT)")
        first_msg = f"[Hôm nay: {today_str}]\n\n{q}"
        response = chat.send_message(first_msg)

        # Tool-use loop — max 4 rounds
        for _ in range(4):
            fc_parts = [
                p.function_call
                for p in response.parts
                if hasattr(p, "function_call") and p.function_call.name
            ]
            if not fc_parts:
                break  # no more tool calls → final answer

            # Execute all tool calls in this round
            fn_responses = []
            for fc in fc_parts:
                name = fc.name
                args = dict(fc.args)
                result = _execute_tool(name, args)

                if name not in tools_used:
                    tools_used.append(name)
                tool_results[name] = result

                logger.info("[ask] tool=%s args=%s → %d keys", name, args, len(result))

                fn_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=name,
                            response={"result": json.dumps(result, ensure_ascii=False, default=str)},
                        )
                    )
                )

            response = chat.send_message(fn_responses)

        answer = (response.text or "").strip()
        if not answer:
            answer = "AI không có câu trả lời. Thử hỏi cụ thể hơn."

    except Exception as e:
        logger.error("ask() failed: %s", e, exc_info=True)
        return {"answer": "", "error": str(e)[:300], "tools_used": [], "tool_results": {}}

    return {
        "answer": answer,
        "tools_used": tools_used,
        "tool_results": tool_results,
    }
