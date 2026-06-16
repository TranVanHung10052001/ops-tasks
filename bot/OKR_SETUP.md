# OKR ↔ Google Sheets — Setup Guide

Bidirectional sync: Google Sheet ↔ Bot SQLite ↔ Dashboard

---

## 1. Tạo Google Sheet

Tạo 1 spreadsheet với **2 tabs**:

### Tab 1: `OKR Progress`

| Cột | Tên | Mô tả |
|---|---|---|
| A | id | O1, O2, O3, O4 |
| B | label | Fill Rate, Supply & Retention… |
| C | progress | 0–100 (số nguyên) |
| D | current | VD: "FR HAN 78%, FR Core 62%" |
| E | status | on_track / at_risk / behind / done |
| F | note | Ghi chú tùy chọn |
| G | updated_at | Tự điền bởi script |

Dữ liệu mẫu hàng 2–5:
```
O1  Fill Rate               45   FR HAN 78%     at_risk   Cần tăng FR LH
O2  Supply & Retention      30   KCN BDG live   on_track
O3  Service & Cost          25   SLA 51%        behind    GXT chưa xong
O4  Tech & Growth           20   Dynamic 60%    on_track
```

### Tab 2: `Action Items`

| Cột | Tên | Mô tả |
|---|---|---|
| A | id | 1.1.1, 1.1.2… |
| B | okr | O1.1, O2.1… |
| C | name | Tên action |
| D | pic | Người phụ trách |
| E | priority | P0/P1/P2/P3 |
| F | deadline | YYYY-MM-DD |
| G | status | pending / in_progress / done / cancelled |
| H | note | Ghi chú |

---

## 2. Apps Script (Tools → Apps Script)

Paste toàn bộ code sau vào **Code.gs**:

```javascript
const BOT_URL    = "https://your-bot-url.railway.app"; // thay bằng URL Railway
const BOT_SECRET = "ops-tasks-secret-2026";            // phải khớp BOT_API_SECRET trong .env

// ── Push Sheet → Dashboard ────────────────────────────────────────────────────

function pushOkrToDashboard() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Tab OKR Progress
  const objSheet = ss.getSheetByName("OKR Progress");
  const objRows  = objSheet.getDataRange().getValues().slice(1); // bỏ header
  const objectives = objRows
    .filter(r => r[0]) // có ID
    .map(r => ({
      id:       String(r[0]).trim().toUpperCase(),
      label:    String(r[1] || ""),
      progress: parseInt(r[2]) || null,
      current:  String(r[3] || ""),
      status:   String(r[4] || "on_track"),
      note:     String(r[5] || ""),
    }));

  // Tab Action Items
  const actSheet = ss.getSheetByName("Action Items");
  const actRows  = actSheet.getDataRange().getValues().slice(1);
  const actions = actRows
    .filter(r => r[0] && r[6]) // có ID và status
    .map(r => ({
      id:     String(r[0]).trim(),
      status: String(r[6] || "pending"),
      note:   String(r[7] || ""),
    }));

  const payload = JSON.stringify({ objectives, actions });
  const resp = UrlFetchApp.fetch(`${BOT_URL}/api/okr/sync`, {
    method:  "post",
    contentType: "application/json",
    headers: { Authorization: `Bearer ${BOT_SECRET}` },
    payload,
    muteHttpExceptions: true,
  });

  const result = JSON.parse(resp.getContentText());
  Logger.log(`OKR sync: ${result.updated} rows updated`);

  // Ghi updated_at
  const now = new Date().toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
  const lastRow = objSheet.getLastRow();
  if (lastRow > 1) {
    objSheet.getRange(2, 7, lastRow - 1, 1).setValue(now);
  }
  return result;
}

// ── Pull Dashboard → Sheet ────────────────────────────────────────────────────

function pullFromDashboard() {
  const resp = UrlFetchApp.fetch(`${BOT_URL}/api/okr`, {
    headers: { Authorization: `Bearer ${BOT_SECRET}` },
    muteHttpExceptions: true,
  });

  const data = JSON.parse(resp.getContentText());
  const ss   = SpreadsheetApp.getActiveSpreadsheet();

  // Cập nhật OKR Progress tab
  const objSheet = ss.getSheetByName("OKR Progress");
  data.objectives.forEach((obj, i) => {
    const row = i + 2;
    objSheet.getRange(row, 1).setValue(obj.id);
    objSheet.getRange(row, 2).setValue(obj.label);
    if (obj.progress_override != null) objSheet.getRange(row, 3).setValue(obj.progress_override);
    if (obj.current_override)          objSheet.getRange(row, 4).setValue(obj.current_override);
    if (obj.okr_status)                objSheet.getRange(row, 5).setValue(obj.okr_status);
  });

  // Cập nhật Action Items tab  
  const actSheet = ss.getSheetByName("Action Items");
  const actRows  = actSheet.getDataRange().getValues().slice(1);
  data.actions.forEach(action => {
    const rowIdx = actRows.findIndex(r => String(r[0]) === String(action.id));
    if (rowIdx >= 0 && action.status) {
      actSheet.getRange(rowIdx + 2, 7).setValue(action.status);
    }
  });

  Logger.log(`Pulled ${data.objectives.length} objectives, ${data.actions.length} actions`);
}

// ── onEdit trigger (auto-push khi sửa trên Sheet) ────────────────────────────

function onEdit(e) {
  const sheet = e.source.getActiveSheet();
  const name  = sheet.getName();
  if (name !== "OKR Progress" && name !== "Action Items") return;

  // Chỉ push khi sửa cột progress/status (C hoặc G)
  const col = e.range.getColumn();
  const watchCols = (name === "OKR Progress") ? [3, 5] : [7]; // C/E hoặc G
  if (!watchCols.includes(col)) return;

  // Debounce: chỉ push nếu chưa push trong 10 giây
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    pushOkrToDashboard();
  } finally {
    lock.releaseLock();
  }
}
```

---

## 3. Cài trigger tự động

1. Apps Script → **Triggers** (đồng hồ bên trái)
2. **+ Add Trigger**:
   - Function: `pushOkrToDashboard`
   - Event source: **Time-driven**
   - Type: **Hour timer** → every **1 hour**
3. Save → Authorize

---

## 4. Cấu hình

Sửa 2 dòng đầu trong `Code.gs`:
```javascript
const BOT_URL    = "https://your-bot.railway.app"; // URL Railway production
const BOT_SECRET = "ops-tasks-secret-2026";        // Phải khớp BOT_API_SECRET
```

---

## 5. Test

Trong Apps Script:
- Chạy `pushOkrToDashboard()` → kiểm tra dashboard `/okr`
- Chạy `pullFromDashboard()` → kiểm tra sheet cập nhật

Từ terminal (test thủ công):
```bash
# Push 1 objective thủ công
curl -X PATCH https://your-bot.railway.app/api/okr/objectives/O1 \
  -H "Authorization: Bearer ops-tasks-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"progress": 52, "status": "at_risk", "current": "FR HAN 78%, FR Core 62%"}'

# Update 1 action
curl -X PATCH https://your-bot.railway.app/api/okr/actions/1.1.3 \
  -H "Authorization: Bearer ops-tasks-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'

# Bulk sync từ sheet
curl -X POST https://your-bot.railway.app/api/okr/sync \
  -H "Authorization: Bearer ops-tasks-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"objectives":[{"id":"O1","progress":52,"status":"at_risk"}], "actions":[]}'
```

---

## Flow tóm tắt

```
Google Sheet (team sửa progress/status)
    └→ onEdit trigger (realtime) hoặc hourly timer
    └→ POST /api/okr/sync
    └→ Bot SQLite (okr_progress + okr_action_status tables)
    └→ Dashboard /okr (next load)

Dashboard (manager click ✎ Cập nhật tiến độ hoặc click status action)
    └→ PATCH /api/okr/objectives/{id} hoặc /api/okr/actions/{id}
    └→ Bot SQLite
    └→ Hiển thị ngay (optimistic update)
    └→ Sheet chưa tự cập nhật — chạy pullFromDashboard() để sync ngược
```

> **Note**: Sheet → Dashboard sync là real-time (onEdit). Dashboard → Sheet là manual (chạy `pullFromDashboard()`). Full bidirectional realtime cần thêm webhook từ bot về sheet — có thể build sau nếu cần.
