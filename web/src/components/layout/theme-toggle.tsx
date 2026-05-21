"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";

type Theme = "toi" | "sang";

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("toi");

  useEffect(() => {
    const stored = (localStorage.getItem("ops-theme") as Theme | null) ?? "toi";
    setTheme(stored);
  }, []);

  const change = (next: Theme) => {
    setTheme(next);
    localStorage.setItem("ops-theme", next);
    if (next === "sang") {
      document.documentElement.setAttribute("data-theme", "sang");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  };

  return (
    <div className="px-3 py-4 border-t border-divider">
      <div className="px-3 mb-2 label-ops text-2xs">Hiển thị</div>
      <div className="flex gap-1 px-3">
        <button
          onClick={() => change("toi")}
          className={clsx(
            "flex-1 mono text-2xs uppercase tracking-wider py-1.5 border transition-colors",
            theme === "toi"
              ? "bg-surface-raised border-accent-amber-deep text-accent-paper"
              : "border-divider-strong text-text-tertiary hover:text-text-primary"
          )}
        >
          ◐ Tối
        </button>
        <button
          onClick={() => change("sang")}
          className={clsx(
            "flex-1 mono text-2xs uppercase tracking-wider py-1.5 border transition-colors",
            theme === "sang"
              ? "bg-surface-raised border-accent-amber-deep text-accent-paper"
              : "border-divider-strong text-text-tertiary hover:text-text-primary"
          )}
        >
          ◑ Sáng
        </button>
      </div>
      <div className="px-3 mt-2 mono text-2xs text-text-tertiary">⌘⇧L để đổi</div>
    </div>
  );
}
