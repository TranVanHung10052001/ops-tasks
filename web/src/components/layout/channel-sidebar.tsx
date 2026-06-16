"use client";

import Link from "next/link";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { ApiMember, ApiTask } from "@/lib/api";
import { apiMemberToMember, apiTaskToOpsTask } from "@/lib/data";
import ThemeToggle from "./theme-toggle";
import UserPicker from "./user-picker";
import clsx from "clsx";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const NAV_ITEMS = [
  { href: "/",         label: "Tổng quan",     code: "I"   },
  { href: "/tasks",    label: "Bảng điều vận", code: "II"  },
  { href: "/okr",      label: "Theo dõi OKR",  code: "III" },
  { href: "/team",     label: "Nhóm điều vận", code: "IV"  },
  { href: "/performance", label: "Hiệu suất",  code: "V"   },
  { href: "/ask",      label: "Hỏi AI",        code: "VI"  },
  { href: "/telegram", label: "Telegram bot",  code: "VII" },
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

  // ── Live data from bot (same source as the rest of the dashboard) ──────────
  const { data: teamRaw } = useSWR<ApiMember[] | { error: string }>(
    "/api/team", fetcher, { refreshInterval: 60_000 }
  );
  const { data: tasksRaw } = useSWR<{ tasks: ApiTask[] } | { error: string }>(
    "/api/tasks?limit=200", fetcher, { refreshInterval: 30_000 }
  );

  const members = Array.isArray(teamRaw)
    ? teamRaw.map((m, i) => apiMemberToMember(m, i))
    : [];
  const tasks = (tasksRaw && "tasks" in tasksRaw ? tasksRaw.tasks : [])
    .map(apiTaskToOpsTask)
    // active only — match the dispatch board's default scope
    .filter((t) => t.status !== "hoan_thanh" && t.status !== "tam_dung");

  const activeChannel = searchParams.get("channel");
  const activeMember = searchParams.get("member");
  const activePriorities = searchParams.get("priority")?.split(",").filter(Boolean) ?? [];

  function filterByChannel(channel: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (channel) params.set("channel", channel); else params.delete("channel");
    params.delete("member");
    router.push(`/tasks?${params.toString()}`);
  }

  function filterByMember(memberId: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (activeMember === memberId) params.delete("member");
    else params.set("member", memberId);
    router.push(`/tasks?${params.toString()}`);
  }

  function togglePriority(p: string) {
    const set = new Set(activePriorities);
    if (set.has(p)) set.delete(p); else set.add(p);
    const next = Array.from(set);
    if (pathname === "/tasks") {
      const params = new URLSearchParams(searchParams.toString());
      if (next.length) params.set("priority", next.join(","));
      else params.delete("priority");
      router.push(`/tasks?${params.toString()}`);
    } else {
      router.push(next.length ? `/tasks?priority=${next.join(",")}` : "/tasks");
    }
  }

  const tasksByChannel = {
    JD:    tasks.filter((t) => t.channel === "JD").length,
    OKR:   tasks.filter((t) => t.channel === "OKR").length,
    Adhoc: tasks.filter((t) => t.channel === "Adhoc").length,
    total: tasks.length,
  };

  const botOffline = teamRaw !== undefined && !Array.isArray(teamRaw);

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
              <span className="mono text-2xs text-text-tertiary tabular">{count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="dotted-divider mx-3" />

      {/* TEAM */}
      <div className="px-3 py-4">
        <div className="px-3 mb-2 label-ops text-2xs flex items-center justify-between">
          <span>Thành viên</span>
          <span className="mono text-tertiary-ops">{members.length}</span>
        </div>
        <div className="space-y-0.5">
          {members.length === 0 && (
            <div className="px-3 py-2 mono text-2xs text-text-disabled">
              {botOffline ? "Chưa kết nối bot" : "Đang tải…"}
            </div>
          )}
          {members.map((m) => {
            const ratio = m.workloadMax ? m.workload / m.workloadMax : 0;
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
                  <span className="flex-1 truncate">{m.unclaimed ? "⚠ " : ""}{m.name}</span>
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
        <div className="px-3 mb-2 label-ops text-2xs">Lọc theo mức độ</div>
        <div className="space-y-1 px-3">
          {(["P0", "P1", "P2", "P3", "P4"] as const).map((p) => {
            const count = tasks.filter((t) => t.priority === p).length;
            const checked = activePriorities.includes(p);
            return (
              <label
                key={p}
                className="flex items-center gap-2.5 text-sm text-text-secondary cursor-pointer hover:text-text-primary"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => togglePriority(p)}
                  className="appearance-none w-3 h-3 border border-divider-strong bg-surface checked:bg-accent-amber checked:border-accent-amber cursor-pointer"
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
                  {checked ? "◼" : "◻"} {p}
                </span>
                <span className="flex-1 text-xs">
                  {p === "P0" ? "Khẩn" : p === "P1" ? "Cao" : p === "P2" ? "Trung bình" : p === "P3" ? "Thấp" : "Khi rảnh"}
                </span>
                <span className="mono text-2xs text-text-tertiary tabular">{count}</span>
              </label>
            );
          })}
        </div>
        {activePriorities.length > 0 && (
          <button
            onClick={() => router.push(pathname === "/tasks"
              ? `/tasks?${(() => { const p = new URLSearchParams(searchParams.toString()); p.delete("priority"); return p.toString(); })()}`
              : "/tasks")}
            className="mt-2 mx-3 mono text-2xs text-text-tertiary hover:text-accent-amber"
          >
            ✕ Xóa lọc mức độ
          </button>
        )}
      </div>

      <div className="flex-1" />
      <UserPicker />
      <ThemeToggle />
    </aside>
  );
}
