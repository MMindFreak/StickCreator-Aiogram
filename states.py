from aiogram.fsm.state import State, StatesGroup

class StickerStates(StatesGroup):
    waiting_for_pack_title = State()
    waiting_for_pack_type = State()
