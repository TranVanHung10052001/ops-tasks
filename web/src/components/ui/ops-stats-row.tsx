import { TRUCK_KPIS } from "@/lib/mock";

export default function OpsStatsRow() {
  return (
    <section className="ops-surface">
      <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <span className="label-ops text-2xs">Tín hiệu vận hành</span>
          <span className="mono text-2xs text-text-tertiary">cập nhật mỗi 60s</span>
        </div>
        <span className="mono text-2xs text-text-tertiary">truck-ops-realtime</span>
      </header>
      <div className="grid grid-cols-4 divide-x divide-divider">
        <div className="p-5">
          <div className="label-ops text-2xs mb-2">{TRUCK_KPIS.activeDrivers.label}</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-text-primary tabular leading-none">
              {TRUCK_KPIS.activeDrivers.value.toLocaleString("vi-VN")}
            </span>
            <span className="mono text-xs text-text-tertiary tabular">{TRUCK_KPIS.activeDrivers.unit}</span>
          </div>
          <div className="mono text-xs text-text-secondary">{TRUCK_KPIS.activeDrivers.delta}</div>
          <div className="mt-3 h-1 bg-surface-deep">
            <div className="h-full bg-signal-p3" style={{ width: "42%" }} />
          </div>
          <div className="mt-2 text-2xs text-text-tertiary">Station 18% · Core 31% · Hub 28% · Mass 23%</div>
        </div>

        <div className="p-5">
          <div className="label-ops text-2xs mb-2">{TRUCK_KPIS.taskActive.label}</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-text-primary tabular leading-none">{TRUCK_KPIS.taskActive.value}</span>
            <span className="mono text-xs text-text-tertiary">task</span>
          </div>
          <div className="mono text-xs text-signal-p3">▲ {TRUCK_KPIS.taskActive.delta}</div>
          <div className="mt-3 flex gap-px h-1">
            <div className="bg-signal-p0" style={{ width: "6%" }} />
            <div className="bg-signal-p1" style={{ width: "25%" }} />
            <div className="bg-signal-p2" style={{ width: "38%" }} />
            <div className="bg-signal-p3" style={{ width: "31%" }} />
          </div>
          <div className="mt-2 text-2xs text-text-tertiary">P0 3 · P1 12 · P2 18 · P3 14</div>
        </div>

        <div className="p-5">
          <div className="label-ops text-2xs mb-2">{TRUCK_KPIS.p0Open.label}</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-signal-p0 tabular leading-none">{TRUCK_KPIS.p0Open.value}</span>
            <span className="mono text-xs text-text-tertiary">task</span>
          </div>
          <div className="mono text-xs text-signal-p0">● {TRUCK_KPIS.p0Open.delta}</div>
          <div className="mt-3 text-xs text-text-secondary leading-snug">
            <div>· VSIP II 3 xe trễ → 11:00</div>
            <div>· Long Hậu SLA → 14:30</div>
            <div>· SLP pitch → 17:00</div>
          </div>
        </div>

        <div className="p-5">
          <div className="label-ops text-2xs mb-2">{TRUCK_KPIS.capacity.label}</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="font-display text-2xl text-text-primary tabular leading-none">{TRUCK_KPIS.capacity.value}</span>
            <span className="mono text-xs text-text-tertiary">{TRUCK_KPIS.capacity.unit}</span>
          </div>
          <div className="mono text-xs text-text-secondary">{TRUCK_KPIS.capacity.delta}</div>
          <div className="mt-3 flex gap-px h-1">
            {[1, 1, 1, 0.9, 0.8, 0.5, 0.7, 0.3].map((v, i) => (
              <div
                key={i}
                className="flex-1"
                style={{
                  background: v >= 0.8 ? "var(--signal-p0)" : v >= 0.6 ? "var(--signal-p2)" : "var(--signal-p3)",
                  opacity: v < 0.4 ? 0.3 : 1,
                }}
              />
            ))}
          </div>
          <div className="mt-2 text-2xs text-text-tertiary">OPS-03 9/10 overload</div>
        </div>
      </div>
    </section>
  );
}
