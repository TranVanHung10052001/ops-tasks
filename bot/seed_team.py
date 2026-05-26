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


def seed():
    init_db()  # ensures schema + migrations are applied

    inserted = 0
    updated  = 0
    skipped  = 0

    with get_db() as conn:
        for (pid, name, email, role, team, grade, reports_to) in TEAM:
            # Check if a record with this full_name already exists
            existing = conn.execute(
                "SELECT telegram_id, is_preseeded FROM users WHERE full_name = ?",
                (name,)
            ).fetchone()

            if existing:
                tid = existing["telegram_id"]
                if tid > 0:
                    # Already claimed by real user — update non-ID fields only
                    conn.execute("""
                        UPDATE users
                           SET email = ?, role = ?, team = ?, grade = ?
                         WHERE full_name = ?
                    """, (email, role, team, grade, name))
                    print(f"  [skip-claimed]  {name} (real id={tid})")
                    skipped += 1
                else:
                    # Still placeholder — refresh data
                    conn.execute("""
                        UPDATE users
                           SET email = ?, role = ?, team = ?, grade = ?,
                               is_approved = 1, is_preseeded = 1
                         WHERE full_name = ?
                    """, (email, role, team, grade, name))
                    print(f"  [updated]       {name} (placeholder id={tid})")
                    updated += 1
            else:
                # Fresh insert
                conn.execute("""
                    INSERT INTO users
                        (telegram_id, username, full_name, email, role, team, grade,
                         reports_to, is_approved, is_preseeded)
                    VALUES (?, '', ?, ?, ?, ?, ?, ?, 1, 1)
                """, (pid, name, email, role, team, grade, reports_to))
                print(f"  [inserted]      {name} (placeholder id={pid})")
                inserted += 1

    print(f"\nDone. inserted={inserted}  updated={updated}  skipped={skipped}")
    print("All pre-seeded members will be auto-approved when they /start the bot.")


if __name__ == "__main__":
    print("Seeding Truck Ops team into bot DB…\n")
    seed()
