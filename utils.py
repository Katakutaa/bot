from aiogram.types import InputMediaDocument, InputMediaPhoto
from config import PRICE, CARD_NUMBER
from datetime import datetime
import html


def escape_md_v2(text: str) -> str:
    """Escape text for Telegram MarkdownV2 formatting.

    Prefixes special MarkdownV2 characters with a backslash so Telegram won't
    treat user-provided text as markup.
    """
    if text is None:
        return ""
    specials = r"_\*\[\]()~`>#+\-=|{}.!"
    escaped_chars = []
    for ch in str(text):
        if ch in specials:
            escaped_chars.append("\\" + ch)
        else:
            escaped_chars.append(ch)
    return "".join(escaped_chars)


def escape_html(text: str) -> str:
    """Escape text for HTML parse mode in Telegram messages."""
    if text is None:
        return ""
    return html.escape(str(text))

def format_invoice(direction: str, order_id: int) -> str:
    return f"""
🧾 **INVOYoS** #{order_id}

📌 **Yo'nalish:** {direction}
💰 **Summa:** {PRICE:,} so'm

**Xizmat tarkibi:**
• Malaka talabi asosida o'quv reja tuzish
• Kunduzgi/masofaviy ta'lim shakli uchun
• Bir dona o'quv reja

📅 **Muddati:** 3-5 ish kuni

💳 **To'lov kartasi:** `{CARD_NUMBER}`

━━━━━━━━━━━━━━━━━━━━━
To'lovni amalga oshirgach, skrinshotni yuboring.
"""

def format_order_history(orders: list) -> str:
    if not orders:
        return "📭 Sizning buyurtmalaringiz topilmadi."
    
    result = "📋 **Buyurtma tarixi:**\n\n"
    for order in orders:
        status_text = {
            "pending": "⏳ Kutilmoqda",
            "pending_payment": "💳 To'lov kutilmoqda",
            "accepted": "✅ Qabul qilingan",
            "completed": "📄 Bajarilgan",
            "rejected": "❌ Rad etilgan"
        }.get(order['status'], order['status'])
        
        result += f"**#{order['order_id']}** - {order['direction']}\n"
        result += f"📊 {status_text}\n"
        result += f"📅 {order['created_at'][:16]}\n"
        
        if order['status'] == 'completed' and order['completed_file_id']:
            result += f"📎 Hujjat tayyor\n"
        elif order['status'] == 'rejected' and order.get('admin_note'):
            result += f"ℹ️ Izoh: {order['admin_note']}\n"
        
        result += "\n"
    
    return result

def format_new_order_for_channel(order: dict, username: str) -> dict:
    # Use HTML formatting for channel captions and escape dynamic content
    safe_username = escape_html(username or str(order.get('telegram_id')))
    safe_direction = escape_html(order.get('direction') or '')

    caption = f"""
<b>🆕 YANGI BUYURTMA</b> #{order['order_id']}

👤 <b>Foydalanuvchi:</b> {safe_username}
🆔 <b>User ID:</b> {order['telegram_id']}
📌 <b>Yo'nalish:</b> {safe_direction}
💰 <b>Summa:</b> {PRICE:,} so'm

📅 <b>Buyurtma vaqti:</b> {order['created_at'][:19]}

━━━━━━━━━━━━━━━━━━━━━
📎 <b>Malaka talabi fayli</b> (quyida)
💳 <b>To'lov skrinshoti</b> (quyida)
"""
    return {"caption": caption, "need_media_group": True}

def format_completed_order_for_channel(order: dict, username: str) -> dict:
    # Use HTML formatting for channel captions and escape dynamic content
    payment_date = order.get('payment_date', '')
    completed_date = order.get('completed_date', '')
    safe_username = escape_html(username or str(order.get('telegram_id')))
    safe_direction = escape_html(order.get('direction') or '')

    caption = f"""
<b>✅ BUYURTMA BAJARILDI</b> #{order['order_id']}

👤 <b>Foydalanuvchi:</b> {safe_username}
🆔 <b>User ID:</b> {order['telegram_id']}
📌 <b>Yo'nalish:</b> {safe_direction}
💰 <b>Summa:</b> {PRICE:,} so'm

📅 <b>Buyurtma:</b> {order['created_at'][:19]}
📅 <b>To'lov:</b> {payment_date[:19] if payment_date else 'Noma\'lum'}
📅 <b>Tayyorlangan:</b> {completed_date[:19] if completed_date else 'Noma\'lum'}

━━━━━━━━━━━━━━━━━━━━━
📚 <b>Tayyor o'quv reja</b> (quyida)
"""
    return {"caption": caption, "need_media_group": False}


def build_file_caption(order: dict, username: str, label: str = None) -> str:
    """Build an HTML-escaped caption for a file containing order id and user info.

    label: optional short label for the file, e.g. 'Malaka talabi fayli' or 'To'lov skrinshoti'
    """
    safe_user = escape_html(username or str(order.get('telegram_id')))
    order_id = order.get('order_id')
    parts = []
    if label:
        parts.append(f"<b>{escape_html(label)}</b>")
    parts.append(f"<b>Buyurtma:</b> #{order_id}")
    parts.append(f"<b>Foydalanuvchi:</b> {safe_user}")
    return "\n".join(parts)

async def send_order_to_channel(bot, order: dict, order_type: str, username: str):
    from config import CHANNEL_ID
    
    if not CHANNEL_ID:
        return
    
    try:
        if order_type == "new":
            data = format_new_order_for_channel(order, username)

            req = order.get('requirement_file_id')
            pay = order.get('payment_screenshot_id')

            caption = data.get('caption')
            # send summary caption (HTML) first; log its repr to help debugging parsing issues
            if caption:
                try:
                    await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="HTML")
                except Exception as exc:
                    print("Kanalga caption yuborishda xatolik:")
                    print(repr(caption))
                    raise

            # Build per-file captions and send files with their own captions
            if req:
                try:
                    file_caption = build_file_caption(order, username, label="Malaka talabi fayli")
                    await bot.send_document(chat_id=CHANNEL_ID, document=req, caption=file_caption, parse_mode="HTML")
                except Exception as exc:
                    print("Kanalga document yuborishda xatolik:", exc)
                    raise

            if pay:
                try:
                    file_caption = build_file_caption(order, username, label="To'lov skrinshoti")
                    await bot.send_photo(chat_id=CHANNEL_ID, photo=pay, caption=file_caption, parse_mode="HTML")
                except Exception as exc:
                    print("Kanalga photo yuborishda xatolik:", exc)
                    raise

        elif order_type == "completed":
            data = format_completed_order_for_channel(order, username)
            caption = data.get('caption')
            if order.get('completed_file_id'):
                try:
                    await bot.send_document(
                        chat_id=CHANNEL_ID,
                        document=order['completed_file_id'],
                        caption=caption,
                        parse_mode="HTML"
                    )
                except Exception as exc:
                    print("Kanalga completed document yuborishda xatolik:")
                    print(repr(caption))
                    raise
            else:
                try:
                    await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="HTML")
                except Exception as exc:
                    print("Kanalga caption yuborishda xatolik:")
                    print(repr(caption))
                    raise
    except Exception as e:
        # Final catch — keep previous behavior of printing an error for visibility
        print(f"Kanalga xabar yuborishda xatolik: {e}")
        # re-raise so upstream handlers see the error if needed
        raise

def is_admin(user_id: int) -> bool:
    from config import ADMIN_IDS
    return user_id in ADMIN_IDS