import { COMPETITORS } from "@/lib/mock";

export default function CompetitiveStrip() {
  return (
    <section className="ops-surface">
      <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <span className="label-ops text-2xs">Đối thủ — thị phần truck</span>
          <span className="mono text-2xs text-text-tertiary">Nov 2025 baseline · CLAUDE.md</span>
        </div>
        <span className="mono text-2xs text-state-done">Ahamove + Lalamove ≈ 99% on-demand truck</span>
      </header>
      <table className="w-full">
        <thead>
          <tr className="mono text-2xs uppercase tracking-wider text-text-tertiary border-b border-divider">
            <th className="text-left px-5 py-2 font-normal">Đối thủ</th>
            <th className="text-right px-3 py-2 font-normal">SGN share</th>
            <th className="text-right px-3 py-2 font-normal">HAN share</th>
            <th className="text-left px-3 py-2 font-normal">Điểm mạnh</th>
            <th className="text-right px-5 py-2 font-normal">Threat</th>
          </tr>
        </thead>
        <tbody>
          {COMPETITORS.map((c) => {
            const isAha = c.name === "Ahamove";
            return (
              <tr key={c.name} className={isAha ? "bg-surface-raised" : "border-b border-divider"}>
                <td className="px-5 py-2.5">
                  <span className={isAha ? "text-accent-paper font-medium" : "text-text-primary"}>{c.name}</span>
                </td>
                <td className="px-3 py-2.5 text-right">
                  {c.sgnShare !== null ? (
                    <div className="flex items-center justify-end gap-2">
                      <span className="mono text-md text-text-primary tabular">{c.sgnShare}%</span>
                      <span
                        className={
                          "mono text-2xs " +
                          (c.sgnDelta! > 0 ? "text-signal-p3" : c.sgnDelta! < 0 ? "text-signal-p0" : "text-text-tertiary")
                        }
                      >
                        {c.sgnDelta! > 0 ? "▲" : c.sgnDelta! < 0 ? "▼" : "—"}
                        {Math.abs(c.sgnDelta!)}
                      </span>
                    </div>
                  ) : (
                    <span className="mono text-text-tertiary">—</span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-right">
                  {c.hanShare !== null ? (
                    <div className="flex items-center justify-end gap-2">
                      <span className="mono text-md text-text-primary tabular">{c.hanShare}%</span>
                      <span
                        className={
                          "mono text-2xs " +
                          (c.hanDelta! > 0 ? "text-signal-p3" : c.hanDelta! < 0 ? "text-signal-p0" : "text-text-tertiary")
                        }
                      >
                        {c.hanDelta! > 0 ? "▲" : c.hanDelta! < 0 ? "▼" : "—"}
                        {Math.abs(c.hanDelta!)}
                      </span>
                    </div>
                  ) : (
                    <span className="mono text-text-tertiary">—</span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-sm text-text-secondary">{c.strength}</td>
                <td className="px-5 py-2.5 text-right">
                  <span
                    className={
                      "mono text-2xs uppercase tracking-wider " +
                      (c.threat.includes("VERY HIGH")
                        ? "text-signal-p0"
                        : c.threat.includes("HIGH")
                        ? "text-signal-p1"
                        : c.threat.includes("MEDIUM")
                        ? "text-signal-p2"
                        : "text-text-tertiary")
                    }
                  >
                    {c.threat}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
