"use client";

import { useState } from "react";
import { OpsTask, Member, TaskStatus, formatDeadline, statusLabel, priorityLabel } from "@/lib/mock";
import SignalBadge from "./signal-badge";
import clsx from "clsx";

const STATUS_FLOW: { key: TaskStatus; label: string; icon: string; color: string }[] = [
  { key: "can_lam",     label: "Cần làm",       icon: "○",  color: "text-state-pending border-state-pending/40" },
  { key: "dang_lam",    label: "Đang làm",      icon: "◎",  color: "text-state-active border-state-active/40" },
  { key: "dang_review", label: "Đang review",   icon: "◈",  color: "text-accent-paper border-accent-paper/40" },
  { key: "hoan_thanh",  label: "Hoàn thành",    icon: "●",  color: "text-signal-p3 border-signal-p3/40" },
  { key: "bi_chan",      label: "Bị chặn",       icon: "✕",  color: "text-signal-p1 border-signal-p1/40" },
  { key: "tam_dung",    label: "Tạm dừng",      icon: "⏸",  color: "text-state-paused border-state-paused/40" },
];

interface Props {
  task: OpsTask;
  members: Member[];
  onClose: () => void;
  onStatusChange: (taskId: string, newStatus: TaskStatus) => Promise<void>;
  onDelete?: (taskId: string) => Promise<void>;
  onEdit?: (task: OpsTask) => void;
}

export default function TaskDetailModal({ task, members, onClose, onStatusChange, onDelete, onEdit }: Props) {
  const [saving, setSaving] = useState(false);
  const [savedStatus, setSavedStatus] = useState<TaskStatus>(task.status);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const m = members.find((mb) => mb.id === task.assignee);
  const d = formatDeadline(task.deadline);
  const overdue = d.relative.startsWith("quá");
  const blocked = savedStatus === "bi_chan";

  async function handleStatus(s: TaskStatus) {
    if (s === savedStatus) return;
    setSaving(true);
    setSavedStatus(s);
    try {
      await onStatusChange(task.id, s);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!onDelete) return;
    setDeleting(true);
    try {
      await onDelete(task.id);
      onClose();
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-canvas/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal panel */}
      <div
        className={clsx(
          "relative z-10 w-full max-w-lg bg-surface border-2 shadow-2xl",
          overdue ? "border-signal-p0/60" : blocked ? "border-signal-p1/60" : "border-divider-strong"
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top accent */}
        {overdue && <div className="absolute top-0 left-0 right-0 h-[3px] bg-signal-p0" />}
        {blocked && !overdue && <div className="absolute top-0 left-0 right-0 h-[3px] bg-signal-p1" />}

        {/* Header */}
        <div className="flex items-start justify-between px-5 pt-5 pb-3 border-b border-divider">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="mono text-2xs text-text-tertiary tabular">{task.id}</span>
              <span className="mono text-2xs uppercase tracking-wider px-1.5 py-px border border-divider-strong text-text-secondary">
                {task.channel}
              </span>
              <SignalBadge priority={task.priority} outline={task.priority === "P3" || task.priority === "P4"} />
            </div>
            <div className="mono text-2xs text-accent-paper">{task.channelLabel}</div>
          </div>
          <button
            onClick={onClose}
            className="mono text-xl text-text-tertiary hover:text-text-primary leading-none mt-0.5"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4 max-h-[60vh] overflow-y-auto scroll-ops">
          {/* Title */}
          <h2 className="text-md text-text-primary leading-snug">{task.title}</h2>

          {/* Description */}
          {task.description && (
            <p className="text-xs text-text-secondary leading-relaxed border-l-2 border-divider-strong pl-3 py-1">
              {task.description}
            </p>
          )}

          {/* Meta grid */}
          <div className="grid grid-cols-2 gap-3">
            {/* Assignee */}
            <div>
              <div className="label-ops text-2xs mb-1.5">Người thực hiện</div>
              {m ? (
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 border border-divider-strong bg-surface-deep mono text-xs flex items-center justify-center text-accent-paper">
                    {m.initials}
                  </div>
                  <div>
                    <div className="text-sm text-text-primary">{m.name}</div>
                    <div className="mono text-2xs text-text-tertiary">{m.initials}</div>
                  </div>
                </div>
              ) : (
                <span className="mono text-xs text-text-disabled">Chưa giao</span>
              )}
            </div>

            {/* Deadline */}
            <div>
              <div className="label-ops text-2xs mb-1.5">Thời hạn</div>
              <div className={clsx("mono text-xs", overdue ? "text-signal-p0" : "text-text-primary")}>
                {d.date} · {d.time}
              </div>
              <div className={clsx("mono text-2xs mt-0.5", overdue ? "text-signal-p0" : "text-text-tertiary")}>
                {d.relative}
                {overdue && " · ⚠ OVERDUE"}
              </div>
            </div>

            {/* Estimate */}
            <div>
              <div className="label-ops text-2xs mb-1">Ước tính</div>
              <span className="mono text-xs text-text-primary">{task.estimateHours}h</span>
            </div>

            {/* Created by */}
            <div>
              <div className="label-ops text-2xs mb-1">Tạo bởi</div>
              <span className="mono text-xs text-text-secondary">{task.createdBy}</span>
            </div>
          </div>

          {/* Tags */}
          {task.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {task.tags.map((tag) => (
                <span key={tag} className="mono text-2xs text-accent-paper">
                  #{tag}
                </span>
              ))}
              {task.aiClassified && (
                <span className="mono text-2xs text-accent-amber flex items-center gap-1">
                  ⊙ AI {Math.round((task.aiConfidence || 0) * 100)}%
                </span>
              )}
            </div>
          )}

          {/* Priority info */}
          <div>
            <div className="label-ops text-2xs mb-1">Mức độ ưu tiên</div>
            <span className="mono text-xs text-text-secondary">{priorityLabel(task.priority)}</span>
          </div>

          {/* Status update */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="label-ops text-2xs">Cập nhật trạng thái</div>
              {saving && (
                <span className="mono text-2xs text-accent-amber animate-pulse">đang lưu…</span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {STATUS_FLOW.map((s) => (
                <button
                  key={s.key}
                  onClick={() => handleStatus(s.key)}
                  disabled={saving}
                  className={clsx(
                    "px-2 py-2 mono text-2xs uppercase tracking-wider border transition-all text-left flex items-center gap-1.5",
                    savedStatus === s.key
                      ? "border-accent-amber bg-accent-amber-deep text-canvas"
                      : clsx(
                          "hover:bg-surface-raised",
                          s.color
                        ),
                    saving && "opacity-50 cursor-not-allowed"
                  )}
                >
                  <span className="text-xs">{s.icon}</span>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-divider flex items-center justify-between">
          <div className="mono text-2xs text-text-disabled">
            Trạng thái: {statusLabel(savedStatus)}
          </div>
          <div className="flex gap-2 items-center">
            {onDelete && (
              confirmDelete ? (
                <>
                  <span className="mono text-2xs text-signal-p0">Xác nhận xoá?</span>
                  <button
                    onClick={handleDelete}
                    disabled={deleting}
                    className="btn-ops mono text-2xs text-signal-p0 border-signal-p0/60 hover:bg-signal-p0/10"
                  >
                    {deleting ? "Đang xoá…" : "✕ Xoá"}
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="btn-ops"
                  >
                    Huỷ
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="btn-ops mono text-2xs text-text-tertiary hover:text-signal-p0 hover:border-signal-p0/60"
                >
                  ✕ Xoá task
                </button>
              )
            )}
            {onEdit && (
              <button
                onClick={() => { onEdit(task); onClose(); }}
                className="btn-ops mono text-2xs text-accent-paper border-accent-paper/40 hover:bg-accent-paper/10"
              >
                ✎ Sửa
              </button>
            )}
            <button onClick={onClose} className="btn-ops">
              Đóng
            </button>
            <a
              href="https://t.me/ahamove_truck_ops_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ops primary flex items-center gap-1"
            >
              ▸ Telegram
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
