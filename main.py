import asyncio
import logging
from config import BOT_TOKEN
from loader import bot, dp
from database import init_db
from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found in .env file")
        return
    
    await init_db()
    
    from middlewares import SubscriptionMiddleware
    router.message.middleware(SubscriptionMiddleware())
    
    dp.include_router(router)
    
    print("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
