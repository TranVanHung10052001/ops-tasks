import { type ReactNode } from "react";
import { TODAY, OpsTask } from "@/lib/mock";
import { ApiStats, ApiMetrics } from "@/lib/api";

function buildOverviewText(stats?: ApiStats, metrics?: ApiMetrics): string {
  const active = stats?.active ?? 0;
  const blocked = stats?.blocked ?? 0;

  let parts: string[] = [];

  if (active > 0) {
    parts.push(`Truck team đang chạy ${active} task.`);
  } else if (stats) {
    parts.push("Queue sạch — không có task đang chạy.");
  } else {
    parts.push("Hệ thống đang khởi động.");
  }

  if (blocked > 0) {
    parts.push(`${blocked} task bị chặn cần giải tỏa.`);
  }

  if (metrics?.gsv_today_b) {
    const wow = metrics.gsv_wow_pct ? ` (${parseFloat(metrics.gsv_wow_pct) > 0 ? "+" : ""}${parseFloat(metrics.gsv_wow_pct).toFixed(0)}% WoW)` : "";
    parts.push(`GSV truck hôm nay ${metrics.gsv_today_b} tỷ${wow}.`);
  }

  if (metrics?.fill_rate_core_pct) {
    parts.push(`Fill rate core ${metrics.fill_rate_core_pct}%.`);
  }

  return parts.join(" ") || "Đang tải dữ liệu vận hành…";
}

type Signal = { tone: "p0" | "p1" | "p2"; text: ReactNode };

function buildSignals(stats?: ApiStats, metrics?: ApiMetrics): Signal[] {
  const signals: Signal[] = [];

  // Signal 1: overloaded members
  if (stats && stats.overloaded_count > 0) {
    signals.push({
      tone: "p0",
      text: (
        <span>
          <span className="text-signal-p0">{stats.overloaded_count} thành viên overload</span>
          {" "}— kiểm tra phân bổ task ngay.
        </span>
      ),
    });
  }

  // Signal 2: overdue tasks
  if (stats && stats.overdue > 0) {
    signals.push({
      tone: "p1",
      text: (
        <span>
          <span className="text-accent-paper">{stats.overdue} task quá hạn</span>
          {" "}— cần giải tỏa hoặc cập nhật deadline.
        </span>
      ),
    });
  }

  // Signal 3: Fill rate warning
  if (metrics?.fill_rate_core_pct) {
    const fr = parseFloat(metrics.fill_rate_core_pct);
    if (!isNaN(fr) && fr < 65) {
      signals.push({
        tone: "p1",
        text: (
          <span>
            FR core <span className="text-accent-paper">{fr.toFixed(1)}%</span>
            {" "}— dưới target 68%, cần kích hoạt supply thêm.
          </span>
        ),
      });
    }
  }

  // Signal 4: COGS warning
  if (metrics?.cogs_bulky_pct) {
    const cogs = parseFloat(metrics.cogs_bulky_pct);
    if (!isNaN(cogs) && cogs > 30) {
      signals.push({
        tone: "p1",
        text: (
          <span>
            COGS Bulky <span className="text-accent-paper">{cogs.toFixed(1)}%</span>
            {" "}— vượt target 30%, cần review route + vendor.
          </span>
        ),
      });
    }
  }

  return signals.slice(0, 3);
}

export default function BriefingCard({
  stats,
  topTasks,
  metrics,
}: {
  stats?: ApiStats;
  topTasks?: OpsTask[];
  metrics?: ApiMetrics;
}) {
  const p0Tasks = topTasks?.filter((t) => t.priority === "P0").slice(0, 3) ?? [];
  const signals = buildSignals(stats, metrics);
  const overviewText = buildOverviewText(stats, metrics);

  return (
    <section className="ops-surface relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent-amber" />
      <div className="hatch absolute top-0 right-0 w-32 h-full opacity-40" />

      <div className="p-6 relative">
        <div className="flex items-baseline justify-between mb-5">
          <div className="flex items-center gap-3">
            <span className="section-label">Báo cáo điều vận</span>
            <span className="text-text-tertiary">·</span>
            <span className="mono text-2xs text-text-tertiary tracking-wider">
              {TODAY.short} · {TODAY.dayName}
            </span>
          </div>
          <div className="mono text-2xs text-text-tertiary">
            {metrics?.updated_at
              ? `cập nhật ${new Date(metrics.updated_at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`
              : "chờ kết nối dữ liệu"}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-8">
          {/* Overview */}
          <div>
            <div className="section-label mb-2">Tổng quan</div>
            <p className="editorial text-xl leading-snug text-text-primary">
              {overviewText}
            </p>
          </div>

          {/* Priority tasks */}
          <div>
            <div className="section-label mb-2">Ưu tiên hôm nay</div>
            <ol className="space-y-2 text-md text-text-primary">
              {p0Tasks.length > 0 ? (
                p0Tasks.map((t, i) => (
                  <li key={t.id} className="flex gap-2.5">
                    <span className="mono text-accent-amber w-4">{String(i + 1).padStart(2, "0")}</span>
                    <span>{t.title.slice(0, 80)}{t.title.length > 80 ? "…" : ""}</span>
                  </li>
                ))
              ) : (
                <li className="text-text-disabled text-sm">
                  {topTasks !== undefined
                    ? "Không có task P0 đang mở"
                    : "Chờ kết nối Telegram bot để lấy task"}
                </li>
              )}
            </ol>
          </div>

          {/* Signals */}
          <div>
            <div className="section-label mb-2">Tín hiệu cần chú ý</div>
            {signals.length > 0 ? (
              <ul className="space-y-2 text-md text-text-primary">
                {signals.map((s, i) => (
                  <li key={i} className="flex gap-2.5 items-start">
                    <span className={`mt-1 ${s.tone === "p0" ? "text-signal-p0" : s.tone === "p1" ? "text-signal-p1" : "text-signal-p2"}`}>●</span>
                    <span>{s.text}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-text-disabled text-sm">
                {stats ? "Không có tín hiệu bất thường." : "Chờ kết nối dữ liệu."}
              </p>
            )}
          </div>
        </div>

        <div className="dotted-divider my-5" />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-2xs text-text-tertiary">
            <span className="text-accent-amber">⊙</span>
            <span className="mono uppercase tracking-wider">
              Ahamove Ops · Nguồn: Ops DB + Redash BI
            </span>
          </div>
          <div />
        </div>
      </div>
    </section>
  );
}
