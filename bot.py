import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers.user import router as user_router
from handlers.admin import router as admin_router

logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())