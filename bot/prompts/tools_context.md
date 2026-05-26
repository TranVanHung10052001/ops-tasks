# TOOLS & DATA SOURCES — Truck Ops Team
# Điền thông tin thật vào đây để AI coaching chính xác hơn.
# File này được inject vào system prompt của AI coach.

---

## METABASE DASHBOARDS / CARDS
# Team dùng Metabase để xem data — có card theo từng chủ đề, filter được, download CSV được.
# Điền tên card/dashboard thật để AI dùng đúng tên thay vì tự đặt.

### Fill Rate
- Card/Dashboard: `[TÊN THẬT — vd: "Fill Rate EXP KCN"]`
- Filters có sẵn: date_range, zone (Core/EXP/LH/SME), city (HAN/SGN), kcn
- Key fields: fill_rate_pct, total_requests, matched_requests

### B2B / Vendor
- Card/Dashboard: `[TÊN THẬT — vd: "B2B Trip Logs"]`
- Filters có sẵn: date_range, service_type, vendor_id
- Key fields: order_id, driver_id, revenue, cost, vendor_name

### COGS / Cost
- Card/Dashboard: `[TÊN THẬT — vd: "GXT Cost Tracker"]`
- Filters có sẵn: date_range, service_type
- Key fields: cost_per_order, total_cost, cogs_pct

### Driver Supply
- Card/Dashboard: `[TÊN THẬT — vd: "Driver Active Daily"]`
- Filters có sẵn: date_range, tier (Station/Core/Hub/Mass), city
- Key fields: active_count, retention_d30, avg_orders

---

## GOOGLE SHEETS

### Bảng kê B2B / Vendor cost
- Sheet name: `[TÊN THẬT — vd: "Truck Ops - B2B Cost Tracker 2026"]`
- Link: [để trống hoặc điền URL]
- Tab structure:
  - `[Tab tuần — vd: "W21"]` — dữ liệu chi phí theo tuần
  - `[Tab phụ lục — vd: "Phụ lục Giá"]` — bảng giá hợp đồng
  - `[Tab summary — vd: "Monthly Summary"]` — tổng hợp tháng
- Macros có sẵn: `[TÊN MACRO THẬT nếu có, bỏ trống nếu không]`

### Fill Rate Tracking
- Sheet name: `[TÊN THẬT — vd: "FR Tracking Q2/2026"]`
- Link: [để trống hoặc điền URL]
- Tab structure:
  - `[vd: "Daily FR"]` — fill rate theo ngày
  - `[vd: "KCN Breakdown"]` — FR theo từng KCN

### KPI Input (manager-maintained)
- Sheet name: `[TÊN THẬT nếu dùng sheet KPI manual]`
- Link: [để trống hoặc điền URL]

### Driver Retention / Onboarding
- Sheet name: `[TÊN THẬT nếu có]`
- Link: [để trống]

---

## HỢP ĐỒNG / TÀI LIỆU

### Hợp đồng B2B Vendor
- Lưu tại: `[vd: Google Drive > Truck Ops > Hợp đồng B2B Q2/2026]`
- Format: `[vd: PDF — đặt tên theo vendor_tháng_năm]`

### Phụ lục giá
- Lưu tại: `[vd: cùng folder hợp đồng, tab riêng trong sheet B2B]`
- Người giữ bản mới nhất: Ngân (Nganntk1@ahamove.com)

---

## INTERNAL TOOLS / CHANNELS

### Báo cáo / Communication
- Daily report gửi qua: `[vd: Telegram group "Truck Ops Daily" / Email / Slack]`
- EOD recap gửi ai: `[vd: Huy + Thống]`

### Dispatch / Ops tool
- Tool chính: `[vd: AhaOps portal / internal dashboard URL]`
- Truy cập: `[vd: VPN cần thiết / không cần]`

---

## GHI CHÚ
- Để trống hoặc xóa section nào không liên quan
- AI sẽ ưu tiên dùng tên thật ở đây thay vì tự đặt tên
- Cập nhật file này khi có tool/sheet mới
