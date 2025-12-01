import asyncio
import logging
import os
from io import BytesIO
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InputSticker,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_NAME = "stickers.db"


class StickerStates(StatesGroup):
    waiting_for_pack_title = State()
    waiting_for_pack_type = State()


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                title TEXT,
                pack_type TEXT DEFAULT 'regular',
                UNIQUE(name)
            )
            """
        )
        
        try:
            await db.execute("SELECT pack_type FROM packs LIMIT 1")
        except Exception:
            print("Migrating database: adding pack_type column...")
            await db.execute("ALTER TABLE packs ADD COLUMN pack_type TEXT DEFAULT 'regular'")
            await db.commit()
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                current_pack_id INTEGER
            )
            """
        )
        await db.commit()


def get_main_keyboard(packs, current_pack_id):
    buttons = []
    
    for pack in packs:
        pack_id, _, _, title, pack_type = pack
        type_icon = "📦" if pack_type == "regular" else "😀"
        text = f"✅ {type_icon} {title}" if pack_id == current_pack_id else f"{type_icon} {title}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"select_{pack_id}")])
    
    buttons.append([InlineKeyboardButton(text="➕ Создать новый пак", callback_data="create_pack")])
    
    if current_pack_id:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить текущий пак", callback_data="delete_pack")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def process_image(image_data: BytesIO, is_emoji: bool = False) -> BytesIO:
    with Image.open(image_data) as img:
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        if is_emoji:
            img.thumbnail((100, 100), Image.Resampling.LANCZOS)
            
            canvas = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            
            x = (100 - img.width) // 2
            y = (100 - img.height) // 2
            canvas.paste(img, (x, y))
            img = canvas
        else:
            width, height = img.size
            if width >= height:
                new_width = 512
                new_height = int(height * (512 / width))
            else:
                new_height = 512
                new_width = int(width * (512 / height))
            
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM packs WHERE user_id = ?", (user_id,)) as cursor:
            packs = await cursor.fetchall()
        
        async with db.execute("SELECT current_pack_id FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            setting = await cursor.fetchone()
            current_pack_id = setting[0] if setting else None

    if not current_pack_id and packs:
        current_pack_id = packs[0][0]
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_settings (user_id, current_pack_id) VALUES (?, ?)",
                (user_id, current_pack_id),
            )
            await db.commit()

    keyboard = get_main_keyboard(packs, current_pack_id)
    await message.answer(
        "Здарова, я могу стикерпак сделать типа из картинок, кидай картинку",
        reply_markup=keyboard,
    )


@dp.callback_query(F.data == "create_pack")
async def cb_create_pack(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Название какое ни-будь накалякай другалёк для стикерпака")
    await state.set_state(StickerStates.waiting_for_pack_title)
    await callback.answer()


@dp.message(StickerStates.waiting_for_pack_title)
async def process_pack_title(message: Message, state: FSMContext):
    title = message.text
    await state.update_data(title=title)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Обычные стикеры", callback_data="type_regular")],
        [InlineKeyboardButton(text="😀 Эмодзи пак", callback_data="type_custom_emoji")]
    ])
    
    await message.answer("А теперь выбери тип пака:", reply_markup=keyboard)
    await state.set_state(StickerStates.waiting_for_pack_type)


@dp.callback_query(StickerStates.waiting_for_pack_type)
async def process_pack_type(callback: CallbackQuery, state: FSMContext):
    pack_type = callback.data.replace("type_", "")
    data = await state.get_data()
    title = data['title']
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    
    import time
    suffix = int(time.time())
    name = f"stickers_{user_id}_{suffix}_by_{bot_info.username}"
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO packs (user_id, name, title, pack_type) VALUES (?, ?, ?, ?)",
            (user_id, name, title, pack_type)
        )
        await db.commit()
        
        async with db.execute("SELECT id FROM packs WHERE name = ?", (name,)) as cursor:
            new_pack = await cursor.fetchone()
            new_pack_id = new_pack[0]
            
        await db.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, current_pack_id) VALUES (?, ?)",
            (user_id, new_pack_id),
        )
        await db.commit()
        
        async with db.execute("SELECT * FROM packs WHERE user_id = ?", (user_id,)) as cursor:
            packs = await cursor.fetchall()

    keyboard = get_main_keyboard(packs, new_pack_id)
    type_text = "стикерпак" if pack_type == "regular" else "эмодзи пак"
    await callback.message.answer(
        f"Пак '{title}' ({type_text}) создан, теперь кидай картинку",
        reply_markup=keyboard
    )
    await callback.answer()
    await state.clear()


@dp.callback_query(F.data.startswith("select_"))
async def cb_select_pack(callback: CallbackQuery):
    pack_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, current_pack_id) VALUES (?, ?)",
            (user_id, pack_id),
        )
        await db.commit()
        
        async with db.execute("SELECT * FROM packs WHERE user_id = ?", (user_id,)) as cursor:
            packs = await cursor.fetchall()
            
    keyboard = get_main_keyboard(packs, pack_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    await callback.answer("Пак выбран!")


@dp.callback_query(F.data == "delete_pack")
async def cb_delete_pack(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT current_pack_id FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            setting = await cursor.fetchone()
            current_pack_id = setting[0] if setting else None
            
        if current_pack_id:
            await db.execute("DELETE FROM packs WHERE id = ?", (current_pack_id,))
            await db.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
            await db.commit()
            
        async with db.execute("SELECT * FROM packs WHERE user_id = ?", (user_id,)) as cursor:
            packs = await cursor.fetchall()
            
        new_current_id = packs[0][0] if packs else None
        if new_current_id:
            await db.execute(
                "INSERT OR REPLACE INTO user_settings (user_id, current_pack_id) VALUES (?, ?)",
                (user_id, new_current_id),
            )
            await db.commit()
            
    keyboard = get_main_keyboard(packs, new_current_id)
    await callback.message.edit_text(
        "Пак удален из списка (в телеграме он остался, если там были стикеры). Выбери другой или создай новый.",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.message(F.photo | F.document)
async def handle_image(message: Message):
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT current_pack_id FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            setting = await cursor.fetchone()
            current_pack_id = setting[0] if setting else None
            
        if not current_pack_id:
            await message.answer("Эй, сначала выбери или создай пак! Жми кнопку выше.")
            return
            
        async with db.execute("SELECT name, title, pack_type FROM packs WHERE id = ?", (current_pack_id,)) as cursor:
            pack_data = await cursor.fetchone()
            if not pack_data:
                await message.answer("Чет не могу найти этот пак, выбери другой")
                return
            pack_name, pack_title, pack_type = pack_data

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document and message.document.mime_type.startswith("image/"):
        file_id = message.document.file_id
    else:
        await message.answer("Пожалуйста, отправь картинку а не хуйню какую то")
        return

    file = await bot.get_file(file_id)
    file_data = BytesIO()
    await bot.download_file(file.file_path, file_data)
    
    is_emoji = pack_type == "custom_emoji"
    try:
        processed_image = process_image(file_data, is_emoji=is_emoji)
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        await message.answer("Бля чет ошибка какая то при создании стикерпака")
        return

    sticker_file = BufferedInputFile(processed_image.read(), filename="sticker.png")
    input_sticker = InputSticker(
        sticker=sticker_file,
        format="static",
        emoji_list=["😀"]
    )

    try:
        await bot.add_sticker_to_set(
            user_id=user_id,
            name=pack_name,
            sticker=input_sticker
        )
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
                    sticker_format="static",
                    sticker_type=sticker_type,
                )
                await message.answer(f"Создал новый пак и добавил туда стикер!\nСсылка: https://t.me/addstickers/{pack_name}")
            except Exception as create_e:
                logging.error(f"Error creating sticker set: {create_e}")
                await message.answer(f"Не удалось создать пак: {create_e}")
        else:
            logging.error(f"Error adding sticker: {e}")
            await message.answer(f"Не удалось добавить стикер: {e}")


async def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found in .env file")
        return
    
    await init_db()
    print("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
