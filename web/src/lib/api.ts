import type { Task, Member, User, TeamStats, OkrData } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_SECRET = process.env.NEXT_PUBLIC_API_SECRET || "ops-tasks-secret-change-me";

async function req<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_SECRET}`,
      ...options.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path}: ${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  stats: () => req<TeamStats>("/api/stats"),

  team: () => req<Member[]>("/api/team"),

  memberTasks: (userId: number, status?: string) =>
    req<Task[]>(
      `/api/team/${userId}/tasks${status ? `?status=${status}` : ""}`
    ),

  tasks: (params?: {
    status?: string;
    assignee_id?: number;
    priority?: string;
    search?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.assignee_id) q.set("assignee_id", String(params.assignee_id));
    if (params?.priority) q.set("priority", params.priority);
    if (params?.search) q.set("search", params.search);
    return req<{ tasks: Task[]; total: number }>(
      `/api/tasks${q.toString() ? `?${q}` : ""}`
    );
  },

  doneTasks: () => req<Task[]>("/api/tasks/done"),

  taskDetail: (id: number) => req<Task>(`/api/tasks/${id}`),

  updateTask: (
    id: number,
    body: {
      status?: string;
      priority?: string;
      assignee_id?: number;
      deadline?: string;
      block_reason?: string;
    }
  ) =>
    req<{ ok: boolean; task: Task }>(`/api/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  createTask: (body: {
    summary: string;
    assignee_id: number;
    priority?: string;
    deadline?: string;
    category?: string;
  }) =>
    req<{ ok: boolean; task_id: number }>("/api/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  users: () => req<User[]>("/api/users"),

  pendingUsers: () => req<User[]>("/api/users/pending"),

  approveUser: (id: number) =>
    req<{ ok: boolean }>(`/api/users/${id}/approve`, { method: "POST" }),

  setRole: (id: number, role: string, team?: string) =>
    req<{ ok: boolean }>(`/api/users/${id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role, team }),
    }),

  okr: () => req<OkrData>("/api/okr"),
};
