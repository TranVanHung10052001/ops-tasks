"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { OkrData, OkrObjective, OkrAction } from "@/lib/types";
import { PriorityBadge } from "@/components/ui/badge";
import { AlertTriangle, ChevronDown, ChevronRight, RefreshCw, Target } from "lucide-react";
import { formatDistanceToNow, parseISO } from "date-fns";

function ActionRow({ action }: { action: OkrAction }) {
  return (
    <div className={`flex items-center gap-3 px-4 py-2.5 border-b border-gray-50 last:border-0 table-row-hover ${action.is_overdue ? "bg-red-50/30" : ""}`}>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900">{action.name}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {action.kr} · {action.pic}
        </p>
      </div>
      <PriorityBadge priority={action.priority} />
      <div className="text-xs text-right min-w-20">
        {action.is_overdue ? (
          <span className="text-red-500 flex items-center gap-1 justify-end">
            <AlertTriangle size={11} />
            Overdue
          </span>
        ) : action.days_left !== null ? (
          <span className={action.days_left <= 3 ? "text-orange-500 font-medium" : "text-gray-400"}>
            {action.days_left === 0 ? "Today" : `${action.days_left}d left`}
          </span>
        ) : (
          <span className="text-gray-300">—</span>
        )}
        <p className="text-gray-300 text-[11px]">{action.deadline}</p>
      </div>
    </div>
  );
}

function ObjectiveBlock({
  obj,
  actions,
}: {
  obj: OkrObjective;
  actions: OkrAction[];
}) {
  const [open, setOpen] = useState(true);
  const objActions = actions.filter((a) => a.okr.startsWith(obj.id + ".") || a.okr === obj.id);
  const overdue = objActions.filter((a) => a.is_overdue).length;

  return (
    <div className="card mb-4 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="w-7 h-7 rounded-md bg-gray-900 text-white text-xs font-bold flex items-center justify-center shrink-0">
          {obj.id}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-900 text-sm">{obj.label}</p>
          <p className="text-xs text-gray-400">{obj.category} · {obj.krs.length} KRs · {objActions.length} actions</p>
        </div>
        {overdue > 0 && (
          <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded flex items-center gap-1">
            <AlertTriangle size={10} />
            {overdue} overdue
          </span>
        )}
        {open ? <ChevronDown size={15} className="text-gray-400 shrink-0" /> : <ChevronRight size={15} className="text-gray-400 shrink-0" />}
      </button>

      {open && (
        <>
          {/* KRs */}
          <div className="border-t border-gray-100 px-4 py-3 bg-gray-50/50">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {obj.krs.map((kr) => (
                <div key={kr.id} className="bg-white border border-gray-100 rounded-md px-3 py-2">
                  <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">{kr.id}</p>
                  <p className="text-sm text-gray-900 font-medium mt-0.5">{kr.label}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                    {kr.baseline && <span>Base: {kr.baseline}</span>}
                    <span className="text-gray-800 font-medium">→ {kr.target}</span>
                    <span className="ml-auto text-gray-300">wt {kr.weight}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          {objActions.length > 0 && (
            <div className="border-t border-gray-100">
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide px-4 py-2">Actions</p>
              {objActions.map((a) => (
                <ActionRow key={a.id} action={a} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function OkrPage() {
  const [data, setData] = useState<OkrData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api.okr()
      .then(setData)
      .catch((e: Error) => setError(e.message ?? "Failed to load OKR"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1>OKR</h1>
          {data && (
            <p className="text-xs text-gray-400 mt-0.5">{data.quarter} · {data.total_actions} actions</p>
          )}
        </div>
        <button onClick={load} disabled={loading} className="btn-ghost text-xs">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {data && (
        <div className="mb-5 card p-4 border-l-4 border-l-gray-900">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">North Star</p>
          <p className="text-sm font-medium text-gray-900">{data.north_star}</p>
        </div>
      )}

      {/* Summary bar */}
      {data && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="card p-3 text-center">
            <p className="text-xl font-bold tabular-nums text-gray-900">{data.total_actions}</p>
            <p className="text-xs text-gray-400">Total Actions</p>
          </div>
          <div className={`card p-3 text-center ${data.overdue_actions > 0 ? "border-red-200" : ""}`}>
            <p className={`text-xl font-bold tabular-nums ${data.overdue_actions > 0 ? "text-red-600" : "text-gray-900"}`}>
              {data.overdue_actions}
            </p>
            <p className="text-xs text-gray-400">Overdue</p>
          </div>
          <div className={`card p-3 text-center ${data.p0_actions > 0 ? "border-orange-200" : ""}`}>
            <p className={`text-xl font-bold tabular-nums ${data.p0_actions > 0 ? "text-orange-600" : "text-gray-900"}`}>
              {data.p0_actions}
            </p>
            <p className="text-xs text-gray-400">P0 Actions</p>
          </div>
        </div>
      )}

      {error && (
        <div className="card p-5 border-red-200 mb-4">
          <p className="text-sm text-red-600 font-medium">Cannot connect to API</p>
          <p className="text-xs text-gray-400 mt-0.5">{error}</p>
          <button onClick={load} className="btn-secondary mt-3 text-xs">Retry</button>
        </div>
      )}

      {loading && !data ? (
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card h-32 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : data ? (
        data.objectives.map((obj) => (
          <ObjectiveBlock key={obj.id} obj={obj} actions={data.actions} />
        ))
      ) : null}
    </div>
  );
}
