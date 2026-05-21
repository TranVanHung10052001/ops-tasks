import { MEMBERS, TASKS, memberById } from "@/lib/mock";
import clsx from "clsx";

export default function TeamPage() {
  const online = MEMBERS.filter((m) => m.status === "online").length;

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      <header className="flex items-end justify-between">
        <div>
          <div className="label-ops text-2xs mb-1.5">Đài chính · 04 · Nhóm điều vận</div>
          <h1 className="text-2xl text-text-primary editorial leading-tight">Đội điều vận xe tải · 8 callsign.</h1>
          <p className="text-md text-text-secondary mt-1">
            {online}/{MEMBERS.length} thành viên đang trực · ca ngày 06:00 → 18:00 · ca đêm 18:00 → 06:00.
          </p>
        </div>
        <button className="btn-ops primary">+ Thêm thành viên</button>
      </header>

      <div className="grid grid-cols-4 gap-3">
        {MEMBERS.map((m) => {
          const tasks = TASKS.filter((t) => t.assignee === m.id);
          const p0 = tasks.filter((t) => t.priority === "P0").length;
          const blocked = tasks.filter((t) => t.status === "bi_chan").length;
          const loadPct = (m.workload / m.workloadMax) * 100;
          return (
            <div key={m.id} className="ops-surface p-4 relative">
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

              <div className="flex items-start gap-3 mb-4">
                <div className="callsign large">{m.initials}</div>
                <div className="flex-1 mt-1">
                  <div className="text-md text-text-primary leading-tight">{m.name}</div>
                  <div className="mono text-2xs text-text-tertiary tracking-wider mt-0.5">{m.callsign}</div>
                  <div className="text-xs text-text-tertiary mt-1.5">{m.role}</div>
                </div>
              </div>

              {/* Workload bar */}
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="label-ops text-2xs">Tải công việc</span>
                  <span className="mono text-xs text-text-primary tabular">
                    {m.workload}/{m.workloadMax}
                  </span>
                </div>
                <div className="flex gap-px h-3">
                  {Array.from({ length: m.workloadMax }).map((_, i) => (
                    <div
                      key={i}
                      className={clsx(
                        "flex-1",
                        i < m.workload
                          ? loadPct > 80
                            ? "bg-signal-p0"
                            : loadPct > 60
                            ? "bg-signal-p2"
                            : "bg-signal-p3"
                          : "bg-surface-deep border-y border-divider-strong"
                      )}
                    />
                  ))}
                </div>
              </div>

              {/* Mini stats */}
              <div className="grid grid-cols-3 gap-0 border-y border-divider py-2">
                <div className="text-center border-r border-divider">
                  <div className="mono text-md text-text-primary tabular">{tasks.length}</div>
                  <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">task</div>
                </div>
                <div className="text-center border-r border-divider">
                  <div className={clsx("mono text-md tabular", p0 > 0 ? "text-signal-p0" : "text-text-tertiary")}>
                    {p0}
                  </div>
                  <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">p0</div>
                </div>
                <div className="text-center">
                  <div className={clsx("mono text-md tabular", blocked > 0 ? "text-signal-p1" : "text-text-tertiary")}>
                    {blocked}
                  </div>
                  <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">chặn</div>
                </div>
              </div>

              {/* Top task */}
              {tasks[0] && (
                <div className="mt-3 text-xs">
                  <div className="label-ops text-2xs mb-1">Đang xử lý</div>
                  <div className="text-text-primary leading-snug line-clamp-2">{tasks[0].title}</div>
                </div>
              )}

              <div className="dotted-divider my-3" />

              <div className="flex items-center justify-between">
                <button className="mono text-2xs text-accent-paper uppercase tracking-wider hover:text-accent-amber">
                  ► Chi tiết
                </button>
                <button className="mono text-2xs text-text-tertiary uppercase tracking-wider hover:text-text-primary">
                  + Giao task
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Capacity overview */}
      <section className="ops-surface p-5">
        <header className="flex items-center justify-between mb-4">
          <div>
            <div className="label-ops text-2xs">Tổng quan năng lực</div>
            <div className="mono text-2xs text-text-tertiary mt-0.5">cập nhật 14:32 ICT</div>
          </div>
          <button className="btn-ops">Tái phân bổ tự động</button>
        </header>

        <div className="space-y-3">
          {MEMBERS.map((m) => {
            const loadPct = (m.workload / m.workloadMax) * 100;
            const isOver = loadPct > 80;
            return (
              <div key={m.id} className="flex items-center gap-3">
                <div className="w-24 mono text-xs text-text-secondary tracking-wider shrink-0">{m.callsign}</div>
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
                <div className="w-16 text-right mono text-xs text-text-primary tabular shrink-0">{loadPct}%</div>
                {isOver && (
                  <span className="mono text-2xs text-signal-p0 uppercase tracking-wider shrink-0 w-20">⚠ overload</span>
                )}
                {!isOver && <span className="shrink-0 w-20" />}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
