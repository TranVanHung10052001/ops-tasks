"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { TeamStats, Member } from "@/lib/types";
import StatCard from "@/components/ui/stat-card";
import { LoadBadge, PriorityBadge } from "@/components/ui/badge";
import {
  AlertTriangle,
  CheckCircle2,
  Activity,
  Users,
  ShieldAlert,
  RefreshCw,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

function PageHeader({
  title,
  onRefresh,
  loading,
}: {
  title: string;
  onRefresh: () => void;
  loading: boolean;
}) {
  return (
    <div className="flex items-center justify-between mb-6">
      <h1>{title}</h1>
      <button
        onClick={onRefresh}
        disabled={loading}
        className="btn-ghost text-xs"
      >
        <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        Refresh
      </button>
    </div>
  );
}

function OverduePanel({ tasks }: { tasks: TeamStats["overdue_tasks"] }) {
  if (tasks.length === 0) {
    return (
      <div className="card p-4">
        <h2 className="mb-3 flex items-center gap-2">
          <AlertTriangle size={15} className="text-gray-400" />
          Overdue Tasks
        </h2>
        <p className="text-sm text-gray-400 py-4 text-center">No overdue tasks</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <AlertTriangle size={15} className="text-red-500" />
        <h2>Overdue Tasks</h2>
        <span className="ml-auto text-xs font-semibold text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
          {tasks.length}
        </span>
      </div>
      <ul className="divide-y divide-gray-50">
        {tasks.slice(0, 8).map((t) => (
          <li key={t.id} className="px-4 py-2.5 flex items-center gap-3 table-row-hover">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{t.summary}</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {t.assignee_name ?? "Unassigned"}
                {t.deadline && (
                  <> · <span className="text-red-500">
                    due {formatDistanceToNow(new Date(t.deadline), { addSuffix: true })}
                  </span></>
                )}
              </p>
            </div>
            <PriorityBadge priority={t.priority} />
          </li>
        ))}
      </ul>
      {tasks.length > 8 && (
        <div className="px-4 py-2 border-t border-gray-100">
          <p className="text-xs text-gray-400">+{tasks.length - 8} more overdue</p>
        </div>
      )}
    </div>
  );
}

function TeamGrid({ members }: { members: Member[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <Users size={15} className="text-gray-400" />
        <h2>Team Workload</h2>
        <span className="ml-auto text-xs text-gray-400">{members.length} members</span>
      </div>
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wide">
              <th className="text-left px-4 py-2 font-medium">Member</th>
              <th className="text-left px-4 py-2 font-medium">Role</th>
              <th className="text-center px-4 py-2 font-medium">Active</th>
              <th className="text-center px-4 py-2 font-medium">Done Today</th>
              <th className="text-center px-4 py-2 font-medium">Overdue</th>
              <th className="text-center px-4 py-2 font-medium">Blocked</th>
              <th className="text-left px-4 py-2 font-medium">Load</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {members.map((m) => (
              <tr key={m.telegram_id} className="table-row-hover">
                <td className="px-4 py-2.5">
                  <div className="font-medium text-gray-900">{m.full_name}</div>
                  {m.username && (
                    <div className="text-xs text-gray-400">@{m.username}</div>
                  )}
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-500">{m.role_label}</td>
                <td className="px-4 py-2.5 text-center tabular-nums font-medium">{m.active_count}</td>
                <td className="px-4 py-2.5 text-center tabular-nums text-green-600">{m.done_today}</td>
                <td className="px-4 py-2.5 text-center tabular-nums text-red-500">{m.overdue_count}</td>
                <td className="px-4 py-2.5 text-center tabular-nums text-orange-500">{m.blocked_count}</td>
                <td className="px-4 py-2.5">
                  <LoadBadge load={m.load} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<TeamStats | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, m] = await Promise.all([api.stats(), api.team()]);
      setStats(s);
      setMembers(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (error) {
    return (
      <div className="p-8">
        <div className="card p-6 border-red-200">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={load} className="btn-secondary mt-3 text-xs">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl">
      <PageHeader title="Dashboard" onRefresh={load} loading={loading} />

      {loading && !stats ? (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-4 h-24 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : stats ? (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard
              label="Active Tasks"
              value={stats.active}
              sub={`${stats.member_count} members`}
              icon={<Activity size={18} />}
            />
            <StatCard
              label="Done Today"
              value={stats.done_today}
              sub={`${stats.done_week} this week`}
              accent="green"
              icon={<CheckCircle2 size={18} />}
            />
            <StatCard
              label="Overdue"
              value={stats.overdue}
              accent={stats.overdue > 0 ? "red" : "default"}
              icon={<AlertTriangle size={18} />}
            />
            <StatCard
              label="Blocked"
              value={stats.blocked}
              sub={stats.overloaded_count > 0 ? `${stats.overloaded_count} overloaded` : undefined}
              accent={stats.blocked > 0 ? "orange" : "default"}
              icon={<ShieldAlert size={18} />}
            />
          </div>

          {/* Team + Overdue */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-3">
              <TeamGrid members={members} />
            </div>
            <div className="lg:col-span-2">
              <OverduePanel tasks={stats.overdue_tasks} />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
