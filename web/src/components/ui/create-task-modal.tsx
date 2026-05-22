"use client";

import { useState } from "react";
import { OpsTask, Member, TaskStatus, Priority, Channel, MEMBERS } from "@/lib/mock";
import clsx from "clsx";

const PRIORITY_OPTIONS: { key: Priority; label: string; color: string }[] = [
  { key: "P0", label: "P0 · Khẩn cấp", color: "text-signal-p0" },
  { key: "P1", label: "P1 · Cao",       color: "text-signal-p1" },
  { key: "P2", label: "P2 · Trung bình", color: "text-signal-p2" },
  { key: "P3", label: "P3 · Thấp",      color: "text-signal-p3" },
];

const CHANNEL_OPTIONS: { key: Channel; label: string }[] = [
  { key: "JD",    label: "JD · Việc cố định" },
  { key: "OKR",   label: "OKR · Mục tiêu quý" },
  { key: "Adhoc", label: "Adhoc · Phát sinh" },
];

interface Props {
  members: Member[];
  defaultAssignee?: string;
  onClose: () => void;
  onSubmit: (task: Omit<OpsTask, "id" | "createdAt">) => Promise<void>;
}

export default function CreateTaskModal({ members, defaultAssignee, onClose, onSubmit }: Props) {
  const [saving, setSaving] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("P1");
  const [channel, setChannel] = useState<Channel>("Adhoc");
  const [assignee, setAssignee] = useState<string>(defaultAssignee ?? MEMBERS[0]?.id ?? "m0");
  const [deadline, setDeadline] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 3);
    d.setHours(17, 0, 0, 0);
    return d.toISOString().slice(0, 16); // "YYYY-MM-DDThh:mm"
  });
  const [tags, setTags] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setError("Vui lòng nhập nội dung task."); return; }
    setSaving(true);
    setError("");
    try {
      await onSubmit({
        channel,
        channelLabel: CHANNEL_OPTIONS.find(c => c.key === channel)?.label ?? channel,
        title: title.trim(),
        description: description.trim() || undefined,
        assignee,
        priority,
        status: "can_lam" as TaskStatus,
        deadline: new Date(deadline).toISOString(),
        estimateHours: 2,
        tags: tags ? tags.split(",").map(t => t.trim()).filter(Boolean) : [],
        createdBy: "Web · OPS-10",
      });
      onClose();
    } catch {
      setError("Không thể tạo task. Thử lại sau.");
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center">
      <div className="absolute inset-0 bg-canvas/80 backdrop-blur-sm" onClick={onClose} />

      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-full max-w-lg bg-surface border-2 border-divider-strong shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-divider">
          <div>
            <div className="label-ops text-2xs">Tạo task mới</div>
            <div className="mono text-2xs text-text-tertiary mt-0.5">⌘N · Đài điều vận</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="mono text-xl text-text-tertiary hover:text-text-primary leading-none"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          {/* Title */}
          <div>
            <label className="label-ops text-2xs block mb-1.5">Nội dung task *</label>
            <input
              autoFocus
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Mô tả công việc cần làm…"
              className={clsx(
                "w-full bg-surface-deep border px-3 py-2 text-sm text-text-primary",
                "placeholder:text-text-disabled mono",
                "focus:outline-none focus:border-accent-amber transition-colors",
                error && !title.trim() ? "border-signal-p0" : "border-divider-strong"
              )}
            />
          </div>

          {/* Description */}
          <div>
            <label className="label-ops text-2xs block mb-1.5">Mô tả chi tiết (tuỳ chọn)</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Context, blockers, acceptance criteria…"
              rows={3}
              className="w-full bg-surface-deep border border-divider-strong px-3 py-2 text-xs text-text-primary placeholder:text-text-disabled mono focus:outline-none focus:border-accent-amber transition-colors resize-none"
            />
          </div>

          {/* Priority + Channel */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-ops text-2xs block mb-1.5">Mức độ ưu tiên</label>
              <div className="flex flex-col gap-1">
                {PRIORITY_OPTIONS.map(p => (
                  <label key={p.key} className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="radio"
                      name="priority"
                      value={p.key}
                      checked={priority === p.key}
                      onChange={() => setPriority(p.key)}
                      className="accent-[var(--color-accent-amber)]"
                    />
                    <span className={clsx("mono text-2xs", priority === p.key ? p.color : "text-text-secondary")}>
                      {p.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="label-ops text-2xs block mb-1.5">Kênh</label>
              <div className="flex flex-col gap-1">
                {CHANNEL_OPTIONS.map(c => (
                  <label key={c.key} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="channel"
                      value={c.key}
                      checked={channel === c.key}
                      onChange={() => setChannel(c.key)}
                      className="accent-[var(--color-accent-amber)]"
                    />
                    <span className={clsx("mono text-2xs", channel === c.key ? "text-accent-paper" : "text-text-secondary")}>
                      {c.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Assignee + Deadline */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-ops text-2xs block mb-1.5">Người thực hiện</label>
              <select
                value={assignee}
                onChange={e => setAssignee(e.target.value)}
                className="w-full bg-surface-deep border border-divider-strong px-2 py-1.5 mono text-xs text-text-primary focus:outline-none focus:border-accent-amber"
              >
                {members.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.callsign} · {m.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="label-ops text-2xs block mb-1.5">Thời hạn</label>
              <input
                type="datetime-local"
                value={deadline}
                onChange={e => setDeadline(e.target.value)}
                className="w-full bg-surface-deep border border-divider-strong px-2 py-1.5 mono text-xs text-text-primary focus:outline-none focus:border-accent-amber"
              />
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className="label-ops text-2xs block mb-1.5">
              Tags <span className="text-text-disabled">(phân cách bởi dấu phẩy)</span>
            </label>
            <input
              type="text"
              value={tags}
              onChange={e => setTags(e.target.value)}
              placeholder="LAN, Hub, Urgent…"
              className="w-full bg-surface-deep border border-divider-strong px-3 py-2 mono text-xs text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent-amber"
            />
          </div>

          {error && (
            <div className="mono text-2xs text-signal-p0 flex items-center gap-1.5">
              ⚠ {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-divider flex items-center justify-between">
          <div className="mono text-2xs text-text-disabled">
            Tạo bởi OPS-10 · Sẽ sync lên Telegram bot
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="btn-ops">
              Huỷ
            </button>
            <button
              type="submit"
              disabled={saving}
              className={clsx(
                "btn-ops primary flex items-center gap-1.5",
                saving && "opacity-50 cursor-not-allowed"
              )}
            >
              {saving ? "Đang tạo…" : "+ Tạo task"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
