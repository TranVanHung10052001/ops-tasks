"""
ops-tasks · Combined entry point
Runs FastAPI (uvicorn) + Telegram bot in a single process.

Railway: uvicorn listens on $PORT (web health-check), bot polls Telegram.
Local:   `python server.py` replaces two separate terminal tabs.
"""

import asyncio
import logging
import os
import sys
import threading

import uvicorn
from dotenv import load_dotenv

# Load .env BEFORE importing any module that reads env vars at module level
load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))],
)
logger = logging.getLogger("server")


def _run_api() -> None:
    """Run FastAPI in a background daemon thread."""
    port = int(os.getenv("PORT", "8000"))
    logger.info("API → http://0.0.0.0:%d  (docs: /api/docs)", port)
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        log_level="warning",
        access_log=False,
        reload=False,
    )


async def main() -> None:
    # ── Validate required env vars ────────────────────────────────────────
    required = {
        "TELEGRAM_TOKEN": "token từ @BotFather",
        "GEMINI_API_KEY": "key từ Google AI Studio",
        "MANAGER_CHAT_ID": "Telegram ID của anh Huy",
    }
    missing = [f"{k} ({hint})" for k, hint in required.items() if not os.getenv(k)]
    if missing:
        logger.error("Thiếu biến môi trường trong bot/.env:\n  %s", "\n  ".join(missing))
        sys.exit(1)

    # ── Start FastAPI in background thread ────────────────────────────────
    api_thread = threading.Thread(target=_run_api, daemon=True, name="uvicorn-api")
    api_thread.start()

    # Brief delay for uvicorn to bind the port before bot starts
    await asyncio.sleep(1.5)
    logger.info("API server running — starting Telegram bot")

    # ── Start Telegram bot ────────────────────────────────────────────────
    # main.py has module-level env checks; since we validated above they pass.
    from main import main as bot_main  # noqa: E402
    await bot_main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
