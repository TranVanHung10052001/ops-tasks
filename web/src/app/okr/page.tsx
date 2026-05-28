import { getOkrData, getOkrActionsData } from "@/lib/data";
import OkrView from "./okr-view";

export default async function OkrPage() {
  const [okrs, actions] = await Promise.all([getOkrData(), getOkrActionsData()]);

  const totalProgress = Math.round(okrs.reduce((s, o) => s + o.progress, 0) / (okrs.length || 1));
  const atRisk = okrs.filter((o) => o.risk !== "low").length;
  const overdueCount = actions.filter((a) => a.is_overdue).length;
  const p0Count = actions.filter((a) => a.priority === "P0").length;

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      <OkrView
        initialOkrs={okrs}
        initialActions={actions}
        totalProgress={totalProgress}
        atRisk={atRisk}
        overdueCount={overdueCount}
        p0Count={p0Count}
      />
    </div>
  );
}
