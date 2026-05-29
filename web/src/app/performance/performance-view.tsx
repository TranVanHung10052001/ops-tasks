"use client";

import { useEffect, useState, useCallback } from "react";
import { ApiPerformance, ApiPerformanceTeam } from "@/lib/api";
import clsx from "clsx";

const PERIODS = [
  { days: 30,  label: "30 ngày" },
  { days: 90,  label: "Quý" },
  { days: 180, label: "Nửa năm" },
  { days: 365, label: "1 năm" },
];

type SortKey = "done" | "on_time_pct" | "avg_cycle_h" | "overdue";

function verdict(p: ApiPerformance): { dot: string; text: string } {
  if (p.done === 0) return { dot: "bg-text-tertiary", text: "Chưa có data" };
  if (p.on_time_pct != null && p.on_time_pct >= 85 && p.done >= 5)
    return { dot: "bg-signal-p3", text: "Đáng tin" };
  if (p.on_time_pct != null && p.on_time_pct < 60)
    return { dot: "bg-signal-p0", text: "Cần xem lại" };
  return { dot: "bg-accent-amber", text: "Ổn định" };
}

function pct(v: number | null) {
  return v == null ? "—" : `${v}%`;
}
function cycle(v: number | null) {
  if (v == null) return "—";
  return v < 48 ? `${v}h` : `${Math.round((v / 24) * 10) / 10}d`;
}

export default function PerformanceView({ initial }: { initial: ApiPerformanceTeam }) {
  const [days, setDays] = useState(initial.days || 30);
  const [data, setData] = useState<ApiPerformanceTeam>(initial);
  const [loading, setLoading] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("done");

  const load = useCallback(async (d: number) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/performance?days=${d}`);
      const json = (await res.json()) as ApiPerformanceTeam;
      if (json && Array.isArray(json.members)) setData(json);
    } catch {
      /* keep stale data */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (days !== initial.days) load(days);
  }, [days, initial.days, load]);

  const members = [...(data.members ?? [])].sort((a, b) => {
    if (sortKey === "avg_cycle_h") return (a.avg_cycle_h ?? 1e9) - (b.avg_cycle_h ?? 1e9);
    if (sortKey === "on_time_pct") return (b.on_time_pct ?? -1) - (a.on_time_pct ?? -1);
    return (b[sortKey] ?? 0) - (a[sortKey] ?? 0);
  });

  const totalDone = members.reduce((s, m) => s + m.done, 0);
  const totalOverdue = members.reduce((s, m) => s + m.overdue, 0);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <div className="label-ops text-2xs mb-1">Đánh giá hiệu suất</div>
          <h1 className="text-lg text-text-primary">Hiệu suất thành viên</h1>
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.days}
              onClick={() => setDays(p.days)}
              className={clsx(
                "px-3 py-1.5 text-2xs mono border transition-colors",
                days === p.days
                  ? "border-accent-amber text-accent-amber"
                  : "border-divider text-text-tertiary hover:text-text-secondary"
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="ops-surface p-3">
          <div className="label-ops text-2xs">Thành viên</div>
          <div className="text-xl mono text-text-primary">{members.length}</div>
        </div>
        <div className="ops-surface p-3">
          <div className="label-ops text-2xs">Hoàn thành ({days}d)</div>
          <div className="text-xl mono text-signal-p3">{totalDone}</div>
        </div>
        <div className="ops-surface p-3">
          <div className="label-ops text-2xs">Quá hạn hiện tại</div>
          <div className="text-xl mono text-signal-p0">{totalOverdue}</div>
        </div>
      </div>

      {members.length === 0 ? (
        <div className="ops-surface p-10 text-center">
          <div className="text-md text-text-secondary mb-1">Chưa có dữ liệu hiệu suất</div>
          <div className="mono text-2xs text-text-tertiary">
            Khởi động Telegram bot để đồng bộ ·{" "}
            <a href="/telegram" className="text-accent-amber hover:underline">/telegram</a>
          </div>
        </div>
      ) : (
        <div className={clsx("ops-surface overflow-x-auto", loading && "opacity-60")}>
          <table className="w-full text-xs">
            <thead>
              <tr className="label-ops text-2xs border-b border-divider-strong">
                <th className="text-left p-3">Thành viên</th>
                <th className="text-right p-3 cursor-pointer" onClick={() => setSortKey("done")}>Done / Giao</th>
                <th className="text-right p-3 cursor-pointer" onClick={() => setSortKey("on_time_pct")}>On-time</th>
                <th className="text-right p-3 cursor-pointer" onClick={() => setSortKey("avg_cycle_h")}>Cycle</th>
                <th className="text-right p-3">P0/P1</th>
                <th className="text-right p-3 cursor-pointer" onClick={() => setSortKey("overdue")}>Đang/Trễ</th>
                <th className="text-right p-3">Hoãn/Từ chối</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => {
                const v = verdict(m);
                return (
                  <tr key={m.telegram_id} className="border-b border-divider hover:bg-surface-raised">
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className={clsx("inline-block w-2 h-2 rounded-full", v.dot)} title={v.text} />
                        <span className="text-text-primary">{m.full_name}</span>
                      </div>
                      <div className="mono text-2xs text-text-tertiary ml-4">{v.text}</div>
                    </td>
                    <td className="text-right p-3 mono">
                      <span className="text-text-primary">{m.done}</span>
                      <span className="text-text-tertiary"> / {m.assigned}</span>
                    </td>
                    <td className={clsx("text-right p-3 mono",
                      m.on_time_pct == null ? "text-text-tertiary"
                        : m.on_time_pct >= 85 ? "text-signal-p3"
                        : m.on_time_pct < 60 ? "text-signal-p0" : "text-text-primary")}>
                      {pct(m.on_time_pct)}
                    </td>
                    <td className="text-right p-3 mono text-text-secondary">{cycle(m.avg_cycle_h)}</td>
                    <td className="text-right p-3 mono text-text-secondary">{m.p0_done}/{m.p1_done}</td>
                    <td className="text-right p-3 mono">
                      <span className="text-text-secondary">{m.active}</span>
                      <span className={clsx(m.overdue > 0 ? "text-signal-p0" : "text-text-tertiary")}> / {m.overdue}</span>
                    </td>
                    <td className="text-right p-3 mono text-text-tertiary">
                      {m.defer_total}/{m.declined}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="mono text-2xs text-text-tertiary mt-3">
        Số liệu từ task thật (completed_at, deadline, actual_minutes) · on-time chỉ tính task có deadline ·
        chấm điểm: 🟢 đáng tin (on-time ≥85%, ≥5 task) · 🟡 ổn định · 🔴 cần xem lại (&lt;60%).
      </div>
    </div>
  );
}
