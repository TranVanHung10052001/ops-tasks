"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { Task, Member, Priority, TaskStatus } from "@/lib/types";
import { PriorityBadge, StatusBadge } from "@/components/ui/badge";
import {
  Search,
  Plus,
  RefreshCw,
  ChevronDown,
  Check,
  X,
  AlertTriangle,
} from "lucide-react";
import { format, isPast, parseISO } from "date-fns";

const PRIORITIES: Priority[] = ["P0", "P1", "P2", "P3"];
const STATUSES: TaskStatus[] = ["pending", "in_progress", "blocked", "snoozed", "done", "cancelled"];

interface Filters {
  status: string;
  priority: string;
  assignee_id: string;
  search: string;
}

function InlineSelect({
  value,
  options,
  onChange,
  renderLabel,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
  renderLabel?: (v: string) => React.ReactNode;
}) {
  return (
    <div className="relative inline-block">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none text-xs border border-gray-200 rounded px-2 py-1 pr-5 bg-white focus:outline-none focus:ring-1 focus:ring-gray-900 cursor-pointer"
      >
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
      <ChevronDown size={10} className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400" />
    </div>
  );
}

interface CreateTaskModalProps {
  members: Member[];
  onClose: () => void;
  onCreated: () => void;
}

function CreateTaskModal({ members, onClose, onCreated }: CreateTaskModalProps) {
  const [summary, setSummary] = useState("");
  const [assigneeId, setAssigneeId] = useState(members[0]?.telegram_id.toString() ?? "");
  const [priority, setPriority] = useState<Priority>("P2");
  const [deadline, setDeadline] = useState("");
  const [category, setCategory] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!summary.trim()) return;
    setSaving(true);
    setErr("");
    try {
      await api.createTask({
        summary: summary.trim(),
        assignee_id: Number(assigneeId),
        priority,
        deadline: deadline || undefined,
        category: category || undefined,
      });
      onCreated();
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to create");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg border border-gray-200 w-full max-w-md shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2>New Task</h2>
          <button onClick={onClose} className="btn-ghost p-1"><X size={15} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Summary *</label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              className="input resize-none h-20"
              placeholder="Task description..."
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Assignee *</label>
              <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)} className="select">
                {members.map((m) => (
                  <option key={m.telegram_id} value={m.telegram_id}>{m.full_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)} className="select">
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Deadline</label>
              <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} className="input" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
              <input value={category} onChange={(e) => setCategory(e.target.value)} className="input" placeholder="e.g. fill_rate" />
            </div>
          </div>
          {err && <p className="text-xs text-red-600">{err}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Creating..." : "Create Task"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface InlineEditorState {
  taskId: number;
  field: "status" | "priority" | "assignee_id";
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [members, setMembers] = useState<Member[]>([]);
  const [filters, setFilters] = useState<Filters>({ status: "", priority: "", assignee_id: "", search: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<InlineEditorState | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tasksRes, membersRes] = await Promise.all([
        api.tasks({
          status: filters.status || undefined,
          priority: filters.priority || undefined,
          assignee_id: filters.assignee_id ? Number(filters.assignee_id) : undefined,
          search: filters.search || undefined,
        }),
        api.team(),
      ]);
      setTasks(tasksRes.tasks);
      setTotal(tasksRes.total);
      setMembers(membersRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const patch = async (id: number, body: Parameters<typeof api.updateTask>[1]) => {
    setSaving(id);
    try {
      const res = await api.updateTask(id, body);
      setTasks((prev) => prev.map((t) => (t.id === id ? res.task : t)));
    } finally {
      setSaving(null);
      setEditing(null);
    }
  };

  const memberMap = Object.fromEntries(members.map((m) => [m.telegram_id, m.full_name]));

  return (
    <div className="p-8 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1>Tasks</h1>
          <p className="text-xs text-gray-400 mt-0.5">{total} tasks total</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} disabled={loading} className="btn-ghost text-xs">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </button>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            <Plus size={14} />
            New Task
          </button>
        </div>
      </div>

      {error && (
        <div className="card p-4 border-red-200 mb-4">
          <p className="text-sm text-red-600 font-medium">Cannot connect to API</p>
          <p className="text-xs text-gray-400 mt-0.5">{error}</p>
          <button onClick={load} className="btn-secondary mt-3 text-xs">Retry</button>
        </div>
      )}

      {/* Filters */}
      <div className="card p-3 mb-4 flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-48">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search tasks..."
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            className="input pl-7 text-xs"
          />
        </div>
        <select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="select text-xs w-36"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </select>
        <select
          value={filters.priority}
          onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value }))}
          className="select text-xs w-28"
        >
          <option value="">All Priorities</option>
          {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select
          value={filters.assignee_id}
          onChange={(e) => setFilters((f) => ({ ...f, assignee_id: e.target.value }))}
          className="select text-xs w-40"
        >
          <option value="">All Assignees</option>
          {members.map((m) => (
            <option key={m.telegram_id} value={m.telegram_id}>{m.full_name}</option>
          ))}
        </select>
        {(filters.status || filters.priority || filters.assignee_id || filters.search) && (
          <button
            onClick={() => setFilters({ status: "", priority: "", assignee_id: "", search: "" })}
            className="btn-ghost text-xs text-gray-400"
          >
            <X size={12} /> Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wide bg-gray-50/50">
                <th className="text-left px-4 py-2.5 font-medium w-px">#</th>
                <th className="text-left px-4 py-2.5 font-medium">Summary</th>
                <th className="text-left px-4 py-2.5 font-medium">Assignee</th>
                <th className="text-left px-4 py-2.5 font-medium">Priority</th>
                <th className="text-left px-4 py-2.5 font-medium">Status</th>
                <th className="text-left px-4 py-2.5 font-medium">Deadline</th>
                <th className="text-left px-4 py-2.5 font-medium">Category</th>
                <th className="text-right px-4 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading && tasks.length === 0
                ? [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      {[...Array(8)].map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-3 bg-gray-100 rounded animate-pulse" style={{ width: `${40 + Math.random() * 40}%` }} />
                        </td>
                      ))}
                    </tr>
                  ))
                : tasks.length === 0
                ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-sm text-gray-400">
                      No tasks found
                    </td>
                  </tr>
                )
                : tasks.map((task) => {
                  const isOverdue = task.deadline && !["done", "cancelled"].includes(task.status) && isPast(parseISO(task.deadline));
                  const isSaving = saving === task.id;

                  return (
                    <tr key={task.id} className={`table-row-hover ${isSaving ? "opacity-50" : ""}`}>
                      <td className="px-4 py-2.5 text-xs text-gray-400 tabular-nums">{task.id}</td>
                      <td className="px-4 py-2.5 max-w-xs">
                        <p className="font-medium text-gray-900 truncate">{task.summary}</p>
                        {task.assigner_name && (
                          <p className="text-xs text-gray-400">by {task.assigner_name}</p>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        {editing?.taskId === task.id && editing.field === "assignee_id" ? (
                          <div className="flex items-center gap-1">
                            <select
                              defaultValue={task.assignee_id ?? ""}
                              autoFocus
                              className="select text-xs w-32"
                              onChange={(e) => patch(task.id, { assignee_id: Number(e.target.value) })}
                            >
                              {members.map((m) => (
                                <option key={m.telegram_id} value={m.telegram_id}>{m.full_name}</option>
                              ))}
                            </select>
                            <button onClick={() => setEditing(null)} className="text-gray-400 hover:text-gray-600">
                              <X size={12} />
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setEditing({ taskId: task.id, field: "assignee_id" })}
                            className="text-sm text-left hover:text-gray-900 text-gray-600"
                          >
                            {task.assignee_name ?? <span className="text-gray-300 italic">Unassigned</span>}
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        {editing?.taskId === task.id && editing.field === "priority" ? (
                          <div className="flex items-center gap-1">
                            <select
                              defaultValue={task.priority}
                              autoFocus
                              className="select text-xs w-20"
                              onChange={(e) => patch(task.id, { priority: e.target.value })}
                            >
                              {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                            </select>
                            <button onClick={() => setEditing(null)} className="text-gray-400 hover:text-gray-600">
                              <X size={12} />
                            </button>
                          </div>
                        ) : (
                          <button onClick={() => setEditing({ taskId: task.id, field: "priority" })}>
                            <PriorityBadge priority={task.priority} />
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        {editing?.taskId === task.id && editing.field === "status" ? (
                          <div className="flex items-center gap-1">
                            <select
                              defaultValue={task.status}
                              autoFocus
                              className="select text-xs w-32"
                              onChange={(e) => patch(task.id, { status: e.target.value })}
                            >
                              {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                            </select>
                            <button onClick={() => setEditing(null)} className="text-gray-400 hover:text-gray-600">
                              <X size={12} />
                            </button>
                          </div>
                        ) : (
                          <button onClick={() => setEditing({ taskId: task.id, field: "status" })}>
                            <StatusBadge status={task.status} />
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-xs tabular-nums">
                        {task.deadline ? (
                          <span className={isOverdue ? "text-red-500 font-medium flex items-center gap-1" : "text-gray-500"}>
                            {isOverdue && <AlertTriangle size={11} />}
                            {format(parseISO(task.deadline), "dd MMM")}
                          </span>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-gray-400">{task.category || "—"}</td>
                      <td className="px-4 py-2.5 text-right">
                        {!["done", "cancelled"].includes(task.status) && (
                          <button
                            onClick={() => patch(task.id, { status: "done" })}
                            disabled={isSaving}
                            className="btn-ghost text-green-600 hover:text-green-700 hover:bg-green-50 text-xs px-2 py-1"
                          >
                            <Check size={13} />
                            Done
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && (
        <CreateTaskModal
          members={members}
          onClose={() => setShowCreate(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}
