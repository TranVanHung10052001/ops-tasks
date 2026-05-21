"use client";

import { useEffect, useState } from "react";

const TICKER = [
  "T-04832 · OPS-03 nhận lệnh VSIP II · 3×2.5T",
  "T-04835 · OPS-06 xuất phát Sóng Thần · 08:14",
  "T-04829 · OPS-01 xác nhận Foxconn Quang Châu",
  "T-04840 · AI classify Masan → JD 74%",
  "T-04838 · OPS-05 hoàn thành LG Hải Phòng",
  "T-04831 · Cảnh báo · Lalamove -8% Bulky HCM",
  "T-04833 · OPS-07 routing v2 A/B live Sóng Thần",
  "T-04836 · OPS-02 mini-hub Hồng Bàng · đang cài",
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
            <span className="text-accent-paper">ĐÀI ĐIỀU VẬN</span>
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

      {/* Controls + clock */}
      <div className="flex items-center gap-3 mono text-xs text-text-secondary shrink-0">
        <button className="flex items-center gap-1.5 px-2 py-1 hover:bg-surface transition-colors">
          <span className="text-text-tertiary">{">"}</span>
          <span>tìm task</span>
          <span className="kbd">⌘K</span>
        </button>
        <span className="text-divider-strong">│</span>
        <button className="flex items-center gap-1.5 px-2 py-1 hover:bg-surface transition-colors">
          <span className="text-accent-amber">+</span>
          <span>tạo task</span>
          <span className="kbd">⌘N</span>
        </button>
        <span className="text-divider-strong">│</span>
        <button className="flex items-center gap-1.5 px-2 py-1 hover:bg-surface transition-colors">
          <span>⊙</span>
          <span>trợ lý</span>
          <span className="kbd">⌘J</span>
        </button>
        <span className="text-divider-strong">│</span>
        <div className="flex items-center gap-2">
          <span className="status-dot active" />
          <span className="text-text-primary tabular">{time}</span>
          <span className="text-text-tertiary">ICT</span>
        </div>
      </div>
    </header>
  );
}
