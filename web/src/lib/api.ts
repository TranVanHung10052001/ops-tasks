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
  role: string;
  role_label: string;
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
