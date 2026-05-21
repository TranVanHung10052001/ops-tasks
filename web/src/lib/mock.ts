// Mock data Đài Điều Vận - Ahamove Truck Ops
// Số liệu thật từ company profile 2025-2026:
// - 45.5M orders/year | 2,139 tỷ GSV (+20.6% YoY)
// - 30.9K bike + 4.4K truck drivers
// - Truck GSV +42.1% YoY — fastest growing segment
// - Take rate ~26% | COGS Bulky target <30% | Incentive budget 2.5% GSV
// - Markets: HCM, HAN core | Bình Dương, Đồng Nai, Hải Phòng, Đà Nẵng tier 1
// - Driver tiers: Station >120 stop/m | Core >65 | Hub >40 | Mass >30
// - Income tiers: Pro >1M VNĐ/day | Core >750K | Hub >600K

export type Channel = "JD" | "OKR" | "Adhoc";
export type Priority = "P0" | "P1" | "P2" | "P3" | "P4";
export type TaskStatus = "cho_xu_ly" | "can_lam" | "dang_lam" | "bi_chan" | "dang_review" | "hoan_thanh" | "tam_dung";
export type MemberStatus = "online" | "offline" | "busy" | "away";

export interface Member {
  id: string;
  callsign: string;
  initials: string;
  name: string;
  fullName: string;
  role: string;
  status: MemberStatus;
  workload: number;
  workloadMax: number;
}

export interface OpsTask {
  id: string;
  channel: Channel;
  channelLabel: string;
  title: string;
  description?: string;
  assignee: string;
  priority: Priority;
  status: TaskStatus;
  deadline: string;
  estimateHours: number;
  tags: string[];
  createdAt: string;
  createdBy: string;
  aiConfidence?: number;
  aiClassified?: boolean;
}

export interface OkrObjective {
  id: string;
  title: string;
  subtitle: string;
  progress: number;
  target: string;
  baseline: string;
  current: string;
  risk: "low" | "medium" | "high";
  owner: string;
  bsc: "Tài chính" | "Khách hàng" | "Vận hành" | "Học hỏi";
  keyResults: { id: string; label: string; progress: number; target: string }[];
}

export interface ActivityEvent {
  id: string;
  ts: string;
  date: string;
  actor: string;
  action: string;
  target?: string;
  via?: "web" | "telegram" | "ai";
}

// ====== MEMBERS — Team Truck Ops Ahamove (8 callsign) ======
export const MEMBERS: Member[] = [
  { id: "m1", callsign: "OPS-01", initials: "NVH", name: "Anh Hùng", fullName: "Nguyễn Văn Hùng", role: "Trưởng phòng điều vận Truck", status: "online", workload: 7, workloadMax: 10 },
  { id: "m2", callsign: "OPS-02", initials: "TMT", name: "Anh Tuấn", fullName: "Trần Minh Tuấn", role: "Trưởng nhóm điều vận HCM (Bulky + Longhaul)", status: "online", workload: 8, workloadMax: 10 },
  { id: "m3", callsign: "OPS-03", initials: "LQA", name: "Anh Anh", fullName: "Lê Quang Anh", role: "Điều phối KCN — VSIP, Sóng Thần, Mỹ Phước", status: "busy", workload: 9, workloadMax: 10 },
  { id: "m4", callsign: "OPS-04", initials: "PVB", name: "Anh Bình", fullName: "Phạm Văn Bình", role: "Điều phối Longhaul liên tỉnh", status: "online", workload: 6, workloadMax: 10 },
  { id: "m5", callsign: "OPS-05", initials: "HTL", name: "Chị Lan", fullName: "Hoàng Thị Lan", role: "Account Manager Enterprise (Foxconn, Pegatron)", status: "away", workload: 5, workloadMax: 10 },
  { id: "m6", callsign: "OPS-06", initials: "NMĐ", name: "Anh Đức", fullName: "Nguyễn Minh Đức", role: "BD KCN — Hợp đồng dedicated fleet", status: "online", workload: 4, workloadMax: 10 },
  { id: "m7", callsign: "OPS-07", initials: "VTH", name: "Anh Huy", fullName: "Vũ Thanh Huy", role: "Trưởng nhóm điều vận Hà Nội + Hải Phòng", status: "online", workload: 7, workloadMax: 10 },
  { id: "m8", callsign: "OPS-08", initials: "DTN", name: "Chị Nga", fullName: "Đỗ Thị Nga", role: "Phân tích vận hành — GSV, Fill rate, COGS", status: "offline", workload: 3, workloadMax: 10 },
];

// ====== TASKS — Active 22·05·2026 (Thứ Sáu) — Truck ops thật ======
export const TASKS: OpsTask[] = [
  {
    id: "T-2026-04827",
    channel: "JD",
    channelLabel: "Đối tác KCN — SLA",
    title: "Họp Long Hậu chốt SLA Bulky Q2 — mục tiêu chờ tải <45 phút",
    description: "Họp Ban giám đốc kho Long Hậu, mục tiêu rút idle <45 phút (hiện 58 phút Q1). Chuẩn bị data GSV Q1 + commitment timeline routing v2.",
    assignee: "m1",
    priority: "P0",
    status: "dang_lam",
    deadline: "2026-05-22T14:30:00+07:00",
    estimateHours: 2,
    tags: ["SLA", "Long-Hau", "Bulky", "Q2"],
    createdAt: "2026-05-22T08:32:00+07:00",
    createdBy: "Manager Minh",
    aiConfidence: 0.94,
    aiClassified: true,
  },
  {
    id: "T-2026-04828",
    channel: "JD",
    channelLabel: "Sự cố điều phối",
    title: "Sự cố 3 xe 2.5T trễ chuyến VSIP II — đang chờ phương án backup",
    description: "Xe 51C-789.45, 51C-234.12, 61C-567.89 kẹt trạm cân QL13. Foxconn yêu cầu xe giao trước 11h. Đề xuất: 2 xe Mass tier + 1 xe Core tuyến gần.",
    assignee: "m3",
    priority: "P0",
    status: "bi_chan",
    deadline: "2026-05-22T11:00:00+07:00",
    estimateHours: 1.5,
    tags: ["VSIP-II", "Foxconn", "Sự-cố"],
    createdAt: "2026-05-22T09:14:00+07:00",
    createdBy: "Anh Tuấn",
  },
  {
    id: "T-2026-04829",
    channel: "OKR",
    channelLabel: "Tăng GSV truck KCN +25%",
    title: "Hoàn thiện pitch deck SLP Logistics — dedicated 8 xe 5T/tháng",
    description: "Đối tác SLP Logistics VSIP II. Mục tiêu ký dedicated 8 xe 5T/tháng, GSV dự kiến +14 tỷ Q2-Q3. Deck gồm: SLA cam kết, pricing tier, escalation matrix.",
    assignee: "m6",
    priority: "P0",
    status: "dang_lam",
    deadline: "2026-05-22T17:00:00+07:00",
    estimateHours: 4,
    tags: ["SLP", "VSIP-II", "Dedicated"],
    createdAt: "2026-05-21T16:20:00+07:00",
    createdBy: "Anh Hùng",
  },
  {
    id: "T-2026-04830",
    channel: "OKR",
    channelLabel: "Giảm idle time -20%",
    title: "Triển khai A/B test routing v2 tại hub Sóng Thần (5 hub OKR)",
    description: "Phối hợp Tech team chạy A/B test routing v2 vs v1. KPI: idle time, fill rate, ETA accuracy. Target: -12% idle, +8% fill.",
    assignee: "m2",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-05-23T18:00:00+07:00",
    estimateHours: 6,
    tags: ["Routing-v2", "Song-Than", "AB-test"],
    createdAt: "2026-05-19T10:00:00+07:00",
    createdBy: "Manager Minh",
  },
  {
    id: "T-2026-04831",
    channel: "JD",
    channelLabel: "Báo cáo vận hành",
    title: "Tổng hợp báo cáo tuần 21 — GSV truck, Fill rate, COGS Bulky",
    description: "Báo cáo tuần 21/2026: GSV Bulky/Longhaul/Rental, Fill rate theo hub, COGS Bulky vs target <30%, top 5 KH lớn nhất.",
    assignee: "m8",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-05-22T16:00:00+07:00",
    estimateHours: 3,
    tags: ["Report", "Tuần-21", "GSV"],
    createdAt: "2026-05-22T07:00:00+07:00",
    createdBy: "Hệ thống",
    aiConfidence: 0.98,
    aiClassified: true,
  },
  {
    id: "T-2026-04832",
    channel: "Adhoc",
    channelLabel: "CSKH Enterprise",
    title: "Foxconn Quang Châu yêu cầu đổi tài xế Mass tier xe 4 — thái độ",
    description: "Foxconn KCN Quang Châu Bắc Giang gửi complaint tài xế xe 4 (Mass tier, 38 stop/tháng). Cần thay tài xế Hub tier (>40 stop) trước thứ Hai 26·05.",
    assignee: "m5",
    priority: "P1",
    status: "dang_review",
    deadline: "2026-05-22T18:00:00+07:00",
    estimateHours: 1,
    tags: ["Foxconn", "Quang-Chau", "Mass-tier"],
    createdAt: "2026-05-22T11:42:00+07:00",
    createdBy: "Telegram - Chị Lan",
  },
  {
    id: "T-2026-04833",
    channel: "JD",
    channelLabel: "Audit chất lượng",
    title: "Audit Longhaul HCM → Đà Nẵng tuần 21 — 14 tài xế Pro tier",
    description: "Kiểm tra log GPS, thời gian nghỉ, ETA tuân thủ của 14 tài xế Pro tier (>1M VNĐ/ngày) tuyến HCM-ĐN. Target: 100% nghỉ đủ 30 phút/4 giờ.",
    assignee: "m4",
    priority: "P2",
    status: "can_lam",
    deadline: "2026-05-24T17:00:00+07:00",
    estimateHours: 5,
    tags: ["Audit", "Longhaul", "Pro-tier"],
    createdAt: "2026-05-22T08:00:00+07:00",
    createdBy: "Anh Hùng",
  },
  {
    id: "T-2026-04834",
    channel: "OKR",
    channelLabel: "Mở rộng KV Hải Phòng",
    title: "Khảo sát 3 vị trí mini-hub Hải Phòng — Hồng Bàng",
    description: "Đi khảo sát theo checklist: diện tích >800m², đường ra vào xe 5T, điện 3 pha, cách cảng <8km. Mục tiêu chốt 1 vị trí trước 25·05.",
    assignee: "m7",
    priority: "P2",
    status: "dang_lam",
    deadline: "2026-05-23T12:00:00+07:00",
    estimateHours: 4,
    tags: ["Hai-Phong", "Mini-hub"],
    createdAt: "2026-05-21T14:00:00+07:00",
    createdBy: "Manager Minh",
  },
  {
    id: "T-2026-04835",
    channel: "Adhoc",
    channelLabel: "BD Enterprise",
    title: "Gọi chốt lịch họp Vinamilk — vận chuyển kho Bình Dương → Tây Nguyên",
    assignee: "m6",
    priority: "P2",
    status: "can_lam",
    deadline: "2026-05-22T17:30:00+07:00",
    estimateHours: 0.5,
    tags: ["Vinamilk", "BD", "Longhaul"],
    createdAt: "2026-05-22T10:15:00+07:00",
    createdBy: "Telegram - Anh Đức",
  },
  {
    id: "T-2026-04836",
    channel: "JD",
    channelLabel: "Phân ca tài xế",
    title: "Phân ca tài xế truck ca đêm 22·05 → 23·05 — 168 chuyến HCM",
    description: "Phân ca 168 chuyến Bulky/Longhaul ca đêm. Trong đó: 47 dedicated KCN, 89 Bulky on-demand, 32 Longhaul liên tỉnh.",
    assignee: "m2",
    priority: "P1",
    status: "can_lam",
    deadline: "2026-05-22T20:00:00+07:00",
    estimateHours: 2,
    tags: ["Phân-ca", "Ca-đêm"],
    createdAt: "2026-05-22T13:00:00+07:00",
    createdBy: "Hệ thống tự động",
    aiConfidence: 0.99,
    aiClassified: true,
  },
  {
    id: "T-2026-04837",
    channel: "Adhoc",
    channelLabel: "Đào tạo tài xế",
    title: "Soạn slide onboarding tài xế Mass tier mới Hà Nội (12 người)",
    assignee: "m3",
    priority: "P3",
    status: "can_lam",
    deadline: "2026-05-26T17:00:00+07:00",
    estimateHours: 3,
    tags: ["Training", "Mass-tier", "HAN"],
    createdAt: "2026-05-22T09:30:00+07:00",
    createdBy: "Anh Anh",
  },
  {
    id: "T-2026-04838",
    channel: "OKR",
    channelLabel: "Pilot LTL Q2",
    title: "Chuẩn bị pilot LTL ghép hàng Bình Dương — KCN Mỹ Phước → cảng Cát Lái",
    description: "Pilot LTL (Less Than Truckload) Q2/2026. Mô hình hub-and-spoke, 8 KH SME đầu tiên. Cần: pricing model, SLA, dispatch logic.",
    assignee: "m1",
    priority: "P2",
    status: "can_lam",
    deadline: "2026-05-28T18:00:00+07:00",
    estimateHours: 6,
    tags: ["LTL", "Pilot", "Binh-Duong"],
    createdAt: "2026-05-20T16:00:00+07:00",
    createdBy: "Anh Hùng",
  },
  {
    id: "T-2026-04839",
    channel: "JD",
    channelLabel: "Tài chính & đối soát",
    title: "Đối soát chi phí xăng tuần 21 — 124 tài xế Longhaul",
    description: "Đối soát chi phí xăng 124 tài xế Longhaul. Lưu ý: COGS Bulky đang ở 28.4% (target <30%, dư 1.6 điểm phần trăm).",
    assignee: "m8",
    priority: "P3",
    status: "can_lam",
    deadline: "2026-05-24T17:00:00+07:00",
    estimateHours: 4,
    tags: ["Finance", "COGS", "Longhaul"],
    createdAt: "2026-05-22T08:30:00+07:00",
    createdBy: "Hệ thống",
  },
  {
    id: "T-2026-04840",
    channel: "Adhoc",
    channelLabel: "Đối ngoại — Hợp đồng",
    title: "Review hợp đồng Masan — vận chuyển kho Hậu Giang → Cần Thơ",
    assignee: "m6",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-05-22T18:00:00+07:00",
    estimateHours: 2.5,
    tags: ["Masan", "Hợp-đồng"],
    createdAt: "2026-05-22T09:00:00+07:00",
    createdBy: "Telegram - Anh Đức",
    aiConfidence: 0.74,
    aiClassified: true,
  },
  {
    id: "T-2026-04841",
    channel: "OKR",
    channelLabel: "AI Auto-dispatch",
    title: "Test AI auto-dispatch giờ cao điểm 17-19h Hà Nội",
    description: "Test AI auto-dispatch model v3 ở giờ cao điểm tối Hà Nội. Target: 60% chuyến auto-dispatch (hiện 42%), giảm thời gian phân công <90s.",
    assignee: "m7",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-05-22T19:30:00+07:00",
    estimateHours: 3,
    tags: ["AI-dispatch", "HAN", "Peak"],
    createdAt: "2026-05-22T12:00:00+07:00",
    createdBy: "Anh Huy",
  },
  {
    id: "T-2026-04842",
    channel: "JD",
    channelLabel: "Competitive intel",
    title: "Phân tích Lalamove pricing truck Bulky tháng 5 — capacity check",
    description: "Lalamove vừa giảm giá Bulky 8% tại HCM (theo data từ BD Vinamilk). Cần check tác động lên fill rate Ahamove tuần 21-22.",
    assignee: "m8",
    priority: "P2",
    status: "can_lam",
    deadline: "2026-05-23T16:00:00+07:00",
    estimateHours: 2,
    tags: ["Lalamove", "Pricing", "Bulky"],
    createdAt: "2026-05-22T10:00:00+07:00",
    createdBy: "Manager Minh",
  },
];

// ====== OKR — Q2/2026 — phù hợp Strategic Priorities 2026 ======
export const OKRS: OkrObjective[] = [
  {
    id: "okr1",
    title: "Tăng GSV truck KCN +25% Q2",
    subtitle: "Vết dầu loang — chiều 1: Nội thành → KCN/Liên tỉnh",
    progress: 73,
    target: "GSV truck KCN: 215 → 270 tỷ VNĐ",
    baseline: "215 tỷ Q1",
    current: "248 tỷ (T8/13)",
    risk: "low",
    owner: "OPS-01 · Anh Hùng",
    bsc: "Tài chính",
    keyResults: [
      { id: "kr1", label: "Ký 5 hợp đồng dedicated fleet KCN", progress: 80, target: "4/5 ký" },
      { id: "kr2", label: "Mở 2 mini-hub VSIP II + Mỹ Phước", progress: 50, target: "1/2 mở" },
      { id: "kr3", label: "GSV KCN: 215 → 270 tỷ", progress: 78, target: "248 tỷ" },
    ],
  },
  {
    id: "okr2",
    title: "Giảm idle time tải -20%",
    subtitle: "Tái cấu trúc Supply — routing v2 + 4-tier driver model",
    progress: 45,
    target: "Idle time/chuyến: 58 → 46 phút",
    baseline: "58 phút Q1",
    current: "51 phút",
    risk: "medium",
    owner: "OPS-02 · Anh Tuấn",
    bsc: "Vận hành",
    keyResults: [
      { id: "kr4", label: "Triển khai routing v2 ở 5 hub chính", progress: 60, target: "3/5 hub" },
      { id: "kr5", label: "Idle time trung bình: 58 → 46 phút", progress: 58, target: "51 phút" },
      { id: "kr6", label: "App tài xế v3 adoption rate", progress: 40, target: "60% adopt" },
    ],
  },
  {
    id: "okr3",
    title: "Mở rộng 3 tỉnh tier 1",
    subtitle: "Hải Phòng, Cần Thơ, Đà Nẵng — vết dầu loang chiều 2",
    progress: 88,
    target: "3 tỉnh live truck service trước 30·06",
    baseline: "0 tỉnh có truck",
    current: "Hải Phòng ✓ · Cần Thơ pilot · Đà Nẵng ramp",
    risk: "low",
    owner: "OPS-07 · Anh Huy",
    bsc: "Khách hàng",
    keyResults: [
      { id: "kr7", label: "Setup mini-hub 3 tỉnh tier 1", progress: 90, target: "Hải Phòng ✓ Cần Thơ ✓" },
      { id: "kr8", label: "Recruit 60 truck driver/tỉnh — Hub tier+", progress: 85, target: "152/180" },
      { id: "kr9", label: "Onboard 15 KH enterprise/tỉnh", progress: 90, target: "41/45 KH" },
    ],
  },
  {
    id: "okr4",
    title: "Pilot LTL ghép hàng Q2",
    subtitle: "Niche leadership — dịch vụ mới 2026",
    progress: 38,
    target: "Pilot 100 chuyến LTL/tháng tại Bình Dương",
    baseline: "0 chuyến (chưa có dịch vụ)",
    current: "Đang chuẩn bị, MVP Tech v0",
    risk: "high",
    owner: "OPS-01 · Anh Hùng",
    bsc: "Học hỏi",
    keyResults: [
      { id: "kr10", label: "Pricing model + SLA định nghĩa", progress: 70, target: "v1 draft xong" },
      { id: "kr11", label: "Onboard 8 KH SME đầu tiên", progress: 25, target: "2/8" },
      { id: "kr12", label: "Tech MVP dispatch LTL", progress: 20, target: "30% sprint" },
    ],
  },
  {
    id: "okr5",
    title: "AI auto-dispatch giờ cao điểm 60%",
    subtitle: "AI Automation — giảm chi phí ops, scale dispatch",
    progress: 52,
    target: "60% chuyến truck auto-dispatch peak hour",
    baseline: "42% (Q1)",
    current: "51% (5/22)",
    risk: "medium",
    owner: "OPS-07 · Anh Huy",
    bsc: "Học hỏi",
    keyResults: [
      { id: "kr13", label: "Auto-dispatch peak hour HCM + HAN", progress: 55, target: "51%/60%" },
      { id: "kr14", label: "Thời gian phân công <90s", progress: 70, target: "102s/90s" },
      { id: "kr15", label: "AI chatbot CSKH driver 60%", progress: 30, target: "21% adopt" },
    ],
  },
  {
    id: "okr6",
    title: "COGS Bulky <30% — bảo vệ margin",
    subtitle: "Niche leadership — bảo vệ Bulky bằng SLA + cost discipline",
    progress: 78,
    target: "COGS Bulky <30% suốt Q2",
    baseline: "32.1% Q4/2025",
    current: "28.4% (T21)",
    risk: "low",
    owner: "OPS-08 · Chị Nga",
    bsc: "Tài chính",
    keyResults: [
      { id: "kr16", label: "COGS Bulky <30%", progress: 100, target: "28.4% ✓" },
      { id: "kr17", label: "Incentive truck driver <2.5% GSV", progress: 80, target: "2.1% ✓" },
      { id: "kr18", label: "Take rate truck ≥26%", progress: 65, target: "25.3%" },
    ],
  },
];

// ====== ACTIVITY ======
export const ACTIVITY: ActivityEvent[] = [
  { id: "a1", ts: "14:32", date: "22·05", actor: "OPS-01", action: "đã hoàn thành", target: "T-04825", via: "web" },
  { id: "a2", ts: "14:28", date: "22·05", actor: "Trợ lý điều vận", action: "phân loại 4 task mới từ Telegram", via: "ai" },
  { id: "a3", ts: "14:15", date: "22·05", actor: "OPS-02", action: "phân công OPS-03", target: "T-04828", via: "web" },
  { id: "a4", ts: "14:08", date: "22·05", actor: "Trợ lý điều vận", action: "cảnh báo Lalamove giảm giá Bulky 8% HCM", via: "ai" },
  { id: "a5", ts: "13:50", date: "22·05", actor: "OPS-05", action: "tạo task qua Telegram", target: "T-04832", via: "telegram" },
  { id: "a6", ts: "13:24", date: "22·05", actor: "OPS-03", action: "đánh dấu bị chặn", target: "T-04828", via: "web" },
  { id: "a7", ts: "12:08", date: "22·05", actor: "Trợ lý điều vận", action: "gửi cảnh báo SLA cho 3 task vượt 30 phút", via: "ai" },
  { id: "a8", ts: "11:42", date: "22·05", actor: "OPS-05", action: "tạo task qua Telegram", target: "T-04832", via: "telegram" },
  { id: "a9", ts: "10:15", date: "22·05", actor: "OPS-06", action: "tạo task qua Telegram", target: "T-04835", via: "telegram" },
  { id: "a10", ts: "09:14", date: "22·05", actor: "OPS-02", action: "tạo task sự cố VSIP", target: "T-04828", via: "web" },
  { id: "a11", ts: "08:32", date: "22·05", actor: "Manager Minh", action: "yêu cầu briefing sáng từ AI", via: "ai" },
];

// ====== KPI METRICS — real Ahamove truck data ======
export const TRUCK_KPIS = {
  // Today
  gsvToday: { value: "8.7", unit: "tỷ VNĐ", label: "GSV truck hôm nay", delta: "+12% vs hôm qua", tone: "up" as const },
  ordersToday: { value: 1247, unit: "chuyến", label: "Chuyến truck hôm nay", delta: "+5% vs hôm qua", tone: "up" as const },
  fillRate: { value: "78", unit: "%", label: "Fill rate trung bình", delta: "+3 điểm tuần này", tone: "up" as const },
  cogsBulky: { value: "28.4", unit: "%", label: "COGS Bulky tuần 21", delta: "đạt target <30%", tone: "up" as const },

  // Operational
  activeDrivers: { value: 1847, unit: "/4,412", label: "Tài xế truck đang chạy ca", delta: "42% utilization", tone: "neutral" as const },
  p0Open: { value: 3, unit: "", label: "P0 chưa đóng", delta: "1 bị chặn 47p", tone: "warn" as const },
  capacity: { value: "73", unit: "%", label: "Capacity nhóm điều vận", delta: "5/8 online", tone: "neutral" as const },
  taskActive: { value: 47, unit: "", label: "Task đang chạy", delta: "+5 hôm nay", tone: "up" as const },
};

// ====== COMPETITIVE LANDSCAPE (Nov 2025 — CLAUDE.md) ======
export const COMPETITORS = [
  { name: "Ahamove", sgnShare: 25, sgnDelta: -1, hanShare: 42, hanDelta: 7, strength: "Cost efficiency, Truck dominance", threat: "—" },
  { name: "Grab Express", sgnShare: 34, sgnDelta: -11, hanShare: 32, hanDelta: -3, strength: "Driver density, brand", threat: "HIGH (F&B)" },
  { name: "Be Delivery", sgnShare: 32, sgnDelta: 8, hanShare: 25, hanDelta: -7, strength: "Promo spender", threat: "VERY HIGH" },
  { name: "XanhSM", sgnShare: 8, sgnDelta: 3, hanShare: 10, hanDelta: 3, strength: "EV fleet", threat: "HIGH (Key Acc.)" },
  { name: "Lalamove", sgnShare: null, sgnDelta: null, hanShare: null, hanDelta: null, strength: "Global model, truck direct", threat: "HIGH (Truck)" },
];

// ====== HELPERS ======
export function memberById(id: string): Member | undefined {
  return MEMBERS.find((m) => m.id === id);
}

export function statusLabel(s: TaskStatus): string {
  const map: Record<TaskStatus, string> = {
    cho_xu_ly: "Chờ xử lý",
    can_lam: "Cần làm",
    dang_lam: "Đang làm",
    bi_chan: "Bị chặn",
    dang_review: "Đang review",
    hoan_thanh: "Hoàn thành",
    tam_dung: "Tạm dừng",
  };
  return map[s];
}

export function priorityLabel(p: Priority): string {
  const map: Record<Priority, string> = {
    P0: "P0 · KHẨN CẤP",
    P1: "P1 · CAO",
    P2: "P2 · TRUNG BÌNH",
    P3: "P3 · THẤP",
    P4: "P4 · KHI RẢNH",
  };
  return map[p];
}

export function priorityShort(p: Priority): string {
  const map: Record<Priority, string> = {
    P0: "KHẨN",
    P1: "CAO",
    P2: "TB",
    P3: "THẤP",
    P4: "RẢNH",
  };
  return map[p];
}

export function channelLabel(c: Channel): string {
  const map: Record<Channel, string> = {
    JD: "JD · Việc cố định",
    OKR: "OKR · Mục tiêu quý",
    Adhoc: "Phát sinh",
  };
  return map[c];
}

export function formatDeadline(iso: string): { date: string; time: string; relative: string } {
  const d = new Date(iso);
  const today = new Date("2026-05-22T14:32:00+07:00");
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  const diffMs = d.getTime() - today.getTime();
  const diffH = Math.round(diffMs / (1000 * 60 * 60));
  let relative = "";
  if (diffH < 0) relative = `quá hạn ${Math.abs(diffH)}h`;
  else if (diffH < 1) relative = "sắp đến hạn";
  else if (diffH < 24) relative = `còn ${diffH}h`;
  else relative = `còn ${Math.round(diffH / 24)} ngày`;
  return { date: `${dd}·${mm}`, time: `${hh}:${mi}`, relative };
}

export const TODAY = {
  full: "Thứ Sáu, 22 tháng 5, 2026",
  short: "22·05·2026",
  shortDate: "22·05",
  dayName: "Thứ Sáu",
  greeting: "Chào chiều, Anh Minh",
};
