"""
seed_members.py — Pre-seed team Telegram IDs vào DB.

Cách dùng:
  1. Điền telegram_id (số nguyên) cho từng thành viên bên dưới.
     Để None nếu chưa biết — người đó sẽ tự /start sau.
  2. Chạy: py -3 seed_members.py
  3. Script sẽ insert/update từng người vào DB, tự động approved.

Lấy Telegram ID:
  - Nhờ từng người nhắn @userinfobot → bot trả về "Id: 123456789"
  - Hoặc anh forward tin nhắn của họ vào @userinfobot
"""

import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from store import init_db, register_user, approve_user, set_user_role, get_user
from roles import MANAGER, TEAM_LEAD, EMPLOYEE

# ─── ĐIỀN ID VÀO ĐÂY ──────────────────────────────────────────────────────────
# telegram_id: số nguyên từ @userinfobot, hoặc None nếu chưa biết.
# username:    @username Telegram (không có @ ở đầu), hoặc "" nếu không có.
# role:        MANAGER | TEAM_LEAD | EMPLOYEE

MEMBERS = [
    {
        "callsign":    "OPS-00",
        "full_name":   "Lê Quang Huy",
        "email":       "huyle@ahamove.com",
        "telegram_id": 6764870597,          # ← đã biết (MANAGER_CHAT_ID)
        "username":    "",
        "role":        MANAGER,
    },
    {
        "callsign":    "OPS-01",
        "full_name":   "Lê Hoàng Nhất Thống",
        "email":       "thonglhn@ahamove.com",
        "telegram_id": None,                 # ← điền vào
        "username":    "",
        "role":        TEAM_LEAD,
    },
    {
        "callsign":    "OPS-02",
        "full_name":   "Lưu Thị Hoài Thương",
        "email":       "thuonglth@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        EMPLOYEE,
    },
    {
        "callsign":    "OPS-03",
        "full_name":   "Phạm Phú Toàn",
        "email":       "toanpt@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        EMPLOYEE,
    },
    {
        "callsign":    "OPS-04",
        "full_name":   "Trần Quốc Thành",
        "email":       "thanhtq@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        TEAM_LEAD,
    },
    {
        "callsign":    "OPS-05",
        "full_name":   "Trần Ngọc Phú",
        "email":       "phutn@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        EMPLOYEE,
    },
    {
        "callsign":    "OPS-06",
        "full_name":   "Phạm Đình Chiến",
        "email":       "chienpd@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        EMPLOYEE,
    },
    {
        "callsign":    "OPS-07",
        "full_name":   "Lê Văn Khánh",
        "email":       "khanhlv@ahamove.com",
        "telegram_id": 6623345057,              # ← đã biết
        "username":    "",
        "role":        TEAM_LEAD,
    },
    {
        "callsign":    "OPS-08",
        "full_name":   "Nguyễn Thị Kim Ngân",
        "email":       "Nganntk1@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        EMPLOYEE,
    },
    {
        "callsign":    "OPS-09",
        "full_name":   "Nguyễn Duy Khâm",
        "email":       "khamnd@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        EMPLOYEE,
    },
    {
        "callsign":    "OPS-10",
        "full_name":   "Trần Văn Hùng",
        "email":       "hungtv@ahamove.com",
        "telegram_id": None,
        "username":    "",
        "role":        EMPLOYEE,
    },
]

# ──────────────────────────────────────────────────────────────────────────────

def seed():
    init_db()
    skipped = []
    seeded = []
    updated = []

    for m in MEMBERS:
        tid = m["telegram_id"]
        if tid is None:
            skipped.append(m["callsign"])
            continue

        existing = get_user(tid)
        if existing:
            # Already in DB — just ensure approved + correct role
            from store import get_db
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET full_name=?, username=?, is_approved=1 WHERE telegram_id=?",
                    (m["full_name"], m["username"], tid),
                )
            set_user_role(tid, m["role"])
            updated.append(f"{m['callsign']} {m['full_name']}")
        else:
            register_user(tid, m["username"], m["full_name"])
            approve_user(tid)
            set_user_role(tid, m["role"])
            seeded.append(f"{m['callsign']} {m['full_name']}")

    print("\n── Seed kết quả ──────────────────────────────────────")
    if seeded:
        print(f"✓ Đã thêm mới ({len(seeded)}):")
        for s in seeded:
            print(f"   {s}")
    if updated:
        print(f"↑ Đã cập nhật ({len(updated)}):")
        for u in updated:
            print(f"   {u}")
    if skipped:
        print(f"– Bỏ qua (chưa có ID) ({len(skipped)}): {', '.join(skipped)}")
    print("──────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    seed()
