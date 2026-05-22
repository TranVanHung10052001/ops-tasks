"use client";

import { useState, useCallback } from "react";
import { Member, OpsTask, TaskStatus, MEMBERS } from "@/lib/mock";
import CreateTaskModal from "@/components/ui/create-task-modal";
import TaskDetailModal from "@/components/ui/task-detail-modal";
import SignalBadge from "@/components/ui/signal-badge";
import { formatDeadline, statusLabel } from "@/lib/mock";
import clsx from "clsx";

const GRADE_COLOR: Record<string, string> = {
  "G4":     "text-accent-amber border-accent-amber",
  "G3":     "text-signal-p3 border-signal-p3",
  "ACT-G3": "text-signal-p2 border-signal-p2",
  "G2":     "text-text-secondary border-divider-strong",
  "G1":     "text-text-tertiary border-divider",
};

interface Props {
  members: Member[];
  tasks: OpsTask[];
}

export default function TeamView({ members: membersProp, tasks: tasksProp }: Props) {
  const members = membersProp.length ? membersProp : MEMBERS;
  const [tasks, setTasks] = useState<OpsTask[]>(tasksProp);

  // Create-task modal state: null = closed, string = defaultAssignee member ID
  const [createForMember, setCreateForMember] = useState<string | null>(null);

  // Member detail panel: null = closed, Member = open
  const [detailMember, setDetailMember] = useState<Member | null>(null);

  // Selected task (from member detail panel)
  const [selectedTask, setSelectedTask] = useState<OpsTask | null>(null);

  const online = members.filter((m) => m.status === "online" || m.status === "busy").length;
  const memberById = (id: string) => members.find((m) => m.id === id);

  const handleCreateTask = useCallback(async (taskData: Omit<OpsTask, "id" | "createdAt">) => {
    const tempId = `T-${Date.now().toString().slice(-7)}`;
    const newTask: OpsTask = { ...taskData, id: tempId, createdAt: new Date().toISOString() };
    setTasks((prev) => [newTask, ...prev]);
    try {
      await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: taskData.title,
          priority: taskData.priority,
          status: "pending",
          category: taskData.channel.toLowerCase(),
          deadline: taskData.deadline,
          assignee_id: taskData.assignee.replace("m", ""),
          block_reason: taskData.description,
        }),
      });
    } catch { /* optimistic — no rollback */ }
  }, []);

  const handleStatusChange = useCallback(async (taskId: string, newStatus: TaskStatus) => {
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t)));
    setSelectedTask((prev) => (prev?.id === taskId ? { ...prev, status: newStatus } : prev));
    try {
      const numericId = taskId.replace(/\D/g, "").slice(-5);
      await fetch(`/api/tasks/${numericId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch { /* silent */ }
  }, []);

  return (
    <>
      {/* Header */}
      <div className="flex items-end justify-between mb-5">
        <div>
          <div className="label-ops text-2xs mb-1.5">Ops · 04 · Nhóm điều vận</div>
          <h1 className="text-2xl text-text-primary editorial leading-tight">
            Đội điều vận xe tải · {members.length} thành viên.
          </h1>
          <p className="text-md text-text-secondary mt-1">
            {online}/{members.length} thành viên đang trực · ca ngày 06:00 → 18:00 · ca đêm 18:00 → 06:00.
          </p>
        </div>
        <button
          className="btn-ops primary"
          onClick={() => setCreateForMember(members[1]?.id ?? members[0]?.id ?? "m0")}
        >
          + Giao task mới
        </button>
      </div>

      {/* Member cards */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        {members.map((m) => {
          const memberTasks = tasks.filter((t) => t.assignee === m.id);
          const activeTasks = memberTasks.filter((t) => t.status !== "hoan_thanh" && t.status !== "tam_dung");
          const p0 = activeTasks.filter((t) => t.priority === "P0").length;
          const blocked = activeTasks.filter((t) => t.status === "bi_chan").length;
          const overdue = activeTasks.filter((t) => new Date(t.deadline) < new Date()).length;
          const loadPct = (m.workload / m.workloadMax) * 100;

          return (
            <div key={m.id} className="ops-surface p-4 relative group">
              {/* Status chip */}
              {m.status === "online" && (
                <div className="absolute top-3 right-3 flex items-center gap-1.5">
                  <span className="status-dot active" />
                  <span className="mono text-2xs text-state-active uppercase tracking-wider">trực</span>
                </div>
              )}
              {m.status === "busy" && (
                <div className="absolute top-3 right-3 flex items-center gap-1.5">
                  <span className="status-dot pending" />
                  <span className="mono text-2xs text-state-pending uppercase tracking-wider">bận</span>
                </div>
              )}
              {m.status === "away" && (
                <div className="absolute top-3 right-3 flex items-center gap-1.5">
                  <span className="status-dot paused" />
                  <span className="mono text-2xs text-state-paused uppercase tracking-wider">vắng</span>
                </div>
              )}
              {m.status === "offline" && (
                <div className="absolute top-3 right-3 flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-text-disabled" />
                  <span className="mono text-2xs text-text-disabled uppercase tracking-wider">off</span>
                </div>
              )}

              {/* Member identity */}
              <div className="flex items-start gap-3 mb-4">
                <div className="callsign large">{m.initials}</div>
                <div className="flex-1 mt-1">
                  <div className="flex items-center gap-2">
                    <div className="text-md text-text-primary leading-tight">{m.name}</div>
                    {m.grade && (
                      <span className={clsx(
                        "mono text-2xs border px-1 py-px leading-none shrink-0",
                        GRADE_COLOR[m.grade] ?? "text-text-tertiary border-divider"
                      )}>
                        {m.grade}
                      </span>
                    )}
                  </div>
                  <div className="mono text-2xs text-text-tertiary tracking-wider mt-0.5">{m.initials}</div>
                  <div className="text-xs text-text-tertiary mt-1 leading-snug">{m.role}</div>
                  {m.email && (
                    <div className="mono text-2xs text-text-disabled mt-1 truncate">{m.email}</div>
                  )}
                  {m.reportsTo && memberById(m.reportsTo) && (
                    <div className="mono text-2xs text-text-disabled mt-0.5">
                      ↑ {memberById(m.reportsTo)!.initials}
                    </div>
                  )}
                </div>
              </div>

              {/* Workload bar */}
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="label-ops text-2xs">Tải công việc</span>
                  <span className="mono text-xs text-text-primary tabular">{m.workload}/{m.workloadMax}</span>
                </div>
                <div className="flex gap-px h-3">
                  {Array.from({ length: m.workloadMax }).map((_, i) => (
                    <div
                      key={i}
                      className={clsx(
                        "flex-1",
                        i < m.workload
                          ? loadPct > 80 ? "bg-signal-p0" : loadPct > 60 ? "bg-signal-p2" : "bg-signal-p3"
                          : "bg-surface-deep border-y border-divider-strong"
                      )}
                    />
                  ))}
                </div>
              </div>

              {/* Mini stats */}
              <div className="grid grid-cols-4 gap-0 border-y border-divider py-2">
                <div className="text-center border-r border-divider">
                  <div className="mono text-md text-text-primary tabular">{activeTasks.length}</div>
                  <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">task</div>
                </div>
                <div className="text-center border-r border-divider">
                  <div className={clsx("mono text-md tabular", p0 > 0 ? "text-signal-p0" : "text-text-tertiary")}>
                    {p0}
                  </div>
                  <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">p0</div>
                </div>
                <div className="text-center border-r border-divider">
                  <div className={clsx("mono text-md tabular", blocked > 0 ? "text-signal-p1" : "text-text-tertiary")}>
                    {blocked}
                  </div>
                  <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">chặn</div>
                </div>
                <div className="text-center">
                  <div className={clsx("mono text-md tabular", overdue > 0 ? "text-signal-p0" : "text-text-tertiary")}>
                    {overdue}
                  </div>
                  <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">trễ</div>
                </div>
              </div>

              {/* Top task preview */}
              {activeTasks[0] && (
                <div className="mt-3 text-xs">
                  <div className="label-ops text-2xs mb-1">Đang xử lý</div>
                  <div className="text-text-primary leading-snug line-clamp-2">{activeTasks[0].title}</div>
                </div>
              )}

              <div className="dotted-divider my-3" />

              {/* Action buttons */}
              <div className="flex items-center justify-between">
                <button
                  className="mono text-2xs text-accent-paper uppercase tracking-wider hover:text-accent-amber transition-colors"
                  onClick={() => setDetailMember(m)}
                >
                  ► Chi tiết ({activeTasks.length})
                </button>
                <button
                  className="mono text-2xs text-text-tertiary uppercase tracking-wider hover:text-text-primary border border-divider px-2 py-1 hover:border-accent-amber transition-colors"
                  onClick={() => setCreateForMember(m.id)}
                >
                  + Giao task
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Capacity overview */}
      <section className="ops-surface p-5 mb-5">
        <header className="flex items-center justify-between mb-4">
          <div>
            <div className="label-ops text-2xs">Tổng quan năng lực</div>
            <div className="mono text-2xs text-text-tertiary mt-0.5">live · từ bot API</div>
          </div>
        </header>
        <div className="space-y-3">
          {members.map((m) => {
            const loadPct = (m.workload / m.workloadMax) * 100;
            const isOver = loadPct > 80;
            return (
              <div key={m.id} className="flex items-center gap-3">
                <div className="w-10 mono text-xs text-text-secondary tracking-wider shrink-0">{m.initials}</div>
                <div className="w-32 text-sm text-text-primary shrink-0">{m.name}</div>
                <div className="flex-1 h-5 bg-surface-deep border border-divider relative">
                  <div
                    className={clsx(
                      "absolute top-0 bottom-0 left-0",
                      isOver ? "bg-signal-p0/50" : loadPct > 60 ? "bg-signal-p2/40" : "bg-signal-p3/40"
                    )}
                    style={{ width: `${loadPct}%` }}
                  />
                  <div
                    className="absolute top-0 bottom-0 w-px bg-text-tertiary opacity-50"
                    style={{ left: "80%" }}
                    title="Ngưỡng overload 80%"
                  />
                </div>
                <div className="w-16 text-right mono text-xs text-text-primary tabular shrink-0">
                  {Math.round(loadPct)}%
                </div>
                {isOver ? (
                  <span className="mono text-2xs text-signal-p0 uppercase tracking-wider shrink-0 w-20">⚠ overload</span>
                ) : (
                  <span className="shrink-0 w-20" />
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Org chart */}
      <section className="ops-surface p-5">
        <div className="label-ops text-2xs mb-4">Sơ đồ tổ chức · Q2/2026</div>
        <div className="space-y-1 font-mono text-xs">
          {members.filter((m) => !m.reportsTo).map((mgr) => {
            const directReports = members.filter((m) => m.reportsTo === mgr.id);
            return (
              <div key={mgr.id}>
                <div className="flex items-center gap-2 py-1">
                  <span className={clsx("border px-1.5 py-px leading-none", GRADE_COLOR[mgr.grade] ?? "text-text-tertiary border-divider")}>
                    {mgr.grade}
                  </span>
                  <span className="text-text-secondary">{mgr.initials}</span>
                  <span className="text-text-primary">{mgr.fullName}</span>
                  <span className="text-text-disabled">—</span>
                  <span className="text-text-tertiary">{mgr.role}</span>
                </div>
                {directReports.map((dr) => {
                  const drReports = members.filter((m) => m.reportsTo === dr.id);
                  return (
                    <div key={dr.id} className="ml-6">
                      <div className="flex items-center gap-2 py-0.5 text-text-secondary">
                        <span className="text-text-disabled">└─</span>
                        <span className={clsx("border px-1 py-px leading-none text-2xs", GRADE_COLOR[dr.grade] ?? "text-text-tertiary border-divider")}>
                          {dr.grade}
                        </span>
                        <span>{dr.initials}</span>
                        <span className="text-text-primary">{dr.fullName}</span>
                        <span className="text-text-disabled">·</span>
                        <span className="text-text-tertiary truncate">{dr.email}</span>
                      </div>
                      {drReports.map((l2) => (
                        <div key={l2.id} className="ml-8 flex items-center gap-2 py-0.5 text-text-tertiary">
                          <span className="text-text-disabled">└─</span>
                          <span className={clsx("border px-1 py-px leading-none text-2xs", GRADE_COLOR[l2.grade] ?? "text-text-tertiary border-divider")}>
                            {l2.grade}
                          </span>
                          <span>{l2.initials}</span>
                          <span className="text-text-secondary">{l2.fullName}</span>
                          <span className="text-text-disabled">·</span>
                          <span className="truncate">{l2.email}</span>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Member detail panel ───────────────────────────────────────── */}
      {detailMember && (
        <div className="fixed inset-0 z-[100] flex items-start justify-end">
          <div className="absolute inset-0 bg-canvas/60 backdrop-blur-sm" onClick={() => setDetailMember(null)} />
          <aside className="relative z-10 w-[480px] h-full bg-surface border-l-2 border-divider-strong shadow-2xl flex flex-col overflow-hidden">
            {/* Panel header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-divider shrink-0">
              <div className="flex items-center gap-3">
                <div className="callsign large">{detailMember.initials}</div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-md text-text-primary">{detailMember.fullName}</span>
                    <span className={clsx("mono text-2xs border px-1 py-px leading-none", GRADE_COLOR[detailMember.grade] ?? "text-text-tertiary border-divider")}>
                      {detailMember.grade}
                    </span>
                  </div>
                  <div className="mono text-2xs text-text-tertiary mt-0.5">{detailMember.initials} · {detailMember.role}</div>
                  <div className="mono text-2xs text-text-disabled mt-0.5">{detailMember.email}</div>
                </div>
              </div>
              <button
                onClick={() => setDetailMember(null)}
                className="mono text-xl text-text-tertiary hover:text-text-primary leading-none"
              >×</button>
            </div>

            {/* Action bar */}
            <div className="px-5 py-2.5 border-b border-divider flex items-center gap-2 shrink-0">
              <button
                className="btn-ops primary flex items-center gap-1.5"
                onClick={() => { setCreateForMember(detailMember.id); setDetailMember(null); }}
              >
                + Giao task
              </button>
              <div className="flex-1" />
              <span className="mono text-2xs text-text-tertiary">
                {tasks.filter((t) => t.assignee === detailMember.id && t.status !== "hoan_thanh" && t.status !== "tam_dung").length} task active
              </span>
            </div>

            {/* Tasks list */}
            <div className="flex-1 overflow-y-auto scroll-ops">
              {tasks
                .filter((t) => t.assignee === detailMember.id && t.status !== "hoan_thanh" && t.status !== "tam_dung")
                .sort((a, b) => {
                  const order = ["P0", "P1", "P2", "P3", "P4"];
                  return order.indexOf(a.priority) - order.indexOf(b.priority);
                })
                .map((task) => {
                  const d = formatDeadline(task.deadline);
                  const overdue = d.relative.startsWith("quá");
                  return (
                    <div
                      key={task.id}
                      className={clsx(
                        "px-5 py-3 border-b border-divider cursor-pointer hover:bg-surface-raised transition-colors",
                        overdue ? "bg-signal-p0/5" : task.status === "bi_chan" ? "bg-signal-p1/5" : ""
                      )}
                      onClick={() => setSelectedTask(task)}
                    >
                      <div className="flex items-start gap-2.5">
                        <SignalBadge priority={task.priority} />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-text-primary leading-snug line-clamp-2">{task.title}</div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="mono text-2xs text-text-tertiary">{task.id}</span>
                            <span className="mono text-2xs text-text-tertiary">·</span>
                            <span className={clsx("mono text-2xs font-bold", overdue ? "text-signal-p0" : "text-text-tertiary")}>
                              {d.relative}
                            </span>
                            <span className="mono text-2xs text-text-tertiary">·</span>
                            <span className="mono text-2xs text-text-secondary">{statusLabel(task.status)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              {tasks.filter((t) => t.assignee === detailMember.id && t.status !== "hoan_thanh" && t.status !== "tam_dung").length === 0 && (
                <div className="px-5 py-8 text-center">
                  <div className="mono text-2xs text-text-disabled uppercase tracking-wider">Không có task active</div>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}

      {/* ── Create task modal ────────────────────────────────────────── */}
      {createForMember && (
        <CreateTaskModal
          members={members}
          defaultAssignee={createForMember}
          onClose={() => setCreateForMember(null)}
          onSubmit={async (taskData) => {
            await handleCreateTask(taskData);
            setCreateForMember(null);
          }}
        />
      )}

      {/* ── Task detail modal (from member panel) ───────────────────── */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          members={members}
          onClose={() => setSelectedTask(null)}
          onStatusChange={handleStatusChange}
        />
      )}
    </>
  );
}
