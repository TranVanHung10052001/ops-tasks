"use client";

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

function TaskCard({ task, members, onTaskClick }: { task: OpsTask; members: Member[]; onTaskClick?: (t: OpsTask) => void }) {
  const m = members.find((mb) => mb.id === task.assignee);
  const d = formatDeadline(task.deadline);
  const overdue = d.relative.startsWith("quá");
  const blocked = task.status === "bi_chan";

  return (
    <div
      onClick={() => onTaskClick?.(task)}
      className={clsx(
        "ops-surface cursor-pointer relative overflow-hidden",
        "p-[10px]",
        overdue && "border-signal-p0/60",
        blocked && "border-signal-p1/60",
        !overdue && !blocked && (task.aiClassified ? "ai-classified-card" : "hover:bg-surface-raised transition-colors")
      )}
    >
      {/* Top accent bar for overdue/blocked */}
      {overdue && <div className="absolute top-0 left-0 right-0 h-[2px] bg-signal-p0" />}
      {blocked && !overdue && <div className="absolute top-0 left-0 right-0 h-[2px] bg-signal-p1" />}

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
            <span className="mono text-2xs text-text-tertiary">{m.initials}</span>
          </div>
        )}
        <div className="text-right">
          <div className="mono text-xs text-text-primary tabular">{d.date} {d.time}</div>
          <div className={clsx("mono text-2xs font-bold", overdue ? "text-signal-p0" : "text-text-tertiary")}>
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
}: {
  tasks?: OpsTask[];
  members?: Member[];
  onTaskClick?: (task: OpsTask) => void;
}) {
  const allTasks = tasksProp ?? TASKS;
  const allMembers = membersProp ?? MEMBERS;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "28fr 26fr 23fr 23fr", gap: "12px" }}>
      {COLUMNS.map((col) => {
        const items = allTasks.filter((t) => t.priority === col.key);
        return (
          <div key={col.key} className="bg-surface-deep border border-divider min-h-[500px] flex flex-col">
            <header
              className={clsx(
                "px-3 py-2 border-b-2 flex items-center justify-between",
                PRIORITY_BORDER[col.key]
              )}
            >
              <div>
                <div className={clsx("mono text-xs uppercase tracking-wider", PRIORITY_TEXT[col.key])}>
                  {PRIORITY_ICON[col.key]} {col.label}
                </div>
                <div className="mono text-2xs text-text-tertiary mt-0.5">{col.sub}</div>
              </div>
              <span className="mono text-md text-text-primary tabular">{items.length}</span>
            </header>
            <div className="flex-1 p-2 space-y-1.5">
              {items.map((t) => (
                <TaskCard key={t.id} task={t} members={allMembers} onTaskClick={onTaskClick} />
              ))}
              {items.length === 0 && (
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
