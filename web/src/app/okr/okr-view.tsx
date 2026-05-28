"use client";

import { useState, useCallback } from "react";
import { OkrObjective } from "@/lib/mock";
import { ApiOkrAction } from "@/lib/api";
import OkrDial from "@/components/ui/okr-dial";
import clsx from "clsx";

// ── Action status cycle ───────────────────────────────────────────────────────

type ActionStatus = "pending" | "in_progress" | "done" | "cancelled";

const STATUS_CYCLE: ActionStatus[] = ["pending", "in_progress", "done"];

const STATUS_LABEL: Record<ActionStatus, string> = {
  pending:     "○ Chưa bắt đầu",
  in_progress: "◎ Đang làm",
  done:        "● Xong",
  cancelled:   "✕ Huỷ",
};

const STATUS_COLOR: Record<ActionStatus, string> = {
  pending:     "text-text-tertiary",
  in_progress: "text-accent-amber",
  done:        "text-signal-p3/75",
  cancelled:   "text-text-disabled line-through",
};

const PRIORITY_COLOR: Record<string, string> = {
  P0: "text-signal-p0/80 border-signal-p0/40",
  P1: "text-signal-p1/80 border-signal-p1/40",
  P2: "text-signal-p2/80 border-signal-p2/40",
  P3: "text-signal-p3/80 border-signal-p3/40",
};

const OKR_ACCENT: Record<string, string> = {
  O1: "border-l-signal-p3",
  O2: "border-l-signal-p2",
  O3: "border-l-signal-p1",
  O4: "border-l-accent-paper",
  O5: "border-l-accent-amber",
};

function daysLabel(action: ApiOkrAction) {
  if (action.is_overdue) {
    const d = Math.abs(action.days_left ?? 0);
    return `quá hạn ${d}ngày`;
  }
  const d = action.days_left ?? 0;
  if (d === 0) return "hôm nay";
  if (d === 1) return "mai";
  return `còn ${d} ngày`;
}

// ── OKR progress inline edit ──────────────────────────────────────────────────

function ProgressEdit({
  okrId, current, onSave, onCancel,
}: { okrId: string; current: number; onSave: (p: number, current: string) => void; onCancel: () => void }) {
  const [val, setVal] = useState(String(current));
  const [cur, setCur] = useState("");
  return (
    <div className="flex items-center gap-2 mt-2">
      <input
        type="number" min={0} max={100}
        value={val} onChange={e => setVal(e.target.value)}
        className="w-16 bg-surface-deep border border-accent-amber px-2 py-1 mono text-sm text-text-primary focus:outline-none tabular"
        autoFocus
      />
      <span className="mono text-xs text-text-tertiary">%</span>
      <input
        type="text" value={cur} onChange={e => setCur(e.target.value)}
        placeholder="Hiện tại (vd: FR HAN 78%)…"
        className="flex-1 bg-surface-deep border border-divider-strong px-2 py-1 mono text-xs text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent-amber"
      />
      <button
        onClick={() => onSave(Math.min(100, Math.max(0, Number(val))), cur)}
        className="btn-ops primary py-1 px-2 text-2xs"
      >✓ Lưu</button>
      <button onClick={onCancel} className="btn-ops py-1 px-2 text-2xs">Huỷ</button>
    </div>
  );
}

// ── Main OkrView ──────────────────────────────────────────────────────────────

export default function OkrView({
  initialOkrs,
  initialActions,
  totalProgress: initTotalProgress,
  atRisk: initAtRisk,
  overdueCount: initOverdueCount,
  p0Count,
}: {
  initialOkrs: OkrObjective[];
  initialActions: ApiOkrAction[];
  totalProgress: number;
  atRisk: number;
  overdueCount: number;
  p0Count: number;
}) {
  const [okrs, setOkrs] = useState(initialOkrs);
  const [actions, setActions] = useState(initialActions);
  const [editingOkr, setEditingOkr] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  const totalProgress = Math.round(okrs.reduce((s, o) => s + o.progress, 0) / (okrs.length || 1));
  const overdueCount = actions.filter((a) => a.is_overdue && (a.status as ActionStatus) !== "done").length;

  // Sort: overdue+P0 first
  const sortedActions = [...actions].sort((a, b) => {
    const aScore = (a.is_overdue && a.status !== "done" ? 100 : 0) + (a.priority === "P0" ? 50 : a.priority === "P1" ? 30 : 10);
    const bScore = (b.is_overdue && b.status !== "done" ? 100 : 0) + (b.priority === "P0" ? 50 : b.priority === "P1" ? 30 : 10);
    return bScore - aScore;
  });

  // ── Action status toggle ──
  const handleActionStatus = useCallback(async (actionId: string, currentStatus: ActionStatus) => {
    const idx = STATUS_CYCLE.indexOf(currentStatus);
    const next: ActionStatus = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
    // Optimistic
    setActions(prev => prev.map(a => a.id === actionId ? { ...a, status: next } : a));
    setSaving(actionId);
    try {
      await fetch(`/api/okr/actions/${encodeURIComponent(actionId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: next }),
      });
    } catch {
      // revert
      setActions(prev => prev.map(a => a.id === actionId ? { ...a, status: currentStatus } : a));
    } finally {
      setSaving(null);
    }
  }, []);

  // ── OKR progress update ──
  const handleOkrProgressSave = useCallback(async (okrId: string, progress: number, current: string) => {
    setEditingOkr(null);
    const upperOkrId = okrId.toUpperCase();
    setOkrs(prev => prev.map(o =>
      o.id.toLowerCase() === okrId.toLowerCase()
        ? { ...o, progress, current: current || o.current }
        : o
    ));
    try {
      await fetch(`/api/okr/objectives/${upperOkrId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ progress, current: current || undefined }),
      });
    } catch {}
  }, []);

  return (
    <>
      {/* Header */}
      <header className="flex items-end justify-between">
        <div>
          <div className="label-ops text-2xs mb-1.5">Ops · 03 · Theo dõi OKR</div>
          <h1 className="text-2xl text-text-primary editorial leading-tight">
            OKR quý 2 · 2026 · {okrs.length} mục tiêu.
          </h1>
          <p className="text-md text-text-secondary mt-1">
            {okrs.reduce((s, o) => s + o.keyResults.length, 0)} kết quả then chốt · {actions.length} action item · click trạng thái để cập nhật.
          </p>
        </div>
        <div className="ops-surface px-4 py-2.5 flex gap-6">
          <div>
            <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">Tổng tiến độ</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-display text-3xl text-accent-paper tabular leading-none">{totalProgress}%</span>
              <span className="mono text-2xs text-text-tertiary">/ {initAtRisk} có rủi ro</span>
            </div>
          </div>
          <div className="border-l border-divider pl-6">
            <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">Action overdue</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-display text-3xl text-signal-p0/80 tabular leading-none">{overdueCount}</span>
              <span className="mono text-2xs text-text-tertiary">/ {p0Count} P0</span>
            </div>
          </div>
        </div>
      </header>

      {/* North star */}
      <section className="ops-surface p-5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent-amber" />
        <div className="grid grid-cols-2 gap-8">
          <div>
            <div className="section-label mb-2">North Star · Q2/2026</div>
            <p className="editorial text-xl leading-snug text-text-primary">
              GSV Non-Bulky 70% YoY: 69B → 117.3B · Fill Rate toàn network ≥68%.
            </p>
          </div>
          <div>
            <div className="section-label mb-2">Tóm tắt tiến độ</div>
            <ul className="space-y-2 text-md text-text-primary">
              {okrs.slice(0, 3).map((o) => (
                <li key={o.id} className="flex gap-2.5 items-start">
                  <span className={
                    o.risk === "high" ? "text-signal-p0/75 mt-1" :
                    o.risk === "medium" ? "text-signal-p2/75 mt-1" :
                    "text-signal-p3/75 mt-1"
                  }>
                    {o.risk === "high" ? "▼" : o.risk === "medium" ? "●" : "▲"}
                  </span>
                  <span>
                    <span className="text-accent-paper">{o.title.split(" · ")[0]}</span>
                    {" — "}{o.progress}% · {o.current.split(" · ")[0]}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* OKR dials grid — with inline progress edit */}
      <div className="grid grid-cols-2 gap-4">
        {okrs.map((o) => (
          <div key={o.id} className="relative">
            <OkrDial okr={o} />
            <div className="px-5 pb-4">
              {editingOkr === o.id ? (
                <ProgressEdit
                  okrId={o.id}
                  current={o.progress}
                  onSave={(p, cur) => handleOkrProgressSave(o.id, p, cur)}
                  onCancel={() => setEditingOkr(null)}
                />
              ) : (
                <button
                  onClick={() => setEditingOkr(o.id)}
                  className="mono text-2xs text-text-tertiary hover:text-accent-amber transition-colors flex items-center gap-1 mt-1"
                >
                  ✎ Cập nhật tiến độ
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Action items table */}
      <section className="ops-surface">
        <header className="flex items-center justify-between px-5 py-3 border-b border-divider">
          <div className="flex items-baseline gap-3">
            <span className="section-label">Action Items · Q2/2026</span>
            <span className="mono text-2xs text-text-tertiary">{actions.length} actions</span>
            {overdueCount > 0 && (
              <span className="mono text-2xs text-signal-p0/75 flex items-center gap-1">
                ⚠ {overdueCount} trễ
              </span>
            )}
          </div>
          <div className="mono text-2xs text-text-tertiary">
            {p0Count} P0 · click trạng thái để cập nhật
          </div>
        </header>

        <div className="overflow-x-auto scroll-ops">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-divider mono text-2xs tracking-wider text-text-tertiary">
                <th className="w-1 p-0" />
                <th className="px-3 py-2 font-normal w-16">OKR</th>
                <th className="px-3 py-2 font-normal">Action</th>
                <th className="px-3 py-2 font-normal w-36">PIC</th>
                <th className="px-3 py-2 font-normal w-16">Mức</th>
                <th className="px-3 py-2 font-normal w-28 text-right">Thời hạn</th>
                <th className="px-3 py-2 font-normal w-32 text-right">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {sortedActions.map((action) => {
                const okrRoot = action.okr.split(".")[0];
                const st = (action.status as ActionStatus) || "pending";
                const isDone = st === "done";
                const overdue = action.is_overdue && !isDone;
                const daysTxt = daysLabel(action);
                const isSaving = saving === action.id;
                return (
                  <tr
                    key={action.id}
                    className={clsx(
                      "border-b border-divider transition-colors",
                      isDone ? "opacity-50" :
                      overdue && action.priority === "P0"
                        ? "bg-signal-p0/5 hover:bg-signal-p0/8"
                        : overdue
                        ? "bg-signal-p1/5 hover:bg-signal-p1/8"
                        : "hover:bg-surface-raised"
                    )}
                  >
                    <td className={clsx("p-0 w-1 border-l-2", OKR_ACCENT[okrRoot] ?? "")} />
                    <td className="px-3 py-2.5">
                      <span className="mono text-2xs text-accent-paper">{action.okr}</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className={clsx("text-sm text-text-primary leading-snug", isDone && "line-through text-text-tertiary")}>
                        {action.name}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="mono text-xs text-text-secondary">{action.pic}</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={clsx("mono text-2xs border px-1.5 py-0.5 leading-none", PRIORITY_COLOR[action.priority] ?? "text-text-tertiary border-divider")}>
                        {action.priority}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="mono text-xs text-text-primary tabular">{action.deadline}</div>
                      <div className={clsx("mono text-2xs", overdue ? "text-signal-p0/75" : (action.days_left ?? 99) <= 3 ? "text-signal-p2/75" : "text-text-tertiary")}>
                        {overdue && "⚠ "}{daysTxt}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <button
                        onClick={() => handleActionStatus(action.id, st)}
                        disabled={isSaving}
                        title="Click để đổi trạng thái"
                        className={clsx(
                          "mono text-2xs transition-colors cursor-pointer hover:opacity-100",
                          STATUS_COLOR[st],
                          isSaving && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        {isSaving ? "…" : STATUS_LABEL[st]}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
