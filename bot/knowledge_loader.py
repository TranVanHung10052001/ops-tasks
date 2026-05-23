"""
Knowledge Loader — reads seed JSON files for grade matrix, playbooks, and member scopes.
Cached at module load; reload by re-importing or calling reload().
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

_grade_matrix: dict | None = None
_playbooks: dict | None = None
_member_scopes: dict | None = None


def _load_json(filename: str) -> dict:
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        logger.warning(f"Knowledge file missing: {path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def reload() -> None:
    global _grade_matrix, _playbooks, _member_scopes
    _grade_matrix = None
    _playbooks = None
    _member_scopes = None


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
