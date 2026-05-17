"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Member, Task } from "@/lib/types";
import { LoadBadge, PriorityBadge, StatusBadge } from "@/components/ui/badge";
import { ChevronRight, RefreshCw, X } from "lucide-react";

function MemberCard({
  member,
  onClick,
}: {
  member: Member;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="card p-4 text-left hover:border-gray-300 transition-colors w-full"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="font-semibold text-gray-900">{member.full_name}</p>
          {member.username && (
            <p className="text-xs text-gray-400">@{member.username}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <LoadBadge load={member.load} />
          <ChevronRight size={14} className="text-gray-300" />
        </div>
      </div>
      <p className="text-xs text-gray-500 mb-3">{member.role_label}{member.team && ` · ${member.team}`}</p>
      <div className="grid grid-cols-4 gap-2 text-center">
        <div>
          <p className="text-lg font-bold text-gray-900 tabular-nums">{member.active_count}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Active</p>
        </div>
        <div>
          <p className="text-lg font-bold text-green-600 tabular-nums">{member.done_today}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Done</p>
        </div>
        <div>
          <p className="text-lg font-bold text-red-500 tabular-nums">{member.overdue_count}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Overdue</p>
        </div>
        <div>
          <p className="text-lg font-bold text-orange-500 tabular-nums">{member.blocked_count}</p>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide">Blocked</p>
        </div>
      </div>
    </button>
  );
}

function MemberDrawer({
  member,
  onClose,
}: {
  member: Member;
  onClose: () => void;
}) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("active");

  useEffect(() => {
    setLoading(true);
    api
      .memberTasks(member.telegram_id, statusFilter === "active" ? undefined : statusFilter)
      .then(setTasks)
      .finally(() => setLoading(false));
  }, [member.telegram_id, statusFilter]);

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-full max-w-lg bg-white border-l border-gray-200 flex flex-col h-full shadow-xl">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2>{member.full_name}</h2>
            <p className="text-xs text-gray-400">{member.role_label}</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5">
            <X size={16} />
          </button>
        </div>

        {/* Stats row */}
        <div className="px-5 py-3 border-b border-gray-100 grid grid-cols-4 gap-3 text-center">
          {[
            { label: "Active", val: member.active_count, color: "text-gray-900" },
            { label: "Done Today", val: member.done_today, color: "text-green-600" },
            { label: "Overdue", val: member.overdue_count, color: "text-red-500" },
            { label: "Blocked", val: member.blocked_count, color: "text-orange-500" },
          ].map(({ label, val, color }) => (
            <div key={label}>
              <p className={`text-xl font-bold tabular-nums ${color}`}>{val}</p>
              <p className="text-[10px] text-gray-400">{label}</p>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div className="px-5 py-2 border-b border-gray-100 flex gap-1">
          {["active", "done", "blocked", "snoozed"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-gray-900 text-white"
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        {/* Task list */}
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {loading ? (
            <div className="p-5 space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : tasks.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-10">No tasks</p>
          ) : (
            <ul className="divide-y divide-gray-50">
              {tasks.map((t) => (
                <li key={t.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{t.summary}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <PriorityBadge priority={t.priority} />
                        {t.deadline && (
                          <span className="text-[11px] text-gray-400">
                            due {t.deadline.slice(0, 10)}
                          </span>
                        )}
                        {t.category && (
                          <span className="text-[11px] text-gray-400">{t.category}</span>
                        )}
                      </div>
                      {t.block_reason && (
                        <p className="text-xs text-red-500 mt-1 bg-red-50 px-2 py-0.5 rounded">
                          Blocked: {t.block_reason}
                        </p>
                      )}
                    </div>
                    <StatusBadge status={t.status} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Member | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    api.team()
      .then(setMembers)
      .catch((e: Error) => setError(e.message ?? "Failed to load team"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1>Team</h1>
          <p className="text-xs text-gray-400 mt-0.5">{members.length} members</p>
        </div>
        <button onClick={load} disabled={loading} className="btn-ghost text-xs">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="card p-5 border-red-200 mb-4">
          <p className="text-sm text-red-600 font-medium">Cannot connect to API</p>
          <p className="text-xs text-gray-400 mt-0.5">{error}</p>
          <button onClick={load} className="btn-secondary mt-3 text-xs">Retry</button>
        </div>
      )}

      {loading && members.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card p-4 h-40 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : (
        <>
          {/* Manager/Lead first */}
          {["manager", "team_lead"].map((role) => {
            const group = members.filter((m) => m.role === role);
            if (group.length === 0) return null;
            return (
              <div key={role} className="mb-6">
                <h3 className="mb-3">{role === "manager" ? "Manager" : "Team Leads"}</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {group.map((m) => (
                    <MemberCard key={m.telegram_id} member={m} onClick={() => setSelected(m)} />
                  ))}
                </div>
              </div>
            );
          })}
          {members.filter((m) => m.role === "employee").length > 0 && (
            <div>
              <h3 className="mb-3">Team Members</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {members.filter((m) => m.role === "employee").map((m) => (
                  <MemberCard key={m.telegram_id} member={m} onClick={() => setSelected(m)} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {selected && (
        <MemberDrawer member={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
