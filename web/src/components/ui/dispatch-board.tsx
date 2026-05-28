"use client";

import { useState, useCallback } from "react";
import { TASKS, MEMBERS, formatDeadline, Priority, OpsTask, Member } from "@/lib/mock";
import clsx from "clsx";

const COLUMNS: { key: Priority; label: string; sub: string }[] = [
  { key: "P0", label: "P0 · Khẩn cấp", sub: "xử lý ngay" },
  { key: "P1", label: "P1 · Cao", sub: "trong ngày" },
  { key: "P2", label: "P2 · Trung bình", sub: "trong tuần" },
  { key: "P3", label: "P3 · Thấp", sub: "khi rảnh" },
];

const PRIORITY_BORDER: Record<Priority, string> = {
  P0: "border-signal-p0",
  P1: "border-signal-p1",
  P2: "border-signal-p2",
  P3: "border-signal-p3",
  P4: "border-signal-p4",
};

const PRIORITY_TEXT: Record<Priority, string> = {
  P0: "text-signal-p0",
  P1: "text-signal-p1",
  P2: "text-signal-p2",
  P3: "text-signal-p3",
  P4: "text-signal-p4",
};

const PRIORITY_ICON: Record<Priority, string> = {
  P0: "◼",
  P1: "◼",
  P2: "◻",
  P3: "◻",
  P4: "◻",
};

function TaskCard({ task, members, onTaskClick, onDragStart, selected, onToggleSelect }: {
  task: OpsTask;
  members: Member[];
  onTaskClick?: (t: OpsTask) => void;
  onDragStart?: (taskId: string) => void;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
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
        onDragStart?.(task.id);
      }}
      onClick={(e) => {
        // Don't open detail when clicking checkbox
        if ((e.target as HTMLElement).closest("[data-checkbox]")) return;
        onTaskClick?.(task);
      }}
      className={clsx(
        "ops-surface cursor-grab active:cursor-grabbing relative overflow-hidden select-none",
        "p-[10px]",
        selected ? "border-accent-amber bg-accent-amber/5" :
        overdue ? "border-signal-p0/60" :
        blocked ? "border-signal-p1/60" :
        !task.aiClassified ? "hover:bg-surface-raised transition-colors" : "ai-classified-card"
      )}
    >
      {/* Top accent bar for overdue/blocked/selected */}
      {selected && <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent-amber" />}
      {!selected && overdue && <div className="absolute top-0 left-0 right-0 h-[2px] bg-signal-p0" />}
      {!selected && blocked && !overdue && <div className="absolute top-0 left-0 right-0 h-[2px] bg-signal-p1" />}

      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          {/* Checkbox — always visible when selected, hover-visible otherwise */}
          <div
            data-checkbox
            onClick={(e) => { e.stopPropagation(); onToggleSelect?.(task.id); }}
            className={clsx(
              "w-3.5 h-3.5 border flex items-center justify-center shrink-0 cursor-pointer transition-all",
              selected
                ? "border-accent-amber bg-accent-amber text-canvas"
                : "border-divider-strong bg-surface opacity-0 group-hover:opacity-100 hover:border-accent-amber"
            )}
          >
            {selected && <span className="text-[8px] leading-none">✓</span>}
          </div>
          <span className="mono text-2xs text-text-tertiary tabular">{task.id}</span>
        </div>{/* end left flex */}
        <div className="flex items-center gap-1">
          {overdue && (
            <span className="mono text-2xs text-signal-p0/70 px-1 py-px">
              ⚠ trễ
            </span>
          )}
          {blocked && !overdue && (
            <span className="mono text-2xs text-signal-p1/70 px-1 py-px">
              ✕ chặn
            </span>
          )}
          <span className="mono text-2xs uppercase tracking-wider px-1 py-0.5 border border-divider-strong text-text-tertiary">
            {task.channel}
          </span>
        </div>
      </div>

      <h3 className="text-sm text-text-primary leading-snug mb-1.5">{task.title}</h3>

      {task.description && (
        <p className="text-xs text-text-tertiary leading-snug mb-1.5 line-clamp-2">{task.description}</p>
      )}

      <div className="flex flex-wrap gap-1 mb-2">
        {task.tags.slice(0, 3).map((t) => (
          <span key={t} className="mono text-2xs text-accent-paper">
            #{t}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between pt-1.5 border-t border-divider">
        {m && (
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 border border-divider-strong bg-surface-deep mono text-2xs flex items-center justify-center text-accent-paper">
              {m.initials}
            </div>
            <span className="text-xs text-text-secondary">{m.name}</span>
          </div>
        )}
        <div className="text-right">
          <div className="mono text-xs text-text-primary tabular">{d.date} {d.time}</div>
          <div className={clsx("mono text-2xs", overdue ? "text-signal-p0/75" : "text-text-tertiary")}>
            {d.relative}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DispatchBoard({
  tasks: tasksProp,
  members: membersProp,
  onTaskClick,
  onPriorityChange,
  selectedIds,
  onToggleSelect,
}: {
  tasks?: OpsTask[];
  members?: Member[];
  onTaskClick?: (task: OpsTask) => void;
  onPriorityChange?: (taskId: string, newPriority: Priority) => Promise<void>;
  selectedIds?: Set<string>;
  onToggleSelect?: (id: string) => void;
}) {
  const allTasks = tasksProp ?? TASKS;
  const allMembers = membersProp ?? MEMBERS;
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverCol, setDragOverCol] = useState<Priority | null>(null);
  const [localOverrides, setLocalOverrides] = useState<Record<string, Priority>>({});

  const getEffectivePriority = useCallback(
    (task: OpsTask): Priority => localOverrides[task.id] ?? task.priority,
    [localOverrides]
  );

  const handleDrop = useCallback(
    async (newPriority: Priority) => {
      if (!draggingId) return;
      setDragOverCol(null);
      const task = allTasks.find((t) => t.id === draggingId);
      if (!task) { setDraggingId(null); return; }
      if (getEffectivePriority(task) === newPriority) { setDraggingId(null); return; }
      setLocalOverrides((prev) => ({ ...prev, [draggingId]: newPriority }));
      setDraggingId(null);
      try {
        await onPriorityChange?.(draggingId, newPriority);
      } catch {
        setLocalOverrides((prev) => { const n = { ...prev }; delete n[draggingId ?? ""]; return n; });
      }
    },
    [draggingId, allTasks, getEffectivePriority, onPriorityChange]
  );

  return (
    <div
      style={{ display: "grid", gridTemplateColumns: "28fr 26fr 23fr 23fr", gap: "12px" }}
      onDragEnd={() => { setDraggingId(null); setDragOverCol(null); }}
    >
      {COLUMNS.map((col) => {
        const items = allTasks.filter((t) => getEffectivePriority(t) === col.key);
        const isOver = dragOverCol === col.key;
        return (
          <div
            key={col.key}
            className={clsx(
              "bg-surface-deep border min-h-[500px] flex flex-col transition-colors",
              isOver ? "border-accent-amber bg-accent-amber/5" : "border-divider"
            )}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverCol(col.key); }}
            onDrop={(e) => { e.preventDefault(); handleDrop(col.key); }}
            onDragLeave={() => setDragOverCol(null)}
          >
            <header
              className={clsx(
                "px-3 py-2 border-b-2 flex items-center justify-between",
                PRIORITY_BORDER[col.key]
              )}
            >
              <div>
                <div className={clsx("mono text-xs tracking-wide", PRIORITY_TEXT[col.key])}>
                  {PRIORITY_ICON[col.key]} {col.label}
                </div>
                <div className="mono text-2xs text-text-tertiary mt-0.5">{col.sub}</div>
              </div>
              <span className="mono text-lg text-text-primary tabular font-light">{items.length}</span>
            </header>
            {isOver && (
              <div className="mx-2 mt-2 border border-dashed border-accent-amber/60 py-2 text-center mono text-2xs text-accent-amber uppercase tracking-wider">
                ↓ thả vào đây
              </div>
            )}
            <div className="flex-1 p-2 space-y-1.5">
              {items.map((t) => (
                <TaskCard
                  key={t.id}
                  task={t}
                  members={allMembers}
                  onTaskClick={onTaskClick}
                  onDragStart={setDraggingId}
                  selected={selectedIds?.has(t.id)}
                  onToggleSelect={onToggleSelect}
                />
              ))}
              {items.length === 0 && !isOver && (
                <div className="text-center text-2xs text-text-tertiary py-8 mono uppercase tracking-wider">
                  không có task
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
