"use client";

import Link from "next/link";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import { MEMBERS, TASKS } from "@/lib/mock";
import ThemeToggle from "./theme-toggle";
import UserPicker from "./user-picker";
import clsx from "clsx";

const NAV_ITEMS = [
  { href: "/",         label: "Tổng quan",     code: "I"   },
  { href: "/tasks",    label: "Bảng điều vận", code: "II"  },
  { href: "/okr",      label: "Theo dõi OKR",  code: "III" },
  { href: "/team",     label: "Nhóm điều vận", code: "IV"  },
  { href: "/ask",      label: "Hỏi AI",        code: "V"   },
  { href: "/telegram", label: "Telegram bot",  code: "VI"  },
];

function workloadColor(ratio: number) {
  if (ratio > 0.8) return "var(--signal-p0)";
  if (ratio > 0.6) return "var(--accent-amber)";
  return "var(--state-active)";
}

export default function ChannelSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  const activeChannel = searchParams.get("channel");
  const activeMember = searchParams.get("member");

  function filterByChannel(channel: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (channel) params.set("channel", channel); else params.delete("channel");
    params.delete("member");
    router.push(`/tasks?${params.toString()}`);
  }

  function filterByMember(memberId: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (activeMember === memberId) {
      params.delete("member");
    } else {
      params.set("member", memberId);
    }
    router.push(`/tasks?${params.toString()}`);
  }

  const tasksByChannel = {
    JD:    TASKS.filter((t) => t.channel === "JD").length,
    OKR:   TASKS.filter((t) => t.channel === "OKR").length,
    Adhoc: TASKS.filter((t) => t.channel === "Adhoc").length,
    total: TASKS.length,
  };

  return (
    <aside className="w-[220px] bg-surface-deep border-r border-divider flex flex-col h-full fixed left-0 top-10 bottom-0 overflow-y-auto scroll-ops">
      {/* NAV */}
      <div className="px-3 py-4">
        <div className="px-3 mb-2 label-ops text-2xs">Menu chính</div>
        <nav className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-2.5 px-3 py-1.5 text-sm transition-colors border-l-2",
                  active
                    ? "border-accent-amber bg-surface text-text-primary"
                    : "border-transparent text-text-secondary hover:bg-surface hover:text-text-primary"
                )}
              >
                <span className="mono text-2xs text-text-tertiary w-5 shrink-0">{item.code}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="dotted-divider mx-3" />

      {/* CHANNELS */}
      <div className="px-3 py-4">
        <div className="px-3 mb-2 label-ops text-2xs flex items-center justify-between">
          <span>Tần số</span>
          <span className="mono text-tertiary-ops">━━━</span>
        </div>
        <div className="space-y-0">
          {([
            { key: null,    label: "Tất cả",   count: tasksByChannel.total },
            { key: "JD",    label: "JD",        count: tasksByChannel.JD },
            { key: "OKR",   label: "OKR",       count: tasksByChannel.OKR },
            { key: "Adhoc", label: "Phát sinh", count: tasksByChannel.Adhoc },
          ] as const).map(({ key, label, count }) => (
            <button
              key={label}
              onClick={() => pathname === "/tasks" ? filterByChannel(key) : router.push(key ? `/tasks?channel=${key}` : "/tasks")}
              className={clsx(
                "channel-radio w-full text-left cursor-pointer transition-colors",
                (!key && !activeChannel) || activeChannel === key ? "active" : ""
              )}
            >
              <div className="dot" />
              <span className="text-sm flex-1">{label}</span>
              <span className="mono text-2xs text-text-tertiary">{count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="dotted-divider mx-3" />

      {/* TEAM */}
      <div className="px-3 py-4">
        <div className="px-3 mb-2 label-ops text-2xs flex items-center justify-between">
          <span>Thành viên</span>
          <span className="mono text-tertiary-ops">{MEMBERS.length}</span>
        </div>
        <div className="space-y-0.5">
          {MEMBERS.map((m) => {
            const ratio = m.workload / m.workloadMax;
            const isActive = activeMember === m.id;
            return (
              <button
                key={m.id}
                onClick={() => pathname === "/tasks" ? filterByMember(m.id) : router.push(`/tasks?member=${m.id}`)}
                className={clsx(
                  "w-full flex flex-col px-3 py-1.5 text-sm transition-colors text-left",
                  isActive
                    ? "bg-surface text-text-primary border-l-2 border-accent-amber"
                    : "text-text-secondary hover:bg-surface hover:text-text-primary border-l-2 border-transparent"
                )}
              >
                <div className="flex items-center gap-2.5 w-full">
                  <span
                    className={clsx(
                      "status-dot shrink-0",
                      m.status === "online"  && "active",
                      m.status === "busy"    && "pending",
                      m.status === "away"    && "paused",
                      m.status === "offline" && "bg-text-disabled"
                    )}
                  />
                  <span className="mono text-2xs text-text-tertiary w-8 shrink-0">{m.initials}</span>
                  <span className="flex-1 truncate">{m.name}</span>
                  <span className="mono text-2xs text-text-tertiary tabular shrink-0">
                    {m.workload}/{m.workloadMax}
                  </span>
                </div>
                {/* Workload mini bar */}
                <div className="w-full h-[3px] bg-surface-raised mt-1 ml-[18px]">
                  <div
                    className="h-full transition-all"
                    style={{
                      width: `${Math.round(ratio * 100)}%`,
                      backgroundColor: workloadColor(ratio),
                    }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="dotted-divider mx-3" />

      {/* FILTERS */}
      <div className="px-3 py-4">
        <div className="px-3 mb-2 label-ops text-2xs">Bộ lọc tín hiệu</div>
        <div className="space-y-1 px-3">
          {(["P0", "P1", "P2", "P3", "P4"] as const).map((p) => {
            const count = TASKS.filter((t) => t.priority === p).length;
            return (
              <label
                key={p}
                className="flex items-center gap-2.5 text-sm text-text-secondary cursor-pointer hover:text-text-primary"
              >
                <input
                  type="checkbox"
                  defaultChecked={p === "P0" || p === "P1"}
                  className="appearance-none w-3 h-3 border border-divider-strong bg-surface checked:bg-accent-amber checked:border-accent-amber"
                />
                <span
                  className={clsx(
                    "mono text-2xs uppercase tracking-wider",
                    p === "P0" && "text-signal-p0",
                    p === "P1" && "text-signal-p1",
                    p === "P2" && "text-signal-p2",
                    p === "P3" && "text-signal-p3",
                    p === "P4" && "text-signal-p4"
                  )}
                >
                  {p === "P0" || p === "P1" ? "◼" : "◻"} {p}
                </span>
                <span className="flex-1 text-xs">
                  {p === "P0" ? "Khẩn" : p === "P1" ? "Cao" : p === "P2" ? "Trung bình" : p === "P3" ? "Thấp" : "Khi rảnh"}
                </span>
                <span className="mono text-2xs text-text-tertiary">{count}</span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="flex-1" />
      <UserPicker />
      <ThemeToggle />
    </aside>
  );
}
