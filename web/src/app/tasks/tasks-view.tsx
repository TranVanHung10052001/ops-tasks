"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import DispatchBoard from "@/components/ui/dispatch-board";
import StatusBoard from "@/components/ui/dispatch-board-status";
import TaskLedger from "@/components/ui/task-ledger";
import TimelineTrack from "@/components/ui/timeline-track";
import TaskDetailModal from "@/components/ui/task-detail-modal";
import CreateTaskModal from "@/components/ui/create-task-modal";
import { OpsTask, Member, TaskStatus, Priority, TASKS, MEMBERS } from "@/lib/mock";
import clsx from "clsx";

const VIEWS = [
  { key: "board",        label: "Bảng điều vận", sub: "Kanban theo tín hiệu" },
  { key: "status-board", label: "Trạng thái",    sub: "Kanban theo tiến độ" },
  { key: "ledger",       label: "Sổ theo dõi",   sub: "Bảng dense" },
  { key: "timeline",     label: "Timeline",       sub: "Theo giờ" },
] as const;

type DateFilter = "all" | "today" | "week" | "month" | "year";

const DATE_FILTERS: { key: DateFilter; label: string }[] = [
  { key: "all",   label: "Tất cả" },
  { key: "today", label: "Hôm nay" },
  { key: "week",  label: "Tuần này" },
  { key: "month", label: "Tháng này" },
  { key: "year",  label: "Năm này" },
];

function isInDateRange(task: OpsTask, filter: DateFilter): boolean {
  if (filter === "all") return true;
  if (!task.deadline) return true; // no deadline → always show
  const dl = new Date(task.deadline);
  if (isNaN(dl.getTime())) return true;
  const now = new Date();
  // Overdue tasks always visible (need immediate attention)
  if (dl < now) return true;
  const y = now.getFullYear(), mo = now.getMonth();
  const dayStart = new Date(y, mo, now.getDate());
  switch (filter) {
    case "today":
      return dl >= dayStart && dl < new Date(dayStart.getTime() + 86_400_000);
    case "week": {
      const dow = now.getDay();
      const mondayOff = dow === 0 ? -6 : 1 - dow;
      const weekStart = new Date(dayStart);
      weekStart.setDate(dayStart.getDate() + mondayOff);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 7);
      return dl >= weekStart && dl < weekEnd;
    }
    case "month":
      return dl.getFullYear() === y && dl.getMonth() === mo;
    case "year":
      return dl.getFullYear() === y;
  }
}

export default function TasksView({
  tasks: tasksProp,
  members: membersProp,
}: {
  tasks?: OpsTask[];
  members?: Member[];
}) {
  const [view, setView]           = useState<(typeof VIEWS)[number]["key"]>("board");
  const [tasks, setTasks]         = useState<OpsTask[]>(tasksProp ?? TASKS);
  const members                   = membersProp ?? MEMBERS;

  useEffect(() => { if (tasksProp) setTasks(tasksProp); }, [tasksProp]);

  const [selectedTask, setSelectedTask] = useState<OpsTask | null>(null);
  const [editTask, setEditTask]         = useState<OpsTask | null>(null);
  const [createOpen, setCreateOpen]     = useState(false);
  const [searchOpen, setSearchOpen]     = useState(false);
  const [searchQuery, setSearchQuery]   = useState("");
  const [dateFilter, setDateFilter]     = useState<DateFilter>("all");
  const [zoomed, setZoomed]             = useState(false);
  const [selectedIds, setSelectedIds]   = useState<Set<string>>(new Set());
  const searchRef = useRef<HTMLInputElement>(null);

  // ── Filtered task list (search + date) ───────────────────────────────────
  const filteredTasks = useMemo(() => {
    let result = tasks;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((t) =>
        t.title.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q) ||
        t.channelLabel.toLowerCase().includes(q) ||
        t.tags.some((tag) => tag.toLowerCase().includes(q)) ||
        members.find((m) => m.id === t.assignee)?.name.toLowerCase().includes(q) ||
        members.find((m) => m.id === t.assignee)?.initials.toLowerCase().includes(q)
      );
    }
    if (dateFilter !== "all") {
      result = result.filter((t) => isInDateRange(t, dateFilter));
    }
    return result;
  }, [tasks, searchQuery, dateFilter, members]);

  const handleTaskClick = useCallback((task: OpsTask) => setSelectedTask(task), []);

  // ── Keyboard shortcuts ───────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "n") { e.preventDefault(); setCreateOpen(true); }
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchRef.current?.focus(), 50);
      }
      if (e.key === "Escape") {
        setCreateOpen(false); setSelectedTask(null); setEditTask(null);
        setSearchOpen(false); setSearchQuery(""); setZoomed(false);
        if (selectedIds.size > 0) setSelectedIds(new Set());
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedIds]);

  // ── Task CRUD ─────────────────────────────────────────────────────────────

  const handleCreateTask = useCallback(async (taskData: Omit<OpsTask, "id" | "createdAt">) => {
    const tempId = `T-${Date.now().toString().slice(-7)}`;
    setTasks((prev) => [{ ...taskData, id: tempId, createdAt: new Date().toISOString() }, ...prev]);
    try {
      await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: taskData.title, priority: taskData.priority, status: "pending",
          category: taskData.channel.toLowerCase(), deadline: taskData.deadline,
          assignee_id: taskData.assignee.replace(/\D/g, ""), block_reason: taskData.description,
        }),
      });
    } catch {}
  }, []);

  const handleUpdateTask = useCallback(async (taskId: string, taskData: Omit<OpsTask, "id" | "createdAt">) => {
    setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, ...taskData } : t));
    setSelectedTask((prev) => prev?.id === taskId ? { ...prev, ...taskData } : prev);
    setEditTask(null);
    try {
      const num = taskId.replace(/\D/g, "").slice(-5);
      await fetch(`/api/tasks/${num}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: taskData.title, priority: taskData.priority, deadline: taskData.deadline,
          assignee_id: taskData.assignee.replace(/\D/g, ""), block_reason: taskData.description,
        }),
      });
    } catch {}
  }, []);

  const handleStatusChange = useCallback(async (taskId: string, newStatus: TaskStatus) => {
    setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, status: newStatus } : t));
    setSelectedTask((prev) => prev?.id === taskId ? { ...prev, status: newStatus } : prev);
    try {
      const num = taskId.replace(/\D/g, "").slice(-5);
      await fetch(`/api/tasks/${num}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: newStatus }) });
    } catch {}
  }, []);

  const handlePriorityChange = useCallback(async (taskId: string, newPriority: Priority) => {
    setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, priority: newPriority } : t));
    setSelectedTask((prev) => prev?.id === taskId ? { ...prev, priority: newPriority } : prev);
    try {
      const num = taskId.replace(/\D/g, "").slice(-5);
      await fetch(`/api/tasks/${num}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ priority: newPriority }) });
    } catch {}
  }, []);

  const handleQuickCreateWithStatus = useCallback(async (title: string, status: TaskStatus) => {
    const tempId = `T-${Date.now().toString().slice(-7)}`;
    setTasks((prev) => [{ id: tempId, channel: "Adhoc", channelLabel: "Phát sinh", title,
      assignee: members[0]?.id ?? "m0", priority: "P2", status,
      deadline: new Date(Date.now() + 3 * 86_400_000).toISOString(),
      estimateHours: 2, tags: [], createdAt: new Date().toISOString(), createdBy: "Web · OPS-10",
    }, ...prev]);
    try {
      await fetch("/api/tasks", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ summary: title, priority: "P2", status, category: "adhoc" }) });
    } catch {}
  }, [members]);

  const handleDeleteTask = useCallback(async (taskId: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
    setSelectedTask(null);
    setSelectedIds((prev) => { const n = new Set(prev); n.delete(taskId); return n; });
    try {
      const num = taskId.replace(/\D/g, "").slice(-5);
      await fetch(`/api/tasks/${num}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "cancelled" }) });
    } catch {}
  }, []);

  // ── Multi-select & batch ──────────────────────────────────────────────────

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }, []);

  const clearSelection = useCallback(() => setSelectedIds(new Set()), []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(filteredTasks.map((t) => t.id)));
  }, [filteredTasks]);

  const handleBatchPriority = useCallback(async (priority: Priority) => {
    const ids = [...selectedIds];
    setTasks((prev) => prev.map((t) => ids.includes(t.id) ? { ...t, priority } : t));
    clearSelection();
    await Promise.allSettled(ids.map((id) => {
      const num = id.replace(/\D/g, "").slice(-5);
      return fetch(`/api/tasks/${num}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ priority }) });
    }));
  }, [selectedIds, clearSelection]);

  const handleBatchStatus = useCallback(async (status: TaskStatus) => {
    const ids = [...selectedIds];
    setTasks((prev) => prev.map((t) => ids.includes(t.id) ? { ...t, status } : t));
    clearSelection();
    await Promise.allSettled(ids.map((id) => {
      const num = id.replace(/\D/g, "").slice(-5);
      return fetch(`/api/tasks/${num}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    }));
  }, [selectedIds, clearSelection]);

  const handleBatchDelete = useCallback(async () => {
    const ids = [...selectedIds];
    setTasks((prev) => prev.filter((t) => !ids.includes(t.id)));
    clearSelection();
    await Promise.allSettled(ids.map((id) => {
      const num = id.replace(/\D/g, "").slice(-5);
      return fetch(`/api/tasks/${num}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "cancelled" }) });
    }));
  }, [selectedIds, clearSelection]);

  const selectionActive = selectedIds.size > 0;

  return (
    <>
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex gap-0 border border-divider-strong">
          {VIEWS.map((v) => (
            <button key={v.key} onClick={() => setView(v.key)}
              className={clsx(
                "px-3 py-1.5 mono text-2xs uppercase tracking-wider transition-colors border-r border-divider-strong last:border-r-0",
                view === v.key ? "bg-accent-amber-deep text-canvas" : "bg-surface text-text-secondary hover:bg-surface-raised"
              )}>
              {v.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setSearchOpen(s => !s); setTimeout(() => searchRef.current?.focus(), 50); }}
            className={clsx("btn-ops flex items-center gap-1.5", searchOpen && "border-accent-amber text-accent-amber")}>
            {">"} Tìm <span className="kbd">⌘K</span>
          </button>
          {view === "board" && (
            <button onClick={() => setZoomed(z => !z)}
              className={clsx("btn-ops flex items-center gap-1.5", zoomed && "border-accent-amber text-accent-amber")}
              title="Phóng to bảng (Esc để thoát)">
              {zoomed ? "⊡ Thu nhỏ" : "⊞ Zoom"}
            </button>
          )}
          <button onClick={() => setCreateOpen(true)} className="btn-ops primary flex items-center gap-1.5">
            + Tạo task <span className="kbd opacity-60">⌘N</span>
          </button>
          <div className="flex items-center gap-2 mono text-2xs text-text-tertiary">
            <span className="status-dot active" /> live
          </div>
        </div>
      </div>

      {/* ── Date filter + selection bar ── */}
      <div className="flex items-center gap-2 mb-4">
        <span className="mono text-2xs text-text-tertiary shrink-0">Deadline:</span>
        <div className="flex gap-0 border border-divider">
          {DATE_FILTERS.map((f) => (
            <button key={f.key} onClick={() => setDateFilter(f.key)}
              className={clsx(
                "px-3 py-1 mono text-2xs transition-colors border-r border-divider last:border-r-0",
                dateFilter === f.key
                  ? "bg-surface-raised text-accent-paper border-r-divider"
                  : "text-text-tertiary hover:text-text-secondary hover:bg-surface"
              )}>
              {f.label}
            </button>
          ))}
        </div>
        {dateFilter !== "all" && (
          <span className="mono text-2xs text-accent-amber">
            {filteredTasks.length}/{tasks.length} task
          </span>
        )}
        <div className="flex-1" />
        {view === "board" && (
          selectionActive ? (
            <div className="flex items-center gap-2">
              <span className="mono text-2xs text-accent-amber">{selectedIds.size} đã chọn</span>
              <button onClick={clearSelection} className="btn-ops py-0.5 px-2 text-2xs">Bỏ chọn</button>
            </div>
          ) : (
            <button onClick={selectAll} className="btn-ops py-0.5 px-2 text-2xs">☐ Chọn tất cả</button>
          )
        )}
      </div>

      {/* ── Search bar ── */}
      {searchOpen && (
        <div className="flex items-center gap-3 mb-4 p-3 bg-surface-deep border border-divider-strong">
          <span className="mono text-xs text-text-tertiary shrink-0">{">"}</span>
          <input ref={searchRef} type="text" value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên task, mã T-, tags, thành viên…"
            className="flex-1 bg-transparent mono text-sm text-text-primary placeholder:text-text-disabled focus:outline-none"
          />
          {searchQuery && (
            <span className="mono text-2xs text-accent-amber shrink-0">{filteredTasks.length}/{tasks.length} task</span>
          )}
          <button onClick={() => { setSearchOpen(false); setSearchQuery(""); }}
            className="mono text-text-tertiary hover:text-text-primary shrink-0 text-lg leading-none">×</button>
        </div>
      )}

      {/* ── Board (with zoom wrapper) ── */}
      <div className={clsx(
        view === "board" && zoomed
          ? "fixed top-10 left-[220px] right-0 bottom-0 z-40 bg-canvas overflow-auto p-5"
          : ""
      )}>
        {view === "board" && zoomed && (
          <div className="flex items-center justify-between mb-3">
            <span className="section-label">Bảng điều vận · Toàn màn hình</span>
            <button onClick={() => setZoomed(false)} className="btn-ops flex items-center gap-1.5">
              ⊡ Thu nhỏ <span className="kbd">Esc</span>
            </button>
          </div>
        )}
        {view === "board" && (
          <DispatchBoard
            tasks={filteredTasks}
            members={members}
            onTaskClick={handleTaskClick}
            onPriorityChange={handlePriorityChange}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
          />
        )}
      </div>

      {view === "status-board" && (
        <StatusBoard tasks={filteredTasks} members={members} onTaskClick={handleTaskClick}
          onStatusChange={handleStatusChange} onQuickCreate={handleQuickCreateWithStatus} />
      )}
      {view === "ledger" && (
        <TaskLedger tasks={filteredTasks} members={members} onTaskClick={handleTaskClick}
          onCreateTask={() => setCreateOpen(true)} />
      )}
      {view === "timeline" && (
        <TimelineTrack tasks={filteredTasks} members={members} />
      )}

      {/* ── Batch action bar (floating) ── */}
      {selectionActive && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex items-center gap-1.5 bg-surface-deep border border-accent-amber px-4 py-2.5 shadow-2xl">
          <span className="mono text-2xs text-accent-amber shrink-0 mr-1">{selectedIds.size} task ·</span>
          <span className="mono text-2xs text-text-tertiary shrink-0">→</span>
          {(["P0","P1","P2","P3"] as Priority[]).map((p) => (
            <button key={p} onClick={() => handleBatchPriority(p)}
              className={clsx("btn-ops py-1 px-2",
                p === "P0" && "text-signal-p0", p === "P1" && "text-signal-p1",
                p === "P2" && "text-signal-p2", p === "P3" && "text-signal-p3",
              )}>{p}</button>
          ))}
          <div className="w-px h-4 bg-divider-strong mx-1" />
          <button onClick={() => handleBatchStatus("hoan_thanh")} className="btn-ops py-1 px-2 text-signal-p3">✓ Hoàn thành</button>
          <button onClick={() => handleBatchStatus("tam_dung")}   className="btn-ops py-1 px-2">⏸ Tạm dừng</button>
          <div className="w-px h-4 bg-divider-strong mx-1" />
          <button onClick={handleBatchDelete} className="btn-ops py-1 px-2 text-signal-p0">× Xóa</button>
          <button onClick={clearSelection} className="mono text-2xs text-text-tertiary hover:text-text-primary ml-2">Bỏ chọn</button>
        </div>
      )}

      {/* ── Task detail modal ── */}
      {selectedTask && (
        <TaskDetailModal task={selectedTask} members={members}
          onClose={() => setSelectedTask(null)}
          onStatusChange={handleStatusChange}
          onDelete={handleDeleteTask}
          onEdit={(task) => { setEditTask(task); setSelectedTask(null); }}
        />
      )}

      {/* ── Create / Edit task modal ── */}
      {(createOpen || editTask) && (
        <CreateTaskModal
          members={members}
          editTask={editTask ?? undefined}
          onClose={() => { setCreateOpen(false); setEditTask(null); }}
          onSubmit={handleCreateTask}
          onUpdate={editTask ? (updates) => handleUpdateTask(editTask.id, updates) : undefined}
        />
      )}
    </>
  );
}
