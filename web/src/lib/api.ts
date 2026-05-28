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
