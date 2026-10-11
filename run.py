import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from app.core.config import settings
from app.core.database import engine, Base, async_session_maker
from app.database.repositories import seed_default_categories

# Middlewares
from app.middlewares.db_session import DatabaseSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.middlewares.subscription import SubscriptionMiddleware

# Handlers
from app.handlers import common
from app.handlers.user import catalog, search, download, favorites, request_app
from app.handlers.admin import (
    admin_menu, add_program, manage_programs,
    categories, broadcast, channels, stats_backup
)

# Windows console UTF-8 qo'llab-quvvatlash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def setup_commands(bot: Bot):
    """Telegram menyusidagi standart buyruqlar."""
    # Barcha oddiy foydalanuvchilar menyusi (faqat /start)
    user_commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish")
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Faqat adminlar menyusi (/start va /admin)
    admin_commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish"),
        BotCommand(command="admin", description="Admin panel")
    ]
    for admin_id in settings.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Admin {admin_id} uchun maxsus buyruqlarni o'rnatishda xatolik: {e}")

async def init_database():
    """Baza jadvallarini yaratish va boshlang'ich ma'lumotlarni kiritish."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE programs ADD COLUMN IF NOT EXISTS download_url VARCHAR(512);"))
        except Exception:
            pass
    logger.info("✅ Ma'lumotlar bazasi jadvallari muvaffaqiyatli tekshirildi/yaratildi.")

    # Boshlang'ich default kategoriyalarni kiritish
    async with async_session_maker() as session:
        await seed_default_categories(session)
    logger.info("✅ Standart kategoriyalar tekshirildi.")

async def handle_ping(request: web.Request) -> web.Response:
    """Render va UptimeRobot uchun salomatlik tekshiruvi (Health Check) va chiroyli status sahifasi."""
    html_content = """<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SoftUz Bot - Online</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: #1e293b;
            padding: 2.5rem;
            border-radius: 1rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            text-align: center;
            max-width: 420px;
            border: 1px solid #334155;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            padding: 0.4rem 0.9rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        .dot {
            width: 8px;
            height: 8px;
            background: #4ade80;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #4ade80;
        }
        h1 { margin: 0 0 0.5rem 0; font-size: 1.4rem; }
        p { color: #94a3b8; font-size: 0.95rem; margin: 0; }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge"><span class="dot"></span> Online 24/7</div>
        <h1>SoftUz Telegram Boti</h1>
        <p>Bot serverda muvaffaqiyatli ishlamoqda va yangilanishlarni qabul qilmoqda.</p>
    </div>
</body>
</html>"""
    return web.Response(text=html_content, content_type="text/html", status=200)

async def start_web_server() -> web.AppRunner:
    """Render Web Service port talab qilgani va UptimeRobot uchun web server."""
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_route("*", "/", handle_ping)
    app.router.add_route("*", "/health", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Web server {port}-portda muvaffaqiyatli ishga tushdi.")
    return runner

async def main():
    logger.info("🚀 Dasturlar Telegram Boti ishga tushmoqda...")

    # Web serverni ishga tushirish (Render port tekshiruvi va UptimeRobot uchun)
    web_runner = None
    try:
        web_runner = await start_web_server()
    except Exception as e:
        logger.warning(f"Web serverni ishga tushirishda ogohlantirish: {e}")

    # Bazani ishga tushirish
    await init_database()

    # Bot va Dispatcher yaratish
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Bot ma'lumotlarini keshga yuklash
    try:
        me = await bot.get_me()
        from app.utils.cache import cache
        cache.set_bot_username(me.username)
        logger.info(f"🤖 Bot ma'lumotlari muvaffaqiyatli yuklandi: @{me.username} (ID: {me.id})")
    except Exception as e:
        logger.warning(f"Bot ma'lumotlarini olishda ogohlantirish: {e}")

    # Middlewarelarni ro'yxatdan o'tkazish
    dp.update.outer_middleware(DatabaseSessionMiddleware())
    dp.message.middleware(ThrottlingMiddleware(limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(limit=0.25))
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # Handler Routerlarini ulash
    # 1. Admin routerlari
    dp.include_router(admin_menu.router)
    dp.include_router(add_program.router)
    dp.include_router(manage_programs.router)
    dp.include_router(categories.router)
    dp.include_router(broadcast.router)
    dp.include_router(channels.router)
    dp.include_router(stats_backup.router)

    # 2. Foydalanuvchi routerlari
    dp.include_router(common.router)
    dp.include_router(catalog.router)
    dp.include_router(search.router)
    dp.include_router(download.router)
    dp.include_router(favorites.router)
    dp.include_router(request_app.router)

    # Buyruqlarni sozlash
    try:
        await setup_commands(bot)
    except Exception as e:
        logger.warning(f"Buyruqlarni o'rnatishda ogohlantirish (Token noto'g'ri bo'lishi mumkin): {e}")

    # Pollingni boshlash
    logger.info("🤖 Bot muvaffaqiyatli ishga tushdi va xabarlarni qabul qilishga tayyor!")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if web_runner:
            try:
                await web_runner.cleanup()
            except Exception:
                pass
        await bot.session.close()
        await engine.dispose()
        logger.info("🛑 Bot to'xtatildi.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot qo'lda to'xtatildi.")
