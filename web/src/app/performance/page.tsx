import { getPerformanceData } from "@/lib/data";
import PerformanceView from "./performance-view";

export const dynamic = "force-dynamic";

export default async function PerformancePage() {
  const initial = await getPerformanceData(30);
  return (
    <div className="p-6 max-w-[1400px]">
      <PerformanceView initial={initial} />
    </div>
  );
}
