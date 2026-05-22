import { getMembersData, getTasksData } from "@/lib/data";
import TeamView from "./team-view";

export default async function TeamPage() {
  const [members, tasks] = await Promise.all([getMembersData(), getTasksData()]);
  return (
    <div className="p-6 max-w-[1400px]">
      <TeamView members={members} tasks={tasks} />
    </div>
  );
}
