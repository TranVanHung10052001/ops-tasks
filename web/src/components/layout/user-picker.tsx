"use client";

import { useState, useEffect, useRef } from "react";
import { MEMBERS } from "@/lib/mock";
import clsx from "clsx";

export default function UserPicker() {
  const [uid, setUid] = useState("m0");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setUid(localStorage.getItem("ops-uid") ?? "m0");
  }, []);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const select = (id: string) => {
    localStorage.setItem("ops-uid", id);
    setUid(id);
    setOpen(false);
    window.dispatchEvent(new Event("ops-user-changed"));
  };

  const me = MEMBERS.find((m) => m.id === uid) ?? MEMBERS[0];

  return (
    <div ref={ref} className="relative border-t border-divider">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2.5 px-4 py-2.5 hover:bg-surface transition-colors text-left"
      >
        <div className="callsign shrink-0 text-xs">{me.initials}</div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-text-primary truncate">{me.name}</div>
          <div className="mono text-2xs text-text-tertiary">{me.initials} · {me.grade ?? me.initials}</div>
        </div>
        <span className="mono text-2xs text-text-tertiary shrink-0">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 right-0 bg-surface-raised border border-divider shadow-lg z-50 max-h-[280px] overflow-y-auto scroll-ops">
          <div className="px-3 py-1.5 label-ops text-2xs border-b border-divider">Chọn tài khoản</div>
          {MEMBERS.map((m) => (
            <button
              key={m.id}
              onClick={() => select(m.id)}
              className={clsx(
                "w-full flex items-center gap-2.5 px-3 py-1.5 hover:bg-surface transition-colors text-left",
                uid === m.id && "bg-surface border-l-2 border-accent-amber"
              )}
            >
              <span className="mono text-2xs text-accent-paper w-8 shrink-0">{m.initials}</span>
              <span className="text-xs text-text-primary flex-1">{m.name}</span>
              {uid === m.id && <span className="mono text-2xs text-accent-amber">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
