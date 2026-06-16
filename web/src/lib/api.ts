import type {
  Task, Member, User, TeamStats, OkrData,
  GradeMatrixData, PlaybookList, Playbook,
  MemberScopeData, MemberScope, DelegationHealth,
  DelegationCoachResult, CrisisReport, CrisisRequest, ModelTiers,
} from "./types";

// Types mirroring bot/api.py serialisers (_fmt_task, _fmt_member)

export interface ApiTask {
  id: number;
  summary: string;
  assignee_id: number | null;
  assignee_name: string | null;
  assigned_by: number | null;
  assigner_name: string | null;
  team: string | null;
  priority: "P0" | "P1" | "P2" | "P3";
  category: string;
  status: "pending" | "in_progress" | "blocked" | "done" | "snoozed" | "cancelled";
  deadline: string | null;
  block_reason: string | null;
  source: string | null;
  created_at: string;
  completed_at: string | null;
  estimated_minutes: number | null;
  actual_minutes: number | null;
  visibility: string;
}

export interface ApiMember {
  telegram_id: number;
  full_name: string;
  username: string | null;
  email: string;
  role: string;
  role_label: string;
  grade: string;
  team: string | null;
  active_count: number;
  done_today: number;
  overdue_count: number;
  blocked_count: number;
  is_preseeded: boolean;   // true = hasn't /start bot yet, no DM will be sent
  load: "critical" | "high" | "normal" | "low";
}

export interface ApiStats {
  active: number;
  done_today: number;
  overdue: number;
  blocked: number;
  done_week: number;
  overloaded_count: number;
  member_count: number;
  overdue_tasks: ApiTask[];
}

export interface ApiOkrKR {
  id: string;
  label: string;
  baseline?: string;
  target: string;
  weight: string;
}

export interface ApiOkrObjective {
  id: string;
  label: string;
  krs: ApiOkrKR[];
  category: string;
  progress_override?: number | null;   // null = not manually set
  current_override?: string | null;
  okr_status?: string;                 // on_track|at_risk|behind|done
}

export interface ApiOkrAction {
  id: string;
  okr: string;
  kr?: string;
  name: string;
  pic: string;
  priority: string;
  deadline: string;
  is_overdue: boolean;
  days_left: number | null;
  status?: string;  // pending|in_progress|done|cancelled
}

export interface ApiOkrResponse {
  objectives: ApiOkrObjective[];
  actions: ApiOkrAction[];
  north_star: string;
  quarter: string;
  total_actions: number;
  overdue_actions: number;
  p0_actions: number;
}

// Performance report per-member (mirrors store.get_member_performance)
export interface ApiPerformance {
  telegram_id: number;
  full_name: string;
  days: number;
  done: number;
  assigned: number;
  completion_pct: number | null;
  on_time: number;
  late: number;
  with_deadline: number;
  on_time_pct: number | null;
  avg_cycle_h: number | null;
  actual_minutes: number;
  p0_done: number;
  p1_done: number;
  active: number;
  overdue: number;
  defer_total: number;
  reminder_total: number;
  declined: number;
}

export interface ApiPerformanceTeam {
  days: number;
  members: ApiPerformance[];
}

// KPI metrics synced from Redash / Google Sheets — all values are strings
export interface ApiMetrics {
  // GSV
  gsv_today_b?: string;           // "8.7" (tỷ VNĐ)
  gsv_wow_pct?: string;           // "12.0" (% week-over-week)
  // Orders
  orders_today?: string;          // "1247"
  orders_wow_pct?: string;        // "9.0"
  // Fill Rate
  fill_rate_core_pct?: string;    // "78.0"
  fill_rate_han_pct?: string;     // "74.0"
  fill_rate_sgn_pct?: string;     // "68.0"
  fill_rate_sme_pct?: string;     // "65.0"  (O1.3 — SME 100-300kg)
  fill_rate_exp_pct?: string;     // "62.0"  (O1.2/O2.1 — KCN BDG/LAN/HPH/EXP)
  fill_rate_vsip_pct?: string;    // "84.0"
  fill_rate_songthan_pct?: string; // "71.0"
  fill_rate_longhau_pct?: string;  // "79.0"
  // COGS
  cogs_bulky_pct?: string;        // "28.4"
  cogs_wow_pct?: string;          // "-0.5" (negative = cost improved)
  // Drivers
  active_drivers?: string;        // "1847"
  driver_station_pct?: string;    // "18"
  driver_core_pct?: string;       // "31"
  driver_hub_pct?: string;        // "28"
  driver_mass_pct?: string;       // "23"
  // Meta
  updated_at?: string;            // ISO datetime of last sync
  [key: string]: string | undefined; // allow extra keys
}

// ── Server-side fetch (used only in Next.js API route handlers) ────────────────

export async function fetchBotApi<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const baseUrl = process.env.BOT_API_URL;
  const secret = process.env.BOT_API_SECRET;

  if (!baseUrl || !secret) {
    throw new Error("BOT_API_URL and BOT_API_SECRET are not configured");
  }

  const res = await fetch(`${baseUrl}${path}`, {
    ...options,
    next: { revalidate: 0 },
    headers: {
      Authorization: `Bearer ${secret}`,
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Bot API ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// ── Client-side fetch (delegation pages, team scope panel) ────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_SECRET = process.env.NEXT_PUBLIC_API_SECRET || "ops-tasks-secret-change-me";

async function req<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_SECRET}`,
      ...options.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path}: ${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  stats: () => req<TeamStats>("/api/stats"),

  team: () => req<Member[]>("/api/team"),

  memberTasks: (userId: number, status?: string) =>
    req<Task[]>(
      `/api/team/${userId}/tasks${status ? `?status=${status}` : ""}`
    ),

  tasks: (params?: {
    status?: string;
    assignee_id?: number;
    priority?: string;
    search?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.assignee_id) q.set("assignee_id", String(params.assignee_id));
    if (params?.priority) q.set("priority", params.priority);
    if (params?.search) q.set("search", params.search);
    return req<{ tasks: Task[]; total: number }>(
      `/api/tasks${q.toString() ? `?${q}` : ""}`
    );
  },

  doneTasks: () => req<Task[]>("/api/tasks/done"),

  taskDetail: (id: number) => req<Task>(`/api/tasks/${id}`),

  updateTask: (
    id: number,
    body: {
      status?: string;
      priority?: string;
      assignee_id?: number;
      deadline?: string;
      block_reason?: string;
    }
  ) =>
    req<{ ok: boolean; task: Task }>(`/api/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  createTask: (body: {
    summary: string;
    assignee_id: number;
    priority?: string;
    deadline?: string;
    category?: string;
  }) =>
    req<{ ok: boolean; task_id: number }>("/api/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  users: () => req<User[]>("/api/users"),

  pendingUsers: () => req<User[]>("/api/users/pending"),

  approveUser: (id: number) =>
    req<{ ok: boolean }>(`/api/users/${id}/approve`, { method: "POST" }),

  setRole: (id: number, role: string, team?: string) =>
    req<{ ok: boolean }>(`/api/users/${id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role, team }),
    }),

  okr: () => req<OkrData>("/api/okr"),

  // ─── Delegation Framework ──────────────────────────────────────────────
  grades: () => req<GradeMatrixData>("/api/grades"),

  playbooks: (params?: { grade?: string; category?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.grade) q.set("grade", params.grade);
    if (params?.category) q.set("category", params.category);
    if (params?.search) q.set("search", params.search);
    return req<PlaybookList>(
      `/api/playbooks${q.toString() ? `?${q}` : ""}`
    );
  },

  playbook: (id: string) => req<Playbook>(`/api/playbooks/${id}`),

  memberScopes: () => req<MemberScopeData>("/api/member-scopes"),

  memberScope: (emailOrName: string) =>
    req<MemberScope>(`/api/member-scopes/${encodeURIComponent(emailOrName)}`),

  delegationHealth: () => req<DelegationHealth>("/api/delegation/health"),

  // ─── Sub-agents ────────────────────────────────────────────────────────
  coachDelegation: (taskId: number) =>
    req<DelegationCoachResult>(`/api/agents/delegation-coach/${taskId}`, {
      method: "POST",
    }),

  crisis: (body: CrisisRequest) =>
    req<CrisisReport>("/api/agents/crisis", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  modelTiers: () => req<ModelTiers>("/api/agents/tiers"),
};
