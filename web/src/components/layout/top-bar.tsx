"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Logo from "./logo";

export default function TopBar() {
  const router = useRouter();
  const [time, setTime] = useState("--:--");
  const [q, setQ] = useState("");

  useEffect(() => {
    const update = () => {
      const d = new Date();
      setTime(`${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`);
    };
    update();
    const id = setInterval(update, 30000);
    return () => clearInterval(id);
  }, []);

  function onSearch(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      const term = q.trim();
      router.push(term ? `/tasks?q=${encodeURIComponent(term)}` : "/tasks");
    }
  }

  return (
    <header
      className="h-16 flex items-center gap-4 px-5 fixed top-0 left-0 right-0 z-50"
      style={{ background: "var(--surface)", boxShadow: "var(--el1)" }}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 shrink-0">
        <Logo />
        <span className="text-2xs text-text-tertiary hidden lg:block leading-tight">
          Ahamove · Điều vận xe tải
        </span>
      </div>

      {/* Search pill (Enter → bảng điều vận) */}
      <label
        className="hidden md:flex items-center gap-3 flex-1 max-w-[520px] rounded-full px-4 py-2.5 transition-shadow focus-within:shadow-md"
        style={{ background: "var(--surface-deep)" }}
      >
        <span className="text-text-tertiary text-base leading-none" aria-hidden>⌕</span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onSearch}
          placeholder="Tìm task, thành viên, OKR…"
          aria-label="Tìm kiếm"
          className="flex-1 bg-transparent outline-none text-sm text-text-primary placeholder:text-text-tertiary"
        />
        <span className="kbd">⌘K</span>
      </label>

      {/* Right cluster */}
      <div className="flex items-center gap-2 shrink-0 ml-auto">
        <span
          className="inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-semibold"
          style={{ background: "var(--sec-container)", color: "var(--on-sec-container)" }}
        >
          <span className="status-dot active" />
          live
        </span>
        <button
          aria-label="Thông báo"
          className="relative w-10 h-10 rounded-full inline-flex items-center justify-center text-text-secondary hover:bg-surface-deep transition-colors text-base"
        >
          🔔
          <span
            className="absolute top-1.5 right-1.5 min-w-[16px] h-4 rounded-full text-[9px] font-bold text-white inline-flex items-center justify-center px-1"
            style={{ background: "var(--signal-p0)", border: "2px solid var(--surface)" }}
          >
            3
          </span>
        </button>
        <span className="text-xs text-text-tertiary tabular mx-1 hidden sm:inline">{time} ICT</span>
        <span
          className="w-10 h-10 rounded-full inline-flex items-center justify-center text-white font-bold text-sm shrink-0"
          style={{ background: "linear-gradient(140deg,#00868d,#004f53)", boxShadow: "var(--el1)" }}
          title="Trần Văn Hùng"
        >
          H
        </span>
      </div>
    </header>
  );
}
