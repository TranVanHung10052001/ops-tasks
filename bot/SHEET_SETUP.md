# Google Sheet KPI Sync — Setup Guide

Bot tự động pull KPI từ 1 Google Sheet manager-maintained mỗi 30 phút.
Đơn giản hơn Redash, không cần SQL — manager paste số tay buổi sáng.

## TL;DR

1. Tạo service account ở Google Cloud → download JSON
2. Share sheet với service account email (Viewer)
3. Paste `GSHEET_ID` + path tới JSON vào `bot/.env`
4. Restart bot

Sau 30 phút, dashboard sẽ hiển thị KPI thay vì `—`.

## Cấu trúc sheet

Hàng đầu = headers. Mỗi hàng sau = 1 ngày (manager append-only).

| Ngày | GSV_hôm_nay_tỷ | Đơn_hôm_nay | FR_Core_% | FR_HAN_% | FR_SGN_% | FR_SME_% | FR_EXP_% | COGS_Bulky_% | Driver_Active | Ghi_chú |
|------|----------------|-------------|-----------|----------|----------|----------|----------|--------------|---------------|---------|
| 23/05/2026 | 8.7 | 1247 | 62 | 64 | 61 | 18 | 55 | 28.4 | 1847 | Ca thường |

**Date format:** `dd/mm/yyyy` (VN convention). Bot pick row có ngày mới nhất.

**Cột ad ngoài cần thiết:** Cứ thêm — bot silent skip nếu không có trong mapping. Hoặc edit `COLUMN_ALIASES` trong `bot/sheet_sync.py` để add mapping mới.

## Setup chi tiết

### Option A — Service Account (recommended, 1 lần setup, dùng vĩnh viễn)

#### 1. Tạo project + service account

- Vào [Google Cloud Console](https://console.cloud.google.com)
- Tạo project mới (hoặc dùng có sẵn)
- Menu `APIs & Services` → `Library` → search `Google Sheets API` → **Enable**
- Menu `IAM & Admin` → `Service Accounts` → **Create Service Account**
  - Name: `ops-tasks-bot`
  - Role: bỏ trống (sheet sẽ grant qua share riêng)
  - Done

#### 2. Tạo key JSON

- Click service account vừa tạo → tab **Keys**
- Add Key → Create new key → **JSON** → download
- Lưu file vào `bot/gsheet-service-account.json` (đã có trong `.gitignore`)

#### 3. Share sheet với service account

- Mở JSON file → copy giá trị `client_email` (dạng `ops-tasks-bot@...iam.gserviceaccount.com`)
- Mở Google Sheet → **Share** → paste email → **Viewer** (read-only đủ rồi)
- Bỏ tick "Notify people" → Send

#### 4. Cấu hình `.env`

```bash
GSHEET_ID=1OGLMk0STGWmBJlWzY-l1UtG9YQt4l0Vw9xwtjoLi4Po
GSHEET_TAB=0
GSHEET_SERVICE_ACCOUNT_JSON=./gsheet-service-account.json
```

`GSHEET_ID` là chuỗi dài trong URL sheet, giữa `/d/` và `/edit`.

#### 5. Restart bot

```bash
cd bot && python server.py
```

Log đầu tiên sẽ in: `Sheet sync: 9 metrics updated (row dated 23/05/2026)` sau ~30 giây.

### Option B — Public CSV (no auth, không khuyến khích)

Nếu chưa muốn setup service account:

1. Sheet → Share → "Anyone with the link" → Viewer
2. `.env`:
   ```bash
   GSHEET_ID=1OGLMk0STGWmBJlWzY-l1UtG9YQt4l0Vw9xwtjoLi4Po
   GSHEET_TAB=0
   # GSHEET_SERVICE_ACCOUNT_JSON=  (để trống)
   ```

Caveat: Sheet phải public — anyone with link đọc được. Không phù hợp nếu sheet có data nhạy cảm.

## Field mapping — Vietnamese ↔ Bot

| Sheet column (header) | Bot metric key | OKR |
|----------------------|----------------|-----|
| `Ngày` | (used to pick row) | — |
| `GSV_hôm_nay_tỷ` | `gsv_today_b` | O5 |
| `Đơn_hôm_nay` | `orders_today` | O5 |
| `FR_Core_%` | `fill_rate_core_pct` | O1.1 |
| `FR_HAN_%` | `fill_rate_han_pct` | O1.1 |
| `FR_SGN_%` | `fill_rate_sgn_pct` | O1.1 |
| `FR_SME_%` | `fill_rate_sme_pct` | O1.3 |
| `FR_EXP_%` | `fill_rate_exp_pct` | O1.2 / O2.1 |
| `COGS_Bulky_%` | `cogs_bulky_pct` | O3.2 |
| `Driver_Active` | `active_drivers` | O2.4 |
| `Ghi_chú` | `kpi_note` | — |

Header matching là **case-insensitive** và **diacritic-insensitive** — `FR_Core_%`, `fr_core`, `FR Core %` đều được hiểu giống nhau.

## Troubleshooting

| Triệu chứng | Fix |
|-------------|-----|
| Bot log `GSHEET_ID not set — skipping` | Chưa fill `GSHEET_ID` trong `.env` |
| Bot log `Service-account sheet fetch failed: ... 403` | Chưa share sheet với service account email, hoặc Google Sheets API chưa enable |
| Bot log `gspread not installed` | `pip install gspread google-auth` |
| Bot log `Sheet sync: no usable rows after mapping` | Header sheet không match alias — check tên cột, hoặc add alias vào `COLUMN_ALIASES` |
| Dashboard vẫn hiển thị `—` | (1) Đợi 30 phút sau restart, hoặc (2) check `/api/metrics` endpoint trả về gì |

## Manual force-sync (debug)

```bash
cd bot
python -c "import asyncio; from sheet_sync import sync_all; asyncio.run(sync_all())"
```
