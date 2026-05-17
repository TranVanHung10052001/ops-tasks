"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  DelegationCoachResult, CrisisReport, CrisisRequest, ModelTiers,
} from "@/lib/types";
import {
  Bot, AlertTriangle, RefreshCw, Loader2, Shield, Siren,
  ArrowDownRight, ArrowUpRight, Scissors, Check, HelpCircle,
} from "lucide-react";

const CRISIS_TYPES = [
  "fr_drop", "sla_drop", "supply_gap", "vendor_failure",
  "hub_delay", "cost_overrun", "external_event",
] as const;

const VERDICT_STYLE: Record<string, { color: string; bg: string; icon: React.ComponentType<{ size?: number }> }> = {
  ok:                     { color: "text-green-700",  bg: "bg-green-50 border-green-200",  icon: Check },
  should_delegate_down:   { color: "text-amber-700",  bg: "bg-amber-50 border-amber-200",  icon: ArrowDownRight },
  should_delegate_up:     { color: "text-blue-700",   bg: "bg-blue-50 border-blue-200",    icon: ArrowUpRight },
  should_split:           { color: "text-purple-700", bg: "bg-purple-50 border-purple-200", icon: Scissors },
  needs_clarification:    { color: "text-gray-700",   bg: "bg-gray-50 border-gray-200",    icon: HelpCircle },
};

const SEVERITY_STYLE: Record<string, { color: string; bg: string }> = {
  watch:          { color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-200" },
  active_crisis:  { color: "text-orange-700", bg: "bg-orange-50 border-orange-200" },
  p0_crisis:      { color: "text-red-700",    bg: "bg-red-50 border-red-200" },
};

function TierBadge({ tier, model }: { tier: string; model?: string }) {
  const color = tier === "premium" ? "bg-purple-100 text-purple-700"
              : tier === "balanced" ? "bg-blue-100 text-blue-700"
              : "bg-green-100 text-green-700";
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono ${color}`}>
      {tier}
      {model && <span className="opacity-60">· {model}</span>}
    </span>
  );
}

function DelegationCoachPanel({ tiers }: { tiers: ModelTiers | null }) {
  const [taskId, setTaskId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DelegationCoachResult | null>(null);

  const run = async () => {
    const id = parseInt(taskId, 10);
    if (!id) {
      setError("Cần task ID hợp lệ.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.coachDelegation(id);
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <Shield size={15} className="text-purple-500" />
        <h2>Delegation Coach</h2>
        <TierBadge tier="premium" model={tiers?.premium} />
        <p className="ml-auto text-[11px] text-gray-400">AI judge delegation quality</p>
      </div>

      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex gap-2">
          <input
            type="number"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            placeholder="Task ID (vd: 12)"
            className="input text-sm flex-1"
            onKeyDown={(e) => e.key === "Enter" && run()}
          />
          <button onClick={run} disabled={loading || !taskId} className="btn-primary text-sm">
            {loading ? <Loader2 size={14} className="animate-spin" /> : "Analyze"}
          </button>
        </div>
        <p className="text-[11px] text-gray-400 mt-1">
          AI evaluates: grade-fit, load, scope match, recommends reassign/split if needed.
        </p>
      </div>

      <div className="p-4">
        {error && (
          <div className="card p-3 border-red-200 text-sm text-red-600">{error}</div>
        )}
        {loading && (
          <div className="text-center py-10 text-sm text-gray-400">
            <Loader2 size={20} className="animate-spin mx-auto mb-2" />
            AI đang phân tích task...
          </div>
        )}
        {!loading && !result && !error && (
          <p className="text-sm text-gray-400 text-center py-10">
            Nhập task ID để AI phân tích delegation.
          </p>
        )}
        {result && <DelegationVerdictCard r={result} />}
      </div>
    </div>
  );
}

function DelegationVerdictCard({ r }: { r: DelegationCoachResult }) {
  const style = VERDICT_STYLE[r.verdict] ?? VERDICT_STYLE.needs_clarification;
  const Icon = style.icon;

  return (
    <div className="space-y-4">
      <div className="mb-1">
        <p className="text-[11px] text-gray-400 font-mono">Task #{r.task_id}</p>
        <p className="text-sm font-medium text-gray-800">{r.task_summary}</p>
      </div>

      <div className={`card p-3 border-l-4 ${style.bg.replace("bg-", "border-l-").replace("50", "500")} ${style.bg}`}>
        <div className="flex items-start gap-2 mb-2">
          <Icon size={18} />
          <div className="flex-1 min-w-0">
            <p className={`text-xs font-bold uppercase tracking-wide ${style.color}`}>
              {r.verdict.replace(/_/g, " ")} · AI {Math.round(r.verdict_confidence * 100)}%
            </p>
            <p className="text-sm font-semibold text-gray-900 mt-1">{r.headline}</p>
          </div>
        </div>
      </div>

      {r.rationale.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-xs text-gray-500 uppercase tracking-wide">Lý do</h3>
          <ul className="text-sm text-gray-700 space-y-1">
            {r.rationale.map((x, i) => (
              <li key={i} className="leading-relaxed pl-3 border-l-2 border-gray-200">{x}</li>
            ))}
          </ul>
        </div>
      )}

      {r.recommended_owner && (
        <div className="card p-3 border-green-200 bg-green-50/40">
          <p className="text-xs text-green-700 font-semibold mb-1">🎯 Recommended owner</p>
          <p className="text-sm font-semibold text-gray-900">
            <span className="font-mono text-[11px] mr-1.5 bg-white px-1.5 py-0.5 rounded border border-green-200">
              {r.recommended_owner.grade}
            </span>
            {r.recommended_owner.name}
          </p>
          {r.recommended_owner.why && (
            <p className="text-xs text-gray-600 mt-1">{r.recommended_owner.why}</p>
          )}
        </div>
      )}

      {r.split_suggestion.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-xs text-gray-500 uppercase tracking-wide">Chia nhỏ</h3>
          <ul className="space-y-1.5">
            {r.split_suggestion.map((s, i) => (
              <li key={i} className="card p-2 flex items-start gap-2 text-sm">
                <span className="font-mono text-[10px] bg-gray-100 px-1.5 py-0.5 rounded mt-0.5">{s.owner_grade}</span>
                <span className="font-medium text-gray-800 mt-0.5">{s.owner_name}:</span>
                <span className="text-gray-700">{s.sub_task}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {r.red_flags.length > 0 && (
        <div className="card p-3 border-red-200 bg-red-50/40">
          <p className="text-xs text-red-700 font-semibold mb-1.5 flex items-center gap-1">
            <AlertTriangle size={11} /> Red flags
          </p>
          <ul className="text-xs text-gray-700 space-y-1">
            {r.red_flags.map((f, i) => (
              <li key={i}>• {f}</li>
            ))}
          </ul>
        </div>
      )}

      {r.coaching_question && (
        <div className="card p-3 border-blue-200 bg-blue-50/40">
          <p className="text-xs text-blue-700 font-semibold mb-1">💭 Coaching question</p>
          <p className="text-sm italic text-gray-700">{r.coaching_question}</p>
        </div>
      )}

      <div className="flex flex-wrap gap-2 text-[11px] text-gray-500 pt-2 border-t border-gray-100">
        {r.playbook_pointer && (
          <a href={`/playbooks?q=${r.playbook_pointer}`} className="font-mono bg-gray-100 hover:bg-gray-200 px-1.5 py-0.5 rounded">
            📘 {r.playbook_pointer}
          </a>
        )}
        {r.principles_applied.map((p) => (
          <span key={p} className="font-mono bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded">{p}</span>
        ))}
      </div>
    </div>
  );
}

function CrisisCommanderPanel({ tiers }: { tiers: ModelTiers | null }) {
  const [form, setForm] = useState<CrisisRequest>({
    type: "fr_drop",
    description: "",
    region: "",
    current_metric: "",
    current_value: "",
    target: "",
    trend: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<CrisisReport | null>(null);

  const run = async () => {
    if (!form.description.trim()) {
      setError("Cần description.");
      return;
    }
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const r = await api.crisis(form);
      setReport(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
        <Siren size={15} className="text-red-500" />
        <h2>Crisis Commander</h2>
        <TierBadge tier="premium" model={tiers?.premium} />
        <p className="ml-auto text-[11px] text-gray-400">RCA + immediate + structural plan</p>
      </div>

      <div className="px-4 py-3 border-b border-gray-100 space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <select
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value })}
            className="select text-sm"
          >
            {CRISIS_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <input
            type="text"
            value={form.region}
            onChange={(e) => setForm({ ...form, region: e.target.value })}
            placeholder="Region (HAN/SGN/EXP/B2B/all)"
            className="input text-sm"
          />
        </div>
        <textarea
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Mô tả crisis: vd 'FR Core HAN drop 8pp 3 ngày, hiện 60% (target 68%)'"
          className="input text-sm w-full min-h-[64px]"
        />
        <div className="grid grid-cols-3 gap-2">
          <input
            type="text"
            value={form.current_value}
            onChange={(e) => setForm({ ...form, current_value: e.target.value })}
            placeholder="Current (60%)"
            className="input text-sm"
          />
          <input
            type="text"
            value={form.target}
            onChange={(e) => setForm({ ...form, target: e.target.value })}
            placeholder="Target (68%)"
            className="input text-sm"
          />
          <input
            type="text"
            value={form.trend}
            onChange={(e) => setForm({ ...form, trend: e.target.value })}
            placeholder="Trend (down -10pp 3d)"
            className="input text-sm"
          />
        </div>
        <button onClick={run} disabled={loading} className="btn-danger text-sm w-full">
          {loading ? <Loader2 size={14} className="animate-spin" /> : "🚨 Activate Crisis Commander"}
        </button>
      </div>

      <div className="p-4">
        {error && <div className="card p-3 border-red-200 text-sm text-red-600">{error}</div>}
        {loading && (
          <div className="text-center py-10 text-sm text-gray-400">
            <Loader2 size={20} className="animate-spin mx-auto mb-2" />
            Premium AI đang build crisis plan (8-15s)...
          </div>
        )}
        {!loading && !report && !error && (
          <p className="text-sm text-gray-400 text-center py-10">
            Activate khi: FR/SLA drop ≥5pp, vendor crisis, supply gap, hub delay.
          </p>
        )}
        {report && <CrisisReportView r={report} />}
      </div>
    </div>
  );
}

function CrisisReportView({ r }: { r: CrisisReport }) {
  const style = SEVERITY_STYLE[r.severity] ?? SEVERITY_STYLE.watch;

  return (
    <div className="space-y-4">
      <div className={`card p-3 border-l-4 ${style.bg} ${style.bg.replace("bg-", "border-l-").replace("50", "500")}`}>
        <p className={`text-[11px] font-bold uppercase tracking-wide ${style.color}`}>
          {r.severity.replace(/_/g, " ")}
        </p>
        <p className="text-sm font-semibold text-gray-900 mt-1">{r.headline}</p>
        {r.severity_rationale && (
          <p className="text-xs text-gray-600 mt-1 italic">{r.severity_rationale}</p>
        )}
      </div>

      {r.rca_questions.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-xs text-gray-500 uppercase tracking-wide">🔍 RCA (5 Whys)</h3>
          <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
            {r.rca_questions.map((q, i) => <li key={i} className="leading-relaxed">{q}</li>)}
          </ol>
        </div>
      )}

      {r.immediate_actions.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-xs text-orange-700 font-semibold uppercase tracking-wide">⚡ Immediate (24-48h)</h3>
          <ul className="space-y-2">
            {r.immediate_actions.map((a, i) => (
              <li key={i} className="card p-3 border-orange-100">
                <div className="flex items-start gap-2 mb-1">
                  <span className="font-mono text-[10px] bg-orange-100 px-1.5 py-0.5 rounded text-orange-700">{a.owner_grade}</span>
                  <span className="text-xs font-medium">{a.owner_name}</span>
                  {a.deadline_hours && (
                    <span className="ml-auto text-[10px] text-gray-500">⏱ {a.deadline_hours}h</span>
                  )}
                </div>
                <p className="text-sm text-gray-800 leading-relaxed">{a.action}</p>
                {a.success_criterion && (
                  <p className="text-xs text-gray-500 mt-1">📏 {a.success_criterion}</p>
                )}
                {a.cost_estimate_vnd != null && (
                  <p className="text-xs text-gray-500">💸 ~{a.cost_estimate_vnd.toLocaleString()}đ</p>
                )}
                {a.escalation_if_fail && (
                  <p className="text-[11px] text-red-500 mt-1">↗ {a.escalation_if_fail}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {r.structural_actions.length > 0 && (
        <div>
          <h3 className="mb-1.5 text-xs text-blue-700 font-semibold uppercase tracking-wide">🔧 Structural (1 tuần)</h3>
          <ul className="space-y-2">
            {r.structural_actions.map((a, i) => (
              <li key={i} className="card p-3 border-blue-100">
                <div className="flex items-start gap-2 mb-1">
                  <span className="font-mono text-[10px] bg-blue-100 px-1.5 py-0.5 rounded text-blue-700">{a.owner_grade}</span>
                  <span className="text-xs font-medium">{a.owner_name}</span>
                  {a.deadline_days && (
                    <span className="ml-auto text-[10px] text-gray-500">📅 {a.deadline_days}d</span>
                  )}
                </div>
                <p className="text-sm text-gray-800 leading-relaxed">{a.action}</p>
                {a.deliverable && (
                  <p className="text-xs text-gray-500 mt-1">📤 {a.deliverable}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {r.war_room.lead && (
        <div className="card p-3 border-purple-200 bg-purple-50/30">
          <p className="text-xs text-purple-700 font-semibold mb-1">🛟 War Room</p>
          <p className="text-sm">Lead: <span className="font-semibold">{r.war_room.lead}</span></p>
          {r.war_room.core_team && (
            <p className="text-xs text-gray-600">Team: {r.war_room.core_team.join(", ")}</p>
          )}
          {r.war_room.cadence && (
            <p className="text-xs text-gray-600 italic">Cadence: {r.war_room.cadence}</p>
          )}
        </div>
      )}

      {(r.communication_plan.internal_team || r.communication_plan.escalate_to_c_level) && (
        <div className="card p-3 border-gray-200 bg-gray-50/30">
          <p className="text-xs text-gray-700 font-semibold mb-1.5">📢 Communication</p>
          <ul className="text-xs space-y-1">
            {r.communication_plan.internal_team && (
              <li>• <span className="text-gray-600">Team:</span> {r.communication_plan.internal_team}</li>
            )}
            {r.communication_plan.manager_brief && (
              <li>• <span className="text-gray-600">Brief lên:</span> {r.communication_plan.manager_brief}</li>
            )}
            {r.communication_plan.escalate_to_c_level && (
              <li className="text-red-600">⬆️ Escalate C-level: {r.communication_plan.escalate_when ?? "ASAP"}</li>
            )}
          </ul>
        </div>
      )}

      {r.risks_to_action_plan.length > 0 && (
        <div className="card p-3 border-amber-200 bg-amber-50/30">
          <p className="text-xs text-amber-700 font-semibold mb-1.5">⚠️ Risks to action plan</p>
          <ul className="text-xs text-gray-700 space-y-1">
            {r.risks_to_action_plan.map((rk, i) => <li key={i}>• {rk}</li>)}
          </ul>
        </div>
      )}

      <div className="flex gap-2 text-[11px] text-gray-500 pt-2 border-t border-gray-100">
        {r.playbook_pointer && (
          <a href={`/playbooks?q=${r.playbook_pointer}`} className="font-mono bg-gray-100 hover:bg-gray-200 px-1.5 py-0.5 rounded">
            📘 {r.playbook_pointer}
          </a>
        )}
      </div>
    </div>
  );
}

export default function AgentsPage() {
  const [tiers, setTiers] = useState<ModelTiers | null>(null);

  useEffect(() => {
    api.modelTiers().then(setTiers).catch(() => {});
  }, []);

  return (
    <div className="p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="flex items-center gap-2"><Bot size={20} /> AI Sub-agents</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Premium-tier strategic agents — Delegation Coach + Crisis Commander.
            {tiers && <> · Models: fast=<span className="font-mono">{tiers.fast}</span> · balanced=<span className="font-mono">{tiers.balanced}</span> · premium=<span className="font-mono">{tiers.premium}</span></>}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <DelegationCoachPanel tiers={tiers} />
        <CrisisCommanderPanel tiers={tiers} />
      </div>

      <div className="mt-6 text-xs text-gray-400">
        Tip: <a href="/roles" className="text-gray-700 underline">/roles</a> để xem grade matrix làm input cho Delegation Coach ·{" "}
        <a href="/playbooks" className="text-gray-700 underline">/playbooks</a> để xem SOP mà Crisis Commander reference (PB14).
      </div>
    </div>
  );
}
