"use client";

import { useState, useRef, useCallback } from "react";
import { OpsTask, Member, TaskStatus, formatDeadline, statusLabel } from "@/lib/mock";
import clsx from "clsx";

// ── Status columns definition ──────────────────────────────────────────────
interface StatusCol {
  key: TaskStatus;
  label: string;
  sub: string;
  dotClass: string;
  borderClass: string;
  textClass: string;
}

const COLUMNS: StatusCol[] = [
  {
    key: "cho_xu_ly",
    label: "Chờ xử lý",
    sub: "mới vào / chưa giao",
    dotClass: "status-dot pending",
    borderClass: "border-state-pending",
    textClass: "text-state-pending",
  },
  {
    key: "dang_lam",
    label: "Đang xử lý",
    sub: "đang triển khai",
    dotClass: "status-dot active",
    borderClass: "border-state-active",
    textClass: "text-state-active",
  },
  {
    key: "bi_chan",
    label: "Bị chặn",
    sub: "cần gỡ rối",
    dotClass: "status-dot blocked",
    borderClass: "border-state-blocked",
    textClass: "text-state-blocked",
  },
  {
    key: "hoan_thanh",
    label: "Hoàn thành",
    sub: "đã xong",
    dotClass: "status-dot done",
    borderClass: "border-state-done",
    textClass: "text-state-done",
  },
];

const PRIORITY_TEXT: Record<string, string> = {
  P0: "text-signal-p0",
  P1: "text-signal-p1",
  P2: "text-signal-p2",
  P3: "text-signal-p3",
  P4: "text-signal-p4",
};

// ── TaskCard ───────────────────────────────────────────────────────────────
function TaskCard({
  task,
  members,
  onTaskClick,
  onDragStart,
}: {
  task: OpsTask;
  members: Member[];
  onTaskClick?: (t: OpsTask) => void;
  onDragStart: (taskId: string) => void;
}) {
  const m = members.find((mb) => mb.id === task.assignee);
  const d = formatDeadline(task.deadline);
  const overdue = d.relative.startsWith("quá");
  const blocked = task.status === "bi_chan";

  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        onDragStart(task.id);
      }}
      onClick={() => onTaskClick?.(task)}
      className={clsx(
        "ops-surface cursor-grab active:cursor-grabbing relative overflow-hidden select-none",
        "p-[10px] transition-opacity",
        overdue && "border-signal-p0/50",
        blocked && !overdue && "border-signal-p1/50",
        !overdue && !blocked && (task.aiClassified ? "ai-classified-card" : "hover:bg-surface-raised transition-colors")
      )}
    >
      {/* Top accent bar */}
      {overdue && <div className="absolute top-0 left-0 right-0 h-[2px] bg-signal-p0" />}
      {blocked && !overdue && <div className="absolute top-0 left-0 right-0 h-[2px] bg-signal-p1" />}

      {/* Drag handle hint */}
      <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-divider-strong opacity-0 group-hover:opacity-100 transition-opacity" />

      {/* Header row: ID + channel tag */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="mono text-2xs text-text-tertiary tabular">{task.id}</span>
        <div className="flex items-center gap-1">
          {overdue && (
            <span className="mono text-2xs text-signal-p0 uppercase tracking-wider border border-signal-p0/50 px-1 py-px">
              OVERDUE
            </span>
          )}
          {blocked && !overdue && (
            <span className="mono text-2xs text-signal-p1 uppercase tracking-wider border border-signal-p1/50 px-1 py-px">
              CHẶN
            </span>
          )}
          <span
            className={clsx(
              "mono text-2xs uppercase tracking-wider px-1 py-0.5 border border-divider-strong",
              PRIORITY_TEXT[task.priority] || "text-text-tertiary"
            )}
          >
            {task.priority}
          </span>
          <span className="mono text-2xs uppercase tracking-wider px-1 py-0.5 border border-divider-strong text-text-tertiary">
            {task.channel}
          </span>
        </div>
      </div>

      {/* Title */}
      <h3 className="text-sm text-text-primary leading-snug mb-1.5 line-clamp-2">{task.title}</h3>

      {/* Tags */}
      {task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {task.tags.slice(0, 3).map((t) => (
            <span key={t} className="mono text-2xs text-accent-paper">
              #{t}
            </span>
          ))}
          {task.aiClassified && (
            <span className="mono text-2xs text-accent-amber">⊙ AI {Math.round((task.aiConfidence || 0) * 100)}%</span>
          )}
        </div>
      )}

      {/* Footer row: assignee + deadline */}
      <div className="flex items-center justify-between pt-1.5 border-t border-divider">
        {m ? (
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 border border-divider-strong bg-surface-deep mono text-2xs flex items-center justify-center text-accent-paper">
              {m.initials}
            </div>
            <span className="mono text-2xs text-text-tertiary">{m.callsign}</span>
          </div>
        ) : (
          <span className="mono text-2xs text-text-disabled">—</span>
        )}
        <div className="text-right">
          <div className="mono text-xs text-text-primary tabular">
            {d.date} {d.time}
          </div>
          <div className={clsx("mono text-2xs font-bold", overdue ? "text-signal-p0" : "text-text-tertiary")}>
            {d.relative}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── QuickAdd inline form ───────────────────────────────────────────────────
function QuickAdd({
  status,
  onAdd,
  onCancel,
}: {
  status: TaskStatus;
  onAdd: (title: string) => void;
  onCancel: () => void;
}) {
  const [val, setVal] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="mt-1 border border-divider-strong bg-surface-deep p-2">
      <input
        ref={inputRef}
        autoFocus
        type="text"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && val.trim()) {
            onAdd(val.trim());
            setVal("");
          }
          if (e.key === "Escape") onCancel();
        }}
        placeholder={`Nội dung task → "${statusLabel(status)}"…`}
        className="w-full bg-transparent mono text-xs text-text-primary placeholder:text-text-disabled focus:outline-none"
      />
      <div className="flex items-center justify-between mt-2">
        <span className="mono text-2xs text-text-disabled">↵ thêm · Esc huỷ</span>
        <div className="flex gap-1">
          <button
            onClick={onCancel}
            className="mono text-2xs text-text-tertiary hover:text-text-primary px-1.5 py-0.5 border border-divider-strong"
          >
            Huỷ
          </button>
          <button
            onClick={() => { if (val.trim()) { onAdd(val.trim()); setVal(""); } }}
            className="mono text-2xs text-canvas bg-accent-amber-deep hover:bg-accent-amber px-2 py-0.5 border border-accent-amber"
          >
            + Thêm
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Column ─────────────────────────────────────────────────────────────────
function StatusColumn({
  col,
  tasks,
  members,
  dragOverCol,
  onTaskClick,
  onDragStart,
  onDragOver,
  onDrop,
  onDragLeave,
  onQuickAdd,
}: {
  col: StatusCol;
  tasks: OpsTask[];
  members: Member[];
  dragOverCol: TaskStatus | null;
  onTaskClick?: (t: OpsTask) => void;
  onDragStart: (taskId: string) => void;
  onDragOver: (status: TaskStatus) => void;
  onDrop: (status: TaskStatus) => void;
  onDragLeave: () => void;
  onQuickAdd: (status: TaskStatus, title: string) => void;
}) {
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const isOver = dragOverCol === col.key;

  return (
    <div
      className={clsx(
        "bg-surface-deep border flex flex-col min-h-[500px] transition-colors",
        isOver ? "border-accent-amber bg-accent-amber/5" : "border-divider"
      )}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        onDragOver(col.key);
      }}
      onDrop={(e) => {
        e.preventDefault();
        onDrop(col.key);
      }}
      onDragLeave={onDragLeave}
    >
      {/* Column header */}
      <header className={clsx("px-3 py-2.5 border-b-2 flex items-center justify-between", col.borderClass)}>
        <div className="flex items-center gap-2">
          <span className={col.dotClass} />
          <div>
            <div className={clsx("mono text-xs uppercase tracking-wider font-semibold", col.textClass)}>
              {col.label}
            </div>
            <div className="mono text-2xs text-text-disabled mt-0.5">{col.sub}</div>
          </div>
        </div>
        <span className="mono text-lg text-text-primary tabular font-light">{tasks.length}</span>
      </header>

      {/* Drop zone indicator */}
      {isOver && (
        <div className="mx-2 mt-2 border border-dashed border-accent-amber/60 py-2 text-center mono text-2xs text-accent-amber uppercase tracking-wider">
          ↓ thả vào đây
        </div>
      )}

      {/* Cards */}
      <div className="flex-1 p-2 space-y-1.5 overflow-y-auto scroll-ops">
        {tasks.map((t) => (
          <TaskCard
            key={t.id}
            task={t}
            members={members}
            onTaskClick={onTaskClick}
            onDragStart={onDragStart}
          />
        ))}
        {tasks.length === 0 && !isOver && (
          <div className="text-center text-2xs text-text-disabled py-8 mono uppercase tracking-wider">
            không có task
          </div>
        )}
      </div>

      {/* Quick-add */}
      <div className="p-2 border-t border-divider">
        {quickAddOpen ? (
          <QuickAdd
            status={col.key}
            onAdd={(title) => {
              onQuickAdd(col.key, title);
              setQuickAddOpen(false);
            }}
            onCancel={() => setQuickAddOpen(false)}
          />
        ) : (
          <button
            onClick={() => setQuickAddOpen(true)}
            className="w-full mono text-2xs text-text-disabled hover:text-accent-amber uppercase tracking-wider py-1.5 border border-transparent hover:border-divider-strong transition-colors flex items-center gap-1.5"
          >
            <span className="text-base leading-none">+</span> thêm task
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main board ─────────────────────────────────────────────────────────────
interface Props {
  tasks?: OpsTask[];
  members?: Member[];
  onTaskClick?: (task: OpsTask) => void;
  onStatusChange?: (taskId: string, newStatus: TaskStatus) => Promise<void>;
  onQuickCreate?: (title: string, status: TaskStatus) => void;
}

export default function StatusBoard({
  tasks = [],
  members = [],
  onTaskClick,
  onStatusChange,
  onQuickCreate,
}: Props) {
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverCol, setDragOverCol] = useState<TaskStatus | null>(null);
  // Optimistic local status override for smooth UX
  const [localOverrides, setLocalOverrides] = useState<Record<string, TaskStatus>>({});

  const getEffectiveStatus = useCallback(
    (task: OpsTask): TaskStatus => localOverrides[task.id] ?? task.status,
    [localOverrides]
  );

  const handleDragStart = useCallback((taskId: string) => {
    setDraggingId(taskId);
  }, []);

  const handleDragOver = useCallback((status: TaskStatus) => {
    setDragOverCol(status);
  }, []);

  const handleDragLeave = useCallback(() => {
    // Don't clear immediately — child fires DragLeave when entering a child element
    // Use a small timeout to avoid flickering
  }, []);

  const handleDrop = useCallback(
    async (newStatus: TaskStatus) => {
      if (!draggingId) return;
      setDragOverCol(null);
      const task = tasks.find((t) => t.id === draggingId);
      if (!task) { setDraggingId(null); return; }
      const prevStatus = getEffectiveStatus(task);
      if (prevStatus === newStatus) { setDraggingId(null); return; }

      // Optimistic update
      setLocalOverrides((prev) => ({ ...prev, [draggingId]: newStatus }));
      setDraggingId(null);

      try {
        await onStatusChange?.(draggingId, newStatus);
      } catch {
        // Revert on failure
        setLocalOverrides((prev) => {
          const next = { ...prev };
          delete next[draggingId ?? ""];
          return next;
        });
      }
    },
    [draggingId, tasks, getEffectiveStatus, onStatusChange]
  );

  const handleQuickAdd = useCallback(
    (status: TaskStatus, title: string) => {
      onQuickCreate?.(title, status);
    },
    [onQuickCreate]
  );

  // Build columns with effective status (accounts for optimistic overrides)
  const colTasks = (key: TaskStatus) =>
    tasks.filter((t) => {
      const s = getEffectiveStatus(t);
      // Only show the 4 main status columns; skip tam_dung, can_lam, dang_review
      if (key === "cho_xu_ly") return s === "cho_xu_ly" || s === "can_lam";
      if (key === "dang_lam") return s === "dang_lam" || s === "dang_review";
      return s === key;
    });

  return (
    <div
      className="grid gap-3"
      style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
      onDragEnd={() => { setDraggingId(null); setDragOverCol(null); }}
    >
      {COLUMNS.map((col) => (
        <StatusColumn
          key={col.key}
          col={col}
          tasks={colTasks(col.key)}
          members={members}
          dragOverCol={dragOverCol}
          onTaskClick={onTaskClick}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragLeave={handleDragLeave}
          onQuickAdd={handleQuickAdd}
        />
      ))}
    </div>
  );
}
