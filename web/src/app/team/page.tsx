"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Member, Task, MemberScope } from "@/lib/types";
import { LoadBadge, PriorityBadge, StatusBadge } from "@/components/ui/badge";
import { ChevronRight, RefreshCw, X, BookOpen, ArrowUpRight, AlertTriangle } from "lucide-react";

const GRADE_COLOR: Record<string, string> = {
  G4: "bg-purple-50 border-purple-200 text-purple-900",
  G3: "bg-blue-50 border-blue-200 text-blue-900",
  "ACT-G3": "bg-blue-50 border-blue-200 text-blue-900",
  G2: "bg-green-50 border-green-200 text-green-900",
  G1: "bg-amber-50 border-amber-200 text-amber-900",
};

const GRADE_DOT: Record<string, string> = {
  G4: "bg-purple-500",
  G3: "bg-blue-500",
  "ACT-G3": "bg-blue-400",
  G2: "bg-green-500",
  G1: "bg-amber-500",
};

function GradeBadge({ grade }: { grade: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-semibold border ${GRADE_COLOR[grade] ?? "bg-gray-100 border-gray-200 text-gray-700"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${GRADE_DOT[grade] ?? "bg-gray-400"}`} />
      {grade}
    </span>
  );
}

function MemberCard({
  member,
  scope,
  onClick,
}: {
  member: Member;
  scope?: MemberScope;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="card p-4 text-left hover:border-gray-300 transition-colors w-full"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="font-semibold text-gray-900 truncate">{member.full_name}</p>
            {scope?.grade && <GradeBadge grade={scope.grade} />}
          </div>
          {member.username && (
            <p className="text-xs text-gray-400">@{member.username}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <LoadBadge load={member.load} />
          <ChevronRight size={14} className="text-gray-300" />
        </div>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        {scope?.title ?? member.role_label}
        {member.team && ` · ${member.team}`}
      </p>
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

function ScopePanel({ scope }: { scope: MemberScope }) {
  return (
    <div className="px-5 py-4 space-y-4">
      <div className="bg-gray-50 rounded p-3 text-xs">
        <div className="grid grid-cols-2 gap-2 mb-2">
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">Reports to</p>
            <p className="text-gray-800 font-medium">{scope.reports_to}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide">Direct reports</p>
            <p className="text-gray-800 font-medium">
              {scope.direct_reports.length > 0 ? scope.direct_reports.join(", ") : "—"}
            </p>
          </div>
        </div>
        {scope.owns_okr.length > 0 && (
          <div className="pt-2 border-t border-gray-200">
            <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-1">OKR ownership</p>
            <div className="flex gap-1 flex-wrap">
              {scope.owns_okr.map((o) => (
                <span key={o} className="text-[10px] bg-white border border-gray-200 px-1.5 py-0.5 rounded font-mono">{o}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-gray-800">🎯 Owns ({scope.owns.length})</h3>
        <ul className="text-xs text-gray-700 space-y-1">
          {scope.owns.map((x, i) => (
            <li key={i} className="leading-relaxed pl-3 border-l-2 border-gray-200">{x}</li>
          ))}
        </ul>
      </div>

      <div className="grid grid-cols-1 gap-3">
        <div className="card p-3 border-green-200 bg-green-50/30">
          <h3 className="mb-1.5 text-green-700 text-xs font-semibold">✅ DO MORE</h3>
          <ul className="text-xs text-gray-700 space-y-1">
            {scope.do_more.map((x, i) => (
              <li key={i} className="leading-relaxed">• {x}</li>
            ))}
          </ul>
        </div>

        <div className="card p-3 border-red-200 bg-red-50/30">
          <h3 className="mb-1.5 text-red-700 text-xs font-semibold">🚫 DO LESS / DON'T</h3>
          <ul className="text-xs text-gray-700 space-y-1">
            {scope.do_less.map((x, i) => (
              <li key={i} className="leading-relaxed">• {x}</li>
            ))}
          </ul>
        </div>

        {Object.keys(scope.delegate_to).length > 0 && (
          <div className="card p-3 border-blue-200 bg-blue-50/30">
            <h3 className="mb-1.5 text-blue-700 text-xs font-semibold">🔁 DELEGATE TO</h3>
            <ul className="text-xs text-gray-700 space-y-1.5">
              {Object.entries(scope.delegate_to).map(([k, v]) => (
                <li key={k} className="leading-relaxed flex items-start gap-1.5">
                  <ArrowUpRight size={11} className="mt-0.5 shrink-0 text-blue-500" />
                  <span><span className="text-gray-600">{k}</span> → <span className="font-medium">{v}</span></span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {scope.playbooks_to_supervise.length > 0 && (
        <div>
          <h3 className="mb-2 text-gray-800 flex items-center gap-1.5">
            <BookOpen size={13} />
            Playbooks
          </h3>
          <div className="flex gap-1.5 flex-wrap">
            {scope.playbooks_to_supervise.map((pb) => (
              <a
                key={pb}
                href={`/playbooks?q=${pb}`}
                className="text-[11px] font-mono bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded transition"
              >
                {pb}
              </a>
            ))}
          </div>
        </div>
      )}

      {scope.red_flags.length > 0 && (
        <div className="card p-3 border-amber-200 bg-amber-50/30">
          <h3 className="mb-1.5 text-amber-700 text-xs font-semibold flex items-center gap-1">
            <AlertTriangle size={12} />
            RED FLAGS (signals cần coach)
          </h3>
          <ul className="text-xs text-gray-700 space-y-1">
            {scope.red_flags.map((x, i) => (
              <li key={i} className="leading-relaxed">• {x}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function MemberDrawer({
  member,
  scope,
  onClose,
}: {
  member: Member;
  scope?: MemberScope;
  onClose: () => void;
}) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("active");
  const [view, setView] = useState<"scope" | "tasks">(scope ? "scope" : "tasks");

  useEffect(() => {
    if (view !== "tasks") return;
    setLoading(true);
    api
      .memberTasks(member.telegram_id, statusFilter === "active" ? undefined : statusFilter)
      .then(setTasks)
      .finally(() => setLoading(false));
  }, [member.telegram_id, statusFilter, view]);

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-full max-w-lg bg-white border-l border-gray-200 flex flex-col h-full shadow-xl">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="truncate">{member.full_name}</h2>
              {scope?.grade && <GradeBadge grade={scope.grade} />}
            </div>
            <p className="text-xs text-gray-400">{scope?.title ?? member.role_label}</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 shrink-0">
            <X size={16} />
          </button>
        </div>

        {scope && (
          <div className="px-5 border-b border-gray-100 flex gap-3 -mt-px">
            {[
              { id: "scope" as const, label: "Scope" },
              { id: "tasks" as const, label: "Tasks" },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setView(t.id)}
                className={`py-2 text-sm font-medium border-b-2 transition-colors ${
                  view === t.id
                    ? "border-gray-900 text-gray-900"
                    : "border-transparent text-gray-500 hover:text-gray-900"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {view === "scope" && scope ? (
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            <ScopePanel scope={scope} />
          </div>
        ) : (
          <>
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
        </>
        )}
      </div>
    </div>
  );
}

function findScope(scopes: MemberScope[], member: Member): MemberScope | undefined {
  const name = member.full_name.toLowerCase().trim();
  return scopes.find((s) =>
    s.name.toLowerCase() === name
    || name.includes(s.short_name.toLowerCase())
    || s.name.toLowerCase().includes(name)
  );
}

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [scopes, setScopes] = useState<MemberScope[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Member | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [team, scopeData] = await Promise.all([
        api.team(),
        api.memberScopes().catch(() => ({ members: [] })),
      ]);
      setMembers(team);
      setScopes(scopeData.members ?? []);
    } catch (e) {
      setError((e as Error).message ?? "Failed to load team");
    } finally {
      setLoading(false);
    }
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
                    <MemberCard key={m.telegram_id} member={m} scope={findScope(scopes, m)} onClick={() => setSelected(m)} />
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
                  <MemberCard key={m.telegram_id} member={m} scope={findScope(scopes, m)} onClick={() => setSelected(m)} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {selected && (
        <MemberDrawer member={selected} scope={findScope(scopes, selected)} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
