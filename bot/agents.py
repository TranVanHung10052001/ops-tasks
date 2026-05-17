"""
Sub-Agents — Premium-tier specialized agents for strategic decision support.

Two agents (Phase 2):
  - delegation_coach: cảnh báo G4/G3 khi đang giữ task lẽ ra phải delegate xuống.
  - crisis_commander: activate khi FR/SLA drop, vendor failure, supply gap.

Both call premium tier (Gemini 3.1 Pro default, swappable Opus 4.7 via env).

Public API:
  - coach_delegation(task: dict, current_assignee: dict, assigner: dict, ...) -> dict
  - run_crisis_commander(trigger: dict, ...) -> dict
"""

import logging
from datetime import datetime
from pathlib import Path

from models import call_tier
import knowledge_loader as kn

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
DELEGATION_PROMPT = (PROMPTS_DIR / "delegation_coach.md").read_text(encoding="utf-8")
CRISIS_PROMPT    = (PROMPTS_DIR / "crisis_commander.md").read_text(encoding="utf-8")
TEAM_CONTEXT     = (PROMPTS_DIR / "team_context.md").read_text(encoding="utf-8")
OKR_CONTEXT      = (PROMPTS_DIR / "okr_truck_ops.md").read_text(encoding="utf-8")


_DELEGATION_SYSTEM = f"""
{DELEGATION_PROMPT}

---

## Team Context

{TEAM_CONTEXT}

---

## OKR Q2/2026

{OKR_CONTEXT}

TODAY = {datetime.now().strftime("%Y-%m-%d (%A)")}
""".strip()


_CRISIS_SYSTEM = f"""
{CRISIS_PROMPT}

---

## Team Context

{TEAM_CONTEXT}

---

## OKR Q2/2026

{OKR_CONTEXT}

TODAY = {datetime.now().strftime("%Y-%m-%d (%A)")}
""".strip()


# ─── Delegation Coach ─────────────────────────────────────────────────────────

def coach_delegation(
    task: dict,
    current_assignee: dict | None = None,
    assigner: dict | None = None,
    team_load: list[dict] | None = None,
) -> dict:
    """
    Evaluate whether a task is correctly delegated. Returns coach verdict.

    Args:
        task: {id, summary, okr_ref, category, priority, deadline_iso, estimated_minutes}
        current_assignee: {name, grade, title, active_count, overdue_count} or None
        assigner: {name, grade, role} or None — who assigned
        team_load: list of {name, grade, active_count, overdue_count} for alternatives
    """
    # Find scope of current assignee from knowledge base
    scope = None
    if current_assignee:
        scope = kn.get_member_scope(name=current_assignee.get("name"))

    # Find playbook match for this task
    pb_match = None
    summary = task.get("summary", "").lower()
    for p in kn.list_playbooks():
        name = p.get("name", "").lower()
        if any(word in name for word in summary.split() if len(word) > 4):
            pb_match = p["id"]
            break

    input_payload = {
        "task": task,
        "current_assignee_scope": scope or {"_note": "scope not found in knowledge base"},
        "current_assignee_load": {
            "active_count": (current_assignee or {}).get("active_count"),
            "overdue_count": (current_assignee or {}).get("overdue_count"),
        } if current_assignee else None,
        "assigner": assigner,
        "playbook_match": pb_match,
        "team_alternatives": team_load[:5] if team_load else [],
    }

    import json
    prompt = (
        "INPUT cho Delegation Coach:\n\n"
        + json.dumps(input_payload, ensure_ascii=False, indent=2)
    )

    result = call_tier(
        "premium",
        prompt,
        system=_DELEGATION_SYSTEM,
        label="delegation_coach",
        max_output_tokens=2000,
        retries=1,
    )

    if not result:
        return {
            "verdict": "needs_clarification",
            "verdict_confidence": 0.0,
            "headline": "AI không phân tích được — thử lại hoặc check log.",
            "rationale": [],
            "recommended_owner": None,
            "split_suggestion": [],
            "red_flags": [],
            "playbook_pointer": pb_match,
            "coaching_question": None,
            "principles_applied": [],
        }

    return {
        "verdict":             result.get("verdict", "needs_clarification"),
        "verdict_confidence":  float(result.get("verdict_confidence", 0.5)),
        "headline":            result.get("headline", ""),
        "rationale":           result.get("rationale", []),
        "recommended_owner":   result.get("recommended_owner"),
        "split_suggestion":    result.get("split_suggestion", []),
        "red_flags":           result.get("red_flags", []),
        "playbook_pointer":    result.get("playbook_pointer") or pb_match,
        "coaching_question":   result.get("coaching_question"),
        "principles_applied":  result.get("principles_applied", []),
    }


# ─── Crisis Commander ─────────────────────────────────────────────────────────

CRISIS_TYPES = (
    "fr_drop", "sla_drop", "supply_gap", "vendor_failure",
    "hub_delay", "cost_overrun", "external_event",
)


def run_crisis_commander(
    trigger: dict,
    current_metrics: dict | None = None,
    team_members: list[dict] | None = None,
    constraints: dict | None = None,
) -> dict:
    """
    Activate crisis advisor. Returns RCA + immediate + structural + war_room + comms plan.

    Args:
        trigger: {type, severity_hint, raw_description, region, started_at?, duration_days?}
        current_metrics: {metric, current_value, target, trend} | None
        team_members: list[{name, grade, team}] available
        constraints: {budget_cap?, stakeholder_pressure?, time_to_recover_target_days?}
    """
    # Group team by grade for the agent
    by_grade: dict[str, list] = {"G3": [], "G2": [], "G1": []}
    for m in team_members or []:
        g = m.get("grade", "")
        if g in by_grade:
            by_grade[g].append({"name": m.get("name"), "team": m.get("team")})

    # Find playbook match
    pb_match = None
    if trigger.get("type") in ("fr_drop", "sla_drop"):
        pb_match = "PB14"

    input_payload = {
        "trigger": trigger,
        "current_metrics": current_metrics or {},
        "team_context": {
            "available_grades": by_grade,
            "playbook_match": pb_match,
        },
        "constraints": constraints or {},
    }

    import json
    prompt = (
        "INPUT cho Crisis Commander:\n\n"
        + json.dumps(input_payload, ensure_ascii=False, indent=2)
    )

    result = call_tier(
        "premium",
        prompt,
        system=_CRISIS_SYSTEM,
        label="crisis_commander",
        max_output_tokens=3000,
        retries=1,
    )

    if not result:
        return {
            "severity": "active_crisis",
            "severity_rationale": "AI không trả response — assume active_crisis để safe.",
            "headline": "⚠️ Crisis Commander offline — escalate manually.",
            "rca_questions": [],
            "immediate_actions": [],
            "structural_actions": [],
            "war_room": {},
            "communication_plan": {},
            "post_mortem_plan": {},
            "playbook_pointer": pb_match,
            "risks_to_action_plan": [],
        }

    return {
        "severity":             result.get("severity", "active_crisis"),
        "severity_rationale":   result.get("severity_rationale", ""),
        "headline":             result.get("headline", ""),
        "rca_questions":        result.get("rca_questions", []),
        "immediate_actions":    result.get("immediate_actions", []),
        "structural_actions":   result.get("structural_actions", []),
        "war_room":             result.get("war_room", {}),
        "communication_plan":   result.get("communication_plan", {}),
        "post_mortem_plan":     result.get("post_mortem_plan", {}),
        "playbook_pointer":     result.get("playbook_pointer") or pb_match,
        "risks_to_action_plan": result.get("risks_to_action_plan", []),
    }
