"use client";

import { useState } from "react";
import type { AutoDigestData, AutoDigestItem } from "@/lib/data";
import type { Member } from "@/lib/mock";

interface Props {
  digest: AutoDigestData;
  members: Member[];
}

function fmtDeadline(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const isTomorrow = d.toDateString() === tomorrow.toDateString();
    const t = d.toTimeString().slice(0, 5);
    if (sameDay) return `Hôm nay ${t}`;
    if (isTomorrow) return `Mai ${t}`;
    return `${d.getDate().toString().padStart(2, "0")}/${(d.getMonth() + 1).toString().padStart(2, "0")} ${t}`;
  } catch {
    return iso.slice(0, 16);
  }
}

const PRIORITY_STYLE: Record<string, string> = {
  P0: "text-signal-p0 bg-signal-p0/10 border-signal-p0/30",
  P1: "text-accent-paper bg-accent-paper/10 border-accent-paper/30",
  P2: "text-text-secondary bg-surface-2 border-divider",
  P3: "text-text-tertiary bg-surface-2 border-divider",
};

export default function AutoDigestCard({ digest, members }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [reassigning, setReassigning] = useState<number | null>(null);
  const [items, setItems] = useState(digest.tasks);

  if (digest.count === 0) {
    return (
      <section className="ops-surface">
        <header className="px-4 py-3 border-b border-divider flex items-center justify-between">
          <div>
            <div className="label-ops text-2xs">AI Auto-assign hôm nay</div>
            <div className="mono text-2xs text-text-disabled mt-0.5">
              Bot chưa tự tạo task nào hôm nay — mọi tin nhắn forward đều confirm thủ công.
            </div>
          </div>
          <span className="mono text-md text-text-tertiary">0</span>
        </header>
      </section>
    );
  }

  async function reassign(taskId: number, newAssigneeId: number) {
    setReassigning(taskId);
    try {
      const res = await fetch(`/api/tasks/${taskId}/reassign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_assignee_id: newAssigneeId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Update local state — find new assignee name
      const newName =
        members.find((m) => m.id === `m${newAssigneeId}`)?.fullName ?? "?";
      setItems((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? { ...t, assignee_id: newAssigneeId, assignee_name: newName }
            : t,
        ),
      );
    } catch (err) {
      console.error("reassign failed:", err);
    } finally {
      setReassigning(null);
    }
  }

  const visible = expanded ? items : items.slice(0, 3);

  return (
    <section className="ops-surface">
      <header className="px-4 py-3 border-b border-divider flex items-center justify-between">
        <div>
          <div className="label-ops text-2xs">AI Auto-assign hôm nay · review</div>
          <div className="mono text-2xs text-text-disabled mt-0.5">
            Bot tự tạo {digest.count} task — manager review & reassign nếu cần
          </div>
        </div>
        <span className="mono text-lg text-accent-paper tabular">{digest.count}</span>
      </header>

      <ol className="divide-y divide-divider">
        {visible.map((t) => (
          <li key={t.id} className="px-4 py-3 flex items-start gap-3">
            <span
              className={`mono text-2xs px-1.5 py-0.5 rounded border ${
                PRIORITY_STYLE[t.priority] ?? PRIORITY_STYLE.P2
              }`}
            >
              {t.priority}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-text-primary truncate">
                <span className="mono text-text-tertiary">#{t.id}</span>{" "}
                {t.summary}
              </div>
              <div className="mono text-2xs text-text-tertiary mt-1 flex gap-3 flex-wrap">
                <span>
                  → <span className="text-text-secondary">{t.assignee_name ?? "?"}</span>
                </span>
                <span>{fmtDeadline(t.deadline)}</span>
                <span>·</span>
                <span>{t.category}</span>
              </div>
            </div>
            <ReassignDropdown
              taskId={t.id}
              currentAssigneeId={t.assignee_id}
              members={members}
              disabled={reassigning === t.id}
              onPick={(newId) => reassign(t.id, newId)}
            />
          </li>
        ))}
      </ol>

      {items.length > 3 && (
        <footer className="px-4 py-2 border-t border-divider">
          <button
            onClick={() => setExpanded(!expanded)}
            className="mono text-2xs text-accent-paper hover:underline"
          >
            {expanded ? "Ẩn bớt" : `+ ${items.length - 3} task khác`}
          </button>
        </footer>
      )}
    </section>
  );
}

function ReassignDropdown({
  taskId,
  currentAssigneeId,
  members,
  disabled,
  onPick,
}: {
  taskId: number;
  currentAssigneeId: number | null;
  members: Member[];
  disabled: boolean;
  onPick: (newId: number) => void;
}) {
  const [open, setOpen] = useState(false);

  const candidates = members.filter(
    (m) => !m.id.startsWith("m0") && m.id !== `m${currentAssigneeId}`,
  );

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={disabled}
        className="mono text-2xs px-2 py-1 rounded border border-divider hover:border-accent-paper text-text-secondary hover:text-accent-paper transition disabled:opacity-50"
        title={`Đổi người làm task #${taskId}`}
      >
        ↗ Đổi
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <ul className="absolute right-0 top-7 z-20 min-w-[180px] max-h-[300px] overflow-y-auto bg-surface-1 border border-divider rounded-md shadow-lg py-1">
            {candidates.map((m) => (
              <li key={m.id}>
                <button
                  onClick={() => {
                    setOpen(false);
                    const newId = parseInt(m.id.replace(/^m/, ""), 10);
                    if (!isNaN(newId)) onPick(newId);
                  }}
                  className="w-full text-left px-3 py-1.5 text-xs hover:bg-surface-2 transition flex justify-between"
                >
                  <span>{m.name}</span>
                  <span className="mono text-2xs text-text-disabled">{m.callsign}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
