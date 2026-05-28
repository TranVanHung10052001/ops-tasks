"use client";

import { TASKS, MEMBERS, formatDeadline, statusLabel, OpsTask, Member, Priority } from "@/lib/mock";
import SignalBadge from "./signal-badge";
import clsx from "clsx";

function exportCsv(tasks: OpsTask[], members: Member[]) {
  const headers = ["ID", "Kênh", "Nội dung", "Người thực hiện", "Mức độ", "Trạng thái", "Thời hạn", "Tags", "Tạo bởi"];
  const rows = tasks.map((t) => {
    const m = members.find((mb) => mb.id === t.assignee);
    const d = formatDeadline(t.deadline);
    return [
      t.id,
      t.channel,
      `"${t.title.replace(/"/g, '""')}"`,
      m ? `${m.initials} ${m.name}` : t.assignee,
      t.priority,
      statusLabel(t.status),
      `${d.date} ${d.time}`,
      t.tags.join("; "),
      t.createdBy,
    ];
  });
  const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ops-tasks-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

const STATUS_DOT_CLASS: Record<string, string> = {
  dang_lam: "active",
  bi_chan: "blocked",
  can_lam: "pending",
  dang_review: "done",
  hoan_thanh: "done",
  tam_dung: "paused",
  cho_xu_ly: "pending",
};

const PRIORITY_BAR: Record<Priority, string> = {
  P0: "bg-signal-p0",
  P1: "bg-signal-p1",
  P2: "bg-signal-p2",
  P3: "bg-signal-p3",
  P4: "bg-signal-p4",
};

export default function TaskLedger({
  limit,
  title = "Task đang hoạt động",
  tasks: tasksProp,
  members: membersProp,
  onTaskClick,
  onCreateTask,
}: {
  limit?: number;
  title?: string;
  tasks?: OpsTask[];
  members?: Member[];
  onTaskClick?: (task: OpsTask) => void;
  onCreateTask?: () => void;
}) {
  const allTasks = tasksProp ?? TASKS;
  const allMembers = membersProp ?? MEMBERS;
  const now = Date.now();
  const tasks = (limit ? allTasks.slice(0, limit) : allTasks).sort((a, b) => {
    const order: Priority[] = ["P0", "P1", "P2", "P3", "P4"];
    const aTs = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const bTs = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    const aOverdue = aTs < now ? -1 : 0;
    const bOverdue = bTs < now ? -1 : 0;
    const aBlocked = a.status === "bi_chan" ? -1 : 0;
    const bBlocked = b.status === "bi_chan" ? -1 : 0;
    const priorityDiff = order.indexOf(a.priority) - order.indexOf(b.priority);
    if (priorityDiff !== 0) return priorityDiff;
    return (aOverdue + aBlocked) - (bOverdue + bBlocked);
  });

  return (
    <section className="ops-surface">
      <header className="flex items-center justify-between px-5 py-3 border-b border-divider">
        <div className="flex items-baseline gap-3">
          <span className="section-label">{title}</span>
          <span className="mono text-2xs text-text-tertiary">{tasks.length} task</span>
        </div>
        <div className="flex items-center gap-2 mono text-2xs text-text-tertiary">
          <button className="btn-ops" onClick={() => window.history.back()}>⊞ Bảng điều vận</button>
          <button className="btn-ops" onClick={() => exportCsv(tasks, allMembers)}>↧ Xuất CSV</button>
          <button className="btn-ops primary" onClick={onCreateTask}>+ Tạo task</button>
        </div>
      </header>

      <div className="overflow-x-auto scroll-ops">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-divider mono text-2xs tracking-wider text-text-tertiary">
              <th className="w-1.5 p-0" />
              <th className="px-3 py-2 font-normal">Mã task</th>
              <th className="px-3 py-2 font-normal w-20">Kênh</th>
              <th className="px-3 py-2 font-normal">Nội dung</th>
              <th className="px-3 py-2 font-normal w-24">Người thực hiện</th>
              <th className="px-3 py-2 font-normal w-24">Mức độ</th>
              <th className="px-3 py-2 font-normal w-28">Trạng thái</th>
              <th className="px-3 py-2 font-normal w-32 text-right">Thời hạn</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t: OpsTask) => {
              const m = allMembers.find((mb) => mb.id === t.assignee);
              const d = formatDeadline(t.deadline);
              const overdue = d.relative.startsWith("quá");
              const blocked = t.status === "bi_chan";
              return (
                <tr
                  key={t.id}
                  onClick={() => onTaskClick?.(t)}
                  className={clsx(
                    "border-b border-divider transition-colors group cursor-pointer",
                    overdue ? "bg-signal-p0/5 hover:bg-signal-p0/10" :
                    blocked ? "bg-signal-p1/5 hover:bg-signal-p1/10" :
                    "hover:bg-surface-raised"
                  )}
                >
                  <td className={clsx("p-0", PRIORITY_BAR[t.priority])} />
                  <td className="px-3 py-2.5 mono text-xs text-text-secondary tabular">{t.id}</td>
                  <td className="px-3 py-2.5">
                    <span className="mono text-2xs uppercase tracking-wider px-1.5 py-0.5 border border-divider-strong text-text-secondary">
                      {t.channel}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="text-md text-text-primary leading-snug">{t.title}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="mono text-2xs text-text-tertiary">{t.channelLabel}</span>
                      {t.tags.slice(0, 2).map((tag) => (
                        <span key={tag} className="mono text-2xs text-accent-paper">
                          #{tag}
                        </span>
                      ))}
                      {t.aiClassified && (
                        <span className="mono text-2xs text-accent-amber flex items-center gap-1">
                          ⊙ AI {Math.round((t.aiConfidence || 0) * 100)}%
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    {m && (
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 border border-divider-strong bg-surface mono text-2xs flex items-center justify-center text-accent-paper">
                          {m.initials}
                        </div>
                        <div className="leading-tight">
                          <div className="text-xs text-text-primary">{m.name}</div>
                          <div className="mono text-2xs text-text-tertiary">{m.initials}</div>
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <SignalBadge priority={t.priority} outline={t.priority === "P3" || t.priority === "P4"} />
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className={clsx("status-dot", STATUS_DOT_CLASS[t.status])} />
                      <span className="text-xs text-text-secondary">{statusLabel(t.status)}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <div className="mono text-xs text-text-primary tabular">
                      {d.date} · {d.time}
                    </div>
                    <div className={clsx("mono text-2xs", overdue ? "text-signal-p0/75" : "text-text-tertiary")}>
                      {d.relative}
                    </div>
                    {overdue && (
                      <div className="mono text-2xs text-signal-p0/70">⚠ trễ</div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
