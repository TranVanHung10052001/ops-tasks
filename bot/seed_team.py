"""
seed_team.py — Pre-populate bot DB with all 11 Truck Ops team members.

Run once before launch (or after Railway Volume is mounted):
    cd bot && python seed_team.py

Design:
- Uses placeholder telegram_ids (negative: -1 to -11).
- All records are marked is_approved=1 + is_preseeded=1.
- When a member /start s and types their name, bot.py claims the record:
    • Swaps placeholder ID → real Telegram ID
    • Sets is_preseeded=0
    • Grants immediate access (no manager approval step)
- Script is idempotent: re-running updates role/team/grade without overwriting
  real telegram_ids of already-claimed accounts.
"""

import sys
import os

# Run from bot/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from store import init_db, get_db

# ── Team data ────────────────────────────────────────────────────────────────
# (placeholder_id, full_name, email, role, team, grade, reports_to_placeholder)
TEAM = [
    (-1,  "Lê Quang Huy",        "huyle@ahamove.com",     "manager",   None,        "G4",     None),
    (-2,  "Lê Hoàng Nhất Thống", "thonglhn@ahamove.com",  "team_lead", "HAN",       "G3",     -1),
    (-3,  "Lưu Thị Hoài Thương", "thuonglth@ahamove.com", "employee",  "HAN",       "G2",     -2),
    (-4,  "Phạm Phú Toàn",       "toanpt@ahamove.com",    "employee",  "HAN",       "G1",     -2),
    (-5,  "Trần Quốc Thành",     "thanhtq@ahamove.com",   "team_lead", "SGN",       "ACT-G3", -1),
    (-6,  "Trần Ngọc Phú",       "phutn@ahamove.com",     "employee",  "SGN",       "G1",     -5),
    (-7,  "Phạm Đình Chiến",     "chienpd@ahamove.com",   "employee",  "SGN",       "G2",     -5),
    (-8,  "Lê Văn Khánh",        "khanhlv@ahamove.com",   "team_lead", "B2B",       "G3",     -1),
    (-9,  "Nguyễn Thị Kim Ngân", "Nganntk1@ahamove.com",  "employee",  "B2B",       "G1",     -8),
    (-10, "Nguyễn Duy Khâm",     "khamnd@ahamove.com",    "employee",  "expansion", "G2",     -8),
    (-11, "Trần Văn Hùng",       "hungtv@ahamove.com",    "employee",  "B2B",       "G1",     -8),
]


def _name_key(name: str) -> str:
    """Vietnamese 'họ + tên' identity key — first token + last token, lowercased.
    'Lê Hoàng Nhất Thống' → 'lê thống', and the shorthand 'Lê Thống' → 'lê thống'."""
    parts = (name or "").lower().split()
    if not parts:
        return ""
    return f"{parts[0]} {parts[-1]}" if len(parts) >= 2 else parts[0]


def _find_matches(conn, name: str, email: str) -> list:
    """All user rows that refer to the same person: exact name, same email, or
    matching họ+tên key. Used to detect + merge duplicate accounts."""
    key = _name_key(name)
    rows = conn.execute("SELECT * FROM users").fetchall()
    out = []
    for r in rows:
        rn = (r["full_name"] or "").strip().lower()
        re_ = (r["email"] or "").strip().lower()
        if rn == name.lower() or (re_ and re_ == email.lower()) or _name_key(r["full_name"]) == key:
            out.append(r)
    return out


def seed():
    init_db()  # ensures schema + migrations are applied

    inserted = 0
    updated  = 0
    merged   = 0

    # placeholder_id → resolved telegram_id (real if claimed, else placeholder)
    id_map: dict[int, int] = {}

    with get_db() as conn:
        # Disable FK checks for the duration of seed — we enforce integrity manually
        # (we repoint child rows before deleting duplicate parents).
        conn.execute("PRAGMA defer_foreign_keys = ON")

        for (pid, name, email, role, team, grade, reports_to) in TEAM:
            matches = _find_matches(conn, name, email)

            if matches:
                # Keeper = a CLAIMED row (telegram_id > 0, needed for bot DMs) if any,
                # else the existing placeholder row.
                claimed = [m for m in matches if m["telegram_id"] > 0]
                keeper_id = (claimed[0] if claimed else matches[0])["telegram_id"]

                # Merge any duplicate rows into the keeper: repoint children, delete dup.
                for m in matches:
                    old = m["telegram_id"]
                    if old == keeper_id:
                        continue
                    for table, col in [
                        ("tasks", "assignee_id"), ("tasks", "assigned_by"),
                        ("users", "reports_to"), ("audit_log", "actor_id"),
                    ]:
                        try:
                            conn.execute(f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                                         (keeper_id, old))
                        except Exception:
                            pass
                    conn.execute("DELETE FROM users WHERE telegram_id = ?", (old,))
                    print(f"  [merged dup]    {m['full_name']} ({old}) → keeper {keeper_id}")
                    merged += 1

                id_map[pid] = keeper_id
                # Restore canonical fields (also fixes shorthand names like 'Lê Thống').
                # Preserve is_preseeded=0 if the keeper is a real claimed account.
                if keeper_id > 0:
                    conn.execute("""
                        UPDATE users SET full_name=?, email=?, role=?, team=?, grade=?,
                                         is_approved=1
                         WHERE telegram_id=?
                    """, (name, email, role, team, grade, keeper_id))
                    print(f"  [claimed]       {name} (real id={keeper_id})")
                else:
                    conn.execute("""
                        UPDATE users SET full_name=?, email=?, role=?, team=?, grade=?,
                                         is_approved=1, is_preseeded=1
                         WHERE telegram_id=?
                    """, (name, email, role, team, grade, keeper_id))
                    print(f"  [updated]       {name} (placeholder id={keeper_id})")
                updated += 1
            else:
                # Fresh insert — resolve reports_to using id_map built so far
                resolved_rt = id_map.get(reports_to, reports_to) if reports_to is not None else None
                id_map[pid] = pid
                conn.execute("""
                    INSERT INTO users
                        (telegram_id, username, full_name, email, role, team, grade,
                         reports_to, is_approved, is_preseeded)
                    VALUES (?, '', ?, ?, ?, ?, ?, ?, 1, 1)
                """, (pid, name, email, role, team, grade, resolved_rt))
                print(f"  [inserted]      {name} (placeholder id={pid})")
                inserted += 1

        # Second pass: fix reports_to now that every person resolves to a final id.
        for (pid, name, email, role, team, grade, reports_to) in TEAM:
            if reports_to is None:
                continue
            tid = id_map.get(pid, pid)
            rt  = id_map.get(reports_to, reports_to)
            conn.execute("UPDATE users SET reports_to = ? WHERE telegram_id = ?", (rt, tid))

    print(f"\nDone. inserted={inserted}  updated={updated}  merged_dups={merged}")
    print("All pre-seeded members will be auto-approved when they /start the bot.")


if __name__ == "__main__":
    print("Seeding Truck Ops team into bot DB…\n")
    seed()
