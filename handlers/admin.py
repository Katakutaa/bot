from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from database import (
    get_pending_orders, update_order_status, get_order_by_id,
    update_order_completed, get_user_by_telegram_id
)
from keyboards import admin_menu_keyboard, admin_order_action_keyboard, main_menu_keyboard
from states import AdminState
from utils import send_order_to_channel, is_admin

router = Router()

@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin emassiz!")
        return
    
    await message.answer(
        "👨‍💼 **Admin panel**\n\nQuyidagi tugmalardan foydalaning:",
        reply_markup=admin_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@router.message(F.text == "📋 Kutilayotgan buyurtmalar")
async def show_pending_orders(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    orders = get_pending_orders()
    if not orders:
        await message.answer("📭 Hozircha kutilayotgan buyurtmalar yo'q.", reply_markup=admin_menu_keyboard())
        return
    
    for order in orders:
        # send plain-text admin listing to avoid Markdown parsing issues with user-provided fields
        text = (
            f"🆔 Buyurtma ID: #{order['order_id']}\n"
            f"👤 Foydalanuvchi ID: {order['telegram_id']}\n"
            f"📌 Yo'nalish: {order.get('direction')}\n"
            f"📊 Holat: {order.get('status')}\n"
            f"📅 Sana: {order.get('created_at')[:16]}"
        )
        await message.answer(text, reply_markup=admin_order_action_keyboard(order['order_id']))

@router.callback_query(F.data.startswith("admin_approve_"))
async def approve_order(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    update_order_status(order_id, "accepted")
    
    order = get_order_by_id(order_id)
    if order:
        await callback.bot.send_message(
            order['telegram_id'],
            f"✅ Buyurtma #{order_id} tasdiqlandi!\n\nO'quv reja tayyorlanmoqda."
        )
    
    await callback.message.edit_text(f"✅ Buyurtma #{order_id} qabul qilindi.")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_reject_"))
async def reject_order_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    await state.update_data(reject_order_id=order_id)
    await state.set_state(AdminState.waiting_for_reject_reason)
    
    await callback.message.answer(f"❌ Buyurtma #{order_id} rad etilmoqda.\nSababini yozing:")
    await callback.answer()


@router.message(AdminState.waiting_for_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    """Handle a plain-text reject reason after admin pressed reject on a specific order."""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    order_id = data.get('reject_order_id')
    if not order_id:
        await message.answer("❌ Buyurtma topilmadi.")
        await state.clear()
        return

    reason = message.text.strip() if message.text else "Sabab ko'rsatilmagan"

    update_order_status(order_id, "rejected", reason)

    order = get_order_by_id(order_id)
    if order:
        await message.bot.send_message(
            order['telegram_id'],
            f"❌ Buyurtma #{order_id} rad etildi\n\nSabab: {reason}\n\nQayta buyurtma berishingiz mumkin."
        )

    await message.answer(f"✅ Buyurtma #{order_id} rad etildi.", reply_markup=admin_menu_keyboard())
    await state.clear()

@router.message(F.text == "✅ Buyurtmani tasdiqlash")
async def ask_order_id_to_approve(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminState.waiting_for_order_id_to_approve)
    await message.answer("📝 Tasdiqlash uchun **buyurtma ID** raqamini yuboring:", reply_markup=admin_menu_keyboard())

@router.message(AdminState.waiting_for_order_id_to_approve)
async def process_approve_by_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        order_id = int(message.text.strip())
    except:
        await message.answer("❌ Iltimos, to'g'ri raqam yuboring.")
        return
    
    order = get_order_by_id(order_id)
    if not order:
        await message.answer("❌ Bunday buyurtma topilmadi.")
        await state.clear()
        return
    
    update_order_status(order_id, "accepted")
    
    await message.bot.send_message(
        order['telegram_id'],
        f"✅ **Buyurtma #{order_id} tasdiqlandi!**\n\nO'quv reja tayyorlanmoqda.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await message.answer(f"✅ Buyurtma #{order_id} tasdiqlandi.", reply_markup=admin_menu_keyboard())
    await state.clear()

@router.message(F.text == "📤 Hujjat yuklash")
async def ask_order_id_for_upload(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminState.waiting_for_order_id_for_upload)
    await message.answer("📝 **Hujjat yuklash uchun buyurtma ID ni yuboring:**", parse_mode=ParseMode.MARKDOWN)

@router.message(AdminState.waiting_for_order_id_for_upload)
async def get_order_id_for_upload(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        order_id = int(message.text.strip())
    except:
        await message.answer("❌ Iltimos, to'g'ri raqam yuboring.")
        return
    
    order = get_order_by_id(order_id)
    if not order:
        await message.answer("❌ Bunday buyurtma topilmadi.")
        await state.clear()
        return
    
    await state.update_data(upload_order_id=order_id)
    await state.set_state(AdminState.waiting_for_completed_file)
    
    await message.answer(
        f"📎 Buyurtma #{order_id} uchun tayyor o'quv reja faylini yuklang:\n\nYo'nalish: {order.get('direction')}"
    )

@router.message(AdminState.waiting_for_completed_file, F.document)
async def upload_completed_file(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    order_id = data.get('upload_order_id')
    file_id = message.document.file_id
    
    update_order_completed(order_id, file_id)
    
    order = get_order_by_id(order_id)
    
    if order:
        # Username ni olish
        user = get_user_by_telegram_id(order['telegram_id'])
        username = user.get('username') or user.get('full_name') or str(order['telegram_id'])
        
        # Kanalga yuborish
        await send_order_to_channel(message.bot, order, "completed", username)
        
        # Foydalanuvchiga yuborish
        await message.bot.send_document(
            order['telegram_id'],
            file_id,
            caption=(
                f"✅ Buyurtma #{order_id} tayyor!\n\n"
                f"📌 Yo'nalish: {order.get('direction')}\n"
                f"📅 Tayyorlangan vaqt: {order.get('completed_date')[:19]}\n\n"
                f"Rahmat!"
            )
        )
    
    await message.answer(
        f"✅ Hujjat #{order_id} buyurtmaga yuklandi.\n"
        f"✅ Foydalanuvchiga yuborildi.\n"
        f"✅ Kanalga yuborildi.",
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()

@router.message(AdminState.waiting_for_completed_file)
async def invalid_file_admin(message: Message):
    await message.answer("❌ Iltimos, **fayl** (PDF/DOC/DOCX) yuboring.")

@router.message(F.text == "❌ Buyurtmani rad etish")
async def ask_order_id_to_reject(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await state.set_state(AdminState.waiting_for_order_id_to_reject)
    await message.answer(
        "❌ Rad etish uchun buyurtma ID va sababini yuboring:\n\nFormat: ID|Sabab\nMasalan: 123|Noto'g'ri fayl"
    )

@router.message(AdminState.waiting_for_order_id_to_reject)
async def process_reject_by_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split("|", 1)
        order_id = int(parts[0].strip())
        reason = parts[1].strip() if len(parts) > 1 else "Sabab ko'rsatilmagan"
    except:
        await message.answer("❌ Noto'g'ri format. Qaytadan yuboring:\n`123|Sabab matni`", parse_mode=ParseMode.MARKDOWN)
        return
    
    order = get_order_by_id(order_id)
    if not order:
        await message.answer("❌ Bunday buyurtma topilmadi.")
        await state.clear()
        return
    
    update_order_status(order_id, "rejected", reason)
    
    await message.bot.send_message(
        order['telegram_id'],
        f"❌ Buyurtma #{order_id} rad etildi\n\nSabab: {reason}\n\nQayta buyurtma berishingiz mumkin."
    )
    
    await message.answer(f"✅ Buyurtma #{order_id} rad etildi.", reply_markup=admin_menu_keyboard())
    await state.clear()

@router.message(F.text == "🏠 Asosiy menyu")
async def admin_back_to_menu(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Asosiy menyu", reply_markup=main_menu_keyboard())
        return
    
    await state.clear()
    await message.answer("Admin panel", reply_markup=admin_menu_keyboard())