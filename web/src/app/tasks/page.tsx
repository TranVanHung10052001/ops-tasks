"use client";

import { useState } from "react";
import DispatchBoard from "@/components/ui/dispatch-board";
import TaskLedger from "@/components/ui/task-ledger";
import TimelineTrack from "@/components/ui/timeline-track";
import { TASKS } from "@/lib/mock";
import clsx from "clsx";

const VIEWS = [
  { key: "board", label: "Bảng điều vận", sub: "Kanban theo tín hiệu" },
  { key: "ledger", label: "Sổ theo dõi", sub: "Bảng dense" },
  { key: "timeline", label: "Timeline", sub: "Theo giờ" },
] as const;

export default function TasksPage() {
  const [view, setView] = useState<(typeof VIEWS)[number]["key"]>("board");

  return (
    <div className="p-6 max-w-[1400px]">
      <header className="flex items-end justify-between mb-8">
        <div>
          <div className="label-ops text-2xs mb-1.5">Đài chính · II · Bảng điều vận</div>
          <h1 className="text-[32px] text-text-primary editorial leading-tight">Sổ điều vận chiều thứ năm.</h1>
          <p className="text-md text-text-secondary mt-1">
            Tổng {TASKS.length} task đang theo dõi · phân theo 4 mức tín hiệu · cập nhật mỗi 30s.
          </p>
        </div>
        <div className="text-right mono text-2xs text-text-tertiary uppercase tracking-wider">
          T-2026-04827 → T-2026-04840
        </div>
      </header>

      {/* View switcher */}
      <div className="flex items-center gap-3 mb-8">
        <div className="label-ops text-2xs">Chế độ xem</div>
        <div className="flex gap-0 border border-divider-strong">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={clsx(
                "px-3 py-1.5 mono text-2xs uppercase tracking-wider transition-colors border-r border-divider-strong last:border-r-0",
                view === v.key ? "bg-accent-amber-deep text-canvas" : "bg-surface text-text-secondary hover:bg-surface-raised"
              )}
            >
              {v.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2 mono text-2xs text-text-tertiary">
          <span className="status-dot active" /> đồng bộ live
        </div>
      </div>

      {view === "board" && <DispatchBoard />}
      {view === "ledger" && <TaskLedger />}
      {view === "timeline" && <TimelineTrack />}
    </div>
  );
}
