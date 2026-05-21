import { ACTIVITY, MEMBERS } from "@/lib/mock";

const LINKED = MEMBERS.map((m, i) => ({
  ...m,
  linked: i < 6,
  username: m.callsign.toLowerCase().replace("-", "") + "_ahm",
}));

const COMMANDS = [
  { cmd: "/task", desc: "Tạo task nhanh từ chat", example: "/task Họp với kho HCM 14:30" },
  { cmd: "/today", desc: "Task hôm nay của tôi", example: "/today" },
  { cmd: "/me", desc: "Tất cả task của tôi", example: "/me" },
  { cmd: "/done", desc: "Đánh dấu hoàn thành", example: "/done T-04827" },
  { cmd: "/briefing", desc: "Báo cáo nhanh", example: "/briefing" },
  { cmd: "/help", desc: "Hướng dẫn", example: "/help" },
];

export default function TelegramPage() {
  const tgEvents = ACTIVITY.filter((a) => a.via === "telegram");

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      <header className="flex items-end justify-between">
        <div>
          <div className="label-ops text-2xs mb-1.5">Đài chính · 05 · Telegram bot</div>
          <h1 className="text-2xl text-text-primary editorial leading-tight">Kênh liên lạc Telegram.</h1>
          <p className="text-md text-text-secondary mt-1">
            Bot xử lý notify, quick task, query — đồng bộ realtime với Đài Điều Vận.
          </p>
        </div>
        <div className="ops-surface px-4 py-2.5">
          <div className="mono text-2xs text-text-tertiary uppercase tracking-wider mb-1">Trạng thái bot</div>
          <div className="flex items-center gap-2">
            <span className="status-dot active" />
            <span className="mono text-sm text-state-active">đang chạy · uptime 14d 3h</span>
          </div>
        </div>
      </header>

      {/* Bot info */}
      <section className="ops-surface p-5">
        <div className="grid grid-cols-4 gap-6">
          <div>
            <div className="label-ops text-2xs mb-2">Bot username</div>
            <div className="mono text-md text-accent-paper">@AhamoveOps_DieuVan_Bot</div>
            <div className="mono text-2xs text-text-tertiary mt-1">webhook: prod-bot.ahamove.com/tg</div>
          </div>
          <div>
            <div className="label-ops text-2xs mb-2">Tin nhắn hôm nay</div>
            <div className="font-display text-3xl text-text-primary tabular leading-none">412</div>
            <div className="mono text-2xs text-text-tertiary mt-1">avg 28/h</div>
          </div>
          <div>
            <div className="label-ops text-2xs mb-2">Task tạo qua bot</div>
            <div className="font-display text-3xl text-accent-paper tabular leading-none">17</div>
            <div className="mono text-2xs text-text-tertiary mt-1">94% AI phân loại đúng</div>
          </div>
          <div>
            <div className="label-ops text-2xs mb-2">Notify đã gửi</div>
            <div className="font-display text-3xl text-text-primary tabular leading-none">128</div>
            <div className="mono text-2xs text-text-tertiary mt-1">23 P0 alerts</div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-3 gap-5">
        {/* Linked members */}
        <section className="ops-surface col-span-2">
          <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
            <span className="label-ops text-2xs">Thành viên đã liên kết</span>
            <span className="mono text-2xs text-text-tertiary">
              {LINKED.filter((m) => m.linked).length}/{LINKED.length} đã link
            </span>
          </header>
          <table className="w-full">
            <thead>
              <tr className="border-b border-divider mono text-2xs uppercase tracking-wider text-text-tertiary">
                <th className="text-left px-5 py-2 font-normal">Callsign</th>
                <th className="text-left px-3 py-2 font-normal">Tên</th>
                <th className="text-left px-3 py-2 font-normal">Telegram</th>
                <th className="text-left px-3 py-2 font-normal">Trạng thái</th>
                <th className="text-right px-5 py-2 font-normal">Hoạt động</th>
              </tr>
            </thead>
            <tbody>
              {LINKED.map((m) => (
                <tr key={m.id} className="border-b border-divider hover:bg-surface-raised">
                  <td className="px-5 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 border border-divider-strong bg-surface mono text-2xs flex items-center justify-center text-accent-paper">
                        {m.initials}
                      </div>
                      <span className="mono text-xs text-text-secondary">{m.callsign}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-sm text-text-primary">{m.name}</td>
                  <td className="px-3 py-2.5 mono text-xs text-text-secondary">@{m.username}</td>
                  <td className="px-3 py-2.5">
                    {m.linked ? (
                      <span className="mono text-2xs text-state-active uppercase tracking-wider">✓ đã liên kết</span>
                    ) : (
                      <span className="mono text-2xs text-signal-p2 uppercase tracking-wider">⚠ chưa link</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 text-right mono text-xs text-text-tertiary tabular">
                    {m.linked ? "5 phút trước" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Commands */}
        <section className="ops-surface">
          <header className="px-4 py-3 border-b border-divider">
            <span className="label-ops text-2xs">Lệnh khả dụng</span>
          </header>
          <div className="p-4 space-y-3">
            {COMMANDS.map((c) => (
              <div key={c.cmd} className="border-l-2 border-divider-strong pl-3">
                <div className="mono text-md text-accent-paper">{c.cmd}</div>
                <div className="text-xs text-text-secondary">{c.desc}</div>
                <div className="mono text-2xs text-text-tertiary mt-1">{c.example}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Bot conversation preview + Activity */}
      <div className="grid grid-cols-2 gap-5">
        {/* Sample conversation */}
        <section className="ops-surface">
          <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
            <span className="label-ops text-2xs">Hội thoại mẫu</span>
            <span className="mono text-2xs text-text-tertiary">demo · OPS-05</span>
          </header>
          <div className="p-4 space-y-3 bg-surface-deep">
            {/* User msg */}
            <div className="flex justify-end">
              <div className="max-w-[260px] bg-accent-amber-deep text-canvas px-3 py-2 rounded-sm">
                <div className="text-sm">/task Foxconn đổi tài xế xe 4 - thái độ</div>
                <div className="mono text-2xs opacity-70 mt-1 text-right">11:42</div>
              </div>
            </div>

            {/* Bot msg */}
            <div className="flex">
              <div className="max-w-[280px] bg-surface border border-divider px-3 py-2 rounded-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-accent-amber">⊙</span>
                  <span className="mono text-2xs text-text-tertiary uppercase tracking-wider">Đang phân tích</span>
                </div>
                <div className="text-sm text-text-primary mb-2">✓ Đã tạo T-2026-04832</div>
                <div className="space-y-1 text-xs text-text-secondary mb-2">
                  <div>Kênh: <span className="text-accent-paper">Phát sinh · Xử lý sự cố</span></div>
                  <div>Mức độ: <span className="text-signal-p1">P1 · Cao</span> (deadline gần)</div>
                  <div>Đề xuất giao: <span className="text-accent-paper">OPS-05 (CSKH)</span></div>
                </div>
                <div className="flex gap-1.5 pt-2 border-t border-divider">
                  <button className="text-2xs px-2 py-1 bg-accent-amber-deep text-canvas mono uppercase">Xác nhận</button>
                  <button className="text-2xs px-2 py-1 border border-divider-strong text-text-secondary mono uppercase">Đổi</button>
                  <button className="text-2xs px-2 py-1 border border-divider-strong text-text-secondary mono uppercase">Hủy</button>
                </div>
                <div className="mono text-2xs text-text-tertiary mt-2">11:42 · @AhamoveOps_DieuVan_Bot</div>
              </div>
            </div>

            <div className="flex justify-end">
              <div className="max-w-[200px] bg-accent-amber-deep text-canvas px-3 py-2 rounded-sm">
                <div className="text-sm">Xác nhận</div>
                <div className="mono text-2xs opacity-70 mt-1 text-right">11:43</div>
              </div>
            </div>

            <div className="flex">
              <div className="max-w-[260px] bg-surface border border-divider px-3 py-2 rounded-sm">
                <div className="text-sm text-text-primary mb-1">✓ T-04832 đã giao cho OPS-05.</div>
                <div className="text-xs text-text-secondary">Chị Lan vừa nhận task. ETA xử lý: 18:00 hôm nay.</div>
                <div className="mono text-2xs text-text-tertiary mt-2">11:43</div>
              </div>
            </div>
          </div>
        </section>

        {/* Recent bot activity */}
        <section className="ops-surface">
          <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
            <span className="label-ops text-2xs">Sự kiện bot gần đây</span>
            <span className="status-dot active" />
          </header>
          <ol className="px-5 py-3 space-y-3">
            {[...tgEvents, ...ACTIVITY.filter((a) => a.via === "ai")].slice(0, 10).map((a) => (
              <li key={a.id + a.ts} className="flex gap-3 text-xs items-start">
                <span className="mono text-text-tertiary tabular w-12 shrink-0">{a.ts}</span>
                <div className="flex-1">
                  <span className={a.via === "ai" ? "text-accent-amber" : "mono text-accent-paper"}>
                    {a.actor}
                  </span>{" "}
                  <span className="text-text-secondary">{a.action}</span>{" "}
                  {a.target && <span className="mono text-text-primary">{a.target}</span>}
                </div>
                <span className={"mono text-2xs " + (a.via === "telegram" ? "text-state-done" : "text-accent-amber")}>
                  [{a.via === "telegram" ? "TG" : "AI"}]
                </span>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}
