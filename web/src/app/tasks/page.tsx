import { getTasksData, getMembersData } from "@/lib/data";
import { Channel } from "@/lib/mock";
import TasksView from "./tasks-view";

export default async function TasksPage({
  searchParams,
}: {
  searchParams: Promise<{ channel?: string; member?: string; priority?: string }>;
}) {
  const [tasks, members, params] = await Promise.all([
    getTasksData(),
    getMembersData(),
    searchParams,
  ]);

  const channel = params.channel as Channel | undefined;
  const memberId = params.member;
  const priorities = params.priority?.split(",") ?? [];

  const activeTasks = tasks.filter(
    (t) => t.status !== "hoan_thanh" && t.status !== "tam_dung"
  );

  // Apply sidebar filters
  const filteredTasks = activeTasks.filter((t) => {
    if (channel && t.channel !== channel) return false;
    if (memberId && t.assignee !== memberId) return false;
    if (priorities.length > 0 && !priorities.includes(t.priority)) return false;
    return true;
  });

  // Count helpers for sidebar highlight
  const filterActive = !!(channel || memberId || priorities.length);

  return (
    <div className="p-6 max-w-[1400px]">
      <header className="flex items-end justify-between mb-8">
        <div>
          <div className="label-ops text-2xs mb-1.5">Đài chính · II · Bảng điều vận</div>
          <h1 className="text-[32px] text-text-primary editorial leading-tight">Sổ điều vận hôm nay.</h1>
          <p className="text-md text-text-secondary mt-1">
            {filterActive
              ? `${filteredTasks.length}/${activeTasks.length} task sau bộ lọc · ${channel ?? ""} ${memberId ? "· " + members.find(m => m.id === memberId)?.callsign : ""}`
              : `Tổng ${activeTasks.length} task đang theo dõi · phân theo 4 mức tín hiệu · cập nhật mỗi 30s.`
            }
          </p>
        </div>
        <div className="text-right mono text-2xs text-text-tertiary uppercase tracking-wider">
          {filteredTasks.length > 0
            ? `${filteredTasks[0]?.id} → ${filteredTasks[filteredTasks.length - 1]?.id}`
            : "Không có task sau bộ lọc"}
        </div>
      </header>

      <TasksView key={`${channel ?? "all"}-${memberId ?? "all"}`} tasks={filteredTasks} members={members} />
    </div>
  );
}
