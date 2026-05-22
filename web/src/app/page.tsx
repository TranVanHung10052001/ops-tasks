import BriefingCard from "@/components/ui/briefing-card";
import KpiRow from "@/components/ui/kpi-row";
import OpsStatsRow from "@/components/ui/ops-stats-row";
import TimelineTrack from "@/components/ui/timeline-track";
import TaskLedger from "@/components/ui/task-ledger";
import CompetitiveStrip from "@/components/ui/competitive-strip";
import { ACTIVITY, TODAY } from "@/lib/mock";
import { getTasksData, getMembersData, getStatsData, getMetricsData } from "@/lib/data";

export default async function DashboardPage() {
  const [tasks, members, stats, metrics] = await Promise.all([
    getTasksData(),
    getMembersData(),
    getStatsData(),
    getMetricsData(),
  ]);

  const topTasks = tasks
    .filter((t) => t.status !== "hoan_thanh" && t.status !== "tam_dung")
    .sort((a, b) => {
      const order = ["P0", "P1", "P2", "P3", "P4"];
      return order.indexOf(a.priority) - order.indexOf(b.priority);
    });

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      <header className="flex items-end justify-between mb-1">
        <div>
          <div className="label-ops text-2xs mb-1.5">Đài chính · I · Tổng quan</div>
          <h1 className="text-[32px] text-text-primary editorial leading-tight">{TODAY.greeting}.</h1>
          <p className="text-md text-text-secondary mt-1">
            Truck Ops · {members.length} thành viên trực · ca {TODAY.dayName.toLowerCase()} {TODAY.short}
            {metrics.active_drivers ? ` · ${parseInt(metrics.active_drivers).toLocaleString("vi-VN")} truck driver đang hoạt động.` : " · 4,412 truck driver toàn quốc."}
          </p>
        </div>
        <div className="text-right">
          <div className="mono text-2xs text-text-tertiary uppercase tracking-wider mb-1">Trạm trực</div>
          <div className="mono text-md text-text-primary">HCM · HÀ NỘI · BÌNH DƯƠNG · HẢI PHÒNG</div>
          <div className="mono text-2xs text-text-tertiary mt-1">+ Đà Nẵng (ramp) · Cần Thơ (pilot)</div>
        </div>
      </header>

      <BriefingCard stats={stats} topTasks={topTasks} metrics={metrics} />

      <KpiRow metrics={metrics} />

      <OpsStatsRow stats={stats} tasks={topTasks} metrics={metrics} />

      <TimelineTrack tasks={tasks} members={members} />

      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-2">
          <TaskLedger
            tasks={topTasks}
            members={members}
            limit={8}
            title="Task ưu tiên hôm nay"
          />
        </div>

        <aside className="ops-surface">
          <header className="px-4 py-3 border-b border-divider flex items-center justify-between">
            <span className="label-ops text-2xs">Hoạt động đài</span>
            <span className="mono text-2xs text-text-tertiary">live</span>
          </header>
          <ol className="px-4 py-3 space-y-3">
            {ACTIVITY.slice(0, 10).map((a) => (
              <li key={a.id} className="flex gap-3 text-xs">
                <span className="mono text-text-tertiary tabular w-10 shrink-0">{a.ts}</span>
                <span
                  className={
                    "shrink-0 mt-1 w-1 h-1 rounded-full " +
                    (a.via === "ai" ? "bg-accent-amber" : a.via === "telegram" ? "bg-state-done" : "bg-text-tertiary")
                  }
                />
                <div className="flex-1">
                  <span
                    className={
                      a.actor.startsWith("OPS")
                        ? "mono text-accent-paper"
                        : a.via === "ai"
                        ? "text-accent-amber"
                        : "text-text-secondary"
                    }
                  >
                    {a.actor}
                  </span>{" "}
                  <span className="text-text-secondary">{a.action}</span>{" "}
                  {a.target && <span className="mono text-text-primary">{a.target}</span>}
                  {a.via === "telegram" && (
                    <span className="ml-2 mono text-2xs text-state-done">[TG]</span>
                  )}
                </div>
              </li>
            ))}
          </ol>
          <footer className="px-4 py-2 border-t border-divider mono text-2xs text-text-tertiary text-center">
            xem toàn bộ →
          </footer>
        </aside>
      </div>

      <CompetitiveStrip />
    </div>
  );
}
