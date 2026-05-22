"""
Task Store — Multi-user SQLite for ops-tasks team bot.
Handles users, task CRUD, team queries, and statistics.
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "./data/ops_tasks.db")


def _ensure_db_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_db():
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    _ensure_db_dir()
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id   INTEGER PRIMARY KEY,
                username      TEXT,
                full_name     TEXT NOT NULL,
                role          TEXT CHECK(role IN ('manager','team_lead','employee'))
                              DEFAULT 'employee',
                team          TEXT,
                reports_to    INTEGER REFERENCES users(telegram_id),
                is_approved   INTEGER DEFAULT 0,
                joined_at     DATETIME DEFAULT (datetime('now', '+7 hours')),
                last_seen_at  DATETIME
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                assignee_id       INTEGER REFERENCES users(telegram_id),
                assigned_by       INTEGER REFERENCES users(telegram_id),
                team              TEXT,
                raw_message       TEXT NOT NULL,
                summary           TEXT NOT NULL,
                source            TEXT,
                sender            TEXT,
                deadline          DATETIME,
                deadline_confidence TEXT,
                priority          TEXT DEFAULT 'P3',
                category          TEXT DEFAULT 'other',
                status            TEXT DEFAULT 'pending',
                visibility        TEXT DEFAULT 'team',
                created_at        DATETIME DEFAULT (datetime('now', '+7 hours')),
                completed_at      DATETIME,
                snooze_until      DATETIME,
                reminder_count    INTEGER DEFAULT 0,
                defer_count       INTEGER DEFAULT 0,
                block_reason      TEXT,
                estimated_minutes INTEGER DEFAULT 30,
                actual_minutes    INTEGER,
                classifier_meta   TEXT
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id    INTEGER,
                action      TEXT NOT NULL,
                entity_type TEXT,
                entity_id   INTEGER,
                detail      TEXT,
                ts          DATETIME DEFAULT (datetime('now', '+7 hours'))
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_assignee
                ON tasks(assignee_id, status);
            CREATE INDEX IF NOT EXISTS idx_tasks_deadline
                ON tasks(status, deadline);
            CREATE INDEX IF NOT EXISTS idx_tasks_team
                ON tasks(team, status);
        """)


# ─── User operations ──────────────────────────────────────────────────────────

def register_user(telegram_id: int, username: str, full_name: str) -> bool:
    """Register a new user. Returns False if already exists."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        if existing:
            return False
        conn.execute("""
            INSERT INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
        """, (telegram_id, username, full_name))
        return True


def get_user(telegram_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    clean = username.lstrip("@").lower()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(username) = ?", (clean,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    """Find user by Ahamove email (stored in username or full_name won't work — match on email field if exists, else skip)."""
    # Email not stored in DB currently — match by known email→name mapping from team_context
    # This is a best-effort lookup; falls back to get_user_by_name
    return None


def get_user_by_name(name: str) -> dict | None:
    """Find user by partial full_name match (case-insensitive)."""
    if not name:
        return None
    name_lower = name.lower().strip()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_approved = 1"
        ).fetchall()
        # Try exact match first
        for row in rows:
            if row["full_name"].lower() == name_lower:
                return dict(row)
        # Try partial match (last name, nickname)
        for row in rows:
            full = row["full_name"].lower()
            parts = full.split()
            # Match any name part or if search is contained
            if any(p == name_lower for p in parts) or name_lower in full:
                return dict(row)
    return None


def find_users_by_name(name: str) -> list[dict]:
    """Return ALL approved users whose name partially matches — caller resolves ambiguity."""
    if not name:
        return []
    name_lower = name.lower().strip()
    matches = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_approved = 1"
        ).fetchall()
        # Exact matches first (highest confidence)
        exact = [dict(r) for r in rows if r["full_name"].lower() == name_lower]
        if exact:
            return exact
        # Partial matches
        for row in rows:
            full = row["full_name"].lower()
            parts = full.split()
            if any(p == name_lower for p in parts) or name_lower in full:
                matches.append(dict(row))
    return matches


def approve_user(telegram_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_approved = 1 WHERE telegram_id = ?", (telegram_id,)
        )
        return cursor.rowcount > 0


def reject_user(telegram_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM users WHERE telegram_id = ? AND is_approved = 0", (telegram_id,)
        )
        return cursor.rowcount > 0


def set_user_role(telegram_id: int, role: str, team: str = None, reports_to: int = None) -> bool:
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE users SET role = ?, team = ?, reports_to = ?
            WHERE telegram_id = ?
        """, (role, team, reports_to, telegram_id))
        return cursor.rowcount > 0


def list_users(approved_only: bool = True, team: str = None) -> list[dict]:
    with get_db() as conn:
        q = "SELECT * FROM users WHERE 1=1"
        params = []
        if approved_only:
            q += " AND is_approved = 1"
        if team:
            q += " AND team = ?"
            params.append(team)
        q += " ORDER BY role DESC, full_name ASC"
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def list_pending_approval() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_approved = 0 ORDER BY joined_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def touch_user(telegram_id: int):
    with get_db() as conn:
        conn.execute("""
            UPDATE users SET last_seen_at = datetime('now', '+7 hours')
            WHERE telegram_id = ?
        """, (telegram_id,))


# ─── Task operations ──────────────────────────────────────────────────────────

def add_task(
    raw_message: str,
    summary: str,
    assignee_id: int,
    assigned_by: int,
    team: str = None,
    source: str = None,
    sender: str = None,
    deadline: str = None,
    deadline_confidence: str = None,
    priority: str = "P3",
    category: str = "other",
    estimated_minutes: int = 30,
    classifier_meta: dict = None,
    visibility: str = "team",
) -> int:
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO tasks (
                assignee_id, assigned_by, team, raw_message, summary, source, sender,
                deadline, deadline_confidence, priority, category,
                estimated_minutes, classifier_meta, visibility
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assignee_id, assigned_by, team, raw_message, summary, source, sender,
            deadline, deadline_confidence, priority, category,
            estimated_minutes,
            json.dumps(classifier_meta) if classifier_meta else None,
            visibility,
        ))
        return cursor.lastrowid


def get_task(task_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None


def list_user_tasks(user_id: int, status: str = "pending", limit: int = 50) -> list[dict]:
    """Tasks assigned to a specific user."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE assignee_id = ? AND status = ?
            ORDER BY
                CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
                deadline ASC, priority ASC
            LIMIT ?
        """, (user_id, status, limit)).fetchall()
        return [dict(r) for r in rows]


def list_user_today_tasks(user_id: int) -> list[dict]:
    now = datetime.now()
    today_end = now.replace(hour=23, minute=59, second=59)
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE assignee_id = ?
              AND status IN ('pending', 'in_progress')
              AND (deadline <= ? OR deadline IS NULL)
            ORDER BY
                CASE WHEN deadline IS NOT NULL AND deadline < ? THEN 0 ELSE 1 END,
                deadline ASC, priority ASC
        """, (user_id, today_end.isoformat(), now.isoformat())).fetchall()
        return [dict(r) for r in rows]


def list_team_tasks(
    team: str = None,
    statuses: list[str] = None,
    limit: int = 200,
    since: str = None,
) -> list[dict]:
    """All tasks visible to manager/TL, grouped by team if specified.
    `since`: ISO datetime string — filter by updated_at or created_at >= since.
    """
    if statuses is None:
        statuses = ["pending", "in_progress", "blocked"]
    placeholders = ",".join("?" * len(statuses))
    with get_db() as conn:
        q = f"""
            SELECT t.*, u.full_name as assignee_name, u.team as assignee_team,
                   u2.full_name as assigner_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.telegram_id
            LEFT JOIN users u2 ON t.assigned_by = u2.telegram_id
            WHERE t.status IN ({placeholders})
              AND t.visibility = 'team'
        """
        params = list(statuses)
        if team:
            q += " AND u.team = ?"
            params.append(team)
        if since:
            q += " AND COALESCE(t.updated_at, t.created_at) >= ?"
            params.append(since)
        q += " ORDER BY u.full_name ASC, t.priority ASC, t.deadline ASC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(q, params).fetchall()]


def list_team_by_person(manager_id: int = None) -> list[dict]:
    """All team users with their task counts — for dashboard."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                u.telegram_id,
                u.full_name,
                u.username,
                u.team,
                u.role,
                COUNT(CASE WHEN t.status IN ('pending','in_progress') THEN 1 END) as active_count,
                COUNT(CASE WHEN t.status = 'done'
                      AND t.completed_at >= datetime('now', '+7 hours', '-1 day') THEN 1 END) as done_today,
                COUNT(CASE WHEN t.status IN ('pending','in_progress')
                      AND t.deadline IS NOT NULL
                      AND t.deadline < datetime('now', '+7 hours') THEN 1 END) as overdue_count,
                COUNT(CASE WHEN t.status = 'blocked' THEN 1 END) as blocked_count
            FROM users u
            LEFT JOIN tasks t ON t.assignee_id = u.telegram_id AND t.visibility = 'team'
            WHERE u.is_approved = 1
            GROUP BY u.telegram_id
            ORDER BY u.team ASC, u.role DESC, u.full_name ASC
        """).fetchall()
        return [dict(r) for r in rows]


def get_team_stats() -> dict:
    """Aggregate stats for manager dashboard."""
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    with get_db() as conn:
        active = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE status IN ('pending', 'in_progress') AND visibility = 'team'
        """).fetchone()[0]

        done_today = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE status = 'done'
              AND completed_at >= datetime('now', '+7 hours', '-1 day')
        """).fetchone()[0]

        overdue = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE status IN ('pending', 'in_progress')
              AND deadline IS NOT NULL
              AND deadline < datetime('now', '+7 hours')
              AND visibility = 'team'
        """).fetchone()[0]

        blocked = conn.execute("""
            SELECT COUNT(*) FROM tasks WHERE status = 'blocked' AND visibility = 'team'
        """).fetchone()[0]

        done_week = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE status = 'done' AND completed_at >= ?
        """, (monday.isoformat(),)).fetchone()[0]

        return {
            "active": active,
            "done_today": done_today,
            "overdue": overdue,
            "blocked": blocked,
            "done_week": done_week,
        }


def get_user_stats(user_id: int) -> dict:
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    with get_db() as conn:
        done_week = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE assignee_id = ? AND status = 'done' AND completed_at >= ?
        """, (user_id, monday.isoformat())).fetchone()[0]

        pending = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE assignee_id = ? AND status IN ('pending', 'in_progress')
        """, (user_id,)).fetchone()[0]

        overdue = conn.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE assignee_id = ? AND status IN ('pending', 'in_progress')
              AND deadline IS NOT NULL AND deadline < datetime('now', '+7 hours')
        """, (user_id,)).fetchone()[0]

        return {"done_week": done_week, "pending": pending, "overdue": overdue}


# ─── Task status transitions ───────────────────────────────────────────────────

def mark_done(task_id: int) -> bool:
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE tasks SET status = 'done', completed_at = ?
            WHERE id = ? AND status != 'done'
        """, (now, task_id))
        return cursor.rowcount > 0


def cancel_task(task_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE tasks SET status = 'cancelled'
            WHERE id = ? AND status NOT IN ('done', 'cancelled')
        """, (task_id,))
        return cursor.rowcount > 0


def snooze_task(task_id: int, until: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE tasks SET status = 'snoozed', snooze_until = ?
            WHERE id = ? AND status NOT IN ('done', 'cancelled')
        """, (until, task_id))
        return cursor.rowcount > 0


def unsnooze_due_tasks() -> list[dict]:
    now = datetime.now().isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks WHERE status = 'snoozed' AND snooze_until <= ?
        """, (now,)).fetchall()
        if rows:
            conn.execute("""
                UPDATE tasks SET status = 'pending', snooze_until = NULL
                WHERE status = 'snoozed' AND snooze_until <= ?
            """, (now,))
        return [dict(r) for r in rows]


def block_task(task_id: int, reason: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE tasks SET status = 'blocked', block_reason = ?
            WHERE id = ? AND status NOT IN ('done', 'cancelled')
        """, (reason, task_id))
        return cursor.rowcount > 0


def unblock_task(task_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE tasks SET status = 'pending', block_reason = NULL
            WHERE id = ? AND status = 'blocked'
        """, (task_id,))
        return cursor.rowcount > 0


def reassign_task(task_id: int, new_assignee_id: int) -> bool:
    """Change the assignee of a task. Returns True if the row was updated."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET assignee_id = ? WHERE id = ?",
            (new_assignee_id, task_id),
        )
        return cursor.rowcount > 0


def update_task_deadline(task_id: int, deadline: str, confidence: str = "asked"):
    with get_db() as conn:
        conn.execute("""
            UPDATE tasks SET deadline = ?, deadline_confidence = ?
            WHERE id = ?
        """, (deadline, confidence, task_id))


def set_actual_minutes(task_id: int, minutes: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET actual_minutes = ? WHERE id = ?", (minutes, task_id)
        )


def increment_reminder(task_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET reminder_count = reminder_count + 1 WHERE id = ?",
            (task_id,)
        )


def increment_defer(task_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET defer_count = defer_count + 1 WHERE id = ?", (task_id,)
        )


def get_upcoming_deadlines_for_user(user_id: int, hours_ahead: int = 72) -> list[dict]:
    future = (datetime.now() + timedelta(hours=hours_ahead)).isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE assignee_id = ?
              AND status IN ('pending', 'in_progress')
              AND deadline IS NOT NULL AND deadline <= ?
            ORDER BY deadline ASC
        """, (user_id, future)).fetchall()
        return [dict(r) for r in rows]


def get_overdue_tasks_for_user(user_id: int) -> list[dict]:
    now = datetime.now().isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE assignee_id = ?
              AND status IN ('pending', 'in_progress', 'blocked')
              AND deadline IS NOT NULL AND deadline < ?
            ORDER BY deadline ASC
        """, (user_id, now)).fetchall()
        return [dict(r) for r in rows]


def get_top_tasks_for_user(user_id: int, limit: int = 3) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT *,
                CASE priority WHEN 'P0' THEN 100 WHEN 'P1' THEN 50 WHEN 'P2' THEN 20 ELSE 5 END
                + CASE
                    WHEN deadline IS NOT NULL AND deadline <= datetime('now', '+7 hours', '8 hours') THEN 80
                    WHEN deadline IS NOT NULL AND deadline <= datetime('now', '+7 hours', '24 hours') THEN 50
                    WHEN deadline IS NOT NULL AND deadline <= datetime('now', '+7 hours', '72 hours') THEN 20
                    ELSE 0
                  END
                + MIN(CAST((julianday('now') - julianday(created_at)) * 2 AS INTEGER), 20)
                AS score
            FROM tasks
            WHERE assignee_id = ? AND status IN ('pending', 'in_progress')
            ORDER BY score DESC, deadline ASC
            LIMIT ?
        """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]


def get_all_overdue_tasks() -> list[dict]:
    """All team overdue tasks with user info — for manager digest."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT t.*, u.full_name as assignee_name
            FROM tasks t
            JOIN users u ON t.assignee_id = u.telegram_id
            WHERE t.status IN ('pending', 'in_progress', 'blocked')
              AND t.deadline IS NOT NULL AND t.deadline < ?
              AND t.visibility = 'team'
            ORDER BY t.deadline ASC
        """, (now,)).fetchall()
        return [dict(r) for r in rows]


def get_stalled_tasks_for_user(user_id: int, stale_days: int = 2) -> list[dict]:
    threshold = (datetime.now() - timedelta(days=stale_days)).isoformat()
    now_iso = datetime.now().isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM tasks
            WHERE assignee_id = ? AND status = 'pending'
              AND created_at <= ?
              AND (deadline IS NULL OR deadline > datetime(?, '+3 days'))
              AND block_reason IS NULL
            ORDER BY CASE priority
                WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3
            END, created_at ASC
            LIMIT 3
        """, (user_id, threshold, now_iso)).fetchall()
        return [dict(r) for r in rows]


def log_action(actor_id: int, action: str, entity_type: str = None,
               entity_id: int = None, detail: str = None):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO audit_log (actor_id, action, entity_type, entity_id, detail)
            VALUES (?, ?, ?, ?, ?)
        """, (actor_id, action, entity_type, entity_id, detail))
