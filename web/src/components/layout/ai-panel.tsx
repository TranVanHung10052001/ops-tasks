"use client";

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
          <circle
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke="var(--divider-strong)"
            strokeWidth="2.5"
            strokeDasharray={`${arcLen} ${circ}`}
          />
          {pct > 0 && (
            <circle
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={color}
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray={`${arcLen} ${circ}`}
              strokeDashoffset={offset}
            />
          )}
        </g>
        <text
          x={cx}
          y={cy + 5}
          textAnchor="middle"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            fontVariantNumeric: "tabular-nums",
            fill: color,
          }}
        >
          {pct}%
        </text>
      </svg>
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "9px",
          color: "var(--text-tertiary)",
          textAlign: "center",
          maxWidth: "72px",
          lineHeight: 1.3,
        }}
      >
        {label}
      </div>
    </div>
  );
}

export default function AIPanel() {
  return (
    <aside className="w-[320px] bg-surface-deep border-l border-divider flex flex-col h-full fixed right-0 top-10 bottom-0 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-divider">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-accent-amber text-md">⊙</span>
            <span className="text-md text-text-primary font-medium">Trợ lý điều vận</span>
          </div>
          <span className="status-dot active" />
        </div>
        <div className="label-mono text-2xs text-text-tertiary">
          phiên 14:32 · 22·05 · sẵn sàng nhận lệnh
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scroll-ops px-4 py-4 space-y-4">
        {/* User msg */}
        <div className="flex justify-end">
          <div className="max-w-[260px] bg-surface border border-divider px-3 py-2">
            <div className="text-sm text-text-primary">Tóm tắt OKR Q2 truck cho team</div>
            <div className="mono text-2xs text-text-tertiary mt-1">14:30</div>
          </div>
        </div>

        {/* AI msg — OKR dials */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-accent-amber">⊙</span>
            <span className="text-xs text-text-secondary">Trợ lý điều vận</span>
            <span className="mono text-2xs text-text-tertiary">14:30</span>
          </div>
          <div className="bg-surface border border-divider p-3">
            <div className="text-sm text-text-primary mb-3">
              <span className="text-accent-paper">6 OKR Q2</span> · 4 mục tiêu chính:
            </div>

            {/* 4 OKR mini dials 2×2 */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              <MiniDial pct={73} label="GSV KCN +25%" />
              <MiniDial pct={45} label="Giảm idle -20%" />
              <MiniDial pct={38} label="Pilot LTL" />
              <MiniDial pct={78} label="COGS Bulky <30%" />
            </div>

            {/* Remaining 2 OKRs as compact text */}
            <div className="flex gap-3 mb-3 px-1">
              <div className="flex-1 flex items-center gap-1.5">
                <span className="mono text-2xs tabular" style={{ color: colorFor(88) }}>88%</span>
                <div className="h-0.5 flex-1 bg-surface-deep">
                  <div className="h-full bg-signal-p3" style={{ width: "88%" }} />
                </div>
                <span className="text-2xs text-text-tertiary">3 tỉnh</span>
              </div>
              <div className="flex-1 flex items-center gap-1.5">
                <span className="mono text-2xs tabular" style={{ color: colorFor(52) }}>52%</span>
                <div className="h-0.5 flex-1 bg-surface-deep">
                  <div className="h-full bg-signal-p2" style={{ width: "52%" }} />
                </div>
                <span className="text-2xs text-text-tertiary">AI dispatch</span>
              </div>
            </div>

            <div className="editorial text-md text-accent-paper border-t border-divider pt-3">
              "Pilot LTL đang chậm — Tech MVP mới 20%. Đề xuất dời pilot sang đầu tháng 6 hoặc cắt scope KH SME xuống 4 thay vì 8."
            </div>
            <div className="flex gap-1.5 mt-3">
              <button className="btn-ops text-2xs">Xem chi tiết</button>
              <button className="btn-ops primary text-2xs">Tạo plan</button>
            </div>
          </div>
        </div>

        {/* Competitive alert */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-signal-p1">▲</span>
            <span className="text-xs text-text-secondary">Cảnh báo đối thủ · 14:08</span>
          </div>
          <div className="bg-surface border-l-2 border-signal-p1 p-3">
            <div className="text-sm text-text-primary mb-2">
              <span className="text-signal-p1 font-medium">Lalamove vừa giảm giá Bulky -8% HCM.</span>
            </div>
            <div className="text-xs text-text-secondary mb-2">
              Nguồn: BD Vinamilk báo tin 13:45 + crawler price page. Đối thủ trực tiếp truck Ahamove (cùng ~99% on-demand truck share).
            </div>
            <ul className="text-xs text-text-primary space-y-1 mb-2">
              <li className="flex gap-2"><span className="mono text-accent-amber">→</span> Không giảm giá general (giữ take rate 26%)</li>
              <li className="flex gap-2"><span className="mono text-accent-amber">→</span> Bundle SLA + COD 0% cho 5 KH top Bulky</li>
              <li className="flex gap-2"><span className="mono text-accent-amber">→</span> Audit fill rate tuần 21 vs tuần 22</li>
            </ul>
            <button className="btn-ops text-2xs primary">Tạo task phân tích</button>
          </div>
        </div>

        {/* Auto classify */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-accent-amber ai-pulse" />
            <span className="text-xs text-text-secondary">Phân loại tự động · 14:28</span>
          </div>
          <div className="bg-surface border border-divider p-3">
            <div className="text-sm text-text-primary mb-2">
              Vừa phân loại <span className="mono text-accent-paper">4 task mới</span> từ Telegram:
            </div>
            <div className="space-y-1.5 text-sm text-text-secondary mb-3">
              <div className="flex items-center gap-2">
                <span className="text-state-active">●</span>
                <span>2 task JD (CSKH Foxconn + Phân ca)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-state-active">●</span>
                <span>1 task OKR (Routing v2)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-signal-p2">●</span>
                <span>1 task cần xác nhận (Masan, 74%)</span>
              </div>
            </div>
            <div className="bg-surface-deep border border-divider-strong p-2.5">
              <div className="mono text-2xs text-text-tertiary mb-1">T-04840</div>
              <div className="text-sm text-text-primary mb-2">"Review hợp đồng Masan — vận chuyển kho Hậu Giang"</div>
              <div className="space-y-1 mb-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-accent-amber">◉</span>
                  <span className="text-xs">Phát sinh · Hợp đồng (74%)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-text-tertiary">
                  <span>○</span>
                  <span className="text-xs">OKR · GSV Longhaul (22%)</span>
                </label>
              </div>
              <div className="flex gap-1.5">
                <button className="btn-ops text-2xs primary flex-1">Xác nhận</button>
                <button className="btn-ops text-2xs flex-1">Đổi</button>
              </div>
            </div>
          </div>
        </div>

        {/* Risk detect */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-signal-p0">⚠</span>
            <span className="text-xs text-text-secondary">Phát hiện rủi ro · 13:55</span>
          </div>
          <div className="bg-surface border-l-2 border-signal-p0 p-3">
            <div className="text-sm text-text-primary mb-2">
              <span className="text-signal-p0 font-medium">OPS-03 đang overload.</span> Đang giữ 9/10 task — trong đó có 2 P0 KCN VSIP + Sóng Thần.
            </div>
            <div className="text-xs text-text-secondary mb-2">
              Đề xuất chuyển <span className="mono text-accent-paper">T-04837</span> (onboarding Mass tier HAN) sang OPS-04 (6/10).
            </div>
            <button className="btn-ops text-2xs primary">Áp dụng đề xuất</button>
          </div>
        </div>
      </div>

      {/* Quick suggestions */}
      <div className="px-4 py-2 border-t border-divider">
        <div className="label-ops text-2xs mb-2">Gợi ý nhanh</div>
        <div className="flex flex-wrap gap-1 mb-2">
          {["Báo cáo tuần 21", "Top 5 KH Bulky", "Phân tích Lalamove", "Driver Mass tier"].map((s) => (
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
          <span className="mono text-2xs text-text-tertiary">opus-4.7</span>
        </div>
      </div>
    </aside>
  );
}
