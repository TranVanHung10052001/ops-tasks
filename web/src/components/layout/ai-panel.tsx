"use client";

import useSWR from "swr";
import { ApiOkrResponse, ApiStats, ApiMetrics } from "@/lib/api";

// ─── SWR fetcher ──────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then((r) => r.json());

// ─── Mini OKR dial ────────────────────────────────────────────────────────────

function colorFor(p: number) {
  if (p < 34) return "var(--signal-p0)";
  if (p < 67) return "var(--signal-p2)";
  return "var(--signal-p3)";
}

function MiniDial({ pct, label }: { pct: number; label: string }) {
  const size = 76;
  const r = 27;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  const arcLen = (circ * 3) / 4;
  const offset = arcLen * (1 - pct / 100);
  const color = colorFor(pct);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        width={size}
        height={Math.round(size * 0.84)}
        viewBox={`0 0 ${size} ${size}`}
        style={{ overflow: "visible" }}
      >
        <g transform={`rotate(135 ${cx} ${cy})`}>
          <circle cx={cx} cy={cy} r={r} fill="none"
            stroke="var(--divider-strong)" strokeWidth="2.5"
            strokeDasharray={`${arcLen} ${circ}`}
          />
          {pct > 0 && (
            <circle cx={cx} cy={cy} r={r} fill="none"
              stroke={color} strokeWidth="3.5" strokeLinecap="round"
              strokeDasharray={`${arcLen} ${circ}`}
              strokeDashoffset={offset}
            />
          )}
        </g>
        <text x={cx} y={cy + 5} textAnchor="middle"
          style={{ fontFamily: "var(--font-mono)", fontSize: "11px",
            fontVariantNumeric: "tabular-nums", fill: color }}
        >
          {pct}%
        </text>
      </svg>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: "9px",
        color: "var(--text-tertiary)", textAlign: "center",
        maxWidth: "72px", lineHeight: 1.3 }}
      >
        {label}
      </div>
    </div>
  );
}

// ─── Data helpers ─────────────────────────────────────────────────────────────

function computeOkrProgress(okr: ApiOkrResponse) {
  return okr.objectives.map((obj) => {
    const actions = okr.actions.filter(
      (a) => a.okr === obj.id || a.okr.startsWith(obj.id + ".")
    );
    const total = actions.length || 1;
    const done = actions.filter((a) => !a.is_overdue).length;
    const overdue = actions.filter((a) => a.is_overdue).length;
    const pct = Math.round((done / total) * 100);
    // Short label: first KR target or fallback to category
    const firstTarget = obj.krs[0]?.target ?? "";
    const label = `${obj.label.split(" ")[0]} · ${firstTarget.slice(0, 10)}`;
    return { id: obj.id, label, pct, overdue, total };
  });
}

type Signal = { tone: "p0" | "p1" | "p2" | "p3"; text: string };

function buildSignals(
  stats?: ApiStats,
  okrData?: ApiOkrResponse,
  metrics?: ApiMetrics
): Signal[] {
  const signals: Signal[] = [];

  if (stats?.overloaded_count && stats.overloaded_count > 0) {
    signals.push({
      tone: "p0",
      text: `${stats.overloaded_count} thành viên đang overload — kiểm tra phân bổ task.`,
    });
  }

  if (stats?.overdue && stats.overdue > 0) {
    signals.push({
      tone: "p1",
      text: `${stats.overdue} task quá hạn — cần giải tỏa hoặc update deadline.`,
    });
  }

  if (metrics?.fill_rate_core_pct) {
    const fr = parseFloat(metrics.fill_rate_core_pct);
    if (!isNaN(fr) && fr < 65) {
      signals.push({
        tone: "p1",
        text: `FR core ${fr.toFixed(1)}% — dưới target 68%, cần kích hoạt supply.`,
      });
    }
  }

  if (metrics?.cogs_bulky_pct) {
    const cogs = parseFloat(metrics.cogs_bulky_pct);
    if (!isNaN(cogs) && cogs > 30) {
      signals.push({
        tone: "p1",
        text: `COGS Bulky ${cogs.toFixed(1)}% — vượt target 30%.`,
      });
    }
  }

  if (okrData) {
    const atRisk = okrData.objectives.filter((obj) => {
      const actions = okrData.actions.filter(
        (a) => a.okr === obj.id || a.okr.startsWith(obj.id + ".")
      );
      const overdue = actions.filter((a) => a.is_overdue).length;
      return overdue / (actions.length || 1) >= 0.5;
    });
    if (atRisk.length > 0) {
      signals.push({
        tone: "p2",
        text: `${atRisk.length} OKR at-risk: ${atRisk.map((o) => o.id).join(", ")} — >50% actions overdue.`,
      });
    }
  }

  return signals.slice(0, 3);
}

function buildQuickSuggestions(
  stats?: ApiStats,
  metrics?: ApiMetrics,
  okrData?: ApiOkrResponse
): string[] {
  const s: string[] = [];
  const now = new Date();
  const week = Math.ceil(((now.getTime() - new Date(now.getFullYear(), 0, 1).getTime())
    / 86400000 + 1) / 7);

  if (stats?.overdue && stats.overdue > 0) s.push(`Task overdue (${stats.overdue})`);

  const fr = parseFloat(metrics?.fill_rate_core_pct ?? "");
  if (!isNaN(fr) && fr < 68) s.push("Phân tích Fill Rate");

  if (okrData) {
    const lowPct = okrData.objectives.find((obj) => {
      const acts = okrData.actions.filter(
        (a) => a.okr === obj.id || a.okr.startsWith(obj.id + ".")
      );
      const done = acts.filter((a) => !a.is_overdue).length;
      return (done / (acts.length || 1)) < 0.4;
    });
    if (lowPct) s.push(`${lowPct.id} chi tiết`);
  }

  s.push(`Báo cáo tuần ${week}`);
  s.push("Top 5 KH Bulky");

  return s.slice(0, 4);
}

function buildSummaryInsight(okrData?: ApiOkrResponse): string {
  if (!okrData) return "Đang tải dữ liệu vận hành…";

  const worst = okrData.objectives
    .map((obj) => {
      const actions = okrData.actions.filter(
        (a) => a.okr === obj.id || a.okr.startsWith(obj.id + ".")
      );
      const overdue = actions.filter((a) => a.is_overdue).length;
      return { id: obj.id, label: obj.label, overdue, total: actions.length };
    })
    .sort((a, b) => b.overdue - a.overdue)[0];

  if (!worst || worst.overdue === 0) {
    return "Tất cả OKR đang on-track — không có action quá hạn. Tiếp tục duy trì.";
  }

  return `${worst.id} (${worst.label}) có ${worst.overdue}/${worst.total} action overdue — cần ưu tiên giải tỏa trước cuối tuần.`;
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function AIPanel() {
  const { data: okrRaw } = useSWR<ApiOkrResponse>("/api/okr", fetcher, {
    refreshInterval: 60_000,
  });
  const { data: stats } = useSWR<ApiStats>("/api/stats", fetcher, {
    refreshInterval: 30_000,
  });
  const { data: metrics } = useSWR<ApiMetrics>("/api/metrics", fetcher, {
    refreshInterval: 60_000,
  });

  const okrProgress = okrRaw ? computeOkrProgress(okrRaw) : null;
  const signals = buildSignals(stats, okrRaw, metrics);
  const suggestions = buildQuickSuggestions(stats, metrics, okrRaw);
  const insight = buildSummaryInsight(okrRaw);

  const now = new Date();
  const timeStr = now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  const dateStr = `${String(now.getDate()).padStart(2, "0")}·${String(now.getMonth() + 1).padStart(2, "0")}`;

  const isConnected = !!(stats || okrRaw);

  return (
    <aside className="w-[320px] bg-surface-deep border-l border-divider flex flex-col h-full fixed right-0 top-10 bottom-0 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-divider">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-accent-amber text-md">⊙</span>
            <span className="text-md text-text-primary font-medium">Trợ lý điều vận</span>
          </div>
          <span className={`status-dot ${isConnected ? "active" : ""}`} />
        </div>
        <div className="label-mono text-2xs text-text-tertiary">
          {isConnected
            ? `phiên ${timeStr} · ${dateStr} · sẵn sàng nhận lệnh`
            : `${timeStr} · ${dateStr} · chờ kết nối bot`}
        </div>
      </div>

      {/* Messages scroll area */}
      <div className="flex-1 overflow-y-auto scroll-ops px-4 py-4 space-y-4">

        {/* OKR summary block */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-accent-amber">⊙</span>
            <span className="text-xs text-text-secondary">Trợ lý điều vận</span>
            <span className="mono text-2xs text-text-tertiary">{timeStr}</span>
          </div>
          <div className="bg-surface border border-divider p-3">
            <div className="text-sm text-text-primary mb-3">
              <span className="text-accent-paper">{okrRaw ? `${okrRaw.objectives.length} OKR Q2` : "OKR Q2"}</span>
              {okrRaw && (
                <span className="text-text-secondary"> · {okrRaw.overdue_actions} action overdue · {okrRaw.p0_actions} P0</span>
              )}
            </div>

            {/* OKR dials — top 4 */}
            {okrProgress ? (
              <div className="grid grid-cols-2 gap-3 mb-3">
                {okrProgress.slice(0, 4).map((o) => (
                  <MiniDial key={o.id} pct={o.pct} label={o.label} />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3 mb-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex flex-col items-center gap-1 opacity-20">
                    <div className="w-[76px] h-[64px] bg-surface-deep rounded-full" />
                    <div className="h-2 w-16 bg-surface-deep" />
                  </div>
                ))}
              </div>
            )}

            <div className="editorial text-md text-accent-paper border-t border-divider pt-3">
              "{insight}"
            </div>
            <div className="flex gap-1.5 mt-3">
              <button className="btn-ops text-2xs">Xem chi tiết</button>
              <button className="btn-ops primary text-2xs">Tạo plan</button>
            </div>
          </div>
        </div>

        {/* Risk signals */}
        {signals.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-signal-p0">⚠</span>
              <span className="text-xs text-text-secondary">Tín hiệu rủi ro · {timeStr}</span>
            </div>
            <div className="space-y-2">
              {signals.map((s, i) => (
                <div
                  key={i}
                  className={`bg-surface border-l-2 p-3 ${
                    s.tone === "p0" ? "border-signal-p0"
                    : s.tone === "p1" ? "border-signal-p1"
                    : s.tone === "p2" ? "border-signal-p2"
                    : "border-signal-p3"
                  }`}
                >
                  <div className="text-sm text-text-primary">{s.text}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No signals — all green */}
        {isConnected && signals.length === 0 && (
          <div className="bg-surface border border-divider p-3">
            <div className="flex items-center gap-2 text-signal-p3">
              <span>▲</span>
              <span className="text-sm">Không có tín hiệu bất thường. Vận hành ổn định.</span>
            </div>
          </div>
        )}

        {/* Not connected placeholder */}
        {!isConnected && (
          <div className="bg-surface border border-divider p-3 text-center">
            <div className="text-text-disabled text-sm mb-1">Chưa kết nối bot</div>
            <div className="mono text-2xs text-text-tertiary">
              Xem hướng dẫn tại /telegram
            </div>
          </div>
        )}

      </div>

      {/* Quick suggestions */}
      <div className="px-4 py-2 border-t border-divider">
        <div className="label-ops text-2xs mb-2">Gợi ý nhanh</div>
        <div className="flex flex-wrap gap-1 mb-2">
          {suggestions.map((s) => (
            <button
              key={s}
              className="text-2xs px-2 py-1 bg-surface border border-divider text-text-secondary hover:text-text-primary hover:border-accent-amber-deep transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-divider">
        <div className="flex items-center gap-2 bg-surface border border-divider-strong px-3 py-2 focus-within:border-accent-amber-deep">
          <span className="text-accent-amber text-sm">{">"}</span>
          <input
            type="text"
            placeholder="Hỏi gì về team..."
            className="flex-1 bg-transparent outline-none text-sm text-text-primary placeholder:text-text-tertiary"
          />
          <span className="kbd">↵</span>
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="mono text-2xs text-text-tertiary">@mention · #task để link</span>
          <span className="mono text-2xs text-text-tertiary">
            {isConnected ? "live" : "offline"}
          </span>
        </div>
      </div>
    </aside>
  );
}
