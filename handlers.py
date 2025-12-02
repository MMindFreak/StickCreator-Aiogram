import logging
import time
import asyncio
from io import BytesIO
from typing import List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InputSticker
)
from aiogram.exceptions import TelegramRetryAfter

from loader import bot
from states import StickerStates
from database import (
    get_user_packs,
    get_user_current_pack_id,
    set_user_current_pack_id,
    create_pack,
    delete_pack_from_db,
    get_pack_by_id,
    get_user_stats
)
from keyboards import (
    get_main_keyboard, 
    get_pack_type_keyboard,
    get_delete_sticker_keyboard
)
from utils import process_image, process_video

router = Router()
media_group_lock = asyncio.Lock()

@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery):
    from config import CHANNEL_ID
    
    if not CHANNEL_ID:
        await callback.answer("Настройка канала не найдена.", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=callback.from_user.id)
        if member.status not in ["left", "kicked", "banned"]:
            await callback.message.delete()
            await cmd_start(callback.message)
        else:
            await callback.answer("Ты не подписался! Давай подписывайся.", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка проверки: {e}", show_alert=True)


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    packs = await get_user_packs(user_id)
    current_pack_id = await get_user_current_pack_id(user_id)

    if not current_pack_id and packs:
        current_pack_id = packs[0][0]
        await set_user_current_pack_id(user_id, current_pack_id)

    keyboard = get_main_keyboard(packs, current_pack_id)
    await message.answer(
        "Здарова я могу стикерпак сделать типа из картинок\n\n кидай картинку (или видео для видео-стикера)",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "create_pack")
async def cb_create_pack(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Название какое ни-будь накалякай другалёк для стикерпака")
    await state.set_state(StickerStates.waiting_for_pack_title)
    await callback.answer()


@router.message(StickerStates.waiting_for_pack_title)
async def process_pack_title(message: Message, state: FSMContext):
    title = message.text
    await state.update_data(title=title)
    
    keyboard = get_pack_type_keyboard()
    
    await message.answer("А теперь выбери тип пака:", reply_markup=keyboard)
    await state.set_state(StickerStates.waiting_for_pack_type)


@router.callback_query(StickerStates.waiting_for_pack_type)
async def process_pack_type(callback: CallbackQuery, state: FSMContext):
    pack_type = callback.data.replace("type_", "")
    data = await state.get_data()
    title = data['title']
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    
    suffix = int(time.time())
    name = f"stickers_{user_id}_{suffix}_by_{bot_info.username}"
    
    new_pack_id = await create_pack(user_id, name, title, pack_type)
    await set_user_current_pack_id(user_id, new_pack_id)
    
    packs = await get_user_packs(user_id)

    keyboard = get_main_keyboard(packs, new_pack_id)
    type_text = "стикерпак" if pack_type == "regular" else "эмодзи пак"
    await callback.message.answer(
        f"Пак '{title}' ({type_text}) создан, теперь кидай картинку",
        reply_markup=keyboard
    )
    await callback.answer()
    await state.clear()


@router.callback_query(F.data.startswith("select_"))
async def cb_select_pack(callback: CallbackQuery):
    pack_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    await set_user_current_pack_id(user_id, pack_id)
    packs = await get_user_packs(user_id)
            
    keyboard = get_main_keyboard(packs, pack_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    await callback.answer("Пак выбран!")


@router.callback_query(F.data == "delete_pack")
async def cb_delete_pack(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_pack_id = await get_user_current_pack_id(user_id)
            
    if current_pack_id:
        await delete_pack_from_db(current_pack_id, user_id)
            
    packs = await get_user_packs(user_id)
            
    new_current_id = packs[0][0] if packs else None
    if new_current_id:
        await set_user_current_pack_id(user_id, new_current_id)
            
    keyboard = get_main_keyboard(packs, new_current_id)
    await callback.message.edit_text(
        "Пак удален из списка (в телеграме он остался, если там были стикеры). Выбери другой или создай новый.",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    pack_count = await get_user_stats(user_id)
    await callback.answer(f"У тебя {pack_count} паков в базе бота.", show_alert=True)


@router.message(F.sticker)
async def handle_sticker_message(message: Message):
    user_id = message.from_user.id
    
    if message.sticker.set_name and f"_{user_id}_" in message.sticker.set_name:
        keyboard = get_delete_sticker_keyboard(message.sticker.file_id)
        await message.reply("Хочешь удалить этот стикер из пака?", reply_markup=keyboard)


@router.callback_query(F.data.startswith("del_sticker_"))
async def cb_delete_sticker(callback: CallbackQuery):
    file_id = callback.data.replace("del_sticker_", "")
    try:
        await bot.delete_sticker_from_set(file_id)
        await callback.message.edit_text("Стикер удален")
    except Exception as e:
        await callback.message.edit_text(f"Ошибка удаления: {e}")
    await callback.answer()


@router.callback_query(F.data == "cancel_delete")
async def cb_cancel_delete(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


async def process_media_item(message: Message, user_id: int):
    current_pack_id = await get_user_current_pack_id(user_id)
            
    if not current_pack_id:
        await message.answer("Cначала выбери или создай пак\n\n Нажми кнопку выше.")
        return
            
    pack_data = await get_pack_by_id(current_pack_id)
    if not pack_data:
        await message.answer("Чет не могу найти этот пак, выбери другой")
        return
    pack_name, pack_title, pack_type = pack_data

    file_id = None
    is_video = False
    
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
        is_video = True
    elif message.document:
        if message.document.mime_type.startswith("image/"):
            file_id = message.document.file_id
        elif message.document.mime_type.startswith("video/"):
            file_id = message.document.file_id
            is_video = True
            
    if not file_id:
        await message.answer("Отправь картинку или видео")
        return

    file = await bot.get_file(file_id)
    file_data = BytesIO()
    await bot.download_file(file.file_path, file_data)
    
    is_emoji = pack_type == "custom_emoji"
    
    try:
        if is_video:
            processed_data = process_video(file_data)
            filename = "sticker.webm"
            fmt = "video"
        else:
            processed_data = process_image(file_data, is_emoji=is_emoji)
            filename = "sticker.png"
            fmt = "static"
    except Exception as e:
        logging.error(f"Error processing media: {e}")
        await message.answer(f"Ошибка обработки: {e}")
        return

    sticker_file = BufferedInputFile(processed_data.read(), filename=filename)
    input_sticker = InputSticker(
        sticker=sticker_file,
        format=fmt,
        emoji_list=["😀"]
    )

    try:
        try:
            await bot.add_sticker_to_set(
                user_id=user_id,
                name=pack_name,
                sticker=input_sticker
            )
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await bot.add_sticker_to_set(
                user_id=user_id,
                name=pack_name,
                sticker=input_sticker
            )
            
        if not message.media_group_id:
            await message.answer(f"Готово, добавил в пак.\nhttps://t.me/addstickers/{pack_name}")
    except Exception as e:
        if "STICKERSET_INVALID" in str(e) or "set not found" in str(e).lower():
            try:
                sticker_type = "custom_emoji" if is_emoji else "regular"
                await bot.create_new_sticker_set(
                    user_id=user_id,
                    name=pack_name,
                    title=pack_title,
                    stickers=[input_sticker],
                    sticker_format=fmt,
                    sticker_type=sticker_type,
                )
                await message.answer(f"Создал новый пак и добавил туда стикер\nСсылка: https://t.me/addstickers/{pack_name}")
            except Exception as create_e:
                logging.error(f"Error creating sticker set: {create_e}")
                await message.answer(f"Не удалось создать пак: {create_e}")
        else:
            logging.error(f"Error adding sticker: {e}")
            await message.answer(f"Не удалось добавить стикер: {e}")


@router.message(F.photo | F.document | F.video)
async def handle_media(message: Message):
    user_id = message.from_user.id
    
    if message.media_group_id:
        async with media_group_lock:
            await process_media_item(message, user_id)
            await asyncio.sleep(1)
    else:
        await process_media_item(message, user_id)
