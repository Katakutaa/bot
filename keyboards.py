from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    buttons = [
        [KeyboardButton(text="🛒 Buyurtma berish")],
        [KeyboardButton(text="📋 Buyurtma tarixi")],
        [KeyboardButton(text="❓ Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_menu_keyboard():
    buttons = [
        [KeyboardButton(text="📋 Kutilayotgan buyurtmalar")],
        [KeyboardButton(text="✅ Buyurtmani tasdiqlash")],
        [KeyboardButton(text="📤 Hujjat yuklash")],
        [KeyboardButton(text="❌ Buyurtmani rad etish")],
        [KeyboardButton(text="🏠 Asosiy menyu")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def back_menu_keyboard():
    buttons = [[KeyboardButton(text="🏠 Asosiy menyu")]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def order_confirm_keyboard(order_id: int):
    buttons = [
        [InlineKeyboardButton(text="✅ Ha, roziman", callback_data=f"confirm_{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_order_action_keyboard(order_id: int):
    buttons = [
        [InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"admin_approve_{order_id}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_reject_{order_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)