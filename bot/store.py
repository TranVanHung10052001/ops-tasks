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
                email         TEXT,
                role          TEXT CHECK(role IN ('manager','team_lead','employee'))
                              DEFAULT 'employee',
                team          TEXT,
                grade         TEXT,
                reports_to    INTEGER REFERENCES users(telegram_id),
                is_approved   INTEGER DEFAULT 0,
                is_preseeded  INTEGER DEFAULT 0,
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

            CREATE TABLE IF NOT EXISTS metrics (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                source     TEXT DEFAULT 'manual',
                updated_at DATETIME DEFAULT (datetime('now', '+7 hours'))
            );

            CREATE TABLE IF NOT EXISTS pending_actions (
                uid        INTEGER NOT NULL,
                kind       TEXT NOT NULL,
                payload    TEXT,
                created_at DATETIME DEFAULT (datetime('now', '+7 hours')),
                expires_at DATETIME NOT NULL,
                PRIMARY KEY (uid, kind)
            );
            CREATE TABLE IF NOT EXISTS okr_progress (
                okr_id     TEXT PRIMARY KEY,
                progress   INTEGER,
                current    TEXT,
                status     TEXT NOT NULL DEFAULT 'on_track',
                note       TEXT,
                updated_at DATETIME DEFAULT (datetime('now', '+7 hours')),
                source     TEXT DEFAULT 'dashboard'
            );
            CREATE TABLE IF NOT EXISTS okr_action_status (
                action_id  TEXT PRIMARY KEY,
                status     TEXT NOT NULL DEFAULT 'pending',
                note       TEXT,
                updated_at DATETIME DEFAULT (datetime('now', '+7 hours')),
                source     TEXT DEFAULT 'dashboard'
            );
        """)
        # ── Schema migrations (idempotent) ──────────────────────────────────
        for col, typedef in [
            ("email",        "TEXT"),
            ("grade",        "TEXT"),
            ("is_preseeded", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
            except Exception:
                pass  # column already exists


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


def claim_preseeded_user(real_id: int, username: str, typed_name: str) -> dict | None:
    """
    If `typed_name` fuzzy-matches a pre-seeded record (telegram_id < 0),
    update that record to use `real_id` and return the claimed user dict.
    Returns None if no pre-seeded match found.

    Matching priority:
      1. Exact full_name match (case-insensitive)
      2. Last-name token match (Vietnamese last token = given name)
      3. Any part of typed_name contained in full_name
    """
    typed = typed_name.lower().strip()

    # Guard: is_preseeded column might not exist in old DBs (pre-migration)
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE telegram_id < 0 AND is_preseeded = 1"
            ).fetchall()
    except Exception:
        return None  # Column missing — no preseeded records to claim

    if not rows:
        return None

    def _score(row) -> int:
        fn = row["full_name"].lower()
        parts = fn.split()
        if fn == typed:
            return 3
        # Vietnamese name: last token is the given name (most distinctive)
        if parts and parts[-1] == typed:
            return 2
        if typed in fn or any(p == typed for p in parts):
            return 1
        return 0

    best = max(rows, key=_score)
    if _score(best) == 0:
        return None  # No reasonable match

    placeholder_id = best["telegram_id"]
    with get_db() as conn:
        # Disable FK checks for this transaction so we can:
        #   1. Update the primary key (telegram_id) on the claimed row
        #   2. Fix up any child rows that pointed to the old placeholder ID
        conn.execute("PRAGMA defer_foreign_keys = ON")

        # ── Re-registration case ──
        # If real_id already has a row (user typed wrong name first, then
        # retyped correctly), we must clean it up before UPDATE'ing the
        # placeholder's PK to real_id (UNIQUE constraint would fail).
        # Move any child rows pointed at real_id → placeholder_id first,
        # then they'll auto-resolve to real_id after the swap below.
        existing = conn.execute(
            "SELECT telegram_id FROM users WHERE telegram_id = ?",
            (real_id,)
        ).fetchone()
        if existing:
            for table, col in [
                ("tasks", "assignee_id"),
                ("tasks", "assigned_by"),
                ("users", "reports_to"),
                ("audit_log", "actor_id"),
            ]:
                try:
                    conn.execute(
                        f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                        (placeholder_id, real_id),
                    )
                except Exception:
                    pass  # table might not exist on older DBs
            conn.execute("DELETE FROM users WHERE telegram_id = ?", (real_id,))

        # Fix children first — update reports_to to point to the new real_id
        conn.execute(
            "UPDATE users SET reports_to = ? WHERE reports_to = ?",
            (real_id, placeholder_id)
        )

        # Now swap the placeholder telegram_id → real telegram_id
        conn.execute("""
            UPDATE users
               SET telegram_id  = ?,
                   username     = ?,
                   is_preseeded = 0,
                   last_seen_at = datetime('now', '+7 hours')
             WHERE telegram_id = ?
        """, (real_id, username, placeholder_id))

    return get_user(real_id)


def find_preseeded_by_name(typed_name: str) -> dict | None:
    """Return the best matching pre-seeded record without claiming it (for preview)."""
    typed = typed_name.lower().strip()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE telegram_id < 0 AND is_preseeded = 1"
        ).fetchall()
    if not rows:
        return None
    best = None
    best_score = 0
    for row in rows:
        fn = row["full_name"].lower()
        parts = fn.split()
        score = 0
        if fn == typed:
            score = 3
        elif parts and parts[-1] == typed:
            score = 2
        elif typed in fn or any(p == typed for p in parts):
            score = 1
        if score > best_score:
            best_score = score
            best = row
    return dict(best) if best and best_score > 0 else None


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
    """Return ALL approved users whose name partially matches (for ambiguity detection)."""
    if not name:
        return []
    name_lower = name.lower().strip()
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM users WHERE is_approved = 1").fetchall()
    matches = []
    for row in rows:
        full = row["full_name"].lower()
        parts = full.split()
        if full == name_lower or any(p == name_lower for p in parts) or name_lower in full:
            matches.append(dict(row))
    return matches


def reassign_task(task_id: int, new_assignee_id: int) -> bool:
    """Reassign an active task to a different team member.
    Note: assignee_name is derived from users JOIN, not stored on tasks table.
    """
    new_user = get_user(new_assignee_id)
    new_team = new_user.get("team") if new_user else None
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE tasks SET assignee_id = ?, team = ?
               WHERE id = ? AND status NOT IN ('done', 'cancelled')""",
            (new_assignee_id, new_team, task_id),
        )
        return cur.rowcount > 0


def approve_user(telegram_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_approved = 1 WHERE telegram_id = ?", (telegram_id,)
        )
        return cursor.rowcount > 0


def update_user_name(telegram_id: int, full_name: str) -> bool:
    """Update full_name (used when user re-enters name before approval)."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE users SET full_name = ? WHERE telegram_id = ?",
            (full_name, telegram_id),
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
    block_reason: str = None,
) -> int:
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO tasks (
                assignee_id, assigned_by, team, raw_message, summary, source, sender,
                deadline, deadline_confidence, priority, category,
                estimated_minutes, classifier_meta, visibility, block_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assignee_id, assigned_by, team, raw_message, summary, source, sender,
            deadline, deadline_confidence, priority, category,
            estimated_minutes,
            json.dumps(classifier_meta) if classifier_meta else None,
            visibility,
            block_reason,
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


def list_auto_created_today(since_iso: str | None = None) -> list[dict]:
    """
    Tasks that bot auto-created (source='ai_auto') in the current day.
    Used for the 17h manager digest + dashboard widget.

    `since_iso` optional override. If None, uses SQLite's `datetime('now',
    '+7 hours', 'start of day')` so the format matches stored created_at
    (space-separated, NOT ISO 'T' — those compare differently as strings).
    """
    with get_db() as conn:
        if since_iso:
            q_where = "AND t.created_at >= ?"
            params = [since_iso]
        else:
            q_where = "AND t.created_at >= datetime('now', '+7 hours', 'start of day')"
            params = []

        rows = conn.execute(f"""
            SELECT t.*,
                   u.full_name  AS assignee_name,
                   u2.full_name AS assigner_name
              FROM tasks t
              LEFT JOIN users u  ON t.assignee_id = u.telegram_id
              LEFT JOIN users u2 ON t.assigned_by = u2.telegram_id
             WHERE t.source = 'ai_auto'
               {q_where}
             ORDER BY t.created_at DESC
             LIMIT 50
        """, params).fetchall()
        return [dict(r) for r in rows]


def list_team_by_person(manager_id: int = None) -> list[dict]:
    """All team users with their task counts — for dashboard."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                u.telegram_id,
                u.full_name,
                u.username,
                u.email,
                u.team,
                u.role,
                u.grade,
                u.is_preseeded,
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


# ─── Metrics (KPI store for Redash / manual sync) ────────────────────────────

def update_task_priority(task_id: int, priority: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET priority = ? WHERE id = ?", (priority, task_id)
        )
        return cursor.rowcount > 0


def upsert_metric(key: str, value: str, source: str = "redash") -> None:
    """Insert or update a KPI metric (key→value). Thread-safe via WAL."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO metrics (key, value, source, updated_at)
            VALUES (?, ?, ?, datetime('now', '+7 hours'))
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                source     = excluded.source,
                updated_at = datetime('now', '+7 hours')
        """, (key, value, source))


def get_all_metrics() -> dict:
    """Return all stored metrics as {key: value, ..., updated_at: <latest>}."""
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM metrics").fetchall()
        result: dict = {r["key"]: r["value"] for r in rows}
        if rows:
            ts_row = conn.execute(
                "SELECT MAX(updated_at) as ts FROM metrics"
            ).fetchone()
            if ts_row and ts_row["ts"]:
                result["updated_at"] = ts_row["ts"]
        return result


# ─── OKR editable state ───────────────────────────────────────────────────────

def upsert_okr_progress(
    okr_id: str,
    progress: int | None = None,
    status: str | None = None,
    current: str | None = None,
    note: str | None = None,
    source: str = "dashboard",
) -> None:
    """Upsert mutable progress state for an OKR objective."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO okr_progress (okr_id, progress, current, status, note, updated_at, source)
            VALUES (?, ?, ?, COALESCE(?, 'on_track'), ?, datetime('now', '+7 hours'), ?)
            ON CONFLICT(okr_id) DO UPDATE SET
                progress   = COALESCE(excluded.progress,  progress),
                current    = COALESCE(excluded.current,   current),
                status     = COALESCE(excluded.status,    status),
                note       = COALESCE(excluded.note,      note),
                updated_at = datetime('now', '+7 hours'),
                source     = excluded.source
        """, (okr_id, progress, current, status, note, source))


def get_okr_overrides() -> dict:
    """Return {okr_id: {progress, current, status, note}} from DB."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM okr_progress").fetchall()
        return {r["okr_id"]: dict(r) for r in rows}


def upsert_action_status(
    action_id: str,
    status: str,
    note: str | None = None,
    source: str = "dashboard",
) -> None:
    """Upsert mutable status for an OKR action item."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO okr_action_status (action_id, status, note, updated_at, source)
            VALUES (?, ?, ?, datetime('now', '+7 hours'), ?)
            ON CONFLICT(action_id) DO UPDATE SET
                status     = excluded.status,
                note       = COALESCE(excluded.note, note),
                updated_at = datetime('now', '+7 hours'),
                source     = excluded.source
        """, (action_id, status, note, source))


def get_action_overrides() -> dict:
    """Return {action_id: {status, note}} from DB."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM okr_action_status").fetchall()
        return {r["action_id"]: dict(r) for r in rows}


def bulk_sync_okr_from_sheet(objectives: list, actions: list) -> int:
    """Bulk upsert OKR state from Google Sheets. Returns count of upserted rows."""
    count = 0
    for obj in objectives:
        if "id" not in obj:
            continue
        upsert_okr_progress(
            okr_id=str(obj["id"]).upper(),
            progress=obj.get("progress"),
            status=obj.get("status"),
            current=obj.get("current"),
            note=obj.get("note"),
            source="sheets",
        )
        count += 1
    for action in actions:
        if "id" not in action or "status" not in action:
            continue
        upsert_action_status(
            action_id=str(action["id"]),
            status=str(action["status"]),
            note=action.get("note"),
            source="sheets",
        )
        count += 1
    return count


def get_adhoc_ratio_this_week(user_id: int) -> dict:
    """Return ad-hoc task ratio for tasks assigned BY user_id since Monday 00:00 this week.

    Ad-hoc categories: ops, admin, meeting, vendor, other.
    Only non-cancelled tasks are counted.
    Returns {"total": int, "adhoc": int, "ratio_pct": float}.
    """
    _ADHOC_CATEGORIES = {"ops", "admin", "meeting", "vendor", "other"}

    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    with get_db() as conn:
        rows = conn.execute("""
            SELECT category FROM tasks
            WHERE assigned_by = ?
              AND created_at >= ?
              AND status != 'cancel'
        """, (user_id, monday.isoformat())).fetchall()

    total = len(rows)
    if total == 0:
        return {"total": 0, "adhoc": 0, "ratio_pct": 0.0}

    adhoc = sum(1 for r in rows if (r["category"] or "").lower() in _ADHOC_CATEGORIES)
    ratio_pct = round(adhoc / total * 100, 1)
    return {"total": total, "adhoc": adhoc, "ratio_pct": ratio_pct}


# ─── Pending actions (persisted across bot restarts) ─────────────────────────
# Replaces in-memory dicts (_pending_name, _pending_confirm, etc) so callback
# state survives Railway redeploys.

import json as _json
from datetime import timedelta as _timedelta


def _dt_encode(o):
    if isinstance(o, datetime):
        return {"__dt__": o.isoformat()}
    raise TypeError(repr(o) + " is not JSON serializable")


def _dt_decode(d):
    if "__dt__" in d:
        try:
            return datetime.fromisoformat(d["__dt__"])
        except ValueError:
            return d
    return d


def set_pending(uid: int, kind: str, payload: dict, ttl_seconds: int = 3600):
    """Store pending state. expires_at is computed by SQLite itself
    so timezone comparison with get_pending always matches."""
    body = _json.dumps(payload or {}, default=_dt_encode)
    with get_db() as conn:
        conn.execute("""
            INSERT INTO pending_actions (uid, kind, payload, expires_at)
            VALUES (?, ?, ?, datetime('now', '+7 hours', ?))
            ON CONFLICT(uid, kind) DO UPDATE SET
                payload    = excluded.payload,
                expires_at = excluded.expires_at,
                created_at = datetime('now', '+7 hours')
        """, (uid, kind, body, f'+{int(ttl_seconds)} seconds'))


def get_pending(uid: int, kind: str):
    """Return payload dict if present and not expired, else None."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT payload FROM pending_actions
            WHERE uid = ? AND kind = ?
              AND datetime(expires_at) > datetime('now', '+7 hours')
        """, (uid, kind)).fetchone()
    if not row:
        return None
    try:
        return _json.loads(row["payload"], object_hook=_dt_decode)
    except Exception:
        return None


def pop_pending(uid: int, kind: str):
    val = get_pending(uid, kind)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM pending_actions WHERE uid = ? AND kind = ?",
            (uid, kind),
        )
    return val


def cleanup_expired_pending():
    with get_db() as conn:
        conn.execute("""
            DELETE FROM pending_actions
            WHERE datetime(expires_at) <= datetime('now', '+7 hours')
        """)


class PersistedDict:
    """
    Dict-like wrapper that persists each entry to pending_actions table.
    Survives bot restarts (Railway redeploys).

    Usage:
        _pending_confirm = PersistedDict('confirm', ttl_seconds=1800)
        _pending_confirm[uid] = {'task_text': text, 'routed': result}
        if uid in _pending_confirm:
            state = _pending_confirm[uid]
            _pending_confirm.pop(uid)
    """

    def __init__(self, kind: str, ttl_seconds: int = 3600):
        self.kind = kind
        self.ttl = ttl_seconds

    def __setitem__(self, uid, value):
        if isinstance(value, bool):
            value = {"_flag": value}
        elif isinstance(value, tuple):
            value = {"_tuple": list(value)}
        elif not isinstance(value, dict):
            value = {"_value": value}
        set_pending(int(uid), self.kind, value, self.ttl)

    def __getitem__(self, uid):
        val = get_pending(int(uid), self.kind)
        if val is None:
            raise KeyError(uid)
        if isinstance(val, dict):
            if "_flag" in val and len(val) == 1:
                return val["_flag"]
            if "_tuple" in val and len(val) == 1:
                return tuple(val["_tuple"])
            if "_value" in val and len(val) == 1:
                return val["_value"]
        return val

    def __contains__(self, uid):
        return get_pending(int(uid), self.kind) is not None

    def get(self, uid, default=None):
        try:
            return self[uid]
        except KeyError:
            return default

    def pop(self, uid, *args):
        """Pop entry. Returns default (or None if no default) when missing —
        does NOT raise KeyError, unlike standard dict.pop(). Safer for our
        code patterns where pop is often called inside `if uid in d:` guards
        that race against TTL expiry."""
        try:
            val = self[uid]
        except KeyError:
            return args[0] if args else None
        try:
            pop_pending(int(uid), self.kind)
        except Exception:
            pass
        return val
