export type Priority = "P0" | "P1" | "P2" | "P3";
export type TaskStatus = "pending" | "in_progress" | "blocked" | "snoozed" | "done" | "cancelled";
export type UserRole = "manager" | "team_lead" | "employee";
export type MemberLoad = "critical" | "high" | "normal" | "low";

export interface Task {
  id: number;
  summary: string;
  assignee_id: number | null;
  assignee_name: string | null;
  assigned_by: number | null;
  assigner_name: string | null;
  team: string | null;
  priority: Priority;
  category: string;
  status: TaskStatus;
  deadline: string | null;
  block_reason: string | null;
  source: string | null;
  created_at: string;
  completed_at: string | null;
  estimated_minutes: number | null;
  actual_minutes: number | null;
  visibility: string;
}

export interface Member {
  telegram_id: number;
  full_name: string;
  username: string | null;
  role: UserRole;
  role_label: string;
  team: string | null;
  active_count: number;
  done_today: number;
  overdue_count: number;
  blocked_count: number;
  load: MemberLoad;
}

export interface User {
  telegram_id: number;
  full_name: string;
  username: string | null;
  role: UserRole;
  role_label: string;
  team: string | null;
  is_approved: boolean;
  joined_at: string;
}

export interface TeamStats {
  active: number;
  done_today: number;
  overdue: number;
  blocked: number;
  done_week: number;
  overloaded_count: number;
  member_count: number;
  overdue_tasks: Task[];
}

export interface OkrKr {
  id: string;
  label: string;
  baseline?: string;
  target: string;
  weight: string;
}

export interface OkrObjective {
  id: string;
  label: string;
  krs: OkrKr[];
  category: string;
}

export interface OkrAction {
  id: string;
  okr: string;
  kr: string;
  name: string;
  pic: string;
  priority: Priority;
  deadline: string;
  is_overdue: boolean;
  days_left: number | null;
}

export interface OkrData {
  objectives: OkrObjective[];
  actions: OkrAction[];
  north_star: string;
  quarter: string;
  total_actions: number;
  overdue_actions: number;
  p0_actions: number;
}
