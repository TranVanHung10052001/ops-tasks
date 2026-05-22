import { ApiMetrics } from "@/lib/api";
import clsx from "clsx";

interface KpiItem {
  label: string;
  value: string;
  unit?: string;
  delta?: string;
  deltaTone?: "up" | "down" | "warn" | "neutral";
  sub?: string;
}

function fmt(v: string | undefined, suffix = ""): string {
  if (!v) return "—";
  return v + suffix;
}

function deltaTone(pct: string | undefined): "up" | "down" | "warn" | "neutral" {
  if (!pct) return "neutral";
  const n = parseFloat(pct);
  if (isNaN(n)) return "neutral";
  return n > 0 ? "up" : n < 0 ? "warn" : "neutral";
}

function cogsTone(pct: string | undefined): "up" | "down" | "warn" | "neutral" {
  // For COGS: negative delta (cost down) = good (up/green), positive = warn
  if (!pct) return "neutral";
  const n = parseFloat(pct);
  if (isNaN(n)) return "neutral";
  return n < 0 ? "up" : n > 0 ? "warn" : "neutral";
}

function fmtPct(v: string | undefined): string {
  if (!v) return "—";
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return n > 0 ? `+${n.toFixed(1)}%` : `${n.toFixed(1)}%`;
}

function fmtGsvDelta(v: string | undefined): string {
  if (!v) return "";
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return n > 0 ? `+${n.toFixed(0)}% WoW` : `${n.toFixed(0)}% WoW`;
}

function buildFrSub(m: ApiMetrics): string {
  const parts: string[] = [];
  if (m.fill_rate_vsip_pct)     parts.push(`VSIP ${m.fill_rate_vsip_pct}%`);
  if (m.fill_rate_songthan_pct) parts.push(`Sóng Thần ${m.fill_rate_songthan_pct}%`);
  if (m.fill_rate_longhau_pct)  parts.push(`Long Hậu ${m.fill_rate_longhau_pct}%`);
  if (parts.length === 0) return "VSIP · Sóng Thần · Long Hậu";
  return parts.join(" · ");
}

export default function KpiRow({ metrics = {} }: { metrics?: ApiMetrics }) {
  const kpis: KpiItem[] = [
    {
      label: "GSV Truck hôm nay",
      value: fmt(metrics.gsv_today_b),
      unit: metrics.gsv_today_b ? "tỷ" : undefined,
      delta: metrics.gsv_wow_pct ? fmtGsvDelta(metrics.gsv_wow_pct) : undefined,
      deltaTone: deltaTone(metrics.gsv_wow_pct),
      sub: "Bulky · Longhaul · Rental",
    },
    {
      label: "Chuyến hôm nay",
      value: metrics.orders_today
        ? parseInt(metrics.orders_today).toLocaleString("vi-VN")
        : "—",
      delta: metrics.orders_wow_pct ? fmtPct(metrics.orders_wow_pct) + " WoW" : undefined,
      deltaTone: deltaTone(metrics.orders_wow_pct),
      sub: metrics.updated_at
        ? `Cập nhật: ${new Date(metrics.updated_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`
        : "Chưa có dữ liệu hôm nay",
    },
    {
      label: "Fill Rate Core",
      value: fmt(metrics.fill_rate_core_pct),
      unit: metrics.fill_rate_core_pct ? "%" : undefined,
      delta: metrics.fill_rate_han_pct || metrics.fill_rate_sgn_pct
        ? `HAN ${fmt(metrics.fill_rate_han_pct)}% · SGN ${fmt(metrics.fill_rate_sgn_pct)}%`
        : undefined,
      deltaTone: (() => {
        const v = parseFloat(metrics.fill_rate_core_pct ?? "0");
        return v >= 68 ? "up" : v >= 60 ? "warn" : "down";
      })(),
      sub: buildFrSub(metrics),
    },
    {
      label: "COGS Bulky",
      value: fmt(metrics.cogs_bulky_pct),
      unit: metrics.cogs_bulky_pct ? "%" : undefined,
      delta: metrics.cogs_wow_pct ? fmtPct(metrics.cogs_wow_pct) + " WoW" : undefined,
      deltaTone: cogsTone(metrics.cogs_wow_pct),
      sub: metrics.cogs_bulky_pct
        ? `Target <30% · còn ${Math.max(0, 30 - parseFloat(metrics.cogs_bulky_pct)).toFixed(1)} điểm đệm`
        : "Target <30%",
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-3">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="kpi-box">
          <div className="label-ops text-2xs mb-3">{kpi.label}</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="kpi-number">{kpi.value}</span>
            {kpi.unit && (
              <span className="mono text-md text-text-secondary tabular">{kpi.unit}</span>
            )}
          </div>
          {kpi.delta && (
            <div
              className={clsx(
                "mono text-xs mb-2",
                kpi.deltaTone === "up"      && "text-signal-p3",
                kpi.deltaTone === "warn"    && "text-signal-p0",
                kpi.deltaTone === "down"    && "text-signal-p1",
                kpi.deltaTone === "neutral" && "text-text-secondary",
              )}
            >
              {kpi.deltaTone === "up" ? "▲ " : kpi.deltaTone === "warn" ? "▼ " : ""}
              {kpi.delta}
            </div>
          )}
          {kpi.sub && (
            <div className="text-xs text-text-tertiary leading-snug">{kpi.sub}</div>
          )}
        </div>
      ))}
    </div>
  );
}
