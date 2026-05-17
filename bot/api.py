"""
FastAPI backend — REST API for the web dashboard.
Shares store.py with the Telegram bot (same SQLite DB).
Runs alongside the bot via uvicorn.
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(__file__))

from store import (
    init_db, list_users, get_user, list_team_by_person, get_team_stats,
    list_team_tasks, get_task, mark_done, cancel_task, snooze_task,
    update_task_deadline, list_pending_approval, approve_user,
    set_user_role, add_task, block_task, unblock_task,
    get_all_overdue_tasks, get_user_stats, log_action,
)
from roles import MANAGER, TEAM_LEAD, EMPLOYEE, ROLE_LABELS
import knowledge_loader as kn
from agents import coach_delegation, run_crisis_commander, CRISIS_TYPES
from models import tier_info

DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "ops-tasks-secret-change-me")

app = FastAPI(title="Ops Tasks API", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod: ["https://ops.ahamove.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != DASHBOARD_SECRET:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


@app.on_event("startup")
def startup():
    init_db()


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats(token: str = Depends(verify_token)):
    stats = get_team_stats()
    overdue_tasks = get_all_overdue_tasks()
    members = list_team_by_person()

    overloaded = [m for m in members if m.get("active_count", 0) > 8]
    underloaded = [m for m in members if m.get("active_count", 0) <= 1
                   and m.get("role") != MANAGER]

    return {
        **stats,
        "overloaded_count": len(overloaded),
        "member_count": len(members),
        "overdue_tasks": [_fmt_task(t) for t in overdue_tasks[:5]],
    }


# ─── Team ─────────────────────────────────────────────────────────────────────

@app.get("/api/team")
def get_team(token: str = Depends(verify_token)):
    members = list_team_by_person()
    return [_fmt_member(m) for m in members]


@app.get("/api/team/{user_id}/tasks")
def get_member_tasks(
    user_id: int,
    status: Optional[str] = Query(None),
    token: str = Depends(verify_token),
):
    statuses = [status] if status else ["pending", "in_progress", "blocked"]
    tasks = list_team_tasks(statuses=statuses)
    user_tasks = [t for t in tasks if t.get("assignee_id") == user_id]
    return [_fmt_task(t) for t in user_tasks]


# ─── Tasks ────────────────────────────────────────────────────────────────────

@app.get("/api/tasks")
def get_tasks(
    status: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    token: str = Depends(verify_token),
):
    statuses = [status] if status else ["pending", "in_progress", "blocked", "snoozed"]
    all_tasks = list_team_tasks(team=team, statuses=statuses, limit=limit)

    if assignee_id:
        all_tasks = [t for t in all_tasks if t.get("assignee_id") == assignee_id]
    if priority:
        all_tasks = [t for t in all_tasks if t.get("priority") == priority]
    if search:
        q = search.lower()
        all_tasks = [t for t in all_tasks
                     if q in t.get("summary", "").lower()
                     or q in (t.get("assignee_name") or "").lower()]

    return {
        "tasks": [_fmt_task(t) for t in all_tasks],
        "total": len(all_tasks),
    }


@app.get("/api/tasks/done")
def get_done_tasks(
    days: int = Query(7, le=30),
    token: str = Depends(verify_token),
):
    tasks = list_team_tasks(statuses=["done"], limit=200)
    return [_fmt_task(t) for t in tasks]


@app.get("/api/tasks/{task_id}")
def get_task_detail(task_id: int, token: str = Depends(verify_token)):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _fmt_task(task)


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    deadline: Optional[str] = None
    block_reason: Optional[str] = None


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate, token: str = Depends(verify_token)):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.status == "done":
        mark_done(task_id)
    elif body.status == "cancelled":
        cancel_task(task_id)
    elif body.status == "blocked" and body.block_reason:
        block_task(task_id, body.block_reason)
    elif body.status == "pending":
        unblock_task(task_id)

    if body.priority:
        from store import update_task_priority
        update_task_priority(task_id, body.priority)

    if body.deadline:
        update_task_deadline(task_id, body.deadline, "dashboard")

    if body.assignee_id:
        import sqlite3, json
        from store import get_db, DB_PATH
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET assignee_id = ? WHERE id = ?",
                (body.assignee_id, task_id)
            )

    log_action(0, "dashboard_update", "task", task_id, str(body.dict(exclude_none=True)))
    return {"ok": True, "task": _fmt_task(get_task(task_id))}


class CreateTaskBody(BaseModel):
    summary: str
    assignee_id: int
    priority: str = "P2"
    deadline: Optional[str] = None
    category: str = "other"


@app.post("/api/tasks")
def create_task(body: CreateTaskBody, token: str = Depends(verify_token)):
    assignee = get_user(body.assignee_id)
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    task_id = add_task(
        raw_message=body.summary,
        summary=body.summary,
        assignee_id=body.assignee_id,
        assigned_by=0,  # dashboard-created
        team=assignee.get("team"),
        source="dashboard",
        deadline=body.deadline,
        priority=body.priority,
        category=body.category,
    )
    log_action(0, "create_task", "task", task_id, body.summary)
    return {"ok": True, "task_id": task_id}


# ─── Users ────────────────────────────────────────────────────────────────────

@app.get("/api/users")
def get_users(
    approved_only: bool = Query(True),
    token: str = Depends(verify_token),
):
    users = list_users(approved_only=approved_only)
    return [_fmt_user(u) for u in users]


@app.get("/api/users/pending")
def get_pending_users(token: str = Depends(verify_token)):
    pending = list_pending_approval()
    return [_fmt_user(u) for u in pending]


@app.post("/api/users/{user_id}/approve")
def approve_user_endpoint(user_id: int, token: str = Depends(verify_token)):
    if not approve_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    log_action(0, "approve_user", "user", user_id)
    return {"ok": True}


class SetRoleBody(BaseModel):
    role: str
    team: Optional[str] = None


@app.patch("/api/users/{user_id}/role")
def set_role(user_id: int, body: SetRoleBody, token: str = Depends(verify_token)):
    if body.role not in (MANAGER, TEAM_LEAD, EMPLOYEE):
        raise HTTPException(status_code=400, detail="Invalid role")
    set_user_role(user_id, body.role, team=body.team)
    return {"ok": True}


# ─── OKR Progress ─────────────────────────────────────────────────────────────

OKR_TREE = [
    {
        "id": "O1",
        "label": "Fill Rate",
        "krs": [
            {"id": "O1.1", "label": "FR Core ≥68%", "baseline": "60.5%", "target": "68%", "weight": "2%"},
            {"id": "O1.2", "label": "FR Long Haul ≥70%", "baseline": "~50%", "target": "70%", "weight": "9%"},
            {"id": "O1.3", "label": "FR SME 100–300kg ≥65%", "baseline": "17%", "target": "65%", "weight": "shared"},
        ],
        "category": "ops",
    },
    {
        "id": "O2",
        "label": "Supply & Retention",
        "krs": [
            {"id": "O2.1", "label": "KCN BDG live 30/04 + Mini-hub LAN 15/05", "target": "2 hubs live", "weight": "shared"},
            {"id": "O2.2", "label": "Shift Model ≥100 drivers", "target": "100 drivers", "weight": "8%"},
            {"id": "O2.3", "label": "Moving Crew ≥50 certified", "target": "50 crew", "weight": "shared"},
            {"id": "O2.4", "label": "Driver Retention D30 70%", "baseline": "65%", "target": "70%", "weight": "8%"},
            {"id": "O2.5", "label": "Decal verified 1,900", "baseline": "1,600", "target": "1,900", "weight": "6%"},
            {"id": "O2.6", "label": "EV Van 1 đối tác live", "target": "1 partner", "weight": "6%"},
        ],
        "category": "supply",
    },
    {
        "id": "O3",
        "label": "Service & Cost",
        "krs": [
            {"id": "O3.1", "label": "1st PU On-Time 80%", "baseline": "47.6%", "target": "80%", "weight": "9%"},
            {"id": "O3.2", "label": "COGS GXT 75,000đ/kiện", "baseline": "80,000đ", "target": "75,000đ", "weight": "9%"},
            {"id": "O3.3", "label": "Vendor Truck B2B 11", "baseline": "8", "target": "11", "weight": "—"},
            {"id": "O3.4", "label": "Distribution GSV ≥4.5B pilot", "target": "4.5B", "weight": "7%"},
        ],
        "category": "quality",
    },
    {
        "id": "O4",
        "label": "Tech & Growth",
        "krs": [
            {"id": "O4.1", "label": "Dynamic Pricing 100% research", "target": "100%", "weight": "8%"},
            {"id": "O4.2", "label": "Vehicle Classification 60% fleet", "target": "60%", "weight": "7%"},
            {"id": "O4.3", "label": "AI Bot OPS report 40% auto", "target": "40%", "weight": "7%"},
            {"id": "O5.1", "label": "GHN 9 tỉnh thành", "baseline": "7 tỉnh", "target": "9 tỉnh", "weight": "2%"},
        ],
        "category": "tech",
    },
]

ACTIONS = [
    # O1
    {"id":"1.1.1","okr":"O1.1","kr":"O5.KR5.2","name":"Supply Gap Analysis by Region","pic":"OPS + BA","priority":"P0","deadline":"2026-04-29"},
    {"id":"1.1.2","okr":"O1.1","kr":"O5.KR5.2","name":"Driver Reactivation Campaign","pic":"OPS SGN/HAN","priority":"P0","deadline":"2026-04-30"},
    {"id":"1.1.3","okr":"O1.1","kr":"O5.KR5.2","name":"EXP Region Supply Build-up","pic":"OPS Extension","priority":"P1","deadline":"2026-05-27"},
    {"id":"1.1.4","okr":"O1.1","kr":"O5.KR5.2","name":"Weekly FR Monitoring Dashboard","pic":"OPS + BA","priority":"P1","deadline":"2026-04-30"},
    {"id":"1.2.1","okr":"O1.2","kr":"O1.KR1.3","name":"Long Haul Driver Pool Analysis","pic":"OPS Extension + BA","priority":"P0","deadline":"2026-05-10"},
    {"id":"1.2.2","okr":"O1.2","kr":"O1.KR1.3","name":"LH Recruit Driver Program","pic":"OPS Extension","priority":"P0","deadline":"2026-05-22"},
    {"id":"1.2.3","okr":"O1.2","kr":"O1.KR1.3","name":"Schedule Booking LH order","pic":"OPS + BA","priority":"P0","deadline":"2026-06-15"},
    {"id":"1.2.4","okr":"O1.2","kr":"O1.KR1.3","name":"LH Supply Activation","pic":"OPS HAN","priority":"P0","deadline":"2026-05-31"},
    {"id":"1.3.1","okr":"O1.3","kr":"O5.KR5.2","name":"RCA FR SME 100–300kg","pic":"OPS + Product","priority":"P0","deadline":"2026-05-18"},
    {"id":"1.3.2","okr":"O1.3","kr":"O5.KR5.2","name":"Relaunch Pooling SME 100–300kg","pic":"OPS SGN/HAN","priority":"P0","deadline":"2026-05-22"},
    {"id":"1.3.3","okr":"O1.3","kr":"O5.KR5.2","name":"Add service + Cross service","pic":"OPS SGN/HAN","priority":"P0","deadline":"2026-05-15"},
    {"id":"1.3.4","okr":"O1.3","kr":"O5.KR5.2","name":"Tier Commission 100–300kg","pic":"OPS SGN/HAN","priority":"P1","deadline":"2026-04-30"},
    # O2
    {"id":"2.1.1","okr":"O2.1","kr":"O5.KR5.2","name":"KCN BDG Site Survey","pic":"OPS EXP","priority":"P1","deadline":"2026-05-10"},
    {"id":"2.1.2","okr":"O2.1","kr":"O5.KR5.2","name":"Driver Recruitment KCN BDG","pic":"OPS EXP","priority":"P1","deadline":"2026-05-27"},
    {"id":"2.1.3","okr":"O2.1","kr":"O5.KR5.2","name":"BDG KCN Hub Go-live","pic":"OPS EXP","priority":"P1","deadline":"2026-05-20"},
    {"id":"2.1.4","okr":"O2.1","kr":"O5.KR5.2","name":"LAN Hub Location & Lease","pic":"OPS EXP","priority":"P1","deadline":"2026-06-30"},
    {"id":"2.1.5","okr":"O2.1","kr":"O5.KR5.2","name":"Driver Recruitment LAN","pic":"OPS EXP","priority":"P1","deadline":"2026-05-27"},
    {"id":"2.1.6","okr":"O2.1","kr":"O5.KR5.2","name":"Mini-hub LAN Go-live","pic":"OPS EXP","priority":"P1","deadline":"2026-05-15"},
    {"id":"2.2.1","okr":"O2.2","kr":"O2.KR2.1","name":"Shift Model Design & Scheme","pic":"OPS HAN + HCM","priority":"P1","deadline":"2026-04-22"},
    {"id":"2.2.2","okr":"O2.2","kr":"O2.KR2.1","name":"Cohort Selection SGN+HAN","pic":"OPS HAN + HCM","priority":"P1","deadline":"2026-04-30"},
    {"id":"2.2.3","okr":"O2.2","kr":"O2.KR2.1","name":"Shift Scheduling System Setup","pic":"OPS + Product","priority":"P1","deadline":"2026-05-07"},
    {"id":"2.2.4","okr":"O2.2","kr":"O2.KR2.1","name":"HAN Shift Pilot Launch","pic":"OPS HAN","priority":"P1","deadline":"2026-05-15"},
    {"id":"2.2.5","okr":"O2.2","kr":"O2.KR2.1","name":"SGN Shift Pilot Launch","pic":"OPS SGN","priority":"P1","deadline":"2026-05-15"},
    {"id":"2.3.1","okr":"O2.3","kr":"O1.KR1.3","name":"Moving Crew Profile & Training","pic":"OPS","priority":"P0","deadline":"2026-05-15"},
    {"id":"2.3.2","okr":"O2.3","kr":"O1.KR1.3","name":"HAN+HCM Crew Recruitment","pic":"OPS HAN + HCM","priority":"P0","deadline":"2026-06-15"},
    {"id":"2.4.1","okr":"O2.4","kr":"O2.KR2.1","name":"Driver Churn Analysis","pic":"OPS + BA","priority":"P0","deadline":"2026-05-07"},
    {"id":"2.4.2","okr":"O2.4","kr":"O2.KR2.1","name":"Driver Loyalty Program Design","pic":"OPS Fleet + Product","priority":"P0","deadline":"2026-05-15"},
    {"id":"2.4.3","okr":"O2.4","kr":"O2.KR2.1","name":"Loyalty Program Launch","pic":"OPS Fleet","priority":"P1","deadline":"2026-05-31"},
    {"id":"2.5.1","okr":"O2.5","kr":"O2.KR2.3","name":"Decal Campaign April Push","pic":"Growth + OPS","priority":"P1","deadline":"2026-04-30"},
    {"id":"2.5.2","okr":"O2.5","kr":"O2.KR2.3","name":"Decal Tracking Q2","pic":"Growth + OPS","priority":"P1","deadline":"2026-06-30"},
    {"id":"2.6.1","okr":"O2.6","kr":"O2.KR2.2","name":"EV Van Pilot XanhSM Contract","pic":"OPS Supply","priority":"P1","deadline":"2026-04-30"},
    {"id":"2.6.2","okr":"O2.6","kr":"O2.KR2.2","name":"EV Fleet Technical Setup","pic":"OPS + Product","priority":"P1","deadline":"2026-05-31"},
    # O3
    {"id":"3.1.1","okr":"O3.1","kr":"O3.KR3.2","name":"SLA Redesign GHN/GXT","pic":"OPS + MP","priority":"P0","deadline":"2026-04-15"},
    {"id":"3.1.2","okr":"O3.1","kr":"O3.KR3.2","name":"Convert active Bulky MP","pic":"OPS Supply","priority":"P0","deadline":"2026-04-30"},
    {"id":"3.1.3","okr":"O3.1","kr":"O3.KR3.2","name":"Plan End Month (cross-service)","pic":"OPS","priority":"P1","deadline":"2026-04-22"},
    {"id":"3.2.1","okr":"O3.2","kr":"O3.KR3.1","name":"COGS Line-item Breakdown","pic":"OPS + BA","priority":"P0","deadline":"2026-04-20"},
    {"id":"3.2.2","okr":"O3.2","kr":"O3.KR3.1","name":"GXT đồng giá + 3P Renegotiation","pic":"Thống Lê + OPS","priority":"P0","deadline":"2026-04-30"},
    {"id":"3.2.3","okr":"O3.2","kr":"O3.KR3.1","name":"Route Optimization GXT","pic":"OPS MP + Product","priority":"P0","deadline":"2026-05-31"},
    {"id":"3.2.4","okr":"O3.2","kr":"O3.KR3.1","name":"Failed Delivery Rate Reduction","pic":"OPS MP","priority":"P1","deadline":"2026-05-31"},
    {"id":"3.3.1","okr":"O3.3","kr":"O3 Cost","name":"Vendor Landscape Mapping","pic":"OPS Extension","priority":"P0","deadline":"2026-05-30"},
    {"id":"3.3.2","okr":"O3.3","kr":"O3 Cost","name":"RFP → Negotiation → Contract","pic":"OPS Extension + Legal","priority":"P0","deadline":"2026-06-15"},
    {"id":"3.4.1","okr":"O3.4","kr":"O3.KR3.3","name":"Distribution Model Design","pic":"BA","priority":"P0","deadline":"2026-04-30"},
    {"id":"3.4.2","okr":"O3.4","kr":"O3.KR3.3","name":"BD Pilot Signing ≥3 Corp Clients","pic":"BD Corp","priority":"P0","deadline":"2026-05-31"},
    # O4
    {"id":"4.1.1","okr":"O4.1","kr":"O4.KR4.1","name":"Market Research Dynamic Pricing","pic":"BA / Tiến Thiều Vĩnh","priority":"P1","deadline":"2026-04-30"},
    {"id":"4.1.2","okr":"O4.1","kr":"O4.KR4.1","name":"Architecture Blueprint + Logic","pic":"BA / Tiến Thiều Vĩnh","priority":"P1","deadline":"2026-05-31"},
    {"id":"4.1.3","okr":"O4.1","kr":"O4.KR4.1","name":"Baseline Data Prep + Pilot Plan","pic":"BA / Yến","priority":"P1","deadline":"2026-06-30"},
    {"id":"4.2.1","okr":"O4.2","kr":"O4.KR4.2","name":"Taxonomy Design + Driver Survey","pic":"Product + OPS Fleet","priority":"P1","deadline":"2026-04-25"},
    {"id":"4.2.2","okr":"O4.2","kr":"O4.KR4.2","name":"Data Pipeline + Classification","pic":"Chiến + Growth","priority":"P1","deadline":"2026-05-31"},
    {"id":"4.2.3","okr":"O4.2","kr":"O4.KR4.2","name":"Field Verification Process","pic":"OPS Extension","priority":"P2","deadline":"2026-06-30"},
    {"id":"4.3.1","okr":"O4.3","kr":"O4.KR4.3","name":"Data Model + Bot Architecture","pic":"BA / Tiến Thiều Vĩnh","priority":"P1","deadline":"2026-04-20"},
    {"id":"4.3.2","okr":"O4.3","kr":"O4.KR4.3","name":"Pilot Bot 1 OPS Team","pic":"BA / Yến","priority":"P1","deadline":"2026-05-31"},
    {"id":"5.1.1","okr":"O5.1","kr":"O5.KR5.3","name":"GHN MOU & 9 Provinces Plan","pic":"Thống Lê / Hs Bin","priority":"P0","deadline":"2026-04-24"},
    {"id":"5.1.2","okr":"O5.1","kr":"O5.KR5.3","name":"Supply Activation 9 Provinces","pic":"OPS EXP","priority":"P1","deadline":"2026-06-30"},
]


@app.get("/api/okr")
def get_okr(token: str = Depends(verify_token)):
    now = datetime.now()
    actions_with_status = []
    for action in ACTIONS:
        dl_str = action.get("deadline", "")
        is_overdue = False
        days_left = None
        if dl_str:
            try:
                dl = datetime.fromisoformat(dl_str)
                delta = dl - now
                days_left = delta.days
                is_overdue = delta.total_seconds() < 0
            except Exception:
                pass
        actions_with_status.append({
            **action,
            "is_overdue": is_overdue,
            "days_left": days_left,
        })

    return {
        "objectives": OKR_TREE,
        "actions": actions_with_status,
        "north_star": "O5.KR5.1 — GSV Non-Bulky 70% YoY: 69B → 117.3B",
        "quarter": "Q2/2026",
        "total_actions": len(ACTIONS),
        "overdue_actions": sum(1 for a in actions_with_status if a["is_overdue"]),
        "p0_actions": sum(1 for a in ACTIONS if a["priority"] == "P0"),
    }


# ─── Delegation Framework: Grades, Playbooks, Member Scope ────────────────────

@app.get("/api/grades")
def get_grades(token: str = Depends(verify_token)):
    """Grade Role Matrix (G4/G3/G2/G1) + Decision Authority + Delegation Principles."""
    gm = kn.grade_matrix()
    return {
        "version": gm.get("version"),
        "updated_at": gm.get("updated_at"),
        "grades": gm.get("grades", []),
        "responsibility_areas": gm.get("responsibility_areas", []),
        "decision_authority_matrix": gm.get("decision_authority_matrix", []),
        "delegation_principles": gm.get("delegation_principles", []),
    }


@app.get("/api/playbooks")
def get_playbooks(
    grade: Optional[str] = Query(None, description="Filter by owner_grade (G1-G4)"),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    token: str = Depends(verify_token),
):
    """Playbook library — task execution SOPs with step-by-step guidance."""
    pb = kn.playbooks()
    items = pb.get("playbooks", [])
    if grade:
        items = [p for p in items if p.get("owner_grade") == grade]
    if category:
        items = [p for p in items if p.get("category") == category]
    if search:
        q = search.lower()
        items = [p for p in items if q in p.get("name", "").lower()
                 or q in p.get("category", "").lower()
                 or any(q in (link or "").lower() for link in p.get("okr_links", []))]
    return {
        "version": pb.get("version"),
        "categories": pb.get("categories", []),
        "playbooks": items,
        "total": len(items),
    }


@app.get("/api/playbooks/{playbook_id}")
def get_playbook_detail(playbook_id: str, token: str = Depends(verify_token)):
    pb = kn.get_playbook(playbook_id)
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return pb


@app.get("/api/member-scopes")
def get_member_scopes(token: str = Depends(verify_token)):
    """All member scope cards (DO / DON'T / DELEGATE per member)."""
    ms = kn.member_scopes()
    return {
        "version": ms.get("version"),
        "members": ms.get("members", []),
        "delegation_health_targets": ms.get("delegation_health_targets", {}),
    }


@app.get("/api/member-scopes/{email}")
def get_member_scope_one(email: str, token: str = Depends(verify_token)):
    scope = kn.get_member_scope(email=email)
    if not scope:
        scope = kn.get_member_scope(name=email)
    if not scope:
        raise HTTPException(status_code=404, detail="Member scope not found")
    return scope


@app.get("/api/delegation/health")
def get_delegation_health(token: str = Depends(verify_token)):
    """Delegation health: targets + red flag signals + principles."""
    members = list_team_by_person()
    by_grade: dict[str, list[dict]] = {}
    for m in members:
        scope = kn.get_member_scope(name=m.get("full_name", ""))
        grade = scope.get("grade") if scope else "—"
        by_grade.setdefault(grade, []).append({
            "name": m.get("full_name"),
            "active_count": m.get("active_count", 0),
            "overdue_count": m.get("overdue_count", 0),
            "done_today": m.get("done_today", 0),
        })

    health = kn.delegation_health()
    return {
        **health,
        "load_by_grade": by_grade,
        "total_members": len(members),
    }


# ─── Sub-agents: Delegation Coach + Crisis Commander ─────────────────────────

@app.post("/api/agents/delegation-coach/{task_id}")
def api_delegation_coach(task_id: int, token: str = Depends(verify_token)):
    """Run Delegation Coach (premium tier) on a task — returns verdict + recommendation."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Build context similar to bot command
    assignee = get_user(task.get("assignee_id")) if task.get("assignee_id") else None
    assignee_scope = kn.get_member_scope(name=(assignee or {}).get("full_name", "")) if assignee else None
    from store import get_user_stats as _stats
    a_stats = _stats(task["assignee_id"]) if task.get("assignee_id") else {}

    current_assignee = None
    if assignee:
        current_assignee = {
            "name": assignee["full_name"],
            "grade": (assignee_scope or {}).get("grade", "?"),
            "title": (assignee_scope or {}).get("title", assignee.get("role", "")),
            "active_count": a_stats.get("pending", 0),
            "overdue_count": a_stats.get("overdue", 0),
        }

    assigner = get_user(task.get("assigned_by")) if task.get("assigned_by") else None
    assigner_scope = kn.get_member_scope(name=(assigner or {}).get("full_name", "")) if assigner else None

    members = list_team_by_person()
    team_load = []
    for m in members:
        if m["telegram_id"] == task.get("assignee_id"):
            continue
        m_scope = kn.get_member_scope(name=m.get("full_name", ""))
        team_load.append({
            "name": m.get("full_name"),
            "grade": (m_scope or {}).get("grade", "?"),
            "title": (m_scope or {}).get("title", ""),
            "active_count": m.get("active_count", 0),
            "overdue_count": m.get("overdue_count", 0),
        })

    verdict = coach_delegation(
        task={
            "id": task["id"],
            "summary": task.get("summary", ""),
            "okr_ref": task.get("okr_ref"),
            "category": task.get("category", "other"),
            "priority": task.get("priority", "P3"),
            "deadline_iso": task.get("deadline"),
            "estimated_minutes": task.get("estimated_minutes"),
        },
        current_assignee=current_assignee,
        assigner={
            "name": (assigner or {}).get("full_name", "?"),
            "grade": (assigner_scope or {}).get("grade", "?"),
            "role": (assigner or {}).get("role", "?"),
        } if assigner else None,
        team_load=team_load,
    )

    log_action(0, "api_delegation_coach", "task", task_id, verdict.get("verdict", ""))
    return {"task_id": task_id, "task_summary": task.get("summary"), **verdict}


class CrisisBody(BaseModel):
    type: str  # one of CRISIS_TYPES
    description: str
    region: Optional[str] = None
    current_metric: Optional[str] = None
    current_value: Optional[str] = None
    target: Optional[str] = None
    trend: Optional[str] = None
    duration_days: Optional[int] = None
    budget_cap: Optional[str] = None


@app.post("/api/agents/crisis")
def api_crisis(body: CrisisBody, token: str = Depends(verify_token)):
    """Activate Crisis Commander (premium tier)."""
    if body.type not in CRISIS_TYPES:
        body.type = "external_event"

    team_members = []
    for m in kn.member_scopes().get("members", []):
        team_members.append({
            "name": m.get("short_name") or m.get("name"),
            "grade": m.get("grade"),
            "team": m.get("team"),
        })

    trigger = {
        "type": body.type,
        "severity_hint": "active",
        "raw_description": body.description,
        "region": body.region or "all",
        "duration_days": body.duration_days,
    }
    current_metrics = {}
    if body.current_metric:
        current_metrics = {
            "metric": body.current_metric,
            "current_value": body.current_value,
            "target": body.target,
            "trend": body.trend,
        }

    report = run_crisis_commander(
        trigger=trigger,
        current_metrics=current_metrics or None,
        team_members=team_members,
        constraints={"budget_cap": body.budget_cap} if body.budget_cap else None,
    )

    log_action(0, "api_crisis_activate", "crisis", 0, f"{body.type}: {body.description[:100]}")
    return {"trigger": trigger, **report}


@app.get("/api/agents/tiers")
def api_agent_tiers(token: str = Depends(verify_token)):
    """Show current model tier mapping (debug + transparency)."""
    return tier_info()


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "ts": datetime.now().isoformat()}


# ─── Serializers ──────────────────────────────────────────────────────────────

def _fmt_task(t: dict) -> dict:
    return {
        "id": t["id"],
        "summary": t.get("summary", ""),
        "assignee_id": t.get("assignee_id"),
        "assignee_name": t.get("assignee_name") or _get_user_name(t.get("assignee_id")),
        "assigned_by": t.get("assigned_by"),
        "assigner_name": t.get("assigner_name"),
        "team": t.get("team"),
        "priority": t.get("priority", "P3"),
        "category": t.get("category", "other"),
        "status": t.get("status", "pending"),
        "deadline": t.get("deadline"),
        "block_reason": t.get("block_reason"),
        "source": t.get("source"),
        "created_at": t.get("created_at"),
        "completed_at": t.get("completed_at"),
        "estimated_minutes": t.get("estimated_minutes"),
        "actual_minutes": t.get("actual_minutes"),
        "visibility": t.get("visibility", "team"),
    }


def _fmt_member(m: dict) -> dict:
    return {
        "telegram_id": m["telegram_id"],
        "full_name": m["full_name"],
        "username": m.get("username"),
        "role": m.get("role", EMPLOYEE),
        "role_label": ROLE_LABELS.get(m.get("role", EMPLOYEE), ""),
        "team": m.get("team"),
        "active_count": m.get("active_count", 0),
        "done_today": m.get("done_today", 0),
        "overdue_count": m.get("overdue_count", 0),
        "blocked_count": m.get("blocked_count", 0),
        "load": (
            "critical" if m.get("overdue_count", 0) > 2
            else "high" if m.get("active_count", 0) > 8
            else "low" if m.get("active_count", 0) <= 1
            else "normal"
        ),
    }


def _fmt_user(u: dict) -> dict:
    return {
        "telegram_id": u["telegram_id"],
        "full_name": u["full_name"],
        "username": u.get("username"),
        "role": u.get("role", EMPLOYEE),
        "role_label": ROLE_LABELS.get(u.get("role", EMPLOYEE), ""),
        "team": u.get("team"),
        "is_approved": bool(u.get("is_approved")),
        "joined_at": u.get("joined_at"),
    }


_user_cache: dict[int, str] = {}


def _get_user_name(user_id: int | None) -> str | None:
    if not user_id:
        return None
    if user_id not in _user_cache:
        u = get_user(user_id)
        _user_cache[user_id] = u["full_name"] if u else str(user_id)
    return _user_cache[user_id]
