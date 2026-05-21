import { OkrObjective } from "@/lib/mock";
import clsx from "clsx";

function colorFor(p: number) {
  if (p < 34) return "var(--signal-p0)";
  if (p < 67) return "var(--signal-p2)";
  return "var(--signal-p3)";
}

export default function OkrDial({ okr, size = 180 }: { okr: OkrObjective; size?: number }) {
  const r = (size / 2) - 14;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  const arcLen = (circ * 3) / 4;
  const offset = arcLen * (1 - okr.progress / 100);
  const color = colorFor(okr.progress);

  return (
    <div className="ops-surface p-5 relative">
      {okr.risk === "high" && (
        <div className="absolute top-3 right-3 mono text-2xs text-signal-p0 uppercase tracking-wider flex items-center gap-1">
          ⚠ Rủi ro cao
        </div>
      )}
      {okr.risk === "medium" && (
        <div className="absolute top-3 right-3 mono text-2xs text-signal-p2 uppercase tracking-wider flex items-center gap-1">
          ⚠ Cảnh báo
        </div>
      )}

      <div className="mb-2 label-ops text-2xs">{okr.id.toUpperCase()} · Mục tiêu quý</div>
      <h3 className="text-md text-text-primary leading-snug mb-1">{okr.title}</h3>
      <p className="text-xs text-text-tertiary mb-4">{okr.subtitle}</p>

      <div className="flex items-center gap-5">
        <div className="relative shrink-0" style={{ width: size, height: size * 0.85 }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            <g transform={`rotate(135 ${cx} ${cy})`}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke="var(--divider-strong)"
                strokeWidth="2"
                strokeDasharray={`${arcLen} ${circ}`}
              />
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke={color}
                strokeWidth="6"
                strokeLinecap="square"
                strokeDasharray={`${arcLen} ${circ}`}
                strokeDashoffset={offset}
                style={{ transition: "stroke-dashoffset 600ms ease-out" }}
              />
            </g>
            {/* tick marks */}
            {[0, 25, 50, 75, 100].map((p) => {
              const angle = 135 + (p / 100) * 270;
              const rad = (angle * Math.PI) / 180;
              const x1 = cx + (r - 4) * Math.cos(rad);
              const y1 = cy + (r - 4) * Math.sin(rad);
              const x2 = cx + (r + 4) * Math.cos(rad);
              const y2 = cy + (r + 4) * Math.sin(rad);
              return <line key={p} x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--text-tertiary)" strokeWidth="1" />;
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-4xl text-text-primary tabular leading-none" style={{ color }}>
              {okr.progress}
            </span>
            <span className="mono text-xs text-text-tertiary mt-1">phần trăm</span>
          </div>
        </div>

        <div className="flex-1 space-y-2.5">
          <div>
            <div className="label-ops text-2xs mb-1">Hiện tại</div>
            <div className="text-md text-text-primary mono tabular">{okr.current}</div>
          </div>
          <div>
            <div className="label-ops text-2xs mb-1">Mục tiêu</div>
            <div className="text-sm text-text-secondary">{okr.target}</div>
          </div>
          <div>
            <div className="label-ops text-2xs mb-1">Phụ trách</div>
            <div className="mono text-xs text-accent-paper">{okr.owner}</div>
          </div>
        </div>
      </div>

      <div className="dotted-divider my-4" />

      <div className="space-y-2">
        <div className="label-ops text-2xs mb-1">Kết quả then chốt</div>
        {okr.keyResults.map((kr) => (
          <div key={kr.id} className="flex items-center gap-2.5 text-xs">
            <span className="mono text-text-tertiary tabular w-9 text-right">{kr.progress}%</span>
            <div className="h-1.5 flex-1 bg-surface-deep border border-divider">
              <div
                className={clsx(
                  "h-full",
                  kr.progress < 34 ? "bg-signal-p0" : kr.progress < 67 ? "bg-signal-p2" : "bg-signal-p3"
                )}
                style={{ width: `${kr.progress}%` }}
              />
            </div>
            <span className="flex-1 text-text-secondary truncate">{kr.label}</span>
            <span className="mono text-2xs text-accent-paper tabular shrink-0">{kr.target}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
