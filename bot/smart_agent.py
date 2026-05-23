"""
Smart Agent — reasoning AI for ops manager Q&A.

Architecture: two-pass tool-use
  Pass 1 (fast tier):  AI decides which tools to call
  Pass 2 (premium tier): AI reasons over tool results + full business context

Tools:
  - team_workload()       : current workload (active/overdue/done per member)
  - okr_status(okr_id?)   : OKR tree + tasks tagged per OKR
  - metrics(name?)        : current Redash KPIs (filter by prefix)
  - find_member_for_task  : recommend candidates based on scope match
  - member_detail(name)   : scope, grade, current load
  - task_detail(task_id)  : full task info

Use cases supported:
  - Decision support: "Task này nên giao ai?", "Tuần này ai overload?"
  - Root cause:        "Vì sao FR HAN giảm?"
  - Status check:      "OKR O1.1 đang thế nào?"
  - Coaching:          "Tôi đang giữ quá nhiều G4 không?"
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from models import call_tier
import knowledge_loader as kn
from store import (
    list_team_by_person, get_team_stats, list_team_tasks, get_all_metrics,
    get_user_by_name, get_task, list_user_tasks,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

# ─── Module-level config constants ───────────────────────────────────────────
_TOOL_TIMEOUT: float       = 5.0     # seconds per tool call before abort
_MAX_TOOLS: int            = 4       # max tools plannable per ask()
_QUESTION_MAX_LEN: int     = 1000    # chars — cap user input
_SYSTEM_CACHE_TTL: float   = 300.0   # 5 min — refresh system prompt (TODAY, overdue alerts)
_TOOL_RESULT_TTL: float    = 30.0    # 30 s  — reuse DB results for rapid follow-ups
_TOOL_OUTPUT_MAX_CHARS: int = 4000   # per tool JSON truncation


# ─── JSON / input utilities ──────────────────────────────────────────────────

_FENCE_RE = re.compile(r'^```(?:json)?\s*(.*?)```\s*$', re.DOTALL)

def safe_parse_json(raw: str | dict | None) -> dict:
    """Robust JSON parser handling LLM quirks — markdown fences, trailing text.

    Tries in order:
      1. Already a dict → return as-is
      2. Strip ``` fences → json.loads
      3. Find first { … last } → json.loads
      4. Return {}
    """
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw:
        return {}
    cleaned = raw.strip()
    # Strip markdown code fences
    m = _FENCE_RE.match(cleaned)
    if m:
        cleaned = m.group(1).strip()
    # Fast path
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Last resort: extract outermost { ... }
    try:
        start = cleaned.index('{')
        end = cleaned.rindex('}') + 1
        return json.loads(cleaned[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.warning(f"safe_parse_json: failed to parse ({len(raw)} chars)")
        return {}


# Injection patterns that should never appear in legitimate ops questions
_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard your",
    "new instructions:",
    "you are now a",
    "###system",
)


def _sanitize_question(question: str) -> str:
    """Cap length and block obvious prompt-injection attempts.

    Raises ValueError if suspicious content detected (caller should surface to user).
    """
    q = question[:_QUESTION_MAX_LEN].strip()
    q_lower = q.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in q_lower:
            logger.warning(f"[smart_agent] injection attempt blocked: {pattern!r}")
            raise ValueError("Câu hỏi không hợp lệ — vui lòng thử lại.")
    return q


# ─── Tool implementations ────────────────────────────────────────────────────

def tool_team_workload(**_) -> dict:
    """Current team workload summary."""
    try:
        members = list_team_by_person()
        stats = get_team_stats()
        return {
            "totals": {
                "active":     stats.get("active", 0),
                "overdue":    stats.get("overdue", 0),
                "done_today": stats.get("done_today", 0),
                "blocked":    stats.get("blocked", 0),
            },
            "by_member": [
                {
                    "name":       m["full_name"],
                    "active":     m.get("active_count", 0),
                    "overdue":    m.get("overdue_count", 0),
                    "done_today": m.get("done_today", 0),
                }
                for m in members
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def tool_okr_status(okr_id: str | None = None, **_) -> dict:
    """OKR tree + tasks tagged per OKR."""
    try:
        okr_md = (PROMPTS_DIR / "okr_truck_ops.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        okr_md = ""

    try:
        all_tasks = list_team_tasks()
    except Exception:
        all_tasks = []

    by_okr: dict[str, list] = {}
    for t in all_tasks:
        meta = t.get("classifier_meta") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, ValueError):
                meta = {}
        okr_ref = meta.get("okr_ref") or ""
        if not okr_ref:
            continue
        if okr_id and not okr_ref.lower().startswith(okr_id.lower()):
            continue

        deadline = t.get("deadline")
        is_overdue = False
        if deadline:
            try:
                dl = datetime.fromisoformat(deadline).replace(tzinfo=None)
                is_overdue = dl < datetime.now()
            except (ValueError, TypeError):
                pass

        by_okr.setdefault(okr_ref, []).append({
            "id":       t["id"],
            "summary":  t["summary"][:80],
            "status":   t.get("status"),
            "assignee": t.get("assignee_name"),
            "priority": t.get("priority"),
            "overdue":  is_overdue,
        })

    # Summary stats per OKR
    summary = {
        ref: {
            "total":      len(tasks),
            "overdue":    sum(1 for t in tasks if t["overdue"]),
            "p0":         sum(1 for t in tasks if t["priority"] == "P0"),
            "by_owner":   {},
        }
        for ref, tasks in by_okr.items()
    }
    for ref, tasks in by_okr.items():
        for t in tasks:
            owner = t["assignee"] or "?"
            summary[ref]["by_owner"][owner] = summary[ref]["by_owner"].get(owner, 0) + 1

    return {
        "okr_tree_md": okr_md[:3000],
        "tasks_by_okr": by_okr,
        "summary_per_okr": summary,
    }


def tool_metrics(name: str | None = None, **_) -> dict:
    """Current Redash/manual metrics with targets from kpi_dict.yaml (L4)."""
    try:
        metrics = get_all_metrics()
    except Exception as e:
        return {"error": str(e)}
    if name:
        metrics = {k: v for k, v in metrics.items() if name.lower() in k.lower()}

    # Single source of truth: L4 kpi_dict.yaml — no hardcoding here
    targets = kn.kpi_targets()
    if name:
        targets = {k: v for k, v in targets.items() if name.lower() in k.lower()}

    return {"values": metrics, "targets": targets}


def tool_find_member_for_task(task_text: str = "", **_) -> dict:
    """Recommend candidates based on scope match (owns / do_more / playbooks)."""
    if not task_text:
        return {"error": "task_text is required"}
    scopes = kn.member_scopes()
    matches = []
    task_lower = task_text.lower()
    keywords = [w for w in task_lower.split() if len(w) > 3]

    for m in scopes.get("members", []):
        scope_text = " ".join([
            *m.get("owns", []),
            *m.get("do_more", []),
            *m.get("delegate_to", []),
            m.get("title", ""),
            m.get("region", ""),
        ]).lower()
        score = sum(1 for kw in keywords if kw in scope_text)
        if score > 0:
            matches.append({
                "name":  m.get("name"),
                "grade": m.get("grade"),
                "title": m.get("title", ""),
                "score": score,
                "owns_top3": m.get("owns", [])[:3],
                "current_red_flags": m.get("red_flags", []),
            })
    matches.sort(key=lambda x: x["score"], reverse=True)
    return {"task": task_text, "keywords": keywords, "candidates": matches[:5]}


def tool_member_detail(name: str = "", **_) -> dict:
    """Full scope + grade + current task load for a member."""
    if not name:
        return {"error": "name is required"}
    scope = kn.get_member_scope(name=name)
    user = get_user_by_name(name)

    load = None
    if user:
        try:
            tasks = list_user_tasks(user["telegram_id"], status="pending", limit=30)
        except Exception:
            tasks = []
        overdue = 0
        p0_count = 0
        for t in tasks:
            if t.get("priority") == "P0":
                p0_count += 1
            if t.get("deadline"):
                try:
                    if datetime.fromisoformat(t["deadline"]).replace(tzinfo=None) < datetime.now():
                        overdue += 1
                except (ValueError, TypeError):
                    pass
        load = {
            "active":   len(tasks),
            "overdue":  overdue,
            "p0_count": p0_count,
            "top_tasks": [
                {"id": t["id"], "summary": t["summary"][:60], "priority": t.get("priority")}
                for t in tasks[:5]
            ],
        }
    return {"scope": scope, "current_load": load}


def tool_task_detail(task_id: int = 0, **_) -> dict:
    """Full info for a specific task."""
    if not task_id:
        return {"error": "task_id is required"}
    t = get_task(task_id)
    if not t:
        return {"error": f"Task #{task_id} not found"}
    meta = t.get("classifier_meta") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, ValueError):
            meta = {}
    return {
        "id":            t["id"],
        "summary":       t["summary"],
        "raw_message":   (t.get("raw_message") or "")[:300],
        "assignee_name": t.get("assignee_name"),
        "deadline":      t.get("deadline"),
        "priority":      t.get("priority"),
        "category":      t.get("category"),
        "status":        t.get("status"),
        "okr_ref":       meta.get("okr_ref"),
        "okr_action_id": meta.get("okr_action_id"),
        "breakdown":     meta.get("breakdown", []),
        "in_scope":      meta.get("in_scope"),
    }


TOOLS = {
    "team_workload":        tool_team_workload,
    "okr_status":           tool_okr_status,
    "metrics":              tool_metrics,
    "find_member_for_task": tool_find_member_for_task,
    "member_detail":        tool_member_detail,
    "task_detail":          tool_task_detail,
}


TOOL_DESCRIPTIONS = """
- team_workload(): tổng active/overdue/done_today + breakdown từng member
- okr_status(okr_id?): OKR tree (Q2/2026) + tasks tagged per OKR. Pass okr_id="O1" để filter.
- metrics(name?): KPI hiện tại (GSV, FR, COGS, driver tier). Pass name="fill_rate" để filter.
- find_member_for_task(task_text): recommend 5 candidates phù hợp scope. Pass task description as text.
- member_detail(name): scope + grade + current load của 1 thành viên. Pass tên người.
- task_detail(task_id): full info 1 task. Pass task_id integer.
""".strip()


# ─── Tool result cache (30s TTL — reuse across rapid follow-up questions) ─────

class _ToolCache:
    """Thread-safe TTL cache for tool results.

    Prevents redundant DB queries when manager asks multiple questions
    in quick succession (e.g., several /ask within 30 seconds).
    Errors are never cached so transient failures don't stick.
    """

    def __init__(self, ttl: float = _TOOL_RESULT_TTL):
        self._cache: dict[str, tuple[float, dict]] = {}
        self._ttl = ttl

    def _key(self, tool_name: str, args: dict) -> str:
        return f"{tool_name}:{json.dumps(args, sort_keys=True, default=str)}"

    def get(self, tool_name: str, args: dict) -> dict | None:
        key = self._key(tool_name, args)
        entry = self._cache.get(key)
        if entry:
            ts, data = entry
            if time.monotonic() - ts < self._ttl:
                return data
            del self._cache[key]
        return None

    def set(self, tool_name: str, args: dict, result: dict) -> None:
        if isinstance(result, dict) and "error" not in result:
            self._cache[self._key(tool_name, args)] = (time.monotonic(), result)

    def clear(self) -> None:
        self._cache.clear()


TOOL_CACHE = _ToolCache()


# ─── Pass 1: Planning ─────────────────────────────────────────────────────────

_PLAN_PROMPT = """Bạn là planner cho AI analyst. Manager hỏi câu sau, hãy CHỈ ĐỊNH tools cần gọi.
KHÔNG trả lời, chỉ pick tools.

TOOLS:
{tools}

Trả về JSON:
{{
  "tools_to_call": [
    {{"name": "<tool_name>", "args": {{<key>: <value>}}}}
  ],
  "reasoning": "Tại sao chọn các tool này (1 câu)"
}}

Rules:
- Gọi MỌI tool có thể giúp ích, tối đa {max_tools} tools
- Args phải đúng signature (xem TOOLS doc)
- Nếu câu hỏi về 1 người cụ thể → gọi member_detail
- Nếu câu hỏi về 1 OKR cụ thể → gọi okr_status với okr_id
- Nếu câu hỏi về metrics/KPI → gọi metrics
- Default fallback: team_workload + okr_status

Câu hỏi của manager:"""


def _plan_tools(question: str) -> list[dict]:
    # XML delimiter isolates user content from prompt instructions
    prompt = (
        _PLAN_PROMPT.format(tools=TOOL_DESCRIPTIONS, max_tools=_MAX_TOOLS)
        + f"\n<user_question>\n{question}\n</user_question>"
    )
    raw = call_tier("fast", prompt, label="ask_plan", max_output_tokens=600)
    result = safe_parse_json(raw)
    if not result:
        return [{"name": "team_workload", "args": {}}]
    tools = result.get("tools_to_call", [])[:_MAX_TOOLS]
    return [t for t in tools if t.get("name") in TOOLS]


# ─── Pass 2: Answer ────────────────────────────────────────────────────────────

def _build_answer_system() -> str:
    """Compose system prompt with business + OKR + team + grade context.

    Knowledge layers injected:
      L1 company_dna  — glossary, unit economics, competitors
      L3 okr_tree     — objectives, KRs, overdue/P0 actions
      L4 kpi_dict     — metric targets & thresholds
      L2 grade_matrix — grade definitions
    """
    # Legacy markdown prompts (fallback if YAML not filled)
    try:
        okr_md_legacy = (PROMPTS_DIR / "okr_truck_ops.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        okr_md_legacy = ""
    try:
        team_md = (PROMPTS_DIR / "team_context.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        team_md = ""

    # Grade matrix summary
    gm = kn.grade_matrix()
    grades_summary = ""
    for g in gm.get("grades", []):
        grades_summary += f"- **{g['id']}** ({g.get('label','')}): {g.get('one_liner','')}\n"

    # L1 — Company DNA
    dna = kn.company_dna()
    unit_econ = dna.get("unit_economics", {})
    ue_summary = ""
    if unit_econ:
        ue_summary = (
            f"Take rate: {unit_econ.get('take_rate_target', '26%')*100:.0f}% | "
            f"COGS Bulky target: <{unit_econ.get('cogs_targets', {}).get('bulky_pct', 0.30)*100:.0f}% | "
            f"Incentive budget: {unit_econ.get('incentive_budget_pct_of_gsv', 0.025)*100:.1f}% GSV | "
            f"COGS GXT target: {unit_econ.get('cogs_targets', {}).get('gxt_per_order_vnd', 75000):,} VNĐ/kiện"
        )

    glossary = kn.glossary_md(max_terms=25)

    # L3 — OKR tree (structured, prefer YAML; fallback to markdown)
    okr_yaml_md = kn.okr_context_md(max_chars=3500)
    okr_section = okr_yaml_md if okr_yaml_md != "(OKR tree not loaded)" else okr_md_legacy[:3000]

    # L2 — Conversion factors (impact quantification)
    cf_section = kn.conversion_impact_md(max_chars=1200)

    # L4 — KPI targets compact table
    kpi_section = kn.kpi_context_md(max_chars=2000)

    # Overdue + P0 urgent summary (injected as priority alerts)
    overdue = kn.list_overdue_actions()
    urgent = kn.list_urgent_actions()
    alert_lines = []
    for a in overdue:
        alert_lines.append(f"  ⚠️ OVERDUE: [{a['id']}] {a['summary']} (owner: {a.get('owner','?')}, DL: {a.get('deadline_iso','?')})")
    for a in urgent:
        if a.get("id") not in {x["id"] for x in overdue}:
            alert_lines.append(f"  🔴 P0 URGENT: [{a['id']}] {a['summary']} (owner: {a.get('owner','?')})")
    alerts_str = "\n".join(alert_lines) if alert_lines else "  (không có action P0/overdue)"

    today = datetime.now().strftime("%Y-%m-%d (%A)")

    return f"""Bạn là senior ops analyst cho team Truck Ops Ahamove. Trả lời câu hỏi từ manager với
phân tích chất lượng cao, dựa trên data + business context đầy đủ bên dưới.

Khi câu hỏi về KPI giảm/drop: CẦN nêu probable cause theo xác suất, câu hỏi chẩn đoán,
và action ngay — không chỉ nói "cần điều tra". Playbook context sẽ được inject vào DATA.

## L1 — Company DNA
Ahamove = tech-driven on-demand logistics platform, Vietnam.
Services Truck: Bulky (500kg-2.5T), Longhaul (>40km), House Moving, Rental (4/8/12h).
{ue_summary}
Driver tiers: Station >120 stop/m · Core >65 · Hub >40 · Mass >30
Driver income: Station >1M VNĐ/ngày · Core >750K · Hub >600K

### Glossary (internal jargon)
{glossary}

## L3 — OKR Q2/2026
{okr_section}

## ⚡ Priority Alerts (auto-detected from OKR tree)
{alerts_str}

## L2 — Business Impact (conversion factors)
{cf_section}

## L4 — KPI Targets & Thresholds
{kpi_section}

## Team & Org
{team_md}

## Grade matrix
{grades_summary}

## Reasoning style
- **Pyramid Principle**: kết luận trước, evidence sau
- **MECE**: phân tích đầy đủ, không overlap
- **Data-driven**: cite tool nào trả về data, không bịa số
- **Actionable**: kết luận phải có next step cụ thể
- **Tiếng Việt**, súc tích, bullet > prose
- Số liệu kèm context (vd: "FR HAN 60% vs target 70% — dưới chuẩn 10pp")
- Nếu thiếu data → nói rõ "không đủ data, cần check thêm X"
- Biết jargon: GXT=đơn Bulky nhỏ/kiện, LAN=Long An, EXP=expansion tỉnh, 1st PU=first pick-up on-time

TODAY = {today}
""".strip()


@dataclass
class _CachedSystem:
    """System prompt with TTL — auto-expires so TODAY + overdue alerts stay fresh."""
    content: str
    built_at: float

    def is_valid(self) -> bool:
        return time.monotonic() - self.built_at < _SYSTEM_CACHE_TTL


_SYSTEM_CACHE: _CachedSystem | None = None


def _answer_system() -> str:
    global _SYSTEM_CACHE
    if _SYSTEM_CACHE is None or not _SYSTEM_CACHE.is_valid():
        _SYSTEM_CACHE = _CachedSystem(
            content=_build_answer_system(),
            built_at=time.monotonic(),
        )
    return _SYSTEM_CACHE.content


def reload_knowledge() -> str:
    """Reload all YAML knowledge files + clear all caches.
    Call this after filling/updating any knowledge YAML file, or via /api/knowledge/reload.
    """
    global _SYSTEM_CACHE
    kn.reload()              # Clear YAML + JSON knowledge caches
    _SYSTEM_CACHE = None     # Force system prompt rebuild
    TOOL_CACHE.clear()       # Stale DB results no longer valid after reload
    return "Knowledge reloaded — system prompt + tool cache cleared."


# ═══════════════════════════════════════════════════════════════════════════
# TASK DECOMPOSITION — Manager sends high-level task → AI breaks into steps
# ═══════════════════════════════════════════════════════════════════════════

# Concrete next-step templates per category — used in smart reminders
# Keys must match category values in store.tasks.category
_REMINDER_STEPS: dict[str, list[str]] = {
    "fill_rate": [
        "Pull FR breakdown theo zone + giờ cao điểm (Redash/dashboard)",
        "So sánh current FR vs baseline + xác định zone bottom 3",
        "Root cause: driver supply thiếu, SLA config sai, hay routing issue?",
    ],
    "supply": [
        "Kiểm tra headcount driver active vs target theo zone",
        "Review onboard pipeline tháng này — bao nhiêu đã active?",
        "Identify zone thiếu supply nhất + propose action (thêm driver/shift incentive)",
    ],
    "cost": [
        "Pull data COGS breakdown theo zone/driver tier (Redash)",
        "Phân tích payout structure: Station vs Core vs Hub vs Mass",
        "Xác định top 3 cost driver + propose mitigation action",
    ],
    "b2b": [
        "Review SLA commitment vs actual performance tuần này",
        "Kiểm tra contract terms + điều khoản phạt/thưởng",
        "Đề xuất resolution hoặc re-negotiate timeline",
    ],
    "expansion": [
        "Confirm địa điểm/mặt bằng + điều kiện pháp lý",
        "Lập kế hoạch recruit driver local (target số lượng + timeline)",
        "Set go-live KPI + define success metric đo lường",
    ],
    "retention": [
        "Phân tích cohort driver churn: D7/D14/D30 retention",
        "Identify nhóm driver churn cao nhất (tier, zone, onboard period)",
        "Propose intervention: incentive/training/assignment adjustment",
    ],
    "tech": [
        "Define requirements + acceptance criteria rõ ràng",
        "Tạo ticket + assign BA/tech team + agree timeline",
        "Review và validate output trước khi deploy",
    ],
    "report": [
        "Collect data cần thiết từ các nguồn (Redash, Sheets, ops team)",
        "Draft report structure: headline → evidence → recommendation",
        "Review với manager trước khi gửi",
    ],
    "vendor": [
        "Liên hệ vendor theo contact list (xem 06_vendors.yaml)",
        "Document vấn đề: timeline, impact, evidence",
        "Escalate nếu SLA breach 2 tháng liên tiếp",
    ],
    "other": [
        "Xác định rõ định nghĩa done (definition of done)",
        "Break down thành milestones nhỏ hơn nếu >3 ngày",
        "Update status sau mỗi milestone",
    ],
}


def _steps_for_task(task: dict) -> list[str]:
    """Return category-appropriate next steps for a task."""
    # Check if steps are stored in classifier_meta
    try:
        import json as _j
        meta = _j.loads(task.get("classifier_meta") or "{}")
        if meta.get("steps"):
            return meta["steps"][:3]
    except Exception:
        pass
    cat = task.get("category", "other")
    return _REMINDER_STEPS.get(cat, _REMINDER_STEPS["other"])


def build_smart_reminder(task: dict, context: str = "deadline") -> str:
    """Build a focused, business-context-aware reminder message.

    context: "deadline" | "overdue" | "stall"
    Returns: Telegram-ready Markdown string.
    """
    tid = task.get("id", "?")
    summary = task.get("summary", "?")[:80]
    priority = task.get("priority", "P3")
    category = task.get("category", "other")
    deadline = task.get("deadline")
    assignee = task.get("assignee_name", "")
    p_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🔵"}.get(priority, "⚪")
    cat_emoji = {
        "fill_rate": "📊", "supply": "🚛", "cost": "💰",
        "b2b": "🏢", "expansion": "🗺", "retention": "🤝",
        "tech": "⚙️", "report": "📝", "vendor": "🤝", "other": "📌",
    }.get(category, "📌")

    # ── Deadline/overdue string ──
    dl_str = ""
    urgency_prefix = ""
    if deadline:
        try:
            dl = datetime.fromisoformat(deadline).replace(tzinfo=None)
            delta = dl - datetime.now()
            hours = delta.total_seconds() / 3600
            if hours < 0:
                days_over = abs(delta.days)
                h_over = abs(int(delta.total_seconds() / 3600))
                dl_str = f"⚠️ Quá hạn {h_over}h" if h_over < 48 else f"⚠️ Quá hạn {days_over} ngày"
                urgency_prefix = "🔴 " if priority in ("P0","P1") else "⚠️ "
            elif hours <= 4:
                dl_str = f"⏰ Còn {int(hours)}h"
                urgency_prefix = "🔥 " if priority == "P0" else "⏰ "
            elif hours <= 28:
                dl_str = f"📅 Còn {int(hours)}h ({dl.strftime('%d/%m %H:%M')})"
            else:
                dl_str = f"📅 {dl.strftime('%d/%m/%Y')}"
        except (ValueError, TypeError):
            dl_str = ""

    # ── OKR context ──
    okr_line = ""
    try:
        meta = {}
        import json as _j
        if task.get("classifier_meta"):
            meta = _j.loads(task["classifier_meta"])
        okr_tag = meta.get("okr_tag") or task.get("okr_tag", "")
        if okr_tag:
            for obj in kn.okr_tree().get("objectives", []):
                for kr in obj.get("krs", []):
                    if kr["id"] == okr_tag:
                        okr_line = f"📌 *OKR {kr['id']}:* {kr['label']} (target: {kr.get('target','?')})"
                        break
                # Check action ID too
                for a in obj.get("actions", []):
                    if a.get("id") == okr_tag or a.get("kr_ref") == okr_tag:
                        okr_line = f"📌 *OKR {obj['id']}:* {obj['label']}"
                        break
    except Exception:
        pass

    # ── Next steps ──
    steps = _steps_for_task(task)

    # ── Build message ──
    # Don't double-print emoji if urgency_prefix already has priority emoji
    p_part = "" if urgency_prefix.strip() in (p_emoji, "⚠️", "🔥") else f"{p_emoji} "
    header = f"{urgency_prefix}{p_part}*Task #{tid} — {cat_emoji} {summary}*"
    lines = [header]

    if dl_str:
        lines.append(dl_str)
    if okr_line:
        lines.append(okr_line)

    if steps:
        lines.append("\n💡 *Bước tiếp theo:*")
        numbers = ["1️⃣", "2️⃣", "3️⃣"]
        for i, step in enumerate(steps[:3]):
            lines.append(f"  {numbers[i]} {step}")

    # Footer
    if context == "overdue":
        lines.append(f"\n`/done {tid}` xong · `Reply` nếu blocked")
    elif context == "stall":
        lines.append(f"\nTask im lặng. Cần gì không? Reply hoặc `/block {tid} <lý do>`")
    else:
        lines.append(f"\n`/done {tid}` khi xong · `/snooze {tid} 2h` nếu cần")

    return "\n".join(lines)


# ─── Decomposition AI prompt ──────────────────────────────────────────────────

def _decompose_system() -> str:
    """System prompt for task decomposition — injected with team + OKR context."""
    # Build team roster from member_scopes
    scopes = kn.member_scopes()
    team_lines = []
    for m in scopes.get("members", []):
        email = m.get("email", "")
        short = m.get("short_name", "")
        grade = m.get("grade", "")
        owns = ", ".join(m.get("owns", [])[:4])
        team_lines.append(f"- {email} ({short}, {grade}): {owns}")
    team_str = "\n".join(team_lines) or "(team chưa load)"

    okr_str = kn.okr_context_md(max_chars=2000)
    cf_str = kn.conversion_impact_md(max_chars=800)
    dna = kn.company_dna()
    ue = dna.get("unit_economics", {})

    return f"""Bạn là senior ops analyst cho Truck Ops Ahamove.
Manager giao 1 task cấp cao. Nhiệm vụ của bạn:
1. Hiểu task → xác định OKR nào liên quan + tại sao quan trọng
2. Đề xuất 2-4 sub-tasks cụ thể, actionable, assign đúng người
3. Với mỗi sub-task: đề xuất 3 bước cụ thể để làm

## Unit economics context
- Take rate target: {ue.get('take_rate_target', 0.26)*100:.0f}%
- COGS Bulky target: <{ue.get('cogs_targets',{}).get('bulky_pct', 0.30)*100:.0f}%
- COGS GXT target: {ue.get('cogs_targets',{}).get('gxt_per_order_vnd', 75000):,} VNĐ/kiện
- Driver tiers: Station >120 · Core >65 · Hub >40 · Mass >30 stop/m

## Business impact (dùng khi set priority cho sub-tasks)
{cf_str}

## OKR Q2/2026
{okr_str}

## Team members (assign đúng scope)
{team_str}

## Rules
- owner_email phải là email thật trong danh sách trên
- summary phải actionable (bắt đầu bằng động từ: Phân tích, Tổng hợp, Implement...)
- steps phải cụ thể (tool/data nào, output là gì)
- deadline_days: tính từ hôm nay, realistic với scope
- priority: P0 (crisis), P1 (KR at-risk), P2 (normal), P3 (nice-to-have)

Return JSON object hợp lệ (không giải thích thêm).
""".strip()


_DECOMPOSE_SCHEMA = """{
  "understood_as": "1 câu diễn giải task theo business context",
  "okr_link": "O1.2",
  "why_urgent": "1 câu tại sao task này quan trọng với OKR",
  "priority": "P1",
  "category": "fill_rate",
  "sub_tasks": [
    {
      "summary": "Tên task ngắn gọn actionable",
      "owner_email": "thonglhn@ahamove.com",
      "owner_short": "Thống",
      "priority": "P1",
      "deadline_days": 3,
      "okr_tag": "O1.2",
      "steps": ["bước 1 cụ thể", "bước 2 cụ thể", "bước 3 cụ thể"]
    }
  ]
}"""


def decompose_task(task_text: str) -> dict:
    """Manager sends high-level task → AI decomposes into sub-tasks with owners + steps.

    Returns dict with keys:
      understood_as, okr_link, why_urgent, priority, category, sub_tasks
    Each sub_task: summary, owner_email, owner_short, priority, deadline_days, okr_tag, steps
    """
    if not task_text or not task_text.strip():
        return {"error": "task_text is required"}

    prompt = (
        f"Manager giao việc:\n\"{task_text.strip()}\"\n\n"
        f"Return JSON theo schema này (KHÔNG giải thích):\n{_DECOMPOSE_SCHEMA}"
    )

    try:
        raw = call_tier("balanced", prompt, system=_decompose_system(), json_mode=True)
        result = safe_parse_json(raw)

        # Validate required keys
        if "sub_tasks" not in result:
            return {"error": "AI did not return sub_tasks", "raw": str(raw)[:300]}

        # Ensure deadline_iso is set
        from datetime import timedelta
        today = datetime.now()
        for st in result.get("sub_tasks", []):
            days = st.get("deadline_days", 3)
            st["deadline_iso"] = (today + timedelta(days=days)).strftime("%Y-%m-%dT17:00:00")

        return result

    except Exception as e:
        logger.error(f"decompose_task failed: {e}")
        return {"error": str(e)}


def format_decompose_preview(decompose_result: dict) -> str:
    """Format decompose result as Telegram Markdown for manager to review."""
    if decompose_result.get("error"):
        return f"❌ Lỗi: {decompose_result['error']}"

    understood = decompose_result.get("understood_as", "?")
    okr_link = decompose_result.get("okr_link", "")
    why = decompose_result.get("why_urgent", "")
    sub_tasks = decompose_result.get("sub_tasks", [])

    lines = [
        "🧠 *Đã phân tích task:*\n",
        f"📎 _{understood}_",
    ]
    if okr_link:
        lines.append(f"📌 OKR: *{okr_link}*")
    if why:
        lines.append(f"⚡ _{why}_")

    lines.append(f"\n*Đề xuất {len(sub_tasks)} sub-tasks:*")

    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    for i, st in enumerate(sub_tasks[:4]):
        dl_days = st.get("deadline_days", 3)
        deadline_label = f"{dl_days} ngày" if dl_days > 1 else "ngày mai"
        p_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🔵"}.get(st.get("priority","P2"), "⚪")
        lines.append(f"\n{nums[i]} {p_emoji} *[{st.get('owner_short','?')}]* {st['summary']}")
        lines.append(f"   ⏱ {deadline_label}")
        steps = st.get("steps", [])
        if steps:
            lines.append("   💡 " + " → ".join(s[:35] for s in steps[:2]))

    lines.append("\n✅ /ok để tạo tất cả · ❌ /huy để bỏ")
    return "\n".join(lines)


def _format_tool_results(results: dict[str, dict]) -> str:
    chunks = []
    for name, data in results.items():
        try:
            blob = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except (TypeError, ValueError):
            blob = str(data)
        # Cap each tool output to keep context manageable
        if len(blob) > _TOOL_OUTPUT_MAX_CHARS:
            blob = blob[:_TOOL_OUTPUT_MAX_CHARS] + "\n... (truncated)"
        chunks.append(f"### Tool: `{name}`\n```json\n{blob}\n```")
    return "\n\n".join(chunks) if chunks else "(no tool data)"


# ─── Main entry ────────────────────────────────────────────────────────────────

def ask(question: str) -> dict:
    """
    Process a question through plan → fetch → reason loop.
    Returns:
      {
        "answer":       <markdown text>,
        "tools_used":   [<tool names>],
        "tool_results": {<name>: <data>},
        "plan_reason":  <why these tools>,
      }
    """
    try:
        question = _sanitize_question(question or "")
    except ValueError as e:
        return {"answer": str(e), "tools_used": [], "tool_results": {}}
    if not question:
        return {"answer": "Câu hỏi trống.", "tools_used": [], "tool_results": {}}

    # ── Pass 1: plan ───────────────────────────────────────────────────────────
    tools_plan = _plan_tools(question)
    if not tools_plan:
        tools_plan = [{"name": "team_workload", "args": {}}]
    logger.info(f"[smart_agent] plan: {[t.get('name') for t in tools_plan]}")

    # ── Execute tools (parallel + per-tool timeout + 30s result cache) ─────────
    tool_results: dict[str, dict] = {}
    to_fetch: list[tuple[str, dict]] = []

    for tc in tools_plan:
        name = tc.get("name")
        if name not in TOOLS:
            continue
        args = tc.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        # Cache hit → skip fetch
        cached = TOOL_CACHE.get(name, args)
        if cached is not None:
            logger.debug(f"[smart_agent] cache hit: {name}")
            tool_results[name] = cached
        else:
            to_fetch.append((name, args))

    if to_fetch:
        with ThreadPoolExecutor(max_workers=_MAX_TOOLS) as executor:
            futures = {
                executor.submit(TOOLS[name], **args): (name, args)
                for name, args in to_fetch
            }
            for future, (name, args) in futures.items():
                try:
                    result = future.result(timeout=_TOOL_TIMEOUT)
                except FuturesTimeout:
                    logger.warning(f"[smart_agent] tool timeout ({_TOOL_TIMEOUT}s): {name}")
                    result = {"error": f"tool timeout {_TOOL_TIMEOUT}s"}
                except TypeError:
                    # Signature mismatch — retry with no args, log it
                    logger.warning(f"[smart_agent] TypeError calling {name} — retrying empty")
                    try:
                        result = TOOLS[name]()
                    except Exception as e:
                        result = {"error": str(e)}
                except Exception as e:
                    result = {"error": str(e)}
                TOOL_CACHE.set(name, args, result)
                tool_results[name] = result

    # ── Playbook injection (if KPI symptom detected) ───────────────────────────
    playbook_context = ""
    try:
        pb = kn.playbook_for_symptom(question)
        if pb:
            playbook_context = (
                f"\n\n## 🔍 DIAGNOSTIC PLAYBOOK (auto-matched)\n"
                f"{kn.format_playbook_md(pb, max_chars=1500)}"
            )
    except Exception:
        pass

    # ── Pass 2: reason ─────────────────────────────────────────────────────────
    user_prompt = (
        f"## CÂU HỎI\n{question}\n\n"
        f"## DATA THU THẬP\n{_format_tool_results(tool_results)}"
        f"{playbook_context}\n\n"
        f"Hãy phân tích và trả lời theo style trong system instruction."
    )
    answer_text = call_tier(
        "premium",
        user_prompt,
        system=_answer_system(),
        json_mode=False,
        label="ask_answer",
        max_output_tokens=3000,
    )

    if not answer_text:
        return {
            "answer":       "Xin lỗi, AI đang lỗi — thử lại sau hoặc check log.",
            "tools_used":   list(tool_results.keys()),
            "tool_results": tool_results,
        }

    return {
        "answer":       answer_text,
        "tools_used":   list(tool_results.keys()),
        "tool_results": tool_results,
    }
