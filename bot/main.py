"""
ops-tasks — Team Task Bot Entry Point
Ahamove Truck Ops / anh Huy's team
"""

import asyncio
import logging
import os
import re
import sys

from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

from bot import (
    cmd_start, cmd_help, cmd_add, cmd_mytasks, cmd_today,
    cmd_done, cmd_snooze, cmd_cancel, cmd_stats, cmd_skip,
    cmd_assign, cmd_team, cmd_pending, cmd_brief, cmd_ask,
    cmd_approve, cmd_users, cmd_setrole, cmd_coach,
    handle_forward, handle_photo, handle_callback,
    handle_keyboard_text, KEYBOARD_ROUTES,
)
from scheduler import (
    morning_briefing_all, manager_team_digest,
    deadline_check_all, eod_recap_all, stall_check_all,
    okr_risk_intel, weekly_report,
)
from redash_sync import sync_all as redash_sync_all
from store import init_db
from roles import MANAGER_CHAT_ID

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("TELEGRAM_TOKEN not set in .env")
    sys.exit(1)
if not MANAGER_CHAT_ID:
    logger.error("MANAGER_CHAT_ID not set in .env")
    sys.exit(1)
if not os.getenv("GEMINI_API_KEY"):
    logger.error("GEMINI_API_KEY not set in .env")
    sys.exit(1)


async def main():
    init_db()
    logger.info("Database initialized")

    app = Application.builder().token(TOKEN).build()

    # ── Commands ──────────────────────────────────────────────────────────
    for cmd, handler in [
        ("start",    cmd_start),
        ("help",     cmd_help),
        ("add",      cmd_add),
        ("mytasks",  cmd_mytasks),
        ("today",    cmd_today),
        ("done",     cmd_done),
        ("snooze",   cmd_snooze),
        ("cancel",   cmd_cancel),
        ("stats",    cmd_stats),
        ("skip",     cmd_skip),
        ("assign",   cmd_assign),
        ("team",     cmd_team),
        ("pending",  cmd_pending),
        ("approve",  cmd_approve),
        ("users",    cmd_users),
        ("setrole",  cmd_setrole),
        ("coach",    cmd_coach),
        ("brief",    cmd_brief),
        ("ask",      cmd_ask),
    ]:
        app.add_handler(CommandHandler(cmd, handler))

    # ── Message handlers ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        handle_photo,
    ))

    kb_texts = list(KEYBOARD_ROUTES.keys())
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(
            "^(" + "|".join(re.escape(t) for t in kb_texts) + ")$"
        ),
        handle_keyboard_text,
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_forward,
    ))

    app.add_handler(MessageHandler(
        filters.FORWARDED & filters.ChatType.PRIVATE,
        handle_forward,
    ))

    # ── Error handler ─────────────────────────────────────────────────────
    async def error_handler(update, context):
        logger.error(f"Unhandled error: {context.error}", exc_info=context.error)
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "Bot gặp lỗi. Thử lại hoặc báo admin."
                )
            except Exception:
                pass

    app.add_error_handler(error_handler)

    # ── Scheduler ─────────────────────────────────────────────────────────
    sched = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")

    sched.add_job(morning_briefing_all,  "cron", hour=8,  minute=0,
                  args=[app], id="morning_all")
    sched.add_job(manager_team_digest,   "cron", hour=8,  minute=30,
                  args=[app], id="manager_digest")
    sched.add_job(deadline_check_all,    "interval", minutes=15,
                  args=[app], id="deadline_check")
    sched.add_job(eod_recap_all,         "cron", hour=18, minute=0,
                  args=[app], id="eod_recap")
    sched.add_job(stall_check_all,       "cron", hour="9,15", minute=0,
                  args=[app], id="stall_check")
    sched.add_job(okr_risk_intel,        "cron", day_of_week="mon,wed,fri",
                  hour=8, minute=35, args=[app], id="okr_risk_intel")
    sched.add_job(weekly_report,         "cron", day_of_week="fri",
                  hour=17, minute=0, args=[app], id="weekly_report")

    # Redash KPI sync — every 30 min (safe no-op if REDASH_URL not configured)
    sched.add_job(redash_sync_all, "interval", minutes=30, id="redash_sync")

    sched.start()
    logger.info("Scheduler started — 8 jobs (Redash sync every 30min)")

    logger.info(f"Bot starting | Manager: {MANAGER_CHAT_ID}")

    async with app:
        await app.start()
        await app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
        logger.info("Bot is running. Ctrl+C to stop.")

        stop_event = asyncio.Event()
        import signal
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                pass

        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            sched.shutdown(wait=False)
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
