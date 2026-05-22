"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import DispatchBoard from "@/components/ui/dispatch-board";
import TaskLedger from "@/components/ui/task-ledger";
import TimelineTrack from "@/components/ui/timeline-track";
import TaskDetailModal from "@/components/ui/task-detail-modal";
import CreateTaskModal from "@/components/ui/create-task-modal";
import { OpsTask, Member, TaskStatus, TASKS, MEMBERS } from "@/lib/mock";
import clsx from "clsx";

const VIEWS = [
  { key: "board", label: "Bảng điều vận", sub: "Kanban theo tín hiệu" },
  { key: "ledger", label: "Sổ theo dõi", sub: "Bảng dense" },
  { key: "timeline", label: "Timeline", sub: "Theo giờ" },
] as const;

export default function TasksView({
  tasks: tasksProp,
  members: membersProp,
}: {
  tasks?: OpsTask[];
  members?: Member[];
}) {
  const [view, setView] = useState<(typeof VIEWS)[number]["key"]>("board");
  const [tasks, setTasks] = useState<OpsTask[]>(tasksProp ?? TASKS);
  const members = membersProp ?? MEMBERS;

  // Sync when server re-renders with new URL filter params
  useEffect(() => {
    if (tasksProp) setTasks(tasksProp);
  }, [tasksProp]);
  const [selectedTask, setSelectedTask] = useState<OpsTask | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  // Filter tasks by search query (title, ID, tags, channel)
  const filteredTasks = useMemo(() => {
    if (!searchQuery.trim()) return tasks;
    const q = searchQuery.toLowerCase();
    return tasks.filter((t) =>
      t.title.toLowerCase().includes(q) ||
      t.id.toLowerCase().includes(q) ||
      t.channelLabel.toLowerCase().includes(q) ||
      t.tags.some((tag) => tag.toLowerCase().includes(q)) ||
      members.find((m) => m.id === t.assignee)?.name.toLowerCase().includes(q) ||
      members.find((m) => m.id === t.assignee)?.callsign.toLowerCase().includes(q)
    );
  }, [tasks, searchQuery, members]);

  const handleTaskClick = useCallback((task: OpsTask) => {
    setSelectedTask(task);
  }, []);

  // ⌘N / ⌘K keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "n") {
        e.preventDefault();
        setCreateOpen(true);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchRef.current?.focus(), 50);
      }
      if (e.key === "Escape") {
        setCreateOpen(false);
        setSelectedTask(null);
        setSearchOpen(false);
        setSearchQuery("");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleCreateTask = useCallback(async (taskData: Omit<OpsTask, "id" | "createdAt">) => {
    // Generate a local ID for optimistic add
    const tempId = `T-${Date.now().toString().slice(-7)}`;
    const newTask: OpsTask = {
      ...taskData,
      id: tempId,
      createdAt: new Date().toISOString(),
    };
    // Optimistic add
    setTasks((prev) => [newTask, ...prev]);

    // Persist to bot API (best-effort)
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
    } catch {
      // Silently keep optimistic state
    }
  }, []);

  const handleStatusChange = useCallback(async (taskId: string, newStatus: TaskStatus) => {
    // Optimistic update
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
    );
    // Also update selectedTask if it's open
    setSelectedTask((prev) => (prev?.id === taskId ? { ...prev, status: newStatus } : prev));

    // Persist to bot API (best-effort)
    try {
      const numericId = taskId.replace(/\D/g, "").slice(-5);
      await fetch(`/api/tasks/${numericId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
    } catch {
      // Silently fail — local state already updated
    }
  }, []);

  return (
    <>
      {/* View switcher + Search */}
      <div className="flex items-center gap-3 mb-4">
        <div className="label-ops text-2xs">Chế độ xem</div>
        <div className="flex gap-0 border border-divider-strong">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={clsx(
                "px-3 py-1.5 mono text-2xs uppercase tracking-wider transition-colors border-r border-divider-strong last:border-r-0",
                view === v.key
                  ? "bg-accent-amber-deep text-canvas"
                  : "bg-surface text-text-secondary hover:bg-surface-raised"
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-3">
          {/* Search toggle */}
          <button
            onClick={() => { setSearchOpen(s => !s); setTimeout(() => searchRef.current?.focus(), 50); }}
            className={clsx(
              "btn-ops flex items-center gap-1.5",
              searchOpen && "border-accent-amber text-accent-amber"
            )}
          >
            {">"} Tìm <span className="kbd">⌘K</span>
          </button>
          <button
            onClick={() => setCreateOpen(true)}
            className="btn-ops primary flex items-center gap-1.5"
          >
            + Tạo task <span className="kbd opacity-60">⌘N</span>
          </button>
          <div className="flex items-center gap-2 mono text-2xs text-text-tertiary">
            <span className="status-dot active" /> live
          </div>
        </div>
      </div>

      {/* Search bar (appears when active) */}
      {searchOpen && (
        <div className="flex items-center gap-3 mb-4 p-3 bg-surface-deep border border-divider-strong">
          <span className="mono text-xs text-text-tertiary shrink-0">{">"}</span>
          <input
            ref={searchRef}
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Tìm theo tên task, mã T-, tags, thành viên…"
            className="flex-1 bg-transparent mono text-sm text-text-primary placeholder:text-text-disabled focus:outline-none"
          />
          {searchQuery && (
            <span className="mono text-2xs text-accent-amber shrink-0">
              {filteredTasks.length}/{tasks.length} task
            </span>
          )}
          <button
            onClick={() => { setSearchOpen(false); setSearchQuery(""); }}
            className="mono text-text-tertiary hover:text-text-primary shrink-0 text-lg leading-none"
          >
            ×
          </button>
        </div>
      )}

      {view === "board" && (
        <DispatchBoard tasks={filteredTasks} members={members} onTaskClick={handleTaskClick} />
      )}
      {view === "ledger" && (
        <TaskLedger tasks={filteredTasks} members={members} onTaskClick={handleTaskClick} onCreateTask={() => setCreateOpen(true)} />
      )}
      {view === "timeline" && (
        <TimelineTrack tasks={filteredTasks} members={members} />
      )}

      {/* Task detail modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          members={members}
          onClose={() => setSelectedTask(null)}
          onStatusChange={handleStatusChange}
        />
      )}

      {/* Create task modal */}
      {createOpen && (
        <CreateTaskModal
          members={members}
          onClose={() => setCreateOpen(false)}
          onSubmit={handleCreateTask}
        />
      )}
    </>
  );
}
