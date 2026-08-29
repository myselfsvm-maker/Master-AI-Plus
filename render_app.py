import asyncio
import logging
import os

from aiohttp import web

import bot as botmodule
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def health(request):
    return web.Response(text="OK - AI aggregator bot is running")


async def run_web_server():
    """Render's free 'Web Service' tier requires something listening on $PORT."""
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Health check server listening on port %s", port)


async def main():
    db.init_db()
    application = botmodule.build_application()

    await run_web_server()

    async with application:
        await application.start()
        await application.updater.start_polling()
        log.info("Telegram bot polling started")
        await asyncio.Event().wait()  # keep running forever


if __name__ == "__main__":
    asyncio.run(main())
