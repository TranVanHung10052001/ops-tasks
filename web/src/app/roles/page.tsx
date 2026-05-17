"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  GradeMatrixData, GradeDefinition, DelegationHealth, MemberScopeData,
} from "@/lib/types";
import {
  Compass, Users as UsersIcon, Zap, BarChart3, Network, Lightbulb, Shield,
  RefreshCw, AlertTriangle, Target, Layers,
} from "lucide-react";

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

const AREA_ICON: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  compass: Compass,
  users: UsersIcon,
  zap: Zap,
  "bar-chart": BarChart3,
  network: Network,
  lightbulb: Lightbulb,
  shield: Shield,
};

function GradeBadge({ grade, size = "sm" }: { grade: string; size?: "sm" | "xs" }) {
  const px = size === "xs" ? "px-1 py-0 text-[10px]" : "px-1.5 py-0.5 text-[11px]";
  return (
    <span className={`inline-flex items-center gap-1 ${px} rounded font-semibold border ${GRADE_COLOR[grade] ?? "bg-gray-100 border-gray-200 text-gray-700"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${GRADE_DOT[grade] ?? "bg-gray-400"}`} />
      {grade}
    </span>
  );
}

function TimeSplitBar({ split }: { split: { strategic: number; tactical: number; operational: number } }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px] text-gray-500">
        <span>Time split</span>
        <span className="tabular-nums">
          Strat {split.strategic}% · Tac {split.tactical}% · Ops {split.operational}%
        </span>
      </div>
      <div className="h-2 flex rounded overflow-hidden bg-gray-100">
        <div className="bg-purple-400" style={{ width: `${split.strategic}%` }} />
        <div className="bg-blue-400" style={{ width: `${split.tactical}%` }} />
        <div className="bg-amber-400" style={{ width: `${split.operational}%` }} />
      </div>
    </div>
  );
}

function GradeCard({ g }: { g: GradeDefinition }) {
  return (
    <div className={`card p-4 border-l-4 ${
      g.id === "G4" ? "border-l-purple-500" :
      g.id === "G3" ? "border-l-blue-500" :
      g.id === "G2" ? "border-l-green-500" :
      "border-l-amber-500"
    }`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <GradeBadge grade={g.id} />
            <h2>{g.label}</h2>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{g.title_short}</p>
        </div>
      </div>

      <div className="bg-gray-50 rounded p-2 mb-3">
        <p className="text-xs text-gray-600 italic">"{g.core_question}"</p>
      </div>

      <div className="mb-3">
        <TimeSplitBar split={g.time_split} />
      </div>

      <div className="text-[11px] text-gray-500 mb-3">
        <span className="font-medium text-gray-700">Span:</span> {g.span_of_control}
      </div>

      <details className="mb-2" open>
        <summary className="text-xs font-semibold text-gray-700 cursor-pointer mb-1">
          ✓ Owns ({g.owns.length})
        </summary>
        <ul className="mt-1 space-y-0.5 text-xs text-gray-600 pl-3">
          {g.owns.map((x, i) => (
            <li key={i} className="leading-relaxed">• {x}</li>
          ))}
        </ul>
      </details>

      <details className="mb-2">
        <summary className="text-xs font-semibold text-blue-700 cursor-pointer mb-1">
          🔁 Delegates ({g.delegates.length})
        </summary>
        <ul className="mt-1 space-y-0.5 text-xs text-gray-600 pl-3">
          {g.delegates.map((x, i) => (
            <li key={i} className="leading-relaxed">• {x}</li>
          ))}
        </ul>
      </details>

      <details className="mb-2">
        <summary className="text-xs font-semibold text-red-700 cursor-pointer mb-1">
          🚫 Should NOT do ({g.should_not_do.length})
        </summary>
        <ul className="mt-1 space-y-0.5 text-xs text-gray-600 pl-3">
          {g.should_not_do.map((x, i) => (
            <li key={i} className="leading-relaxed">• {x}</li>
          ))}
        </ul>
      </details>

      <div className="mt-3 pt-3 border-t border-gray-100">
        <p className="text-[11px] text-gray-500">
          <span className="font-medium text-gray-700">Escalates to:</span> {g.escalates_to}
        </p>
      </div>
    </div>
  );
}

function ResponsibilityMatrix({ data }: { data: GradeMatrixData }) {
  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h2>Responsibility Area Matrix</h2>
        <p className="text-xs text-gray-500 mt-0.5">Mỗi lĩnh vực × grade — ai làm gì</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-gray-600 sticky left-0 bg-gray-50 z-10">Area</th>
              <th className="text-left px-3 py-2 font-medium text-purple-700 min-w-[200px]">G4 Manager</th>
              <th className="text-left px-3 py-2 font-medium text-blue-700 min-w-[200px]">G3 Team Lead</th>
              <th className="text-left px-3 py-2 font-medium text-green-700 min-w-[200px]">G2 Specialist</th>
              <th className="text-left px-3 py-2 font-medium text-amber-700 min-w-[200px]">G1 Executive</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.responsibility_areas.map((area) => {
              const Icon = AREA_ICON[area.icon] ?? Compass;
              return (
                <tr key={area.id} className="align-top">
                  <td className="px-3 py-2.5 font-medium text-gray-800 sticky left-0 bg-white">
                    <div className="flex items-center gap-1.5">
                      <Icon size={13} className="text-gray-400" />
                      {area.label}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-gray-700 leading-relaxed">{area.G4}</td>
                  <td className="px-3 py-2.5 text-gray-700 leading-relaxed">{area.G3}</td>
                  <td className="px-3 py-2.5 text-gray-700 leading-relaxed">{area.G2}</td>
                  <td className="px-3 py-2.5 text-gray-700 leading-relaxed">{area.G1}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DecisionMatrix({ data }: { data: GradeMatrixData }) {
  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <h2>Decision Authority Matrix</h2>
        <p className="text-xs text-gray-500 mt-0.5">Ai quyết được gì — ngưỡng phê duyệt</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-gray-600 sticky left-0 bg-gray-50 min-w-[200px]">Decision</th>
              <th className="text-left px-3 py-2 font-medium text-purple-700">G4</th>
              <th className="text-left px-3 py-2 font-medium text-blue-700">G3</th>
              <th className="text-left px-3 py-2 font-medium text-green-700">G2</th>
              <th className="text-left px-3 py-2 font-medium text-amber-700">G1</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.decision_authority_matrix.map((row, i) => (
              <tr key={i} className="align-top">
                <td className="px-3 py-2.5 font-medium text-gray-800 sticky left-0 bg-white">
                  {row.decision}
                </td>
                <td className="px-3 py-2.5 text-gray-700">{row.G4}</td>
                <td className="px-3 py-2.5 text-gray-700">{row.G3}</td>
                <td className="px-3 py-2.5 text-gray-700">{row.G2}</td>
                <td className="px-3 py-2.5 text-gray-700">{row.G1}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DelegationPrinciples({ data }: { data: GradeMatrixData }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {data.delegation_principles.map((p) => (
        <div key={p.id} className="card p-4">
          <div className="flex items-start justify-between mb-2">
            <span className="text-[11px] font-semibold text-gray-400 tabular-nums">{p.id}</span>
          </div>
          <p className="text-sm font-semibold text-gray-900 mb-2 leading-snug">{p.rule}</p>
          <p className="text-xs text-gray-600 mb-1.5">
            <span className="font-medium text-gray-800">Vì sao:</span> {p.why}
          </p>
          <p className="text-xs text-gray-600">
            <span className="font-medium text-gray-800">Cách áp dụng:</span> {p.test}
          </p>
        </div>
      ))}
    </div>
  );
}

function HealthCheck({ health }: { health: DelegationHealth }) {
  const grouped = health.red_flag_signals.reduce<Record<string, typeof health.red_flag_signals>>((acc, sig) => {
    const key = `${sig.grade}::${sig.member}`;
    if (!acc[key]) acc[key] = [];
    acc[key].push(sig);
    return acc;
  }, {});

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 card overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <AlertTriangle size={15} className="text-red-500" />
          <h2>Red Flag Signals — Cần Check</h2>
          <span className="ml-auto text-xs text-gray-400">
            {health.red_flag_signals.length} signals · {Object.keys(grouped).length} people
          </span>
        </div>
        <div className="divide-y divide-gray-100 max-h-[420px] overflow-y-auto scrollbar-thin">
          {Object.entries(grouped).map(([key, sigs]) => {
            const [grade, member] = key.split("::");
            return (
              <div key={key} className="px-4 py-2.5">
                <div className="flex items-center gap-2 mb-1.5">
                  <GradeBadge grade={grade} size="xs" />
                  <p className="text-sm font-semibold text-gray-900">{member}</p>
                  <span className="text-[11px] text-gray-400">({sigs.length} flag{sigs.length > 1 ? "s" : ""})</span>
                </div>
                <ul className="space-y-0.5 pl-1">
                  {sigs.map((s, i) => (
                    <li key={i} className="text-xs text-gray-600 leading-relaxed">
                      <span className="text-red-500 mr-1">•</span>
                      {s.flag}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Target size={15} className="text-gray-400" />
          <h2>Health Targets</h2>
        </div>
        <ul className="divide-y divide-gray-100 text-xs">
          {Object.entries(health.targets).map(([key, t]) => {
            const value = t.target ?? t.target_max ?? 0;
            const isMax = t.target_max !== undefined;
            return (
              <li key={key} className="px-4 py-2 flex items-center justify-between">
                <span className="text-gray-600">{key.replace(/_/g, " ")}</span>
                <span className="font-semibold tabular-nums text-gray-900">
                  {isMax ? "≤" : "≥"} {value}{key.includes("pct") ? "%" : ""}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

function LoadByGrade({ health }: { health: DelegationHealth }) {
  const order = ["G4", "G3", "ACT-G3", "G2", "G1", "—"];
  const grades = Object.keys(health.load_by_grade).sort(
    (a, b) => order.indexOf(a) - order.indexOf(b)
  );

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <Layers size={15} className="text-gray-400" />
        <h2>Load Distribution by Grade</h2>
        <p className="ml-auto text-[11px] text-gray-400">Active tasks live từ DB</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-x divide-gray-100">
        {grades.map((gr) => {
          const members = health.load_by_grade[gr];
          const totalActive = members.reduce((s, m) => s + m.active_count, 0);
          const totalOverdue = members.reduce((s, m) => s + m.overdue_count, 0);
          return (
            <div key={gr} className="px-4 py-3">
              <div className="flex items-center justify-between mb-2">
                <GradeBadge grade={gr} />
                <span className="text-[11px] text-gray-400">{members.length} ng</span>
              </div>
              <div className="text-2xl font-bold tabular-nums">{totalActive}</div>
              <p className="text-[11px] text-gray-500">active tasks</p>
              {totalOverdue > 0 && (
                <p className="text-[11px] text-red-500 mt-1">{totalOverdue} overdue</p>
              )}
              <ul className="mt-2 space-y-0.5">
                {members.map((m) => (
                  <li key={m.name} className="text-[11px] text-gray-600 flex justify-between">
                    <span className="truncate">{m.name.split(" ").slice(-2).join(" ")}</span>
                    <span className="tabular-nums text-gray-400">{m.active_count}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function RolesPage() {
  const [matrix, setMatrix] = useState<GradeMatrixData | null>(null);
  const [health, setHealth] = useState<DelegationHealth | null>(null);
  const [memberScopes, setMemberScopes] = useState<MemberScopeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"grades" | "matrix" | "decisions" | "principles" | "health">("grades");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, h, ms] = await Promise.all([
        api.grades(),
        api.delegationHealth(),
        api.memberScopes(),
      ]);
      setMatrix(m);
      setHealth(h);
      setMemberScopes(ms);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const TABS = [
    { id: "grades" as const, label: "Grade Cards" },
    { id: "matrix" as const, label: "Responsibility Matrix" },
    { id: "decisions" as const, label: "Decision Authority" },
    { id: "principles" as const, label: "Delegation Principles" },
    { id: "health" as const, label: "Health Check" },
  ];

  return (
    <div className="p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1>Delegation Framework</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Grade × Responsibility × Authority — phân quyền rõ ràng cho 4 cấp G4/G3/G2/G1.
            {matrix && <> · v{matrix.version} · cập nhật {matrix.updated_at}</>}
          </p>
        </div>
        <button onClick={load} disabled={loading} className="btn-ghost text-xs">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-gray-200 mt-4 overflow-x-auto scrollbar-thin">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              tab === t.id
                ? "border-gray-900 text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="card p-5 border-red-200 mb-4">
          <p className="text-sm text-red-600 font-medium">Cannot connect to API</p>
          <p className="text-xs text-gray-400 mt-0.5">{error}</p>
          <button onClick={load} className="btn-secondary mt-3 text-xs">Retry</button>
        </div>
      )}

      {loading && !matrix ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-80 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : matrix ? (
        <>
          {tab === "grades" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {matrix.grades.map((g) => (
                <GradeCard key={g.id} g={g} />
              ))}
            </div>
          )}

          {tab === "matrix" && <ResponsibilityMatrix data={matrix} />}

          {tab === "decisions" && <DecisionMatrix data={matrix} />}

          {tab === "principles" && (
            <div className="space-y-3">
              <p className="text-sm text-gray-600 mb-2">
                6 nguyên tắc cốt lõi — áp dụng khi quyết định 'task này ai làm?'.
              </p>
              <DelegationPrinciples data={matrix} />
            </div>
          )}

          {tab === "health" && health && (
            <div className="space-y-4">
              <LoadByGrade health={health} />
              <HealthCheck health={health} />
            </div>
          )}
        </>
      ) : null}

      {memberScopes && tab === "grades" && (
        <div className="mt-6 text-xs text-gray-400">
          Tip: Vào <a href="/team" className="text-gray-700 underline">Team</a> để xem scope chi tiết từng người ·
          {" "}<a href="/playbooks" className="text-gray-700 underline">Playbooks</a> để xem SOP execution steps.
        </div>
      )}
    </div>
  );
}
