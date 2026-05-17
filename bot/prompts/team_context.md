# Ops Truck Team Context — Q2/2026
# Cập nhật: 2026-05-17
# Dùng làm system context cho AI classifier — KHÔNG xoá, chỉ update khi có nhân sự mới

## Công ty & Bối cảnh
- **Ahamove** — on-demand logistics platform, thị trường Việt Nam
- **Truck Ops** — phụ trách toàn bộ mảng xe tải: Bulky, Long Haul, GXT, B2B Enterprise
- **Mục tiêu Q2/2026**: GSV Non-Bulky 70% YoY (69B → 117.3B), Fill Rate 68%+, COGS GXT <75K/kiện
- **2 thành phố chính**: HCM (SGN) và Hà Nội (HAN), mở rộng tỉnh (EXP): Bình Dương, Long An, và các tỉnh khác

## Cơ cấu Org Chart

```
Lê Quang Huy — Manager (G4)
├── Lê Hoàng Nhất Thống — Team Lead HAN (G3)
│   ├── Lưu Thị Hoài Thương — Specialist HAN (G2)  [FR data, forecast, capacity]
│   └── Phạm Phú Toàn — Executive HAN (G1)          [Recruitment, retention, decal]
├── Trần Quốc Thành — Acting Team Lead SGN (ACT-G3)
│   ├── Trần Ngọc Phú — Executive SGN (G1)           [FR data, capacity, policy]
│   └── Phạm Đình Chiến — Specialist SGN (G2)        [Inactive driver, backlog, retention]
└── Lê Văn Khánh — Team Lead B2B (G3)
    ├── Nguyễn Thị Kim Ngân — Coordinator B2B (G1)   [Vendor B2B, contract, payment]
    ├── Nguyễn Duy Khâm — Specialist Expansion (G2)  [KCN, tỉnh EXP, driver recruitment]
    └── Trần Văn Hùng — Executive B2B (G1)           [Vendor B2B, B2C dispatch]
```

## Chi tiết từng thành viên

### Lê Quang Huy (Huy) — Manager
- **Email**: huyle@ahamove.com | **Grade**: G4
- **Scope**: Quản lý toàn bộ network xe tải, quản trị nhân sự, chịu trách nhiệm kết quả toàn bộ dự án
- **Keywords**: quản lý, toàn bộ, escalate, quyết định, phê duyệt, chiến lược
- **OKR ownership**: Tất cả objectives — O1, O2, O3, O4, O5 (oversight)
- **Reports to**: Lê Hữu Chung

### Lê Hoàng Nhất Thống (Thống) — Team Lead HAN
- **Email**: thonglhn@ahamove.com | **Grade**: G3
- **Scope**:
  - Quản lý vận hành nhân sự + performance khu vực Hà Nội
  - Hỗ trợ vận hành B2B khu vực HAN
  - Planning Service và Supply cho Bulky/GXT toàn khu vực
  - Planning Cost và Performance khu vực HAN
  - Làm việc liên team xử lý sự cố tài xế tại HAN
- **Keywords**: HAN, Hà Nội, miền Bắc, COGS GXT, planning, bulky HAN, GXT HAN, service planning
- **OKR primary**: O1.1 (FR HAN), O2.2 (Shift HAN), O3.2 (COGS GXT planning), O5.1 (GHN 9 tỉnh)
- **OKR support**: O1.2 (Long Haul HAN), O1.3 (SME HAN), O2.3 (Moving Crew), O3.1 (SLA HAN)

### Lưu Thị Hoài Thương (Thương) — Specialist HAN
- **Email**: thuonglth@ahamove.com | **Grade**: G2
- **Scope**:
  - Forecast và update capacity theo từng tập tài xế HAN
  - Update dữ liệu Order Creation/Vol Success/Backlog/Cancel/Return HAN
  - Báo cáo FR tổng quan N-1 & MTD
  - Phân tích insight Fail KPI (tài xế nào, khu vực nào, lý do fail)
  - Truyền thông chính sách cho tài xế mass HAN
  - Planning Cost/Policy hàng tháng HAN
  - Đầu mối với Tech Ops Driver, Data → cải thiện Order Dispatch, MiniHub, Map
- **Keywords**: data HAN, FR HAN, báo cáo, insight, phân tích, capacity HAN, forecast HAN, backlog HAN, Tech Ops
- **OKR primary**: O1.1 (FR data/analysis HAN), O4.2 (Vehicle classification data)
- **OKR support**: O2.4 (data retention HAN), O4.3 (AI bot data)

### Phạm Phú Toàn (Toàn) — Executive HAN
- **Email**: toanpt@ahamove.com | **Grade**: G1
- **Scope**:
  - Làm việc với team Growth về tuyển dụng tài xế mới HAN
  - Xử lý case decal tài xế HAN theo chiến dịch
  - Update Productivity hàng ngày (capacity → tỉ lệ clear hàng HAN)
  - Update Retention hàng ngày (tài xế active/inactive HAN)
  - Báo cáo weekly contribution đội nhóm (total vol, bulky, instant)
  - Lập kế hoạch tuyển dụng đội nhóm HAN
  - Truyền thông hoạt động/dịch vụ mới tới tài xế HAN
  - Đầu mối với S/O điều phối xe HAN
- **Keywords**: tuyển dụng HAN, decal HAN, productivity HAN, retention HAN, đội nhóm HAN, tài xế HAN
- **OKR primary**: O2.4 (Driver Retention HAN), O2.5 (Decal HAN)
- **OKR support**: O2.2 (Shift pilot HAN execution), O4.2 (fleet data)

### Trần Quốc Thành (Thành) — Acting Team Lead SGN
- **Email**: thanhtq@ahamove.com | **Grade**: ACT-G3
- **Scope**:
  - Quản lý vận hành nhân sự + performance khu vực HCM
  - Làm việc với team Growth về tuyển dụng tài xế mới SGN
  - Hỗ trợ vận hành Bulky/GXT tại HCM
  - Xử lý case decal tài xế SGN
  - Update Productivity và Retention hàng ngày SGN
  - Báo cáo weekly contribution (total vol, 4h, instant)
  - Quản lý chất lượng tài xế SGN
  - Đầu mối với S/O điều phối xe SGN
- **Keywords**: SGN, HCM, miền Nam, Hồ Chí Minh, bulky SGN, GXT SGN, tài xế SGN, đội nhóm SGN
- **OKR primary**: O1.1 (FR SGN), O2.2 (Shift SGN), O3.1 (SLA SGN)
- **OKR support**: O1.3 (SME SGN), O2.3 (Moving Crew SGN), O2.4 (Retention SGN)

### Trần Ngọc Phú (Phú) — Executive SGN
- **Email**: phutn@ahamove.com | **Grade**: G1
- **Scope**:
  - Forecast và update capacity tập tài xế SGN
  - Update dữ liệu Order Creation/Vol Success/Backlog SGN
  - Báo cáo FR N-1 & MTD SGN
  - Phân tích insight Fail KPI SGN
  - Đề xuất chương trình chính sách cải thiện chỉ số vận hành
  - Truyền thông chính sách tài xế mass SGN
  - Planning Cost/Policy hàng tháng SGN
- **Keywords**: data SGN, FR SGN, báo cáo SGN, insight SGN, capacity SGN, forecast SGN, policy SGN
- **OKR primary**: O1.1 (FR data/analysis SGN)
- **OKR support**: O2.4 (data retention SGN)

### Phạm Đình Chiến (Chiến) — Specialist SGN
- **Email**: chienpd@ahamove.com | **Grade**: G2
- **Scope**:
  - Cải thiện tỉ lệ inactive hàng ngày (noti/call/policy) SGN
  - Update Productivity hàng ngày SGN
  - Update Retention hàng ngày SGN
  - Báo cáo daily contribution đội nhóm/mass SGN
  - Lập kế hoạch tuyển dụng SGN
  - Chạy backlog hàng ngày → gán đơn cho tài xế (đặc biệt 4h)
  - Làm việc với QM: mở khoá, huỷ đơn cho tài xế SGN
  - Đề xuất cải thiện tính năng vận hành
- **Keywords**: inactive SGN, backlog SGN, tuyển dụng SGN, retention SGN, productivity SGN, gán đơn, QM SGN
- **OKR primary**: O2.4 (Driver Retention SGN), O2.5 (Decal SGN)
- **OKR support**: O2.2 (Shift pilot SGN execution)

### Lê Văn Khánh (Khánh) — Team Lead B2B
- **Email**: khanhlv@ahamove.com | **Grade**: G3
- **Scope**:
  - Quản lý vận hành nhân sự + performance toàn nhánh B2B
  - Tìm kiếm vendor mới cho đơn hàng B2B
  - Hỗ trợ vận hành dự án B2B toàn quốc
  - Planning Cost và Performance B2B
  - Đảm bảo chính xác hợp đồng và giá cước theo từng dự án
  - Làm việc liên team về case khách hàng B2B
  - Update product request phục vụ vận hành B2B
- **Keywords**: B2B, vendor, hợp đồng, giá cước, dự án B2B, enterprise, key account, cost B2B
- **OKR primary**: O3.3 (Vendor Truck B2B 11), O3.4 (Distribution GSV), O5.1 (GHN 9 tỉnh)
- **OKR support**: O2.6 (EV Van partner), O3.1 (SLA B2B), O3.2 (COGS negotiation)

### Nguyễn Thị Kim Ngân (Ngân) — Coordinator B2B
- **Email**: Nganntk1@ahamove.com | **Grade**: G1
- **Scope**:
  - Điều phối vendor B2B hàng ngày cho các dự án
  - Lập bảng kê hàng ngày kiểm soát chi phí B2B
  - Lên hợp đồng dự án B2B và vendor B2C
  - Đảm bảo tính chính xác + đúng hạn thanh toán với team kế toán
  - Update phụ lục giá thường xuyên
- **Keywords**: điều phối B2B, bảng kê, hợp đồng, thanh toán, giá cước, vendor daily, phụ lục
- **OKR primary**: O3.3 (Vendor B2B coordination)
- **OKR support**: O3.4 (Distribution ops support)

### Nguyễn Duy Khâm (Khâm) — Specialist Expansion
- **Email**: khamnd@ahamove.com | **Grade**: G2
- **Scope**:
  - Làm việc với team Growth về tuyển dụng tài xế tỉnh EXP
  - Xử lý case decal tài xế tỉnh theo chiến dịch
  - Update Productivity hàng ngày tỉnh EXP (capacity → clear hàng)
  - Update Retention hàng ngày tài xế EXP
  - Báo cáo weekly contribution đội nhóm EXP (total vol, 4h, instant)
  - Lập kế hoạch tuyển dụng đội nhóm tỉnh
  - Quản lý chất lượng tài xế tỉnh
- **Keywords**: tỉnh, expansion, KCN, Bình Dương, Long An, mở rộng, EXP, tuyển dụng tỉnh, driver EXP
- **OKR primary**: O2.1 (KCN BDG + LAN Hub), O1.2 (FR Long Haul driver pool)
- **OKR support**: O2.5 (Decal EXP), O5.1 (Supply activation 9 tỉnh)

### Trần Văn Hùng (Hùng) — Executive B2B
- **Email**: hungtv@ahamove.com | **Grade**: G1
- **Scope**:
  - Hỗ trợ điều phối vendor B2B hàng ngày
  - Lập bảng kê hàng ngày kiểm soát chi phí B2B
  - Tìm kiếm thêm vendor vận hành B2B
  - Đảm bảo chính xác, đúng giờ bảng kê chi phí (hệ thống + vendor)
  - Xử lý điều phối dự án B2C và Project khi có nhu cầu
- **Keywords**: vendor B2B, bảng kê, chi phí, điều phối B2C, project B2C, tìm vendor
- **OKR primary**: O3.3 (Vendor search B2B)
- **OKR support**: O3.4 (Distribution support)

## OKR → Owner Mapping (Quick Reference)

| OKR | KR | Primary Owner | Support |
|-----|-----|---------------|---------|
| O1.1 | FR Core ≥68% | Thống (HAN) + Thành (SGN) | Thương (data HAN), Phú (data SGN) |
| O1.2 | FR Long Haul ≥70% | Khâm (EXP) + Thống (HAN TL) | — |
| O1.3 | FR SME 100-300kg ≥65% | Thành (SGN) + Thống (HAN) | — |
| O2.1 | KCN BDG + LAN Hub | Khâm | — |
| O2.2 | Shift Model ≥100 drivers | Thống (HAN) + Thành (SGN) | — |
| O2.3 | Moving Crew ≥50 certified | Thống + Thành | — |
| O2.4 | Driver Retention D30 70% | Toàn (HAN) + Chiến (SGN) | Phú (data SGN) |
| O2.5 | Decal 1,900 verified | Toàn (HAN) + Chiến (SGN) | Khâm (EXP) |
| O2.6 | EV Van 1 partner live | Khánh | — |
| O3.1 | 1st PU On-Time 80% | Thành (SGN) + Thống (HAN) | — |
| O3.2 | COGS GXT 75K/kiện | Thống | Khánh (negotiation) |
| O3.3 | Vendor Truck B2B 11 | Khánh | Ngân (coord), Hùng (search) |
| O3.4 | Distribution GSV ≥4.5B | Khánh | Ngân, Hùng |
| O4.1 | Dynamic Pricing research | BA/external | — |
| O4.2 | Vehicle Classification 60% | Thương (data) + Chiến (data) | — |
| O4.3 | AI Bot OPS 40% auto | BA/external | — |
| O5.1 | GHN 9 tỉnh | Khánh + Thống | Khâm (supply) |

## Scope Rules (AI sử dụng để đánh giá in_scope)

**IN SCOPE** — task thuộc về team Ops Truck nếu liên quan đến:
- Fill Rate, FR, tỉ lệ giao hàng thành công
- Driver supply, tuyển dụng, retention, churn tài xế xe tải
- KCN, hub, mini-hub, expansion tỉnh
- COGS, chi phí vận hành xe tải, GXT
- B2B vendor, hợp đồng, dự án enterprise
- Bulky, Long Haul, Moving, GXT operations
- Shift model, moving crew, decal
- SLA xe tải, on-time pickup
- Distribution, last-mile xe tải

**OUT OF SCOPE** — chuyển sang team khác nếu liên quan đến:
- Bike delivery, xe máy (→ Bike Ops team)
- Consumer marketing, app user acquisition (→ Marketing)
- Finance reporting, P&L (→ Finance)
- HR policies (→ HR)
- Product development (→ Product team, nhưng có thể phối hợp)

## Cách AI detect assignee từ task text

1. **Tên rõ**: "Khâm làm..." → assignee = Khâm (confidence: 0.95)
2. **Tên viết tắt/nickname**: "Thống", "Thành", "Ngân", "Chiến", "Toàn", "Phú", "Hùng", "Khánh"
3. **Role/location**: "HAN team", "SGN ops", "B2B" → map theo org chart
4. **OKR keyword**: "KCN Bình Dương" → Khâm | "COGS GXT" → Thống | "vendor B2B" → Khánh
5. **Scope keyword**: "tuyển dụng tỉnh" → Khâm | "backlog SGN" → Chiến | "hợp đồng" → Ngân

## Độ ưu tiên theo Grade (nếu task không rõ assignee)

- G3 Team Lead → assign nếu task cần quyết định, planning, liên team
- G2 Specialist → assign nếu task cần phân tích, execution, specialist skill
- G1 Executive → assign nếu task là daily ops, data collection, coordination
