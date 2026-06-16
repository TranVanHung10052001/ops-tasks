import { MEMBERS, TASKS, OpsTask, Member } from "@/lib/mock";
import clsx from "clsx";

const HOURS = [6, 8, 10, 12, 14, 16, 18, 20, 22];
const START = 6;
const END = 22;
const RANGE = END - START;

const PRIORITY_COLOR: Record<string, string> = {
  P0: "bg-signal-p0",
  P1: "bg-signal-p1",
  P2: "bg-signal-p2",
  P3: "bg-signal-p3",
  P4: "bg-signal-p4",
};

function blockFor(task: OpsTask) {
  if (!task.deadline) return { left: "0%", width: "0%" };
  const d = new Date(task.deadline);
  const endH = d.getHours() + d.getMinutes() / 60;
  const startH = endH - task.estimateHours;
  const left = ((Math.max(startH, START) - START) / RANGE) * 100;
  const width = ((Math.min(endH, END) - Math.max(startH, START)) / RANGE) * 100;
  return { left: `${left}%`, width: `${Math.max(width, 1.5)}%` };
}

export default function TimelineTrack({
  tasks: tasksProp,
  members: membersProp,
}: {
  tasks?: OpsTask[];
  members?: Member[];
}) {
  return (
    <section className="ops-surface p-5">
      <div className="flex items-baseline justify-between mb-4">
        <div className="flex items-baseline gap-3">
          <span className="label-ops text-2xs">Timeline hôm nay</span>
          <span className="mono text-2xs text-text-tertiary">21·05 · 06:00 → 22:00 ICT</span>
        </div>
        <div className="flex items-center gap-3 mono text-2xs text-text-tertiary">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-signal-p0" /> P0
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-signal-p1" /> P1
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-signal-p2" /> P2
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-signal-p3" /> P3
          </span>
        </div>
      </div>

      {/* Hour ruler */}
      <div className="relative h-5 border-b border-divider mb-3 ml-[60px]">
        {HOURS.map((h) => {
          const left = ((h - START) / RANGE) * 100;
          return (
            <div key={h} className="absolute top-0 bottom-0" style={{ left: `${left}%` }}>
              <div className="absolute top-0 h-2 w-px bg-divider-strong" />
              <div className="mono text-2xs text-text-tertiary tabular -translate-x-1/2 absolute top-2">
                {String(h).padStart(2, "0")}:00
              </div>
            </div>
          );
        })}
        {/* now line */}
        <div
          className="absolute top-0 bottom-0 w-px bg-accent-amber z-10"
          style={{ left: `${((14.53 - START) / RANGE) * 100}%` }}
        >
          <div className="absolute -top-1 -left-1 w-2 h-2 bg-accent-amber rotate-45" />
          <div className="mono text-2xs text-accent-amber absolute top-2 left-1.5">14:32</div>
        </div>
      </div>

      {/* Member tracks */}
      <div className="space-y-1.5">
        {(membersProp ?? MEMBERS).slice(0, 7).map((m) => {
          const tasks = (tasksProp ?? TASKS).filter((t) => t.assignee === m.id);
          return (
            <div key={m.id} className="flex items-center gap-3 group">
              <div className="w-[60px] flex items-center gap-2">
                <span className="mono text-2xs text-text-tertiary">{m.initials}</span>
              </div>
              <div className="relative flex-1 h-5 bg-surface-deep border-l border-divider">
                {/* now line */}
                <div
                  className="absolute top-0 bottom-0 w-px bg-accent-amber/40 z-10 pointer-events-none"
                  style={{ left: `${((14.53 - START) / RANGE) * 100}%` }}
                />
                {tasks.map((t) => {
                  const pos = blockFor(t);
                  return (
                    <div
                      key={t.id}
                      className={clsx(
                        "absolute top-1 h-3 timeline-bar",
                        PRIORITY_COLOR[t.priority],
                        t.priority === "P0" && "animate-pulse"
                      )}
                      style={pos}
                      title={`${t.id} · ${t.title}`}
                    >
                      <span className="hidden group-hover:block absolute top-full mt-1 left-0 z-20 bg-surface-raised border border-divider-strong px-2 py-1 text-xs text-text-primary whitespace-nowrap mono">
                        {t.id} · {t.title.slice(0, 40)}...
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="mono text-2xs text-text-tertiary w-10 text-right tabular">
                {tasks.length} tk
              </div>
            </div>
          );
        })}
      </div>

      <div className="dotted-divider my-4" />

      <div className="mono text-2xs text-text-tertiary">
        Màu theo mức độ ưu tiên · P0 nhấp nháy · thanh = thời lượng task ước tính
      </div>
    </section>
  );
}
