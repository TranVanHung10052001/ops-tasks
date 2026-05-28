"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { ApiTask } from "@/lib/api";
import { apiTaskToOpsTask } from "@/lib/data";
import { formatDeadline } from "@/lib/mock";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function TopBar() {
  const [time, setTime] = useState("00:00:00");

  const { data: tasksRaw } = useSWR<{ tasks: ApiTask[] } | { error: string }>(
    "/api/tasks?limit=200", fetcher, { refreshInterval: 30_000 }
  );

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

  // Build the live dispatch feed from real tasks (overdue / blocked / P0 first)
  const now = Date.now();
  const order: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };
  const feed = (tasksRaw && "tasks" in tasksRaw ? tasksRaw.tasks : [])
    .map(apiTaskToOpsTask)
    .filter((t) => t.status !== "hoan_thanh" && t.status !== "tam_dung")
    .sort((a, b) => {
      const aOver = a.deadline && new Date(a.deadline).getTime() < now ? -1 : 0;
      const bOver = b.deadline && new Date(b.deadline).getTime() < now ? -1 : 0;
      if (aOver !== bOver) return aOver - bOver;
      return (order[a.priority] ?? 9) - (order[b.priority] ?? 9);
    })
    .slice(0, 8)
    .map((t) => {
      const d = formatDeadline(t.deadline);
      const overdue = d.relative.startsWith("quá");
      const flag = overdue ? "⚠ " : t.status === "bi_chan" ? "⊘ " : "";
      const title = t.title.length > 48 ? t.title.slice(0, 48) + "…" : t.title;
      return `${flag}${t.id} · ${t.priority} · ${title} · ${d.relative}`;
    });

  const hasFeed = feed.length > 0;
  const tickerText = hasFeed
    ? [...feed, ...feed].join("  ·  ")
    : "Chưa có task đang chạy — kết nối Telegram bot tại /telegram";

  return (
    <header className="h-10 bg-surface-deep border-b border-divider flex items-center justify-between px-4 fixed top-0 left-0 right-0 z-50">
      {/* Brand */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-accent-amber" />
          <span className="mono text-xs text-text-secondary tracking-widest uppercase">
            AHAMOVE OPS <span className="text-text-tertiary">·</span>{" "}
            <span className="text-accent-paper">TRUCK</span>
          </span>
        </div>
        <span className="text-text-tertiary text-xs hidden lg:inline">·</span>
        <span className="mono text-2xs text-text-tertiary tracking-wider uppercase hidden lg:inline">v1.4.2 · Truck</span>
      </div>

      {/* Live ticker — dispatch feed from real tasks */}
      <div className="flex-1 overflow-hidden mx-5 max-w-[360px] hidden md:block">
        {hasFeed ? (
          <div className="marquee-track gap-0">
            <span className="mono text-2xs text-text-tertiary">
              <span className="text-accent-amber mr-2">▸</span>
              {tickerText}
              <span className="text-accent-amber mx-2">▸</span>
              {tickerText}
            </span>
          </div>
        ) : (
          <div className="mono text-2xs text-text-disabled truncate text-center">{tickerText}</div>
        )}
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
