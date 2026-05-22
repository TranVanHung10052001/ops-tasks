"use client";

import { useEffect, useState } from "react";

const TICKER = [
  "⚠ T-2026-02160 · OPS-09 LAN Hub BLOCKED · quá hạn 7 ngày",
  "T-2026-01110 · OPS-02 FR HAN tuần 21 · deadline hôm nay 17h",
  "T-2026-03210 · OPS-01 COGS GXT analysis · P0 chưa bắt đầu",
  "T-2026-03113 · OPS-01 config SLA pickup window Hà Nội",
  "T-2026-02130 · OPS-10 KCN Rental Policy · SOP v1",
  "T-2026-02150 · OPS-09 tuyển 30 driver Long An · 27/05",
  "T-2026-03120 · OPS-01 convert driver Bulky → Marketplace",
  "T-2026-05221 · OPS-06 backlog clearing 4h SGN · ca chiều",
];

export default function TopBar() {
  const [time, setTime] = useState("00:00:00");

  useEffect(() => {
    const update = () => {
      const d = new Date();
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const ss = String(d.getSeconds()).padStart(2, "0");
      setTime(`${hh}:${mm}:${ss}`);
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  const tickerText = [...TICKER, ...TICKER].join("  ·  ");

  return (
    <header className="h-10 bg-surface-deep border-b border-divider flex items-center justify-between px-4 fixed top-0 left-0 right-0 z-50">
      {/* Brand */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-accent-amber" />
          <span className="mono text-xs text-text-secondary tracking-widest uppercase">
            AHAMOVE OPS <span className="text-text-tertiary">·</span>{" "}
            <span className="text-accent-paper">OPS CENTER</span>
          </span>
        </div>
        <span className="text-text-tertiary text-xs">·</span>
        <span className="mono text-2xs text-text-tertiary tracking-wider uppercase">v1.4.2 · Truck</span>
      </div>

      {/* Live ticker — slow dispatch feed */}
      <div className="flex-1 overflow-hidden mx-5 max-w-[360px]">
        <div className="marquee-track gap-0">
          <span className="mono text-2xs text-text-tertiary">
            <span className="text-accent-amber mr-2">▸</span>
            {tickerText}
            <span className="text-accent-amber mx-2">▸</span>
            {tickerText}
          </span>
        </div>
      </div>

      {/* Clock */}
      <div className="flex items-center gap-2 mono text-xs text-text-secondary shrink-0">
        <span className="status-dot active" />
        <span className="text-text-primary tabular">{time}</span>
        <span className="text-text-tertiary">ICT</span>
      </div>
    </header>
  );
}
