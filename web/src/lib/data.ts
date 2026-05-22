import { fetchBotApi, ApiTask, ApiMember, ApiStats, ApiOkrResponse, ApiOkrAction, ApiMetrics } from "./api";
import {
  MEMBERS, OKRS,
  OpsTask, Member, OkrObjective,
  TaskStatus, Channel, Priority,
} from "./mock";

// ── Adapters ──────────────────────────────────────────────────────────────────

function statusToTaskStatus(s: ApiTask["status"]): TaskStatus {
  const map: Record<ApiTask["status"], TaskStatus> = {
    pending: "can_lam",
    in_progress: "dang_lam",
    blocked: "bi_chan",
    done: "hoan_thanh",
    snoozed: "tam_dung",
    cancelled: "hoan_thanh",
  };
  return map[s] ?? "can_lam";
}

function categoryToChannel(cat: string): Channel {
  if (cat === "okr") return "OKR";
  if (!cat || cat === "other" || cat === "adhoc") return "Adhoc";
  return "JD";
}

const CHANNEL_LABELS: Record<Channel, string> = {
  JD: "JD · Việc cố định",
  OKR: "OKR · Mục tiêu quý",
  Adhoc: "Phát sinh",
};

export function apiTaskToOpsTask(t: ApiTask): OpsTask {
  const channel = categoryToChannel(t.category);
  return {
    id: `T-${t.id.toString().padStart(5, "0")}`,
    channel,
    channelLabel: CHANNEL_LABELS[channel],
    title: t.summary,
    description: t.block_reason ?? undefined,
    assignee: t.assignee_id ? `m${t.assignee_id}` : "m0",
    priority: (["P0", "P1", "P2", "P3"].includes(t.priority) ? t.priority : "P2") as Priority,
    status: statusToTaskStatus(t.status),
    deadline: t.deadline ?? new Date(Date.now() + 86_400_000).toISOString(),
    estimateHours: t.estimated_minutes ? t.estimated_minutes / 60 : 2,
    tags: [t.category, t.team ?? ""].filter(Boolean),
    createdAt: t.created_at ?? new Date().toISOString(),
    createdBy: t.source ?? t.assigner_name ?? "Bot",
  };
}

export function apiMemberToMember(m: ApiMember, index: number): Member {
  const parts = m.full_name.trim().split(" ");
  const last = parts[parts.length - 1];
  const first = parts[0];
  const initials = (
    first[0] + (parts[1]?.[0] ?? "") + (parts.length > 2 ? last[0] : "")
  ).toUpperCase().slice(0, 3);
  const workload = ({ critical: 9, high: 7, normal: 5, low: 2 } as Record<string, number>)[m.load] ?? m.active_count;
  const statusMap: Record<ApiMember["load"], Member["status"]> = {
    critical: "busy", high: "online", normal: "online", low: "away",
  };
  return {
    id: `m${m.telegram_id}`,
    callsign: `OPS-${String(index).padStart(2, "0")}`,
    initials,
    name: parts.length > 2 ? `${first} ${last}` : m.full_name,
    fullName: m.full_name,
    email: m.username ? `${m.username}@ahamove.com` : "",
    grade: m.role ?? "G1",
    role: m.role_label || m.role,
    status: statusMap[m.load] ?? "online",
    workload,
    workloadMax: 10,
  };
}

// ── Server-side fetchers with mock fallback ───────────────────────────────────

export async function getTasksData(): Promise<OpsTask[]> {
  try {
    const res = await fetchBotApi<{ tasks: ApiTask[]; total: number }>("/api/tasks?limit=200");
    return res.tasks.map(apiTaskToOpsTask);
  } catch {
    return []; // no mock — show empty state until bot is connected
  }
}

export async function getMembersData(): Promise<Member[]> {
  try {
    const members = await fetchBotApi<ApiMember[]>("/api/team");
    return members.map((m, i) => apiMemberToMember(m, i));
  } catch {
    return MEMBERS;
  }
}

export async function getStatsData(): Promise<ApiStats> {
  try {
    return await fetchBotApi<ApiStats>("/api/stats");
  } catch {
    return {
      active: 0,
      done_today: 0,
      overdue: 0,
      blocked: 0,
      done_week: 0,
      overloaded_count: 0,
      member_count: MEMBERS.length,
      overdue_tasks: [],
    };
  }
}

export async function getMetricsData(): Promise<ApiMetrics> {
  try {
    return await fetchBotApi<ApiMetrics>("/api/metrics");
  } catch {
    return {}; // no mock — show "—" until Redash / manual sync is configured
  }
}

// Fallback mock actions (subset of api.py ACTIONS, reflects real Q2/2026 state)
const MOCK_OKR_ACTIONS: ApiOkrAction[] = [
  { id: "1.1.2", okr: "O1.1", name: "Driver Reactivation Campaign",       pic: "OPS SGN/HAN",      priority: "P0", deadline: "2026-04-30", is_overdue: true,  days_left: -22 },
  { id: "1.3.1", okr: "O1.3", name: "RCA FR SME 100–300kg",               pic: "OPS + Product",    priority: "P0", deadline: "2026-05-18", is_overdue: true,  days_left: -4  },
  { id: "1.3.2", okr: "O1.3", name: "Relaunch Pooling SME 100–300kg",     pic: "OPS SGN/HAN",      priority: "P0", deadline: "2026-05-22", is_overdue: false, days_left: 0   },
  { id: "1.2.4", okr: "O1.2", name: "LH Supply Activation",               pic: "OPS HAN",          priority: "P0", deadline: "2026-05-31", is_overdue: false, days_left: 9   },
  { id: "2.1.5", okr: "O2.1", name: "Driver Recruitment LAN (30 driver)", pic: "OPS EXP · Khâm",   priority: "P1", deadline: "2026-05-27", is_overdue: false, days_left: 5   },
  { id: "2.1.6", okr: "O2.1", name: "Mini-hub LAN Go-live",               pic: "OPS EXP · Khâm",   priority: "P1", deadline: "2026-05-15", is_overdue: true,  days_left: -7  },
  { id: "2.2.4", okr: "O2.2", name: "HAN Shift Pilot Launch",             pic: "OPS HAN · Thống",  priority: "P1", deadline: "2026-05-15", is_overdue: true,  days_left: -7  },
  { id: "2.4.1", okr: "O2.4", name: "Driver Churn Analysis",              pic: "OPS + BA",          priority: "P0", deadline: "2026-05-07", is_overdue: true,  days_left: -15 },
  { id: "3.1.2", okr: "O3.1", name: "Convert active Bulky → Marketplace", pic: "OPS Supply",        priority: "P0", deadline: "2026-04-30", is_overdue: true,  days_left: -22 },
  { id: "3.1.3", okr: "O3.1", name: "Config SLA Pickup Window HAN",       pic: "OPS · Thống",       priority: "P0", deadline: "2026-05-25", is_overdue: false, days_left: 3   },
  { id: "3.2.1", okr: "O3.2", name: "COGS Line-item Breakdown GXT",       pic: "OPS + BA",          priority: "P0", deadline: "2026-04-20", is_overdue: true,  days_left: -32 },
  { id: "3.2.2", okr: "O3.2", name: "GXT Đồng giá + 3P Renegotiation",    pic: "Thống + OPS",       priority: "P0", deadline: "2026-04-30", is_overdue: true,  days_left: -22 },
  { id: "3.4.2", okr: "O3.4", name: "BD Pilot Signing ≥3 Corp Clients",   pic: "BD Corp",           priority: "P0", deadline: "2026-05-31", is_overdue: false, days_left: 9   },
  { id: "4.3.1", okr: "O4.3", name: "Data Model + Bot Architecture",      pic: "BA · Tiến Thiều V", priority: "P1", deadline: "2026-04-20", is_overdue: true,  days_left: -32 },
  { id: "4.3.2", okr: "O4.3", name: "Pilot Bot 1 OPS Team",               pic: "BA · Yến",          priority: "P1", deadline: "2026-05-31", is_overdue: false, days_left: 9   },
  { id: "4.2.2", okr: "O4.2", name: "Vehicle Classification 60% fleet",   pic: "Chiến + Growth",    priority: "P1", deadline: "2026-05-31", is_overdue: false, days_left: 9   },
];

export async function getOkrActionsData(): Promise<ApiOkrAction[]> {
  try {
    const res = await fetchBotApi<ApiOkrResponse>("/api/okr");
    return res.actions;
  } catch {
    return MOCK_OKR_ACTIONS;
  }
}

export async function getOkrData(): Promise<OkrObjective[]> {
  try {
    const res = await fetchBotApi<ApiOkrResponse>("/api/okr");
    const bscMap: Record<string, OkrObjective["bsc"]> = {
      ops: "Vận hành",
      supply: "Học hỏi",
      quality: "Khách hàng",
      tech: "Học hỏi",
    };
    return res.objectives.map((obj) => {
      const actions = res.actions.filter(
        (a) => a.okr === obj.id || a.okr.startsWith(obj.id + ".")
      );
      const total = actions.length || 1;
      const done = actions.filter((a) => !a.is_overdue).length;
      const overdueCount = actions.filter((a) => a.is_overdue).length;
      return {
        id: obj.id.toLowerCase(),
        title: obj.label,
        subtitle: `${obj.krs.length} key result · Q2/2026`,
        progress: Math.round((done / total) * 100),
        target: obj.krs.slice(0, 2).map((k) => k.target).join(" · "),
        baseline: obj.krs[0]?.baseline ?? "—",
        current: `${done}/${total} action on-track`,
        risk: overdueCount > 2 ? "high" : overdueCount > 0 ? "medium" : ("low" as const),
        owner: `OPS · ${obj.category}`,
        bsc: bscMap[obj.category] ?? "Vận hành",
        keyResults: obj.krs.map((kr) => {
          const krActions = actions.filter((a) => a.kr === kr.id);
          const krDone = krActions.filter((a) => !a.is_overdue).length;
          const krTotal = krActions.length || 1;
          return {
            id: kr.id,
            label: kr.label,
            progress: Math.round((krDone / krTotal) * 100),
            target: kr.target,
          };
        }),
      };
    });
  } catch {
    return OKRS;
  }
}
