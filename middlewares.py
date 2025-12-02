from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.cache = TTLCache(maxsize=10_000, ttl=rate_limit)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
            
        user_id = event.from_user.id
        
        if user_id in self.cache:
            return
            
        self.cache[user_id] = True
        return await handler(event, data)


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        from config import CHANNEL_ID, CHANNEL_URL
        from keyboards import get_subscription_keyboard
        from loader import bot

        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        
        # Skip check for channel posts or if channel_id is not set
        if not CHANNEL_ID or not CHANNEL_URL:
            return await handler(event, data)

        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                await event.delete()
                await event.answer(
                    "Йоу, чтобы юзать бота надо подписаться на канал создателя.\n"
                    "Не ссы, потом отпишешься если захочешь.",
                    reply_markup=get_subscription_keyboard(CHANNEL_URL)
                )
                return
        except Exception:
            # If bot is not admin or other error, just pass
            pass

        return await handler(event, data)
