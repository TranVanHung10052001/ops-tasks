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
    update_task_priority, upsert_metric, get_all_metrics,
    list_auto_created_today, reassign_task,
)
from roles import MANAGER, TEAM_LEAD, EMPLOYEE, ROLE_LABELS

import logging
import httpx
import templates as tpl
try:
    from classifier import route_task
except Exception:  # classifier may fail to import without GEMINI_API_KEY
    route_task = None

logger = logging.getLogger("api")


def _send_telegram(chat_id: int, text: str, buttons: list | None = None) -> bool:
    """Fire-and-forget Telegram DM via HTTP API.
    `buttons` = [[(label, callback_data), ...], ...] for inline keyboard.
    Returns True on success, False otherwise. Never raises."""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token or not chat_id or chat_id <= 0:
        return False
    payload = {
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML",
    }
    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": t, "callback_data": cb} for (t, cb) in row]
                for row in buttons
            ]
        }
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload, timeout=10,
        )
        if r.status_code != 200:
            logger.warning(f"Telegram send {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as e:
        logger.warning(f"Telegram send error: {e}")
        return False

DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "ops-tasks-secret-change-me")

# Fix #8: CORS restricted to known origins (not wildcard)
_ALLOWED_ORIGINS_RAW = os.getenv(
    "ALLOWED_ORIGINS",
    "https://ops-tasks-eight.vercel.app,http://localhost:3000,http://localhost:3002",
)
ALLOWED_ORIGINS = [o.strip() for o in _ALLOWED_ORIGINS_RAW.split(",") if o.strip()]

app = FastAPI(title="Ops Tasks API", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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

    return {
        **stats,
        "overloaded_count": len(overloaded),
        "member_count": len(members),
        "overdue_tasks": [_fmt_task(t) for t in overdue_tasks[:5]],
    }


# ─── Activity log ─────────────────────────────────────────────────────────────

@app.get("/api/activity")
def get_activity(
    limit: int = Query(10, le=50),
    token: str = Depends(verify_token),
):
    """Recent activity log — latest actions today from audit_log (bot Telegram actions)."""
    from store import get_db
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.id, a.actor_id, a.action, a.entity_type, a.entity_id,
                   a.detail, a.ts,
                   u.full_name as actor_name
            FROM audit_log a
            LEFT JOIN users u ON a.actor_id = u.telegram_id
            WHERE a.ts >= ?
            ORDER BY a.ts DESC
            LIMIT ?
        """, (today_start, limit)).fetchall()

    action_labels = {
        "assign":             "giao task",
        "assign_ai":          "giao task (AI)",
        "done":               "đánh dấu hoàn thành",
        "block":              "báo blocked",
        "unblock":            "gỡ blocked",
        "dashboard_update":   "cập nhật task",
        "create_task":        "tạo task mới",
        "approve_user":       "duyệt thành viên",
        "bulk_metric_update": "cập nhật KPI metrics",
        "decline":            "từ chối task",
        "set_role":           "cập nhật vai trò",
    }

    events = []
    for r in rows:
        r = dict(r)
        ts = r["ts"] or ""
        try:
            dt = datetime.fromisoformat(ts)
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = ts[:5] if len(ts) >= 5 else ts

        actor_id = r["actor_id"]
        actor = r.get("actor_name") or ("Dashboard" if actor_id == 0 else f"User {actor_id}")
        action_label = action_labels.get(r["action"], r["action"])
        target = None
        if r["entity_type"] == "task" and r["entity_id"]:
            target = f"T-{str(r['entity_id']).zfill(5)}"

        events.append({
            "id":         r["id"],
            "ts":         time_str,
            "actor":      actor,
            "action":     action_label,
            "target":     target,
            "raw_action": r["action"],
        })

    return events



# ─── Team ─────────────────────────────────────────────────────────────────────

@app.get("/api/team")
def get_team(token: str = Depends(verify_token)):
    members = list_team_by_person()
    # Fix #4: exclude pre-seeded placeholder records (telegram_id < 0)
    # until the member has claimed their account via /start
    members = [m for m in members if m["telegram_id"] > 0]
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
    # Fix #5: actually apply the days filter
    from datetime import timedelta
    since = (datetime.now() - timedelta(days=days)).isoformat()
    tasks = list_team_tasks(statuses=["done"], limit=200, since=since)
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
        update_task_priority(task_id, body.priority)

    if body.deadline:
        update_task_deadline(task_id, body.deadline, "dashboard")

    if body.assignee_id:
        # Fix #2: use reassign_task() so team field is also updated
        reassign_task(task_id, body.assignee_id)

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

    # ── AI enrichment: breakdown, OKR ref, deadline parse, estimated time ──
    # Falls back gracefully if Gemini is unavailable.
    routed: dict = {}
    if route_task is not None:
        try:
            routed = route_task(body.summary) or {}
        except Exception as e:
            logger.warning(f"route_task failed: {e}")
            routed = {}

    # User-provided values win over AI suggestions
    final_summary  = routed.get("summary") or body.summary
    final_priority = body.priority or routed.get("priority", "P2")
    final_category = body.category if body.category != "other" else routed.get("category", "other")
    final_deadline = body.deadline or routed.get("deadline_iso")
    est_minutes    = routed.get("estimated_minutes", 30)

    task_id = add_task(
        raw_message=body.summary,
        summary=final_summary,
        assignee_id=body.assignee_id,
        assigned_by=0,  # 0 = dashboard
        team=assignee.get("team"),
        source="dashboard",
        sender="Dashboard",
        deadline=final_deadline,
        priority=final_priority,
        category=final_category,
        estimated_minutes=est_minutes,
        classifier_meta=routed,
    )
    log_action(0, "create_task", "task", task_id, body.summary)

    # ── Notify assignee on Telegram (DM with msg_task_new + Accept/Decline) ──
    if assignee.get("telegram_id") and assignee["telegram_id"] > 0:
        task_dict = {
            "id":              task_id,
            "summary":         final_summary,
            "priority":        final_priority,
            "deadline":        final_deadline,
            "classifier_meta": routed,
        }
        try:
            text = tpl.msg_task_new(task_dict, assigned_by_name="Dashboard")
            buttons = [
                [("✓ Nhận việc", f"accept:{task_id}"),
                 ("✗ Từ chối",   f"decline:{task_id}")],
                [("🎓 Hướng dẫn chi tiết", f"coach:{task_id}")],
            ]
            _send_telegram(assignee["telegram_id"], text, buttons)
        except Exception as e:
            logger.warning(f"notify assignee failed: {e}")

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
    from store import get_okr_overrides, get_action_overrides
    now = datetime.now()
    obj_overrides = get_okr_overrides()
    action_overrides = get_action_overrides()

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
        override = action_overrides.get(action["id"], {})
        actions_with_status.append({
            **action,
            "is_overdue": is_overdue,
            "days_left": days_left,
            "status": override.get("status", "pending"),
        })

    objectives_with_progress = []
    for obj in OKR_TREE:
        override = obj_overrides.get(obj["id"], {})
        objectives_with_progress.append({
            **obj,
            "progress_override": override.get("progress"),   # None = not set
            "current_override": override.get("current"),
            "okr_status": override.get("status", "on_track"),
        })

    return {
        "objectives": objectives_with_progress,
        "actions": actions_with_status,
        "north_star": "O5.KR5.1 — GSV Non-Bulky 70% YoY: 69B → 117.3B",
        "quarter": "Q2/2026",
        "total_actions": len(ACTIONS),
        "overdue_actions": sum(1 for a in actions_with_status if a["is_overdue"]),
        "p0_actions": sum(1 for a in ACTIONS if a["priority"] == "P0"),
    }


# ─── OKR mutations ────────────────────────────────────────────────────────────

class OkrProgressUpdate(BaseModel):
    progress: int | None = None          # 0–100
    status: str | None = None            # on_track|at_risk|behind|done
    current: str | None = None           # human-readable current value e.g. "FR HAN 78%"
    note: str | None = None


@app.patch("/api/okr/objectives/{okr_id}")
def patch_okr_objective(
    okr_id: str,
    body: OkrProgressUpdate,
    token: str = Depends(verify_token),
):
    """Update progress/status for one OKR objective. Called from dashboard or sheet sync."""
    from store import upsert_okr_progress
    upsert_okr_progress(
        okr_id=okr_id.upper(),
        progress=body.progress,
        status=body.status,
        current=body.current,
        note=body.note,
        source="dashboard",
    )
    log_action(0, "okr_progress_update", detail=f"{okr_id} → {body.progress}% {body.status}")
    return {"ok": True, "okr_id": okr_id}


class ActionStatusUpdate(BaseModel):
    status: str           # pending|in_progress|done|cancelled
    note: str | None = None


@app.patch("/api/okr/actions/{action_id}")
def patch_okr_action(
    action_id: str,
    body: ActionStatusUpdate,
    token: str = Depends(verify_token),
):
    """Update status for one OKR action item."""
    from store import upsert_action_status
    upsert_action_status(
        action_id=action_id,
        status=body.status,
        note=body.note,
        source="dashboard",
    )
    log_action(0, "okr_action_update", detail=f"{action_id} → {body.status}")
    return {"ok": True, "action_id": action_id}


class OkrSheetSync(BaseModel):
    objectives: list = []
    actions: list = []


@app.post("/api/okr/sync")
def okr_sync_from_sheet(body: OkrSheetSync, token: str = Depends(verify_token)):
    """Receive bulk OKR update pushed from Google Sheets Apps Script."""
    from store import bulk_sync_okr_from_sheet
    count = bulk_sync_okr_from_sheet(body.objectives, body.actions)
    log_action(0, "okr_sheet_sync", detail=f"{len(body.objectives)} obj + {len(body.actions)} actions from sheets")
    return {"ok": True, "updated": count}


# ─── Metrics (KPI sync from Redash / Google Sheets / manual) ─────────────────

@app.get("/api/metrics")
def get_metrics_endpoint(token: str = Depends(verify_token)):
    """Return all stored KPI metrics as a flat dict {key: value}."""
    return get_all_metrics()


class MetricUpdate(BaseModel):
    key: str
    value: str
    source: str = "manual"


@app.post("/api/metrics")
def update_metric_endpoint(body: MetricUpdate, token: str = Depends(verify_token)):
    """Upsert a single KPI metric."""
    upsert_metric(body.key, body.value, body.source)
    return {"ok": True}


class BulkMetricsBody(BaseModel):
    metrics: dict  # {key: value} — all values coerced to str
    source: str = "sheets"


@app.post("/api/metrics/bulk")
def update_metrics_bulk(body: BulkMetricsBody, token: str = Depends(verify_token)):
    """
    Bulk upsert KPI metrics. Used by Google Sheets Apps Script or manual sync.
    Example body: {"metrics": {"gsv_today_b": "8.7", "fill_rate_core_pct": "78.0"}, "source": "sheets"}
    """
    for key, value in body.metrics.items():
        upsert_metric(str(key), str(value), body.source)
    log_action(0, "bulk_metric_update", detail=f"{len(body.metrics)} keys from {body.source}")
    return {"ok": True, "updated": len(body.metrics)}


# ─── Smart Agent / Q&A ────────────────────────────────────────────────────────

class AskBody(BaseModel):
    question: str


@app.post("/api/ask")
def api_ask(body: AskBody, token: str = Depends(verify_token)):
    """Single-prompt AI query với live team context."""
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    try:
        from ask import ask as ai_ask
        result = ai_ask(body.question)
        log_action(0, "api_ask", detail=body.question[:100])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ask failed: {e}")


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "ts": datetime.now().isoformat()}


# ─── Auto-digest (manager review of bot-created tasks today) ─────────────────

@app.get("/api/auto-digest")
def get_auto_digest(token: str = Depends(verify_token)):
    """Tasks bot auto-created today — for manager review widget on dashboard."""
    tasks = list_auto_created_today()
    return {
        "count": len(tasks),
        "tasks": [_fmt_task(t) for t in tasks],
        "ts": datetime.now().isoformat(),
    }


class ReassignBody(BaseModel):
    new_assignee_id: int
    actor_id: Optional[int] = None  # who triggered the reassign (for audit log)


@app.post("/api/tasks/{task_id}/reassign")
def post_reassign(
    task_id: int,
    body: ReassignBody,
    token: str = Depends(verify_token),
):
    """Reassign an existing task from the dashboard (mirror of bot's digest_reassign)."""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    new_user = get_user(body.new_assignee_id)
    if not new_user:
        raise HTTPException(status_code=400, detail="New assignee not found")
    if reassign_task(task_id, body.new_assignee_id):
        log_action(body.actor_id or 0, "reassign_dashboard", "task", task_id,
                   f"→ {new_user['full_name']}")
        return {"ok": True, "task": _fmt_task(get_task(task_id))}
    raise HTTPException(status_code=500, detail="Reassign failed")


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
    # Fix #3: expose grade (G1/G2/G3/G4) and email from new DB columns
    return {
        "telegram_id": m["telegram_id"],
        "full_name": m["full_name"],
        "username": m.get("username"),
        "email": m.get("email") or "",
        "role": m.get("role", EMPLOYEE),
        "role_label": ROLE_LABELS.get(m.get("role", EMPLOYEE), ""),
        "grade": m.get("grade") or "",
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


def _get_user_name(user_id: int | None) -> str | None:
    """Look up user name without caching — names can change after account claim."""
    # Fix #1: removed permanent module-level cache; after claim_preseeded_user()
    # the telegram_id changes and cached names would be stale.
    if not user_id:
        return None
    u = get_user(user_id)
    return u["full_name"] if u else None
