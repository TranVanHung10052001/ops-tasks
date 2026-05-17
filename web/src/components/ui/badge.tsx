import { type Priority, type TaskStatus, type MemberLoad } from "@/lib/types";

const priorityStyles: Record<Priority, string> = {
  P0: "bg-red-100 text-red-700 border-red-200",
  P1: "bg-orange-100 text-orange-700 border-orange-200",
  P2: "bg-yellow-100 text-yellow-700 border-yellow-200",
  P3: "bg-gray-100 text-gray-600 border-gray-200",
};

const statusStyles: Record<TaskStatus, string> = {
  pending:     "bg-gray-100 text-gray-600 border-gray-200",
  in_progress: "bg-blue-100 text-blue-700 border-blue-200",
  blocked:     "bg-red-100 text-red-700 border-red-200",
  snoozed:     "bg-purple-100 text-purple-700 border-purple-200",
  done:        "bg-green-100 text-green-700 border-green-200",
  cancelled:   "bg-gray-100 text-gray-400 border-gray-200 line-through",
};

const statusLabels: Record<TaskStatus, string> = {
  pending:     "Pending",
  in_progress: "In Progress",
  blocked:     "Blocked",
  snoozed:     "Snoozed",
  done:        "Done",
  cancelled:   "Cancelled",
};

const loadStyles: Record<MemberLoad, string> = {
  critical: "bg-red-100 text-red-700",
  high:     "bg-orange-100 text-orange-700",
  normal:   "bg-green-100 text-green-700",
  low:      "bg-gray-100 text-gray-500",
};

const loadDot: Record<MemberLoad, string> = {
  critical: "bg-red-500",
  high:     "bg-orange-400",
  normal:   "bg-green-500",
  low:      "bg-gray-400",
};

interface BadgeProps {
  children: React.ReactNode;
  className?: string;
}

export function Badge({ children, className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium border ${className}`}>
      {children}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <Badge className={priorityStyles[priority]}>{priority}</Badge>;
}

export function StatusBadge({ status }: { status: TaskStatus }) {
  return <Badge className={statusStyles[status]}>{statusLabels[status]}</Badge>;
}

export function LoadBadge({ load }: { load: MemberLoad }) {
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium ${loadStyles[load]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${loadDot[load]}`} />
      {load.charAt(0).toUpperCase() + load.slice(1)}
    </span>
  );
}
