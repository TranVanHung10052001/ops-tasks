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

// ─── Delegation Framework ────────────────────────────────────────────────────

export type Grade = "G4" | "G3" | "G2" | "G1" | "ACT-G3";

export interface GradeDefinition {
  id: string;
  label: string;
  title_short: string;
  core_question: string;
  time_split: { strategic: number; tactical: number; operational: number };
  span_of_control: string;
  owns: string[];
  delegates: string[];
  should_not_do: string[];
  escalates_to: string;
}

export interface ResponsibilityArea {
  id: string;
  label: string;
  icon: string;
  G4: string;
  G3: string;
  G2: string;
  G1: string;
}

export interface DecisionAuthorityRow {
  decision: string;
  G4: string;
  G3: string;
  G2: string;
  G1: string;
}

export interface DelegationPrinciple {
  id: string;
  rule: string;
  why: string;
  test: string;
}

export interface GradeMatrixData {
  version: string;
  updated_at: string;
  grades: GradeDefinition[];
  responsibility_areas: ResponsibilityArea[];
  decision_authority_matrix: DecisionAuthorityRow[];
  delegation_principles: DelegationPrinciple[];
}

export interface PlaybookStep {
  n: number;
  title: string;
  owner_grade: string;
  expected_output?: string;
  watch_out?: string;
}

export interface Playbook {
  id: string;
  name: string;
  category: string;
  owner_grade: string;
  support_grade?: string;
  frequency: string;
  estimated_minutes: number;
  okr_links: string[];
  inputs: string[];
  outputs: string[];
  steps: PlaybookStep[];
  escalation?: string;
}

export interface PlaybookCategory {
  id: string;
  label: string;
}

export interface PlaybookList {
  version: string;
  categories: PlaybookCategory[];
  playbooks: Playbook[];
  total: number;
}

export interface MemberScope {
  email: string;
  name: string;
  short_name: string;
  grade: string;
  title: string;
  team: string;
  reports_to: string;
  direct_reports: string[];
  owns: string[];
  do_more: string[];
  do_less: string[];
  delegate_to: Record<string, string>;
  owns_okr: string[];
  playbooks_to_supervise: string[];
  red_flags: string[];
}

export interface DelegationHealthTarget {
  target?: number;
  target_max?: number;
  warning?: number;
  warning_max?: number;
}

export interface DelegationHealth {
  targets: Record<string, DelegationHealthTarget>;
  red_flag_signals: Array<{ member: string; grade: string; flag: string }>;
  principles: DelegationPrinciple[];
  load_by_grade: Record<string, Array<{ name: string; active_count: number; overdue_count: number; done_today: number }>>;
  total_members: number;
}

export interface MemberScopeData {
  version: string;
  members: MemberScope[];
  delegation_health_targets: Record<string, DelegationHealthTarget>;
}

// ─── Sub-agents ──────────────────────────────────────────────────────────────

export type DelegationVerdict =
  | "ok"
  | "should_delegate_down"
  | "should_delegate_up"
  | "should_split"
  | "needs_clarification";

export interface DelegationSubTask {
  sub_task: string;
  owner_grade: string;
  owner_name: string;
}

export interface DelegationCoachResult {
  task_id: number;
  task_summary: string;
  verdict: DelegationVerdict;
  verdict_confidence: number;
  headline: string;
  rationale: string[];
  recommended_owner: { name: string; grade: string; why: string } | null;
  split_suggestion: DelegationSubTask[];
  red_flags: string[];
  playbook_pointer: string | null;
  coaching_question: string | null;
  principles_applied: string[];
}

export type CrisisSeverity = "watch" | "active_crisis" | "p0_crisis";

export interface CrisisAction {
  action: string;
  owner_grade: string;
  owner_name: string;
  deadline_hours?: number;
  deadline_days?: number;
  success_criterion?: string;
  cost_estimate_vnd?: number;
  escalation_if_fail?: string;
  deliverable?: string;
}

export interface CrisisReport {
  trigger: {
    type: string;
    raw_description: string;
    region: string;
    severity_hint?: string;
  };
  severity: CrisisSeverity;
  severity_rationale: string;
  headline: string;
  rca_questions: string[];
  immediate_actions: CrisisAction[];
  structural_actions: CrisisAction[];
  war_room: {
    lead?: string;
    core_team?: string[];
    cadence?: string;
    communication_channel?: string;
  };
  communication_plan: {
    internal_team?: string;
    manager_brief?: string;
    customer_facing?: string;
    escalate_to_c_level?: boolean;
    escalate_when?: string;
  };
  post_mortem_plan: {
    trigger_to_close_crisis?: string;
    post_mortem_deadline_days_after_resolve?: number;
    playbook_update_needed?: boolean;
  };
  playbook_pointer: string | null;
  risks_to_action_plan: string[];
}

export interface CrisisRequest {
  type: string;
  description: string;
  region?: string;
  current_metric?: string;
  current_value?: string;
  target?: string;
  trend?: string;
  duration_days?: number;
  budget_cap?: string;
}

export type ModelTiers = {
  fast: string;
  balanced: string;
  premium: string;
};
