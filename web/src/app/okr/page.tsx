import OkrDial from "@/components/ui/okr-dial";
import { getOkrData, getOkrActionsData } from "@/lib/data";
import { ApiOkrAction } from "@/lib/api";
import clsx from "clsx";

function daysLabel(action: ApiOkrAction) {
  if (action.is_overdue) {
    const d = Math.abs(action.days_left ?? 0);
    return `quá hạn ${d}ngày`;
  }
  const d = action.days_left ?? 0;
  if (d === 0) return "hôm nay";
  if (d === 1) return "mai";
  return `còn ${d} ngày`;
}

const PRIORITY_COLOR: Record<string, string> = {
  P0: "text-signal-p0 border-signal-p0",
  P1: "text-signal-p1 border-signal-p1",
  P2: "text-signal-p2 border-signal-p2",
  P3: "text-signal-p3 border-signal-p3",
};

const OKR_ACCENT: Record<string, string> = {
  O1: "border-l-signal-p3",
  O2: "border-l-signal-p2",
  O3: "border-l-signal-p1",
  O4: "border-l-accent-paper",
  O5: "border-l-accent-amber",
};

export default async function OkrPage() {
  const [okrs, actions] = await Promise.all([getOkrData(), getOkrActionsData()]);

  const totalProgress = Math.round(okrs.reduce((s, o) => s + o.progress, 0) / (okrs.length || 1));
  const atRisk = okrs.filter((o) => o.risk !== "low").length;

  // Sort: overdue P0 → overdue other → on-track P0 → on-track other
  const sortedActions = [...actions].sort((a, b) => {
    const aScore = (a.is_overdue ? 100 : 0) + (a.priority === "P0" ? 50 : a.priority === "P1" ? 30 : 10);
    const bScore = (b.is_overdue ? 100 : 0) + (b.priority === "P0" ? 50 : b.priority === "P1" ? 30 : 10);
    return bScore - aScore;
  });

  const overdueCount = actions.filter((a) => a.is_overdue).length;
  const p0Count = actions.filter((a) => a.priority === "P0").length;

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      <header className="flex items-end justify-between">
        <div>
          <div className="label-ops text-2xs mb-1.5">Ops · 03 · Theo dõi OKR</div>
          <h1 className="text-2xl text-text-primary editorial leading-tight">
            OKR quý 2 · 2026 · {okrs.length} mục tiêu.
          </h1>
          <p className="text-md text-text-secondary mt-1">
            {okrs.reduce((s, o) => s + o.keyResults.length, 0)} kết quả then chốt · {actions.length} action item · cập nhật real-time từ bot.
          </p>
        </div>
        <div className="ops-surface px-4 py-2.5 flex gap-6">
          <div>
            <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">Tổng tiến độ</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-display text-3xl text-accent-paper tabular leading-none">{totalProgress}%</span>
              <span className="mono text-2xs text-text-tertiary">/ {atRisk} có rủi ro</span>
            </div>
          </div>
          <div className="border-l border-divider pl-6">
            <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">Action overdue</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="font-display text-3xl text-signal-p0 tabular leading-none">{overdueCount}</span>
              <span className="mono text-2xs text-text-tertiary">/ {p0Count} P0</span>
            </div>
          </div>
        </div>
      </header>

      {/* North star */}
      <section className="ops-surface p-5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent-amber" />
        <div className="grid grid-cols-2 gap-8">
          <div>
            <div className="section-label mb-2">North Star · Q2/2026</div>
            <p className="editorial text-xl leading-snug text-text-primary">
              GSV Non-Bulky 70% YoY: 69B → 117.3B · Fill Rate toàn network ≥68%.
            </p>
          </div>
          <div>
            <div className="section-label mb-2">Tóm tắt tiến độ</div>
            <ul className="space-y-2 text-md text-text-primary">
              {okrs.slice(0, 3).map((o) => (
                <li key={o.id} className="flex gap-2.5 items-start">
                  <span className={
                    o.risk === "high" ? "text-signal-p0 mt-1" :
                    o.risk === "medium" ? "text-signal-p2 mt-1" :
                    "text-signal-p3 mt-1"
                  }>
                    {o.risk === "high" ? "▼" : o.risk === "medium" ? "●" : "▲"}
                  </span>
                  <span>
                    <span className="text-accent-paper">{o.title.split(" · ")[0]}</span>
                    {" — "}{o.progress}% · {o.current.split(" · ")[0]}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* OKR dials grid */}
      <div className="grid grid-cols-2 gap-4">
        {okrs.map((o) => (
          <OkrDial key={o.id} okr={o} />
        ))}
      </div>

      {/* Action items table */}
      <section className="ops-surface">
        <header className="flex items-center justify-between px-5 py-3 border-b border-divider">
          <div className="flex items-baseline gap-3">
            <span className="section-label">Action Items · Q2/2026</span>
            <span className="mono text-2xs text-text-tertiary">{actions.length} actions</span>
            {overdueCount > 0 && (
              <span className="mono text-2xs text-signal-p0 flex items-center gap-1">
                ⚠ {overdueCount} overdue
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mono text-2xs text-text-tertiary">
            <span>{p0Count} P0 · theo độ khẩn</span>
          </div>
        </header>

        <div className="overflow-x-auto scroll-ops">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-divider mono text-2xs tracking-wider text-text-tertiary">
                <th className="w-1 p-0" />
                <th className="px-3 py-2 font-normal w-16">OKR</th>
                <th className="px-3 py-2 font-normal">Action</th>
                <th className="px-3 py-2 font-normal w-36">PIC</th>
                <th className="px-3 py-2 font-normal w-20">Mức</th>
                <th className="px-3 py-2 font-normal w-28 text-right">Thời hạn</th>
                <th className="px-3 py-2 font-normal w-28 text-right">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {sortedActions.map((action) => {
                const okrRoot = action.okr.split(".")[0]; // "O1", "O2", etc.
                const overdue = action.is_overdue;
                const daysTxt = daysLabel(action);
                return (
                  <tr
                    key={action.id}
                    className={clsx(
                      "border-b border-divider transition-colors",
                      overdue && action.priority === "P0"
                        ? "bg-signal-p0/5 hover:bg-signal-p0/10"
                        : overdue
                        ? "bg-signal-p1/5 hover:bg-signal-p1/10"
                        : "hover:bg-surface-raised"
                    )}
                  >
                    <td className={clsx(
                      "p-0 w-1",
                      OKR_ACCENT[okrRoot] ?? "",
                      "border-l-2"
                    )} />
                    <td className="px-3 py-2.5">
                      <span className="mono text-2xs text-accent-paper uppercase tracking-wider">{action.okr}</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="text-sm text-text-primary leading-snug">{action.name}</div>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="mono text-xs text-text-secondary">{action.pic}</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={clsx(
                        "mono text-2xs border px-1.5 py-0.5 leading-none uppercase",
                        PRIORITY_COLOR[action.priority] ?? "text-text-tertiary border-divider"
                      )}>
                        {action.priority}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="mono text-xs text-text-primary tabular">
                        {action.deadline}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <span className={clsx(
                        "mono text-2xs font-bold uppercase tracking-wider",
                        overdue ? "text-signal-p0" : (action.days_left ?? 99) <= 3 ? "text-signal-p2" : "text-signal-p3"
                      )}>
                        {overdue && "⚠ "}{daysTxt}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
