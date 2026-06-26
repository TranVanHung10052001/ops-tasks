# Ahamove Truck Ops — Dashboard + Telegram Bot

Hệ thống quản lý & điều phối task cho đội vận hành xe tải Ahamove.

- **`web/`** — Dashboard Next.js (App Router, React 19, Tailwind). Deploy trên **Vercel**.
- **`bot/`** — Telegram bot + FastAPI (Python 3.12, SQLite). Deploy trên **Railway**.
- **`docs/`** — kế hoạch & tài liệu; `bot/*_SETUP.md` — hướng dẫn nguồn KPI.

Web gọi API của bot qua `BOT_API_URL`; bot lưu dữ liệu vào SQLite (`bot/data/`, trên Railway là volume).

---

## 1. Yêu cầu

| Công cụ | Phiên bản | Cho |
|---------|-----------|-----|
| Node.js | ≥ 20 | web (Next 16) |
| Python  | 3.12  | bot |
| Git     | bất kỳ | — |

Cần thêm (lấy từ người bàn giao — **không có trong repo**):
- **TELEGRAM_TOKEN** (BotFather), **MANAGER_CHAT_ID** (chat id của manager)
- **GEMINI_API_KEY** (Google AI Studio)
- **BOT_API_SECRET / DASHBOARD_SECRET** (1 chuỗi bí mật chung cho web↔bot)
- (tùy chọn) GSheet ID / Redash key cho KPI

---

## 2. Clone

```bash
git clone https://github.com/TranVanHung10052001/ops-tasks.git
cd ops-tasks
```

> Repo private → người nhận phải được mời làm **Collaborator** (GitHub → Settings → Collaborators) hoặc dùng Organization. Public thì clone trực tiếp.

---

## 3. Chạy BOT (local)

```bash
cd bot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # rồi mở .env điền các giá trị thật
python server.py            # chạy FastAPI (:8000) + Telegram bot
```

Lần chạy đầu DB SQLite tự tạo + tự seed 11 thành viên (`seed_team.py`). Tối thiểu cần điền trong `.env`: `TELEGRAM_TOKEN`, `MANAGER_CHAT_ID`, `GEMINI_API_KEY`, `DASHBOARD_SECRET`. Xem chú thích từng biến trong `bot/.env.example`.

---

## 4. Chạy WEB (local)

```bash
cd web
npm install

cp .env.local.example .env.local   # điền BOT_API_URL + BOT_API_SECRET
npm run dev                        # http://localhost:3001
```

- `BOT_API_URL` = URL bot (local: `http://localhost:8000`; prod: URL Railway, **không có dấu /** cuối).
- `BOT_API_SECRET` **phải trùng** `DASHBOARD_SECRET` của bot.
- Bot chưa chạy → web vẫn lên giao diện, các số liệu hiện trạng thái "chờ kết nối".

---

## 5. Deploy

| Phần | Nền tảng | Cấu hình chính |
|------|----------|----------------|
| web  | **Vercel** | Root Directory = `web`, Production Branch = `master`, set env `BOT_API_URL` + `BOT_API_SECRET`. Auto-deploy khi push `master`. |
| bot  | **Railway** | Service root = `bot` (`bot/nixpacks.toml` + `Procfile` → `python server.py`), gắn **Volume** cho `bot/data/`, set toàn bộ env trong `.env.example`. |

> Đổi code trong `web/` → chỉ Vercel deploy. Đổi `bot/` → chỉ Railway deploy.

---

## 6. Checklist bàn giao cho người khác

1. ☐ Cấp quyền repo (Collaborator) hoặc chuyển sang Organization.
2. ☐ Gửi **secret** qua kênh an toàn (1Password/Bitwarden/Vault…), **KHÔNG** commit, **KHÔNG** gửi plaintext qua chat công khai.
3. ☐ Báo họ đọc `README.md` này + `bot/.env.example`.
4. ☐ (Nếu cần dữ liệu production) export SQLite từ Railway Volume gửi riêng — clone **không** kèm DB.
5. ☐ (Tùy chọn) thêm họ vào project Vercel + Railway nếu cần quyền deploy.

Tài liệu thêm: `docs/PROJECT_PLAN.md`, `bot/METRICS_SETUP.md`, `bot/OKR_SETUP.md`, `bot/SHEET_SETUP.md`.
