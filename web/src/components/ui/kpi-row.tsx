import { TRUCK_KPIS } from "@/lib/mock";
import clsx from "clsx";

interface KpiItem {
  label: string;
  value: string | number;
  unit?: string;
  delta?: string;
  deltaTone?: "up" | "down" | "warn" | "neutral";
  sub?: string;
}

const KPIS: KpiItem[] = [
  {
    label: TRUCK_KPIS.gsvToday.label,
    value: TRUCK_KPIS.gsvToday.value,
    unit: TRUCK_KPIS.gsvToday.unit,
    delta: TRUCK_KPIS.gsvToday.delta,
    deltaTone: TRUCK_KPIS.gsvToday.tone,
    sub: "Bulky 64% · Longhaul 28% · Rental 8%",
  },
  {
    label: TRUCK_KPIS.ordersToday.label,
    value: TRUCK_KPIS.ordersToday.value.toLocaleString("vi-VN"),
    delta: TRUCK_KPIS.ordersToday.delta,
    deltaTone: TRUCK_KPIS.ordersToday.tone,
    sub: "Tuần 21: 8,142 chuyến (+9% MoM)",
  },
  {
    label: TRUCK_KPIS.fillRate.label,
    value: TRUCK_KPIS.fillRate.value,
    unit: TRUCK_KPIS.fillRate.unit,
    delta: TRUCK_KPIS.fillRate.delta,
    deltaTone: TRUCK_KPIS.fillRate.tone,
    sub: "VSIP 84% · Sóng Thần 71% · Long Hậu 79%",
  },
  {
    label: TRUCK_KPIS.cogsBulky.label,
    value: TRUCK_KPIS.cogsBulky.value,
    unit: TRUCK_KPIS.cogsBulky.unit,
    delta: TRUCK_KPIS.cogsBulky.delta,
    deltaTone: TRUCK_KPIS.cogsBulky.tone,
    sub: "Target <30% · còn dư 1.6 điểm",
  },
];

export default function KpiRow() {
  return (
    <div className="grid grid-cols-4 gap-3">
      {KPIS.map((kpi) => (
        <div key={kpi.label} className="kpi-box">
          <div className="label-ops text-2xs mb-3">{kpi.label}</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="kpi-number">{kpi.value}</span>
            {kpi.unit && <span className="mono text-md text-text-secondary tabular">{kpi.unit}</span>}
          </div>
          {kpi.delta && (
            <div
              className={clsx(
                "mono text-xs mb-2",
                kpi.deltaTone === "up" && "text-signal-p3",
                kpi.deltaTone === "warn" && "text-signal-p0",
                kpi.deltaTone === "down" && "text-signal-p1",
                kpi.deltaTone === "neutral" && "text-text-secondary"
              )}
            >
              {kpi.deltaTone === "up" ? "▲ " : kpi.deltaTone === "warn" ? "● " : ""}
              {kpi.delta}
            </div>
          )}
          {kpi.sub && <div className="text-xs text-text-tertiary leading-snug">{kpi.sub}</div>}
        </div>
      ))}
    </div>
  );
}
