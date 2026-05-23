// Đài Điều Vận — Ahamove Truck Ops
// Dữ liệu thật: Team member.xlsx + TRUCK 70% OPS PLAN DETAIL.xlsx
// Cập nhật: 22/05/2026

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
  email: string;
  grade: string;
  reportsTo?: string;
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

// ====== MEMBERS — Team Truck Ops anh Huy (11 người thật) ======
// Nguồn: Team member.xlsx · G4 → G1 · Line manager: Lê Hữu Chung
export const MEMBERS: Member[] = [
  {
    id: "m0",
    callsign: "OPS-00",
    initials: "LQH",
    name: "Anh Huy",
    fullName: "Lê Quang Huy",
    email: "huyle@ahamove.com",
    grade: "G4",
    role: "Giám sát Vận hành Xe Tải · Toàn bộ NW",
    status: "online",
    workload: 5,
    workloadMax: 10,
  },
  {
    id: "m1",
    callsign: "OPS-01",
    initials: "LHT",
    name: "Anh Thống",
    fullName: "Lê Hoàng Nhất Thống",
    email: "thonglhn@ahamove.com",
    grade: "G3",
    reportsTo: "m0",
    role: "Trưởng nhóm Vận hành HAN · Bulky/GXT/Supply",
    status: "busy",
    workload: 9,
    workloadMax: 10,
  },
  {
    id: "m2",
    callsign: "OPS-02",
    initials: "LTH",
    name: "Chị Thương",
    fullName: "Lưu Thị Hoài Thương",
    email: "thuonglth@ahamove.com",
    grade: "G2",
    reportsTo: "m1",
    role: "Chuyên viên Vận hành HAN · FR & Capacity",
    status: "online",
    workload: 7,
    workloadMax: 10,
  },
  {
    id: "m3",
    callsign: "OPS-03",
    initials: "PPT",
    name: "Anh Toàn",
    fullName: "Phạm Phú Toàn",
    email: "toanpt@ahamove.com",
    grade: "G1",
    reportsTo: "m1",
    role: "Nhân viên Vận hành HAN · Driver đội nhóm",
    status: "online",
    workload: 6,
    workloadMax: 10,
  },
  {
    id: "m4",
    callsign: "OPS-04",
    initials: "TQT",
    name: "Anh Thành",
    fullName: "Trần Quốc Thành",
    email: "thanhtq@ahamove.com",
    grade: "ACT-G3",
    reportsTo: "m0",
    role: "Chuyên viên Vận hành SGN · Bulky/GXT",
    status: "online",
    workload: 7,
    workloadMax: 10,
  },
  {
    id: "m5",
    callsign: "OPS-05",
    initials: "TNP",
    name: "Anh Phú",
    fullName: "Trần Ngọc Phú",
    email: "phutn@ahamove.com",
    grade: "G1",
    reportsTo: "m4",
    role: "Nhân viên Vận hành SGN · FR & Policy",
    status: "online",
    workload: 6,
    workloadMax: 10,
  },
  {
    id: "m6",
    callsign: "OPS-06",
    initials: "PDC",
    name: "Anh Chiến",
    fullName: "Phạm Đình Chiến",
    email: "chienpd@ahamove.com",
    grade: "G2",
    reportsTo: "m4",
    role: "Chuyên viên Vận hành SGN · Backlog & Inactive",
    status: "online",
    workload: 7,
    workloadMax: 10,
  },
  {
    id: "m7",
    callsign: "OPS-07",
    initials: "LVK",
    name: "Anh Khánh",
    fullName: "Lê Văn Khánh",
    email: "khanhlv@ahamove.com",
    grade: "G3",
    reportsTo: "m0",
    role: "Trưởng nhóm B2B & EXP tỉnh · Toàn quốc",
    status: "online",
    workload: 7,
    workloadMax: 10,
  },
  {
    id: "m8",
    callsign: "OPS-08",
    initials: "NTK",
    name: "Chị Ngân",
    fullName: "Nguyễn Thị Kim Ngân",
    email: "Nganntk1@ahamove.com",
    grade: "G1",
    reportsTo: "m7",
    role: "Điều phối Vận hành B2B · Chi phí & Hợp đồng",
    status: "away",
    workload: 5,
    workloadMax: 10,
  },
  {
    id: "m9",
    callsign: "OPS-09",
    initials: "NDK",
    name: "Anh Khâm",
    fullName: "Nguyễn Duy Khâm",
    email: "khamnd@ahamove.com",
    grade: "G2",
    reportsTo: "m7",
    role: "Chuyên viên EXP tỉnh · Tuyển dụng driver & LAN Hub",
    status: "busy",
    workload: 9,
    workloadMax: 10,
  },
  {
    id: "m10",
    callsign: "OPS-10",
    initials: "TVH",
    name: "Anh Hùng",
    fullName: "Trần Văn Hùng",
    email: "hungtv@ahamove.com",
    grade: "G1",
    reportsTo: "m7",
    role: "Nhân viên Vận hành B2B · Vendor & B2C",
    status: "online",
    workload: 6,
    workloadMax: 10,
  },
];

// ====== TASKS — Active 22·05·2026 · Từ OPS PLAN DETAIL Q2/2026 ======
export const TASKS: OpsTask[] = [
  {
    id: "T-2026-02160",
    channel: "OKR",
    channelLabel: "O2.1 · LAN Hub Go-live",
    title: "Mini-hub Long An Go-live — OVERDUE 15/05, đang bị chặn",
    description: "Hub setup xong. Cần: onboard batch driver đầu tiên + certified. KPI Day-7: ≥5 orders/ngày, FR ≥50%. HARD DEADLINE 15/05 đã qua 7 ngày.",
    assignee: "m9",
    priority: "P0",
    status: "bi_chan",
    deadline: "2026-05-15T23:59:00+07:00",
    estimateHours: 8,
    tags: ["LAN", "Mini-hub", "Go-live", "OVERDUE"],
    createdAt: "2026-04-01T09:00:00+07:00",
    createdBy: "OKR Q2/2026",
  },
  {
    id: "T-2026-03210",
    channel: "OKR",
    channelLabel: "O3.2 · COGS GXT 80K→75K",
    title: "COGS GXT Breakdown Analysis — P0 chưa bắt đầu",
    description: "Pull COGS GXT theo từng dòng: driver cost / fuel / platform fee / handling. Identify top 3 cost driver >70% COGS. Benchmark vs GHN. Output: waterfall chart. ⚠️ Target 75K — không phải 70K.",
    assignee: "m1",
    priority: "P0",
    status: "can_lam",
    deadline: "2026-05-23T17:00:00+07:00",
    estimateHours: 6,
    tags: ["COGS", "GXT", "Analysis", "URGENT"],
    createdAt: "2026-04-20T09:00:00+07:00",
    createdBy: "OPS Plan Q2",
  },
  {
    id: "T-2026-03113",
    channel: "OKR",
    channelLabel: "O3.1 · 1st PU On-Time 80%",
    title: "Config SLA pickup window GHN/GXT tại Hà Nội",
    description: "SGN đã xong. Tuần 11/05 config HAN. Pickup window: AM (8-12h) / PM (13-18h) / Evening (18-21h). Hoàn thiện Blog GXT gửi phòng ban liên quan.",
    assignee: "m1",
    priority: "P0",
    status: "dang_lam",
    deadline: "2026-05-25T18:00:00+07:00",
    estimateHours: 4,
    tags: ["SLA", "HAN", "GHN", "GXT", "Pickup-window"],
    createdAt: "2026-05-11T09:00:00+07:00",
    createdBy: "OPS Plan Q2",
  },
  {
    id: "T-2026-03120",
    channel: "OKR",
    channelLabel: "O3.1 · 1st PU On-Time 80%",
    title: "Convert tài xế Bulky sang Marketplace — training + LMS",
    description: "Add service cho old driver. Training mới (LMS đang làm lại, Chiến hỗ trợ). Work với QM: top 3 lý do ban driver. FC Bulky HAN đang revised. Target pre-assign rate ≥90%.",
    assignee: "m1",
    priority: "P0",
    status: "dang_lam",
    deadline: "2026-05-30T17:00:00+07:00",
    estimateHours: 12,
    tags: ["Bulky", "Marketplace", "Training", "LMS"],
    createdAt: "2026-04-15T09:00:00+07:00",
    createdBy: "OPS Plan Q2",
  },
  {
    id: "T-2026-02150",
    channel: "OKR",
    channelLabel: "O2.1 · Driver Recruitment LAN",
    title: "Tuyển dụng 30 tài xế Long An — deadline 27/05",
    description: "Kênh: Zalo group địa phương + driver network SGN referral. Referral bonus 200K/driver. Training: SOP + app + safety + mini-hub check-in. Target: 25 driver active tuần 1.",
    assignee: "m9",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-05-27T17:00:00+07:00",
    estimateHours: 16,
    tags: ["LAN", "Tuyển-dụng", "Driver", "EXP"],
    createdAt: "2026-04-28T09:00:00+07:00",
    createdBy: "OKR Q2/2026",
  },
  {
    id: "T-2026-02130",
    channel: "OKR",
    channelLabel: "O2.1 · KCN Supply",
    title: "KCN Rental Policy — Research pricing + SOP v1",
    description: "Research: KCN Rental model — pricing, SLA, vehicle type. Build policy: điều kiện thuê, time slots, cancellation. SOP v1: từ khi Sales sign deal → Ops execute. Align Khâm (BDG Go-live). Present cho A Chung + Ops team.",
    assignee: "m10",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-05-30T17:00:00+07:00",
    estimateHours: 8,
    tags: ["KCN", "Rental", "Policy", "SOP", "B2B"],
    createdAt: "2026-05-01T09:00:00+07:00",
    createdBy: "Khánh Lê Văn",
  },
  {
    id: "T-2026-02140",
    channel: "OKR",
    channelLabel: "O2.1 · LAN Hub Lease",
    title: "Long An Hub — Chốt vị trí + ký hợp đồng thuê",
    description: "Map demand hotspot: Long Hậu, Tân Kiên. Đánh giá 2–3 location: gần KCN / chợ đầu mối / quốc lộ 1A. Negotiate thuê short-term 3 tháng pilot. Ký HĐ + setup cơ bản.",
    assignee: "m9",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-06-30T17:00:00+07:00",
    estimateHours: 20,
    tags: ["LAN", "Hub", "Lease", "EXP"],
    createdAt: "2026-04-15T09:00:00+07:00",
    createdBy: "OKR Q2/2026",
  },
  {
    id: "T-2026-02210",
    channel: "OKR",
    channelLabel: "O2.2 · Pilot Shift Model",
    title: "MiniHUB Shift Model Design — 3 ca SGN + HAN",
    description: "Định nghĩa 3 ca: Sáng 9-11h / Chiều 13-15h / Tối 16-20h. Commitment: ≥4 ca/tuần, ≥2 tuần liên tục. Target: 50 driver SGN + 50 driver HAN enrolled.",
    assignee: "m1",
    priority: "P1",
    status: "can_lam",
    deadline: "2026-06-15T17:00:00+07:00",
    estimateHours: 10,
    tags: ["Shift-model", "MiniHub", "SGN", "HAN", "Supply"],
    createdAt: "2026-05-10T09:00:00+07:00",
    createdBy: "OPS Plan Q2",
  },
  {
    id: "T-2026-01110",
    channel: "JD",
    channelLabel: "JD · FR Report HAN",
    title: "FR Weekly HAN tuần 21 — Tổng hợp + phân tích insight",
    description: "Báo cáo tổng quan FR N-1 & MTD. Phân tích Fail KPI: tài xế / khu vực / bộ lý do chiếm tỷ trọng cao. Update Order Creation / Vol Success / Backlog theo quận.",
    assignee: "m2",
    priority: "P1",
    status: "dang_lam",
    deadline: "2026-05-22T17:00:00+07:00",
    estimateHours: 3,
    tags: ["FR", "Report", "HAN", "Tuần-21"],
    createdAt: "2026-05-22T08:00:00+07:00",
    createdBy: "Hệ thống",
    aiConfidence: 0.97,
    aiClassified: true,
  },
  {
    id: "T-2026-04220",
    channel: "OKR",
    channelLabel: "O4.2 · Vehicle Classification 60%",
    title: "Vehicle Classification Survey — tiến độ Q2",
    description: "Field verify + data update. Thống assign lại Chiến để report. Target: 60% active fleet classified Q2. Chú ý active quý 60% update là được.",
    assignee: "m6",
    priority: "P2",
    status: "dang_lam",
    deadline: "2026-06-30T17:00:00+07:00",
    estimateHours: 6,
    tags: ["Vehicle", "Classification", "Tech", "O4"],
    createdAt: "2026-05-01T09:00:00+07:00",
    createdBy: "Thống Lê Hoàng Nhất",
  },
  {
    id: "T-2026-05221",
    channel: "JD",
    channelLabel: "JD · Backlog 4h SGN",
    title: "Backlog clearing 4h SGN — gán đơn ca chiều 22/05",
    description: "Hàng ngày chạy backlog → gán đơn cho tài xế đảm bảo clear backlog (nhất là 4h). Làm việc với QM hỗ trợ case mở khoá / huỷ đơn.",
    assignee: "m6",
    priority: "P1",
    status: "can_lam",
    deadline: "2026-05-22T20:00:00+07:00",
    estimateHours: 2,
    tags: ["Backlog", "4h", "SGN", "Daily"],
    createdAt: "2026-05-22T13:00:00+07:00",
    createdBy: "Hệ thống",
    aiConfidence: 0.99,
    aiClassified: true,
  },
  {
    id: "T-2026-05222",
    channel: "JD",
    channelLabel: "JD · Retention SGN",
    title: "Update Retention data tài xế SGN — trend tuần 21",
    description: "Update dữ liệu Retention hàng ngày. Nắm bắt trend tăng giảm tài xế SGN. Báo cáo tỉ lệ contribution đội nhóm / mass về total volume.",
    assignee: "m5",
    priority: "P2",
    status: "can_lam",
    deadline: "2026-05-22T18:00:00+07:00",
    estimateHours: 1.5,
    tags: ["Retention", "SGN", "Daily", "Driver"],
    createdAt: "2026-05-22T09:00:00+07:00",
    createdBy: "Hệ thống",
    aiConfidence: 0.96,
    aiClassified: true,
  },
  {
    id: "T-2026-05223",
    channel: "JD",
    channelLabel: "JD · B2B Cost Control",
    title: "Bảng kê chi phí B2B tuần 21 — đối soát vendor",
    description: "Lập bảng kê kiểm soát chi phí B2B hàng ngày. Đảm bảo chính xác và đúng hạn thanh toán với team kế toán. Update phụ lục giá nếu có thay đổi.",
    assignee: "m8",
    priority: "P2",
    status: "can_lam",
    deadline: "2026-05-22T17:00:00+07:00",
    estimateHours: 2,
    tags: ["B2B", "Cost", "Vendor", "Finance"],
    createdAt: "2026-05-22T08:00:00+07:00",
    createdBy: "Khánh Lê Văn",
  },
  {
    id: "T-2026-05224",
    channel: "JD",
    channelLabel: "JD · Tuyển dụng HAN",
    title: "Lên kế hoạch tuyển dụng đội nhóm HAN tuần 22-23",
    description: "Làm việc với team Growth. Đảm bảo chỉ số tuyển dụng tài xế mới. Hỗ trợ case dán decal theo từng chiến dịch. Báo cáo contribution đội nhóm HAN.",
    assignee: "m3",
    priority: "P2",
    status: "can_lam",
    deadline: "2026-05-24T17:00:00+07:00",
    estimateHours: 3,
    tags: ["Tuyển-dụng", "HAN", "Growth", "Driver"],
    createdAt: "2026-05-22T09:00:00+07:00",
    createdBy: "Thống Lê Hoàng Nhất",
  },
  {
    id: "T-2026-03220",
    channel: "OKR",
    channelLabel: "O3.2 · Đồng giá GXT",
    title: "Tạo dịch vụ Đồng giá GXT — đảm bảo COGS ≤75K",
    description: "Tạo dịch vụ đồng giá GXT (NW-S9). Đàm phán lại HĐ 3P (GHN Bulky): giảm ≥6.25% cost/đơn. Leverage: volume growth Q2 vs Q1 (+30%). Tiered pricing: volume commitment → better rate.",
    assignee: "m4",
    priority: "P1",
    status: "can_lam",
    deadline: "2026-05-31T17:00:00+07:00",
    estimateHours: 8,
    tags: ["GXT", "Đồng-giá", "3P", "COGS", "SGN"],
    createdAt: "2026-05-15T09:00:00+07:00",
    createdBy: "OPS Plan Q2",
  },
];

// ====== OKR — Q2/2026 · Từ TRUCK 70% OPS PLAN DETAIL.xlsx ======
// North Star: O5.KR5.1 — GSV Non-Bulky 70% YoY: 69B → 117.3B
export const OKRS: OkrObjective[] = [
  {
    id: "o1",
    title: "O1 · Fill Rate — Core ≥68% | EXP ≥65% | LH ≥70% | SME ≥65%",
    subtitle: "Nền tảng tăng trưởng 70% Non-Bulky · Company O5.KR5.2 + O1.KR1.3",
    progress: 42,
    target: "FR Core 60.5%→68% | FR LH ≥70% | FR SME 17%→65%",
    baseline: "FR Core 60.5% · FR SME 17% (Q1/2026)",
    current: "FR Core ~62% · FR SME gap lớn · FR LH đang cải thiện",
    risk: "medium",
    owner: "OPS-01 Thống + OPS-02 Thương (HAN) · OPS-04 Thành + OPS-05 Phú (SGN)",
    bsc: "Khách hàng",
    keyResults: [
      { id: "kr-o1-1", label: "FR Core HAN ≥68%", progress: 58, target: "60.5%→68%" },
      { id: "kr-o1-2", label: "FR Core SGN ≥68%", progress: 52, target: "60.5%→68%" },
      { id: "kr-o1-3", label: "FR LH ≥70% (O1.KR1.3)", progress: 55, target: "50 Moving crew" },
      { id: "kr-o1-4", label: "FR SME 100-300kg ≥65%", progress: 12, target: "17%→65% (critical)" },
    ],
  },
  {
    id: "o2",
    title: "O2 · Supply & Retention — LAN Live | Shift Pilot | Decal 1,900",
    subtitle: "Driver retention D30 65%→70% · Company O2.KR2.1/2.2/2.3",
    progress: 38,
    target: "LAN Hub live 15/05 | 50+50 driver shift pilot | Decal 1,600→1,900",
    baseline: "Chưa có hub LAN · Chưa có shift model · 1,600 decal T4",
    current: "LAN OVERDUE 15/05 ⚠️ · Shift model chưa design · Decal đang push",
    risk: "high",
    owner: "OPS-09 Khâm (LAN) · OPS-01 Thống (Shift) · OPS NW (Decal)",
    bsc: "Vận hành",
    keyResults: [
      { id: "kr-o2-1", label: "Mini-hub LAN live ≥5 orders/ngày", progress: 30, target: "DEADLINE 15/05 — OVERDUE" },
      { id: "kr-o2-2", label: "Pilot Shift Model 50 SGN + 50 HAN", progress: 8, target: "100 driver enrolled" },
      { id: "kr-o2-3", label: "Decal xác minh 1,600→1,900", progress: 68, target: "1,900 driver" },
    ],
  },
  {
    id: "o3",
    title: "O3 · Service & Cost — 1st PU 80% | COGS GXT 75K | Distribution 4.5B",
    subtitle: "Nâng cao chất lượng · Company O3.KR3.1/3.2/3.3",
    progress: 48,
    target: "1st PU On-Time 47.6%→80% · COGS GXT 80K→75K · Distribution pilot ≥4.5B",
    baseline: "1st PU 47.6% · COGS GXT 80K (Q1/2026)",
    current: "SLA SGN done ✓ · HAN config đang làm · COGS analysis chưa bắt đầu ⚠️",
    risk: "medium",
    owner: "OPS-01 Thống (Service) · OPS + BA (COGS) · BA + BD Corp (Distribution)",
    bsc: "Khách hàng",
    keyResults: [
      { id: "kr-o3-1", label: "1st PU On-Time Bulky SGN ≥80%", progress: 72, target: "SLA redesign SGN ✓" },
      { id: "kr-o3-2", label: "1st PU On-Time Bulky HAN ≥80%", progress: 28, target: "Config tuần này" },
      { id: "kr-o3-3", label: "COGS GXT/kiện 80K→75K (-6.25%)", progress: 5, target: "Analysis P0 chưa bắt đầu ⚠️" },
      { id: "kr-o3-4", label: "Distribution model pilot ≥4.5B", progress: 10, target: "BA design phase" },
    ],
  },
  {
    id: "o4",
    title: "O4 · Tech & Growth — Dynamic Pricing | Classification 60% | AI Bot 40%",
    subtitle: "Nền tảng công nghệ (Khát vọng) · Company O4.KR4.1/4.2/4.3",
    progress: 27,
    target: "Dynamic Pricing 100% research · Vehicle classification 60% · AI Bot 40% auto-reports",
    baseline: "0% tất cả (Q1/2026)",
    current: "Pricing research in progress · Classification survey Chiến đang làm · Bot design Apr W3",
    risk: "medium",
    owner: "BA/Yến (Pricing + AI Bot) · OPS-06 Chiến (Classification) · OPS Support",
    bsc: "Học hỏi",
    keyResults: [
      { id: "kr-o4-1", label: "Dynamic Pricing 0%→100% research", progress: 30, target: "100% research done" },
      { id: "kr-o4-2", label: "Vehicle classification 0%→60%", progress: 35, target: "60% fleet classified" },
      { id: "kr-o4-3", label: "AI Bot OPS report 0%→40%", progress: 18, target: "40% auto-reports" },
    ],
  },
];

// ====== ACTIVITY — Real callsign 22·05·2026 ======
export const ACTIVITY: ActivityEvent[] = [
  { id: "a1", ts: "14:32", date: "22·05", actor: "OPS-09", action: "cập nhật tiến độ tuyển dụng LAN", target: "T-2026-02150", via: "telegram" },
  { id: "a2", ts: "14:15", date: "22·05", actor: "Trợ lý điều vận", action: "cảnh báo Mini-hub LAN overdue 7 ngày", via: "ai" },
  { id: "a3", ts: "13:50", date: "22·05", actor: "OPS-02", action: "nộp báo cáo FR HAN tuần 21", target: "T-2026-01110", via: "web" },
  { id: "a4", ts: "13:24", date: "22·05", actor: "OPS-06", action: "update backlog 4h SGN ca chiều", target: "T-2026-05221", via: "telegram" },
  { id: "a5", ts: "12:08", date: "22·05", actor: "OPS-01", action: "đánh dấu COGS Analysis là P0 urgent", target: "T-2026-03210", via: "web" },
  { id: "a6", ts: "11:42", date: "22·05", actor: "OPS-10", action: "tạo task KCN Rental Policy qua Telegram", target: "T-2026-02130", via: "telegram" },
  { id: "a7", ts: "10:15", date: "22·05", actor: "Trợ lý điều vận", action: "phân loại 3 task mới từ Telegram", via: "ai" },
  { id: "a8", ts: "09:30", date: "22·05", actor: "OPS-00", action: "giao việc KCN Rental Policy", target: "T-2026-02130", via: "web" },
  { id: "a9", ts: "08:45", date: "22·05", actor: "OPS-09", action: "báo trễ deadline LAN Go-live", target: "T-2026-02160", via: "telegram" },
  { id: "a10", ts: "08:00", date: "22·05", actor: "Trợ lý điều vận", action: "gửi briefing sáng — 2 task P0 overdue", via: "ai" },
];

// ====== KPI METRICS — Thật từ Ahamove Truck Ops ======
export const TRUCK_KPIS = {
  gsvToday: { value: "8.7", unit: "tỷ VNĐ", label: "GSV truck hôm nay", delta: "+12% vs hôm qua", tone: "up" as const },
  ordersToday: { value: 1247, unit: "chuyến", label: "Chuyến truck hôm nay", delta: "+5% vs hôm qua", tone: "up" as const },
  fillRate: { value: "62", unit: "%", label: "FR Core trung bình", delta: "target 68% — còn 6pp", tone: "warn" as const },
  cogsBulky: { value: "28.4", unit: "%", label: "COGS Bulky tuần 21", delta: "đạt target <30%", tone: "up" as const },
  activeDrivers: { value: 1847, unit: "/4,412", label: "Tài xế truck đang chạy ca", delta: "42% utilization", tone: "neutral" as const },
  p0Open: { value: 3, unit: "", label: "P0 chưa đóng", delta: "1 overdue 7 ngày", tone: "warn" as const },
  capacity: { value: "82", unit: "%", label: "Capacity nhóm điều vận", delta: "9/11 online", tone: "neutral" as const },
  taskActive: { value: 15, unit: "", label: "Task đang tracking", delta: "2 OVERDUE", tone: "warn" as const },
};

// ====== COMPETITIVE LANDSCAPE (Nov 2025) ======
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
  const today = new Date();
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

function _buildToday() {
  const now = new Date();
  const dd = String(now.getDate()).padStart(2, "0");
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const yyyy = now.getFullYear();
  const days = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];
  const dayName = days[now.getDay()];
  const months = ["","tháng 1","tháng 2","tháng 3","tháng 4","tháng 5","tháng 6",
                  "tháng 7","tháng 8","tháng 9","tháng 10","tháng 11","tháng 12"];
  const hour = now.getHours();
  const greeting = hour < 12 ? "Chào sáng" : hour < 18 ? "Chào chiều" : "Chào tối";
  return {
    full: `${dayName}, ${dd} ${months[now.getMonth() + 1]}, ${yyyy}`,
    short: `${dd}·${mm}·${yyyy}`,
    shortDate: `${dd}·${mm}`,
    dayName,
    greeting: `${greeting}, Anh Huy`,
  };
}
export const TODAY = _buildToday();
