"""
Knowledge Loader — reads seed JSON + YAML files for the AI agent.
Layers loaded:
  L1  01_company_dna.yaml      — company context, glossary, unit economics
  L2  02_conversion_factors.yaml — FR/COGS/driver impact quantification
  L2  grade_matrix.json        — grade definitions & delegation principles
  L2  member_scopes.json       — member scopes, red flags
  L3  03_okr_tree.yaml         — OKR objectives, KRs, actions (Q2/2026)
  L4  04_kpi_dictionary.yaml   — KPI definitions, targets, thresholds
  L7  07_operating_rhythm.yaml — cadence, reporting, period definitions
  L10 10_playbooks.yaml        — diagnostic playbooks (root cause trees)
      playbooks.json           — legacy playbooks library (workflow)

Cached at module load; call reload() to refresh all.
"""

import json
import logging
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False
    logging.warning("PyYAML not installed — YAML knowledge files will not load. Run: pip install pyyaml")

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

_grade_matrix: dict | None = None
_playbooks: dict | None = None
_member_scopes: dict | None = None
_company_dna: dict | None = None
_conversion_factors: dict | None = None
_okr_tree: dict | None = None
_kpi_dict: dict | None = None
_operating_rhythm: dict | None = None
_diagnostic_playbooks: dict | None = None


def _load_json(filename: str) -> dict:
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        logger.warning(f"Knowledge file missing: {path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(filename: str) -> dict:
    if not _HAS_YAML:
        return {}
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        logger.debug(f"YAML knowledge not yet filled: {path}")
        return {}
    try:
        return _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return {}


def grade_matrix() -> dict:
    global _grade_matrix
    if _grade_matrix is None:
        _grade_matrix = _load_json("grade_matrix.json")
    return _grade_matrix


def playbooks() -> dict:
    global _playbooks
    if _playbooks is None:
        _playbooks = _load_json("playbooks.json")
    return _playbooks


def member_scopes() -> dict:
    global _member_scopes
    if _member_scopes is None:
        _member_scopes = _load_json("member_scopes.json")
    return _member_scopes


def company_dna() -> dict:
    """L1 — company context, glossary, unit economics, competitors."""
    global _company_dna
    if _company_dna is None:
        _company_dna = _load_yaml("01_company_dna.yaml")
    return _company_dna


def conversion_factors() -> dict:
    """L2 — impact quantification: FR 1pp = X orders/day = Y tỷ GSV, etc."""
    global _conversion_factors
    if _conversion_factors is None:
        _conversion_factors = _load_yaml("02_conversion_factors.yaml")
    return _conversion_factors


def okr_tree() -> dict:
    """L3 — OKR tree: objectives, KRs, actions, dependencies (Q2/2026)."""
    global _okr_tree
    if _okr_tree is None:
        _okr_tree = _load_yaml("03_okr_tree.yaml")
    return _okr_tree


def kpi_dict() -> dict:
    """L4 — KPI dictionary: metric definitions, targets, thresholds."""
    global _kpi_dict
    if _kpi_dict is None:
        _kpi_dict = _load_yaml("04_kpi_dictionary.yaml")
    return _kpi_dict


def operating_rhythm() -> dict:
    """L7 — Operating rhythm: cadence, reporting, period definitions."""
    global _operating_rhythm
    if _operating_rhythm is None:
        _operating_rhythm = _load_yaml("07_operating_rhythm.yaml")
    return _operating_rhythm


def diagnostic_playbooks() -> dict:
    """L10 — Diagnostic playbooks: root cause trees per KPI symptom."""
    global _diagnostic_playbooks
    if _diagnostic_playbooks is None:
        _diagnostic_playbooks = _load_yaml("10_playbooks.yaml")
    return _diagnostic_playbooks


def reload() -> None:
    global _grade_matrix, _playbooks, _member_scopes
    global _company_dna, _conversion_factors, _okr_tree, _kpi_dict
    global _operating_rhythm, _diagnostic_playbooks
    _grade_matrix = None
    _playbooks = None
    _member_scopes = None
    _company_dna = None
    _conversion_factors = None
    _okr_tree = None
    _kpi_dict = None
    _operating_rhythm = None
    _diagnostic_playbooks = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def get_grade(grade_id: str) -> dict | None:
    """e.g. 'G4' → grade definition dict."""
    for g in grade_matrix().get("grades", []):
        if g["id"] == grade_id or g["id"].endswith(f"-{grade_id}"):
            return g
    return None


def get_member_scope(email: str | None = None, name: str | None = None) -> dict | None:
    """Find member scope by email (preferred) or short_name match."""
    if not email and not name:
        return None
    needle_email = email.lower().strip() if email else None
    needle_name = name.lower().strip() if name else None
    for m in member_scopes().get("members", []):
        if needle_email and m.get("email", "").lower() == needle_email:
            return m
    if needle_name:
        for m in member_scopes().get("members", []):
            if (m.get("short_name", "").lower() == needle_name
                or m.get("name", "").lower() == needle_name
                or needle_name in m.get("name", "").lower()):
                return m
    return None


def list_playbooks() -> list[dict]:
    return playbooks().get("playbooks", [])


def get_playbook(playbook_id: str) -> dict | None:
    for p in list_playbooks():
        if p["id"].lower() == playbook_id.lower():
            return p
    return None


def search_playbooks(query: str, grade: str | None = None) -> list[dict]:
    q = query.lower().strip()
    results = []
    for p in list_playbooks():
        match = (
            q in p.get("name", "").lower()
            or q in p.get("category", "").lower()
            or any(q in (link or "").lower() for link in p.get("okr_links", []))
        )
        if grade and p.get("owner_grade") != grade:
            continue
        if not q or match:
            results.append(p)
    return results


def playbooks_for_grade(grade: str) -> list[dict]:
    return [p for p in list_playbooks() if p.get("owner_grade") == grade]


def delegation_health(team_stats: dict | None = None) -> dict:
    """Compute high-level delegation health signals.

    For now, returns target/warning thresholds + static signals from member_scopes red_flags.
    Real-time metrics can be wired in when task tagging by grade is available.
    """
    targets = member_scopes().get("delegation_health_targets", {})
    signals = []
    for m in member_scopes().get("members", []):
        for flag in m.get("red_flags", []):
            signals.append({
                "member": m["short_name"],
                "grade": m["grade"],
                "flag": flag,
            })

    return {
        "targets": targets,
        "red_flag_signals": signals,
        "principles": grade_matrix().get("delegation_principles", []),
    }


# ─── YAML Knowledge Helpers (for smart_agent system prompt injection) ─────────

def okr_context_md(max_chars: int = 3000) -> str:
    """Return a concise markdown summary of OKR tree for system prompt injection."""
    tree = okr_tree()
    if not tree:
        return "(OKR tree not loaded)"

    lines = [f"**Period:** {tree.get('period', '?')}",
             f"**North Star:** {(tree.get('north_star') or '').strip()}", ""]

    for obj in tree.get("objectives", []):
        lines.append(f"### {obj['id']} — {obj['label']}")
        lines.append(f"Owner: {obj.get('owner', '?')}")
        for kr in obj.get("krs", []):
            cur = kr.get("current_value")
            cur_str = f" | current: {cur}" if cur is not None else ""
            lines.append(f"- **{kr['id']}** {kr['label']} (target: {kr.get('target', '?')}{cur_str})")

        # Only show non-done, flagged actions
        actions = obj.get("actions", [])
        urgent = [a for a in actions if a.get("status") in ("overdue", "pending") and "P0" in str(a.get("notes", ""))]
        overdue = [a for a in actions if a.get("status") == "overdue"]
        for a in overdue:
            lines.append(f"  ⚠️ OVERDUE [{a['id']}] {a['summary']} — {a.get('owner','?')} DL:{a.get('deadline_iso','?')}")
        for a in urgent:
            if a not in overdue:
                lines.append(f"  🔴 P0 URGENT [{a['id']}] {a['summary']}")
        lines.append("")

    result = "\n".join(lines)
    return result[:max_chars] if len(result) > max_chars else result


def kpi_context_md(max_chars: int = 2000) -> str:
    """Return key KPI targets as compact markdown for system prompt injection."""
    kd = kpi_dict()
    if not kd:
        return "(KPI dictionary not loaded)"

    lines = ["| Metric | Target | P0 threshold |", "|--------|--------|-------------|"]
    for m in kd.get("metrics", []):
        key = m.get("key", "")
        label = m.get("label", key)
        target = m.get("target", "?")
        p0_low = m.get("threshold_p0_low")
        p0_high = m.get("threshold_p0_high")
        p0 = f"<{p0_low}" if p0_low else (f">{p0_high}" if p0_high else "—")
        unit = m.get("unit", "")
        lines.append(f"| {label} | {target} {unit} | {p0} {unit} |")

    result = "\n".join(lines)
    return result[:max_chars] if len(result) > max_chars else result


def glossary_md(max_terms: int = 20) -> str:
    """Return key glossary terms from company_dna."""
    dna = company_dna()
    glossary = dna.get("glossary", {})
    if not glossary:
        return ""
    lines = []
    for i, (term, definition) in enumerate(glossary.items()):
        if i >= max_terms:
            break
        lines.append(f"- **{term}**: {definition}")
    return "\n".join(lines)


def period_definitions() -> dict:
    """Return period definitions from operating_rhythm for date parsing."""
    rhythm = operating_rhythm()
    return rhythm.get("period_definitions", {})


def kpi_targets() -> dict[str, str]:
    """Return {metric_key: "target X unit"} — single source of truth from kpi_dict.

    Used by tool_metrics() so targets stay in sync with YAML, not hardcoded in code.
    """
    result = {}
    for m in kpi_dict().get("metrics", []):
        key = m.get("key")
        if not key:
            continue
        target = m.get("target", "?")
        unit = m.get("unit", "")
        unit_str = f" {unit}" if unit else ""
        result[key] = f"target {target}{unit_str}"
    return result


def get_metric(key: str) -> dict | None:
    """Look up a metric definition by key."""
    for m in kpi_dict().get("metrics", []):
        if m.get("key") == key:
            return m
    return None


def check_metric_alert(key: str, value: float) -> dict | None:
    """Check if a metric value triggers a P0/P1 alert. Returns alert dict or None."""
    m = get_metric(key)
    if not m:
        return None
    alerts = []
    if "threshold_p0_low" in m and value < m["threshold_p0_low"]:
        alerts.append({"severity": "P0", "direction": "below", "threshold": m["threshold_p0_low"]})
    if "threshold_p1_low" in m and value < m["threshold_p1_low"]:
        alerts.append({"severity": "P1", "direction": "below", "threshold": m["threshold_p1_low"]})
    if "threshold_p0_high" in m and value > m["threshold_p0_high"]:
        alerts.append({"severity": "P0", "direction": "above", "threshold": m["threshold_p0_high"]})
    if "threshold_p1_high" in m and value > m["threshold_p1_high"]:
        alerts.append({"severity": "P1", "direction": "above", "threshold": m["threshold_p1_high"]})
    return alerts[0] if alerts else None


def get_action(action_id: str) -> dict | None:
    """Look up an OKR action by ID (e.g. '2.1.3')."""
    for obj in okr_tree().get("objectives", []):
        for a in obj.get("actions", []):
            if a.get("id") == action_id:
                return {**a, "objective_id": obj["id"], "objective_label": obj["label"]}
    return None


def list_overdue_actions() -> list[dict]:
    """Return all overdue OKR actions with objective context."""
    results = []
    for obj in okr_tree().get("objectives", []):
        for a in obj.get("actions", []):
            if a.get("status") in ("overdue",):
                results.append({**a, "objective": obj["id"], "objective_label": obj["label"]})
    return results


def list_urgent_actions() -> list[dict]:
    """Return P0-urgent pending actions (keyword 'P0' in notes)."""
    results = []
    for obj in okr_tree().get("objectives", []):
        for a in obj.get("actions", []):
            if "P0" in str(a.get("notes", "")) and a.get("status") not in ("done",):
                results.append({**a, "objective": obj["id"]})
    return results


# ─── Conversion Factor Helpers ────────────────────────────────────────────────

def impact_of_initiative(initiative_id: str) -> dict | None:
    """Lookup a ranked initiative from conversion_factors.priority_by_impact."""
    for item in conversion_factors().get("priority_by_impact", []):
        if item.get("initiative", "").startswith(initiative_id):
            return item
    return None


def conversion_impact_md(max_chars: int = 1500) -> str:
    """Return compact impact table for system prompt injection."""
    cf = conversion_factors()
    if not cf:
        return "(Conversion factors not loaded)"

    lines = ["**Tác động theo tỷ VNĐ/quý (ước tính Q2/2026):**",
             "| # | Initiative | Quarterly impact | Status |",
             "|---|-----------|-----------------|--------|"]

    for item in cf.get("priority_by_impact", []):
        rank = item.get("rank", "?")
        name = item.get("initiative", "?")[:50]
        impact = f"{item.get('quarterly_b', '?')} tỷ"
        status = item.get("status", "?")[:30]
        lines.append(f"| {rank} | {name} | {impact} | {status} |")

    # Also add key FR impact per pp
    fr = cf.get("fill_rate", {})
    if fr:
        lines.append("")
        lines.append(f"**FR +1pp** = ~{fr.get('per_pp_orders_per_day', '?')} orders/ngày = {fr.get('per_pp_revenue_per_month_m', '?')}M VNĐ/tháng")

    cogs = cf.get("cogs", {})
    if cogs:
        lines.append(f"**COGS GXT -5K** = {cogs.get('gxt_monthly_saving_m', '?')}M VNĐ tiết kiệm/tháng")

    result = "\n".join(lines)
    return result[:max_chars] if len(result) > max_chars else result


# ─── Diagnostic Playbook Helpers ──────────────────────────────────────────────

def playbook_for_kpi(kpi_key: str) -> dict | None:
    """Return the best matching diagnostic playbook for a KPI metric key."""
    for pb in diagnostic_playbooks().get("playbooks", []):
        if kpi_key in pb.get("kpi_keys", []):
            return pb
    return None


def playbook_for_symptom(symptom_text: str) -> dict | None:
    """Fuzzy match a symptom description to a diagnostic playbook."""
    symptom_lower = symptom_text.lower()
    # Keyword mapping
    keyword_map = {
        ("fill rate", "fr", "fill_rate", "fr drop", "fr thấp"): "PB-01",
        ("cogs", "cost", "chi phí", "gxt"): "PB-02",
        ("driver", "retention", "churn", "d30"): "PB-03",
        ("pick up", "pickup", "pu", "1st pu", "on-time", "ontime"): "PB-04",
        ("gsv", "revenue", "doanh thu", "orders"): "PB-05",
    }
    for keywords, pb_id in keyword_map.items():
        if any(kw in symptom_lower for kw in keywords):
            for pb in diagnostic_playbooks().get("playbooks", []):
                if pb.get("id") == pb_id:
                    return pb
    return None


def format_playbook_md(pb: dict, max_chars: int = 2000) -> str:
    """Format a diagnostic playbook as Telegram-friendly markdown."""
    if not pb:
        return ""
    lines = [
        f"🔍 *Playbook {pb['id']}: {pb['symptom']}*",
        "",
        "*Probable causes (theo xác suất):*",
    ]
    for c in sorted(pb.get("probable_causes", []), key=lambda x: -x.get("weight", 0)):
        pct = int(c["weight"] * 100)
        lines.append(f"  {pct}% — {c['cause']}")

    lines.append("")
    lines.append("*Câu hỏi chẩn đoán:*")
    for q in pb.get("diagnosis_questions", [])[:4]:
        lines.append(f"  ❓ {q}")

    lines.append("")
    lines.append("*Hành động ngay:*")
    for step in pb.get("quick_actions", [])[:3]:
        lines.append(f"  {step['step']}. {step['action']}")

    escalate = pb.get("escalate_if", [])
    if escalate:
        lines.append("")
        lines.append("*Escalate nếu:*")
        for e in escalate[:2]:
            lines.append(f"  🚨 {e['condition']} → {e['escalate_to']}")

    result = "\n".join(lines)
    return result[:max_chars] if len(result) > max_chars else result
