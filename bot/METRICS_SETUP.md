# Hướng dẫn kết nối KPI Dashboard

Dashboard hiển thị dữ liệu thật khi có ít nhất 1 nguồn được cấu hình.
Chọn **một trong ba cách** bên dưới.

---

## CÁCH 1 — Redash (Auto, khuyến nghị)

### Bước 1 — Tạo query tổng hợp trên Redash

Tạo 1 query trả về tất cả metrics theo định dạng `{metric_key, value}`:

```sql
-- Query: "Truck Ops Daily KPIs" — chạy mỗi 30 phút
-- Kết quả: mỗi dòng = 1 metric

SELECT 'gsv_today_b'             AS metric_key,
       ROUND(SUM(gsv_amount)/1e9, 2)::TEXT   AS value
  FROM orders
 WHERE DATE(created_at) = CURRENT_DATE
   AND service_type IN ('bulky','longhaul','rental')

UNION ALL

SELECT 'orders_today',
       COUNT(*)::TEXT
  FROM orders
 WHERE DATE(created_at) = CURRENT_DATE
   AND service_type IN ('bulky','longhaul','rental')

UNION ALL

SELECT 'fill_rate_core_pct',
       ROUND(
         COUNT(CASE WHEN driver_accepted_at IS NOT NULL THEN 1 END) * 100.0
         / NULLIF(COUNT(*), 0), 1
       )::TEXT
  FROM orders
 WHERE DATE(created_at) = CURRENT_DATE

UNION ALL

SELECT 'fill_rate_han_pct',
       ROUND(
         COUNT(CASE WHEN driver_accepted_at IS NOT NULL THEN 1 END) * 100.0
         / NULLIF(COUNT(*), 0), 1
       )::TEXT
  FROM orders
 WHERE DATE(created_at) = CURRENT_DATE AND city = 'HAN'

UNION ALL

SELECT 'fill_rate_sgn_pct',
       ROUND(
         COUNT(CASE WHEN driver_accepted_at IS NOT NULL THEN 1 END) * 100.0
         / NULLIF(COUNT(*), 0), 1
       )::TEXT
  FROM orders
 WHERE DATE(created_at) = CURRENT_DATE AND city = 'SGN'

UNION ALL

SELECT 'cogs_bulky_pct',
       ROUND(SUM(driver_cost) * 100.0 / NULLIF(SUM(revenue), 0), 1)::TEXT
  FROM orders
 WHERE DATE(created_at) = CURRENT_DATE AND service_type = 'bulky'

UNION ALL

SELECT 'active_drivers',
       COUNT(DISTINCT driver_id)::TEXT
  FROM driver_sessions
 WHERE session_date = CURRENT_DATE AND is_active = true
```

### Bước 2 — Lấy Query ID và API Key

- Query ID: số trong URL sau `/queries/` (VD: `https://redash.ahamove.com/queries/42` → ID = 42)
- API Key: Redash → Settings → API Keys → User API Key

### Bước 3 — Điền vào `bot/.env`

```env
REDASH_URL=https://redash.ahamove.com
REDASH_API_KEY=<api_key_của_bạn>
REDASH_QUERY_METRICS=42
```

Bot sẽ tự pull từ Redash mỗi 30 phút. Dashboard cập nhật real-time.

---

## CÁCH 2 — Google Sheets (Manual daily input)

Dùng khi Redash chưa có query sẵn, hoặc muốn override thủ công.

### Bước 1 — Tạo Google Sheet

Tạo sheet tên `KPI Input` với columns:

| A: metric_key | B: value | C: note |
|---|---|---|
| gsv_today_b | 8.7 | tỷ VNĐ |
| orders_today | 1247 | chuyến |
| fill_rate_core_pct | 78.0 | % |
| fill_rate_han_pct | 74.0 | % |
| fill_rate_sgn_pct | 68.0 | % |
| cogs_bulky_pct | 28.4 | % |
| active_drivers | 1847 | driver |
| gsv_wow_pct | 12.0 | % so tuần trước |
| cogs_wow_pct | -0.5 | âm = tốt |

### Bước 2 — Thêm Apps Script

Trong Google Sheet: **Extensions → Apps Script** → paste code sau:

```javascript
const BOT_API_URL = "https://<YOUR_RAILWAY_URL>";   // VD: ops-bot.railway.app
const BOT_API_SECRET = "ops-tasks-secret-2026";      // khớp DASHBOARD_SECRET trong bot/.env

function pushKpisToDashboard() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet()
    .getSheetByName("KPI Input");
  if (!sheet) return;

  const data = sheet.getDataRange().getValues();
  const metrics = {};

  for (let i = 1; i < data.length; i++) {  // skip header row
    const key = String(data[i][0]).trim();
    const val = String(data[i][1]).trim();
    if (key && val && val !== "") {
      metrics[key] = val;
    }
  }

  const payload = JSON.stringify({ metrics, source: "sheets" });

  const resp = UrlFetchApp.fetch(`${BOT_API_URL}/api/metrics/bulk`, {
    method: "POST",
    contentType: "application/json",
    headers: { Authorization: `Bearer ${BOT_API_SECRET}` },
    payload,
    muteHttpExceptions: true,
  });

  const code = resp.getResponseCode();
  Logger.log(`Push result: ${code} — ${resp.getContentText()}`);
  
  if (code === 200) {
    SpreadsheetApp.getActiveSpreadsheet()
      .toast(`✅ Đã push ${Object.keys(metrics).length} metrics lên dashboard`, "KPI Sync", 4);
  } else {
    SpreadsheetApp.getActiveSpreadsheet()
      .toast(`❌ Lỗi ${code} — kiểm tra bot URL và secret`, "KPI Sync", 6);
  }
}

// Tự động push mỗi ngày 8:00 sáng
function setupTrigger() {
  ScriptApp.newTrigger("pushKpisToDashboard")
    .timeBased()
    .everyDays(1)
    .atHour(8)
    .create();
}
```

### Bước 3 — Deploy

1. Chạy `setupTrigger()` một lần để tạo trigger tự động
2. Hoặc bấm nút **Run → pushKpisToDashboard** để push thủ công bất kỳ lúc nào

---

## CÁCH 3 — Manual POST (curl / Postman)

Dùng để test hoặc push ad-hoc:

```bash
curl -X POST https://<YOUR_BOT_URL>/api/metrics/bulk \
  -H "Authorization: Bearer ops-tasks-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": {
      "gsv_today_b": "8.7",
      "orders_today": "1247",
      "fill_rate_core_pct": "78.0",
      "fill_rate_han_pct": "74.0",
      "fill_rate_sgn_pct": "68.0",
      "cogs_bulky_pct": "28.4",
      "active_drivers": "1847",
      "gsv_wow_pct": "12.0",
      "cogs_wow_pct": "-0.5"
    },
    "source": "manual"
  }'
```

---

## Danh sách đầy đủ metric_key

| Key | Ý nghĩa | Ví dụ |
|-----|---------|-------|
| `gsv_today_b` | GSV truck hôm nay (tỷ VNĐ) | `8.7` |
| `gsv_wow_pct` | GSV WoW % (dương = tăng) | `12.0` |
| `orders_today` | Số chuyến hôm nay | `1247` |
| `orders_wow_pct` | Chuyến WoW % | `9.0` |
| `fill_rate_core_pct` | FR toàn network | `78.0` |
| `fill_rate_han_pct` | FR Hà Nội | `74.0` |
| `fill_rate_sgn_pct` | FR TP.HCM | `68.0` |
| `fill_rate_vsip_pct` | FR KCN VSIP | `84.0` |
| `fill_rate_songthan_pct` | FR KCN Sóng Thần | `71.0` |
| `fill_rate_longhau_pct` | FR KCN Long Hậu | `79.0` |
| `cogs_bulky_pct` | COGS Bulky % revenue | `28.4` |
| `cogs_wow_pct` | COGS WoW (âm = tốt) | `-0.5` |
| `active_drivers` | Driver đang hoạt động | `1847` |
| `driver_station_pct` | % Station tier | `18` |
| `driver_core_pct` | % Core tier | `31` |
| `driver_hub_pct` | % Hub tier | `28` |
| `driver_mass_pct` | % Mass tier | `23` |
