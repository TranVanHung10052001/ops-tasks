import { TODAY } from "@/lib/mock";

export default function BriefingCard() {
  return (
    <section className="ops-surface relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-accent-amber" />
      <div className="hatch absolute top-0 right-0 w-32 h-full opacity-40" />

      <div className="p-6 relative">
        <div className="flex items-baseline justify-between mb-5">
          <div className="flex items-center gap-3">
            <span className="label-ops text-2xs">Báo cáo chiều</span>
            <span className="text-text-tertiary">·</span>
            <span className="mono text-2xs text-text-tertiary tracking-wider">
              {TODAY.short} · {TODAY.dayName} · 14:32 ICT
            </span>
          </div>
          <div className="mono text-2xs text-text-tertiary">BRIEF-2026-0522-14</div>
        </div>

        <div className="grid grid-cols-3 gap-8">
          <div>
            <div className="label-ops text-2xs mb-2">Tổng quan</div>
            <p className="editorial text-xl leading-snug text-text-primary">
              Truck team đang chạy 47 task. GSV truck hôm nay đạt 8.7 tỷ (+12%), fill rate 78%. Sự cố VSIP II cần xử lý trong 30 phút.
            </p>
          </div>

          <div>
            <div className="label-ops text-2xs mb-2">Ưu tiên hôm nay</div>
            <ol className="space-y-2 text-md text-text-primary">
              <li className="flex gap-2.5">
                <span className="mono text-accent-amber w-4">01</span>
                <span>Giải tỏa 3 xe 2.5T kẹt QL13, ưu tiên Foxconn trước 11:00.</span>
              </li>
              <li className="flex gap-2.5">
                <span className="mono text-accent-amber w-4">02</span>
                <span>Họp Long Hậu chốt SLA Bulky Q2 — idle &lt;45 phút — 14:30.</span>
              </li>
              <li className="flex gap-2.5">
                <span className="mono text-accent-amber w-4">03</span>
                <span>Hoàn thiện pitch SLP Logistics — dedicated 8 xe 5T — 17:00.</span>
              </li>
            </ol>
          </div>

          <div>
            <div className="label-ops text-2xs mb-2">Tín hiệu cần chú ý</div>
            <ul className="space-y-2 text-md text-text-primary">
              <li className="flex gap-2.5 items-start">
                <span className="text-signal-p0 mt-1">●</span>
                <span>
                  <span className="text-signal-p0">OPS-03 overload</span> — 9/10 task, 2 P0 KCN.
                </span>
              </li>
              <li className="flex gap-2.5 items-start">
                <span className="text-signal-p1 mt-1">●</span>
                <span>
                  <span className="text-accent-paper">Lalamove giảm giá Bulky -8%</span> HCM — cần phản hồi tuần này.
                </span>
              </li>
              <li className="flex gap-2.5 items-start">
                <span className="text-signal-p2 mt-1">●</span>
                <span>
                  OKR <span className="text-accent-paper">LTL pilot</span> chậm — Tech MVP mới 20%.
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div className="dotted-divider my-5" />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-2xs text-text-tertiary">
            <span className="text-accent-amber">⊙</span>
            <span className="mono uppercase tracking-wider">Soạn bởi Trợ lý điều vận · cập nhật mỗi 30 phút · nguồn: Ops DB + GSV warehouse</span>
          </div>
          <div className="flex gap-2">
            <button className="btn-ops">► Xem chi tiết</button>
            <button className="btn-ops primary">Soạn lại</button>
          </div>
        </div>
      </div>
    </section>
  );
}
