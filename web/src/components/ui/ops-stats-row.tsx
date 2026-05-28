import { OpsTask } from "@/lib/mock";
import { ApiStats, ApiMetrics } from "@/lib/api";

export default function OpsStatsRow({
  stats,
  tasks,
  metrics = {},
}: {
  stats?: ApiStats;
  tasks?: OpsTask[];
  metrics?: ApiMetrics;
}) {
  const activeCount = stats?.active ?? 0;
  const blockedCount = stats?.blocked ?? 0;
  const memberCount = stats?.member_count ?? 0;
  const overloadedCount = stats?.overloaded_count ?? 0;
  const capacityPct = memberCount > 0
    ? Math.round(((memberCount - overloadedCount) / memberCount) * 100)
    : 0;

  const p0 = tasks ? tasks.filter((t) => t.priority === "P0").length : 0;
  const p1 = tasks ? tasks.filter((t) => t.priority === "P1").length : 0;
  const p2 = tasks ? tasks.filter((t) => t.priority === "P2").length : 0;
  const p3 = tasks ? tasks.filter((t) => t.priority === "P3").length : 0;
  const pTotal = p0 + p1 + p2 + p3 || 1;

  const activeDrivers = metrics.active_drivers
    ? parseInt(metrics.active_drivers).toLocaleString("vi-VN")
    : "—";

  const driverSub = [
    metrics.driver_station_pct ? `Station ${metrics.driver_station_pct}%` : null,
    metrics.driver_core_pct    ? `Core ${metrics.driver_core_pct}%`    : null,
    metrics.driver_hub_pct     ? `Hub ${metrics.driver_hub_pct}%`     : null,
    metrics.driver_mass_pct    ? `Mass ${metrics.driver_mass_pct}%`   : null,
  ].filter(Boolean).join(" · ") || "Station · Core · Hub · Mass";

  const overdueItems = stats?.overdue_tasks?.slice(0, 3) ?? [];

  return (
    <section className="ops-surface">
      <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <span className="section-label">Tín hiệu vận hành</span>
          <span className="mono text-2xs text-text-tertiary">cập nhật mỗi 60s</span>
        </div>
        <span className="mono text-2xs text-text-tertiary">truck-ops-realtime</span>
      </header>
      <div className="grid grid-cols-4 divide-x divide-divider">
        {/* Driver count */}
        <div className="p-5">
          <div className="section-label mb-2">Driver truck đang hoạt động</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-text-primary tabular leading-none">
              {activeDrivers}
            </span>
            {metrics.active_drivers && (
              <span className="mono text-xs text-text-tertiary tabular">driver</span>
            )}
          </div>
          {metrics.active_drivers ? (
            <>
              <div className="mt-3 h-1 bg-surface-deep">
                <div className="h-full bg-signal-p3" style={{
                  width: `${Math.min(100, Math.round(parseInt(metrics.active_drivers) / 44.12))}%`
                }} />
              </div>
              <div className="mt-2 text-2xs text-text-tertiary">{driverSub}</div>
            </>
          ) : (
            <div className="mono text-xs text-text-disabled mt-1">
              Chưa kết nối Redash
            </div>
          )}
        </div>

        {/* Active tasks */}
        <div className="p-5">
          <div className="section-label mb-2">Task đang chạy</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-text-primary tabular leading-none">{activeCount || "—"}</span>
            {activeCount > 0 && <span className="mono text-xs text-text-tertiary">task</span>}
          </div>
          {stats && (
            <div className="mono text-xs text-signal-p3">▲ {stats.done_today} hoàn thành hôm nay</div>
          )}
          {activeCount > 0 && (
            <>
              <div className="mt-3 flex gap-px h-1">
                <div className="bg-signal-p0" style={{ width: `${(p0 / pTotal) * 100}%` }} />
                <div className="bg-signal-p1" style={{ width: `${(p1 / pTotal) * 100}%` }} />
                <div className="bg-signal-p2" style={{ width: `${(p2 / pTotal) * 100}%` }} />
                <div className="bg-signal-p3" style={{ width: `${(p3 / pTotal) * 100}%` }} />
              </div>
              <div className="mt-2 text-2xs text-text-tertiary">P0 {p0} · P1 {p1} · P2 {p2} · P3 {p3}</div>
            </>
          )}
          {!stats && (
            <div className="mono text-xs text-text-disabled mt-1">Chưa kết nối bot</div>
          )}
        </div>

        {/* P0 / overdue */}
        <div className="p-5">
          <div className="section-label mb-2">P0 đang mở</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-signal-p0 tabular leading-none">{p0 || "—"}</span>
            {p0 > 0 && <span className="mono text-xs text-text-tertiary">task</span>}
          </div>
          <div className="mono text-xs text-signal-p0">● {blockedCount} đang bị chặn</div>
          <div className="mt-3 text-xs text-text-secondary leading-snug">
            {overdueItems.length > 0 ? (
              overdueItems.map((t, i) => (
                <div key={i}>· {(t.summary ?? "").slice(0, 40)}{(t.summary ?? "").length > 40 ? "…" : ""}</div>
              ))
            ) : stats ? (
              <div className="text-text-disabled">Không có task overdue</div>
            ) : (
              <div className="text-text-disabled">Chưa kết nối bot</div>
            )}
          </div>
        </div>

        {/* Capacity */}
        <div className="p-5">
          <div className="section-label mb-2">Năng lực team</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-text-primary tabular leading-none">
              {memberCount > 0 ? capacityPct : "—"}
            </span>
            {memberCount > 0 && <span className="mono text-xs text-text-tertiary">%</span>}
          </div>
          {memberCount > 0 ? (
            <>
              <div className="mono text-xs text-text-secondary">{memberCount} thành viên · {overloadedCount} quá tải</div>
              <div className="mt-3 flex gap-px h-1">
                {Array.from({ length: memberCount }).map((_, i) => (
                  <div
                    key={i}
                    className="flex-1"
                    style={{
                      background: i < overloadedCount ? "var(--signal-p0)" : "var(--signal-p3)",
                    }}
                  />
                ))}
              </div>
              <div className="mt-2 text-2xs text-text-tertiary">
                {overloadedCount > 0 ? `${overloadedCount} thành viên quá tải` : "Tải đồng đều"}
              </div>
            </>
          ) : (
            <div className="mono text-xs text-text-disabled mt-1">Chưa kết nối bot</div>
          )}
        </div>
      </div>
    </section>
  );
}
