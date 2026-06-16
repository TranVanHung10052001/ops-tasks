import { MEMBERS } from "@/lib/mock";

const BOT_USERNAME = "ahamove_truck_ops_bot";
const BOT_NAME = "Ahamove Truck Ops Tasks";

const MEMBERS_WITH_LINK = MEMBERS.map((m) => ({
  ...m,
  setupLink: `https://t.me/${BOT_USERNAME}`,
}));

const COMMANDS = [
  { cmd: "/start", desc: "Đăng ký tài khoản — gõ lần đầu tiên", example: "/start" },
  { cmd: "/add", desc: "Tạo task cho bản thân", example: "/add Họp với kho HCM 14:30" },
  { cmd: "/today", desc: "Task hôm nay + overdue", example: "/today" },
  { cmd: "/mytasks", desc: "Tất cả task đang mở", example: "/mytasks" },
  { cmd: "/done", desc: "Đánh dấu hoàn thành", example: "/done 42" },
  { cmd: "/snooze", desc: "Hoãn lại 2h hoặc 1 ngày", example: "/snooze 42 2h" },
  { cmd: "/stats", desc: "Thống kê tuần này", example: "/stats" },
  { cmd: "/coach", desc: "AI hướng dẫn cách xử lý task", example: "/coach 42" },
  { cmd: "/help", desc: "Xem toàn bộ lệnh", example: "/help" },
];

const SETUP_STEPS = [
  {
    step: "01",
    title: "Mở Telegram",
    detail: `Tìm @${BOT_USERNAME} hoặc click link bên dưới`,
    action: `t.me/${BOT_USERNAME}`,
  },
  {
    step: "02",
    title: "Gõ /start",
    detail: "Bot hỏi họ tên đầy đủ — nhập đúng như trong hệ thống Ahamove",
    action: null,
  },
  {
    step: "03",
    title: "Chờ Manager duyệt",
    detail: "Anh Huy nhận thông báo và bấm Duyệt — thường trong vài phút",
    action: null,
  },
  {
    step: "04",
    title: "Bắt đầu dùng",
    detail: "Bot gửi thông báo khi được duyệt. Forward tin nhắn vào bot để tạo task nhanh.",
    action: null,
  },
];

export default function TelegramPage() {
  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      <header className="flex items-end justify-between">
        <div>
          <div className="label-ops text-2xs mb-1.5">Ops · 05 · Telegram bot</div>
          <h1 className="text-2xl text-text-primary editorial leading-tight">Kênh liên lạc Telegram.</h1>
          <p className="text-md text-text-secondary mt-1">
            Bot nhận lệnh, tạo task, gửi notify — đồng bộ realtime với Ops Center.
          </p>
        </div>
        <div className="ops-surface px-4 py-2.5">
          <div className="mono text-2xs text-text-tertiary uppercase tracking-wider mb-1">Bot</div>
          <div className="mono text-md text-accent-paper">@{BOT_USERNAME}</div>
          <div className="mono text-2xs text-text-tertiary mt-1">{BOT_NAME}</div>
        </div>
      </header>

      {/* Setup steps */}
      <section className="ops-surface p-5">
        <div className="label-ops text-2xs mb-4">Hướng dẫn đăng ký — 4 bước</div>
        <div className="grid grid-cols-4 gap-5">
          {SETUP_STEPS.map((s) => (
            <div key={s.step} className="relative pl-4 border-l-2 border-divider-strong">
              <div className="mono text-2xs text-accent-amber mb-1 uppercase tracking-widest">{s.step}</div>
              <div className="text-sm text-text-primary font-medium mb-1">{s.title}</div>
              <div className="text-xs text-text-secondary leading-relaxed">{s.detail}</div>
              {s.action && (
                <div className="mono text-2xs text-accent-paper mt-2 break-all">{s.action}</div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-5 pt-4 border-t border-divider flex items-center gap-4">
          <a
            href={`https://t.me/${BOT_USERNAME}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ops mono text-xs px-4 py-2 border border-accent-amber text-accent-amber hover:bg-accent-amber hover:text-canvas transition-colors"
          >
            → Mở @{BOT_USERNAME}
          </a>
          <span className="mono text-2xs text-text-tertiary">
            Share link này cho từng thành viên để họ tự đăng ký
          </span>
        </div>
      </section>

      <div className="grid grid-cols-3 gap-5">
        {/* Member list */}
        <section className="ops-surface col-span-2">
          <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
            <span className="label-ops text-2xs">Thành viên — cần đăng ký bot</span>
            <span className="mono text-2xs text-text-tertiary">{MEMBERS_WITH_LINK.length} người</span>
          </header>
          <table className="w-full">
            <thead>
              <tr className="border-b border-divider mono text-2xs uppercase tracking-wider text-text-tertiary">
                <th className="text-left px-5 py-2 font-normal">Callsign</th>
                <th className="text-left px-3 py-2 font-normal">Tên</th>
                <th className="text-left px-3 py-2 font-normal">Email</th>
                <th className="text-right px-5 py-2 font-normal">Link đăng ký</th>
              </tr>
            </thead>
            <tbody>
              {MEMBERS_WITH_LINK.map((m) => (
                <tr key={m.id} className="border-b border-divider hover:bg-surface-raised">
                  <td className="px-5 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 border border-divider-strong bg-surface mono text-2xs flex items-center justify-center text-accent-paper">
                        {m.initials}
                      </div>
                      <span className="mono text-xs text-text-secondary">{m.initials}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-sm text-text-primary">{m.name}</td>
                  <td className="px-3 py-2.5 mono text-xs text-text-secondary">{m.email}</td>
                  <td className="px-5 py-2.5 text-right">
                    <a
                      href={m.setupLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mono text-2xs text-accent-amber hover:text-accent-paper transition-colors"
                    >
                      → t.me/{BOT_USERNAME}
                    </a>
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

      {/* Sample conversation */}
      <section className="ops-surface">
        <header className="px-5 py-3 border-b border-divider flex items-center justify-between">
          <span className="label-ops text-2xs">Hội thoại mẫu — forward tin để tạo task</span>
          <span className="mono text-2xs text-text-tertiary">@{BOT_USERNAME}</span>
        </header>
        <div className="p-4 space-y-3 bg-surface-deep max-w-[560px]">
          <div className="flex justify-end">
            <div className="max-w-[320px] bg-accent-amber-deep text-canvas px-3 py-2 rounded-sm">
              <div className="text-sm">Foxconn đổi tài xế xe 4 - thái độ không phù hợp</div>
              <div className="mono text-2xs opacity-70 mt-1 text-right">11:42 · OPS-05</div>
            </div>
          </div>

          <div className="flex">
            <div className="max-w-[360px] bg-surface border border-divider px-3 py-2 rounded-sm">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-accent-amber">⊙</span>
                <span className="mono text-2xs text-text-tertiary uppercase tracking-wider">Phân loại AI</span>
              </div>
              <div className="text-sm text-text-primary mb-2">✓ Đã tạo task #42</div>
              <div className="space-y-1 text-xs text-text-secondary mb-2">
                <div>Danh mục: <span className="text-accent-paper">Phát sinh · Xử lý sự cố</span></div>
                <div>Mức độ: <span className="text-signal-p1">P1 · Cao</span></div>
                <div>Đề xuất giao: <span className="text-accent-paper">OPS-05</span></div>
              </div>
              <div className="flex gap-1.5 pt-2 border-t border-divider">
                <button className="text-2xs px-2 py-1 bg-accent-amber-deep text-canvas mono uppercase">✓ Xác nhận</button>
                <button className="text-2xs px-2 py-1 border border-divider-strong text-text-secondary mono uppercase">Đổi người</button>
                <button className="text-2xs px-2 py-1 border border-divider-strong text-text-secondary mono uppercase">Huỷ</button>
              </div>
              <div className="mono text-2xs text-text-tertiary mt-2">11:42 · @{BOT_USERNAME}</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
