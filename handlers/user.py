import logging

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from config import ADMIN_IDS, CARD_NUMBER
from utils import escape_md_v2
from database import (
    add_user, update_user_info, create_order, get_user_orders,
    update_order_payment, get_order_by_id
)
from keyboards import main_menu_keyboard, order_confirm_keyboard, back_menu_keyboard
from states import OrderState
from utils import format_invoice, format_order_history, send_order_to_channel, is_admin

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    await message.answer(
        "👋 **Assalomu alaykum!**\n\n"
        "📚 **Bot vazifasi:**\n"
        "Siz malaka talabi faylini yuklaysiz, men esa unga asosan o'quv reja tuzib beraman.\n\n"
        f"💰 **Narx:** {900000:,} so'm\n\n"
        "🛒 Buyurtma berish uchun quyidagi tugmalardan foydalaning.",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(F.text == "🛒 Buyurtma berish")
async def start_order(message: Message, state: FSMContext):
    await state.set_state(OrderState.waiting_for_direction)
    await message.answer(
        "📌 **Qaysi yo'nalish uchun o'quv reja kerak?**\n\n"
        "Masalan: *Kompyuter injiniringi*, *Pedagogika*, *Iqtisodiyot*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_menu_keyboard()
    )

@router.message(OrderState.waiting_for_direction)
async def get_direction(message: Message, state: FSMContext):
    if message.text == "🏠 Asosiy menyu":
        await state.clear()
        await message.answer("Asosiy menyu", reply_markup=main_menu_keyboard())
        return
    
    await state.update_data(direction=message.text)
    await state.set_state(OrderState.waiting_for_requirement_file)
    await message.answer(
        "📎 **Malaka talabi faylini yuklang** (PDF, DOC, DOCX formatda)\n\n"
        "Faylni shu yerga jo'nating.",
        reply_markup=back_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(OrderState.waiting_for_requirement_file, F.document)
async def get_requirement_file(message: Message, state: FSMContext):
    if message.text == "🏠 Asosiy menyu":
        await state.clear()
        await message.answer("Asosiy menyu", reply_markup=main_menu_keyboard())
        return
    
    data = await state.get_data()
    direction = data.get('direction')
    
    order_id = create_order(message.from_user.id, direction, message.document.file_id)
    await state.update_data(order_id=order_id)
    
    invoice_text = format_invoice(direction, order_id)
    
    await message.answer(
        invoice_text + "\n\n🛒 **Buyurtmani tasdiqlaysizmi?**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=order_confirm_keyboard(order_id)
    )

@router.message(OrderState.waiting_for_requirement_file)
async def invalid_file(message: Message):
    await message.answer(
        "❌ Iltimos, **fayl** yuboring (PDF, DOC, DOCX formatda).",
        reply_markup=back_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(OrderState.waiting_for_screenshot)
    
    await callback.message.edit_text(
        f"✅ **Buyurtma #{order_id} qabul qilindi!**\n\n"
        f"💳 **Karta raqami:** `{CARD_NUMBER}`\n\n"
        f"📸 **To'lov skrinshotini yuboring.**\n\n"
        f"To'lovni amalga oshirgandan so'ng, skrinshotni shu yerga jo'nating.",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
    await callback.message.answer("Asosiy menyu", reply_markup=main_menu_keyboard())
    await callback.answer()

@router.message(OrderState.waiting_for_screenshot, F.photo)
async def get_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id')
    logger = logging.getLogger(__name__)
    file_id = message.photo[-1].file_id
    if not order_id:
        logger.warning("No order_id in state when receiving screenshot (photo) from %s", message.from_user.id)
        await message.answer("❌ Buyurtma topilmadi. Iltimos, buyurtma berishdan boshlang.", reply_markup=main_menu_keyboard())
        return
    logger.info("Received screenshot (photo) for order %s: %s", order_id, file_id)

    try:
        update_order_payment(order_id, file_id)
    except Exception as e:
        logger.exception("Failed to update order payment for %s: %s", order_id, e)
        await message.answer("❌ Server xatosi. Iltimos, keyinroq qayta urinib ko'ring.")
        return

    order = get_order_by_id(order_id)
    username = message.from_user.username or message.from_user.full_name
    # prepare safe strings for Markdown
    display_username = f"@{username}" if username and not str(username).startswith("@") else (username or str(message.from_user.id))
    safe_username = escape_md_v2(display_username)
    safe_direction = escape_md_v2(order.get('direction') or '')

    # Kanalga yuborish
    await send_order_to_channel(message.bot, order, "new", username)

    # Adminlarga xabar
    for admin_id in ADMIN_IDS:
            # send plain-text admin notification (avoid Markdown parsing issues)
            await message.bot.send_message(
                admin_id,
                f"🆕 Yangi buyurtma!\n"
                f"ID: #{order_id}\n"
                f"Foydalanuvchi: {display_username}\n"
                f"Yo'nalish: {order.get('direction')}\n\n"
                f"✅ Kanalga ham yuborildi.",
                reply_markup=main_menu_keyboard()
            )

    await state.clear()
    await message.answer(
        f"✅ **To'lov skrinshoti qabul qilindi!**\n\n"
        f"Buyurtma #{order_id} qabul qilindi.\n"
        f"Natija haqida xabar beramiz.",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(OrderState.waiting_for_screenshot)
async def invalid_screenshot(message: Message):
    await message.answer(
        "❌ Iltimos, **rasm (skrinshot)** yoki rasm fayli (JPEG/PNG) yuboring.",
        reply_markup=back_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


@router.message(OrderState.waiting_for_screenshot, F.document)
async def get_screenshot_document(message: Message, state: FSMContext):
    """Accept screenshots sent as documents (some clients send images as documents)."""
    logger = logging.getLogger(__name__)
    data = await state.get_data()
    order_id = data.get('order_id')
    if not order_id:
        logger = logging.getLogger(__name__)
        logger.warning("No order_id in state when receiving screenshot (document) from %s", message.from_user.id)
        await message.answer("❌ Buyurtma topilmadi. Iltimos, buyurtma berishdan boshlang.", reply_markup=main_menu_keyboard())
        return

    doc = message.document
    # Accept only image-like documents
    mime = getattr(doc, 'mime_type', '') or ''
    filename = getattr(doc, 'file_name', '') or ''
    if not (mime.startswith('image/') or filename.lower().endswith(('.png', '.jpg', '.jpeg'))):
        await message.answer("❌ Iltimos, rasm (JPEG/PNG) yuboring.", reply_markup=back_menu_keyboard())
        return

    file_id = doc.file_id
    logger.info("Received screenshot (document) for order %s: %s (mime=%s, name=%s)", order_id, file_id, mime, filename)

    try:
        update_order_payment(order_id, file_id)
    except Exception as e:
        logger.exception("Failed to update order payment for %s: %s", order_id, e)
        await message.answer("❌ Server xatosi. Iltimos, keyinroq qayta urinib ko'ring.")
        return

    order = get_order_by_id(order_id)
    username = message.from_user.username or message.from_user.full_name
    display_username = f"@{username}" if username and not str(username).startswith("@") else (username or str(message.from_user.id))
    safe_username = escape_md_v2(display_username)
    safe_direction = escape_md_v2(order.get('direction') or '')

    # Kanalga yuborish
    await send_order_to_channel(message.bot, order, "new", username)

    # Adminlarga xabar
    for admin_id in ADMIN_IDS:
            # send plain-text admin notification (avoid Markdown parsing issues)
            await message.bot.send_message(
                admin_id,
                f"🆕 Yangi buyurtma!\n"
                f"ID: #{order_id}\n"
                f"Foydalanuvchi: {display_username}\n"
                f"Yo'nalish: {order.get('direction')}\n\n"
                f"✅ Kanalga ham yuborildi.",
                reply_markup=main_menu_keyboard()
            )

    await state.clear()
    await message.answer(
        f"✅ **To'lov skrinshoti qabul qilindi!**\n\n"
        f"Buyurtma #{order_id} qabul qilindi.\n"
        f"Natija haqida xabar beramiz.",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(F.text == "📋 Buyurtma tarixi")
async def order_history(message: Message):
    orders = get_user_orders(message.from_user.id)
    history_text = format_order_history(orders)
    await message.answer(history_text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard())

@router.message(F.text == "❓ Yordam")
async def help_command(message: Message):
    help_text = """
❓ **Yordam**

**Botdan foydalanish tartibi:**

1️⃣ "Buyurtma berish" tugmasini bosing
2️⃣ Yo'nalish nomini yozing
3️⃣ Malaka talabi faylini yuklang
4️⃣ To'lov qiling va skrinshotni yuboring
5️⃣ Admin tekshirgandan so'ng, o'quv reja tayyorlanadi

📞 **Muammo bo'lsa:** Admin bilan bog'lanishingiz mumkin.
"""
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard())

@router.message(F.text == "🏠 Asosiy menyu")
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu", reply_markup=main_menu_keyboard())