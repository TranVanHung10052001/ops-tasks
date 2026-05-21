import OkrDial from "@/components/ui/okr-dial";
import { OKRS } from "@/lib/mock";

export default function OkrPage() {
  const totalProgress = Math.round(OKRS.reduce((s, o) => s + o.progress, 0) / OKRS.length);
  const atRisk = OKRS.filter((o) => o.risk !== "low").length;

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      <header className="flex items-end justify-between">
        <div>
          <div className="label-ops text-2xs mb-1.5">Đài chính · 03 · Theo dõi OKR</div>
          <h1 className="text-2xl text-text-primary editorial leading-tight">
            OKR quý 2 · 2026 · tuần 8 / 13.
          </h1>
          <p className="text-md text-text-secondary mt-1">
            4 mục tiêu lớn · 12 kết quả then chốt · cập nhật cuối: 21·05 06:00 ICT.
          </p>
        </div>
        <div className="ops-surface px-4 py-2.5">
          <div className="mono text-2xs text-text-tertiary uppercase tracking-wider">Tổng tiến độ</div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="font-display text-3xl text-accent-paper tabular leading-none">{totalProgress}%</span>
            <span className="mono text-2xs text-text-tertiary">/ {atRisk} có rủi ro</span>
          </div>
        </div>
      </header>

      {/* Briefing */}
      <section className="ops-surface p-5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent-amber" />
        <div className="grid grid-cols-2 gap-8">
          <div>
            <div className="label-ops text-2xs mb-2">Tóm tắt</div>
            <p className="editorial text-xl leading-snug text-text-primary">
              3 trên 4 OKR đang đúng tiến độ. NPS tài xế chậm hơn dự kiến 18 điểm phần trăm — cần action plan trước 28·05.
            </p>
          </div>
          <div>
            <div className="label-ops text-2xs mb-2">Diễn biến tuần này</div>
            <ul className="space-y-2 text-md text-text-primary">
              <li className="flex gap-2.5 items-start">
                <span className="text-signal-p3 mt-1">▲</span>
                <span>Mở rộng tỉnh: Cần Thơ đã lên pilot — kéo tiến độ OKR lên 88%.</span>
              </li>
              <li className="flex gap-2.5 items-start">
                <span className="text-signal-p2 mt-1">●</span>
                <span>Tăng tải KCN: ký thêm 1 dedicated với Pegatron — 4/5 hợp đồng.</span>
              </li>
              <li className="flex gap-2.5 items-start">
                <span className="text-signal-p0 mt-1">▼</span>
                <span>NPS tài xế: bảo hiểm còn 20%, chậm 2 tuần so kế hoạch.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* OKR dials grid */}
      <div className="grid grid-cols-2 gap-4">
        {OKRS.map((o) => (
          <OkrDial key={o.id} okr={o} />
        ))}
      </div>
    </div>
  );
}
