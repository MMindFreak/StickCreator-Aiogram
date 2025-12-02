from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
        
    buttons.append([InlineKeyboardButton(text="📊 Статистика", callback_data="stats")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_pack_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Обычные стикеры", callback_data="type_regular")],
        [InlineKeyboardButton(text="😀 Эмодзи пак", callback_data="type_custom_emoji")]
    ])

    ])

def get_delete_sticker_keyboard(file_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"del_sticker_{file_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")]
    ])

def get_subscription_keyboard(channel_url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Подписаться на канал", url=channel_url)],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])
