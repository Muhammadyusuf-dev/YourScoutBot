import asyncio
import datetime
import html
import logging
import os
from collections import deque
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ScoutBot")

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

# Configurations
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN .env faylida topilmadi! Iltimos, BotFather bergan tokenni kiriting.")

OWNER_ID_RAW = os.getenv("OWNER_ID", "").strip()
OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW.isdigit() else None

FORCE_DOCUMENT = os.getenv("FORCE_DOCUMENT", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

NOTIFY_ON_DELETE = os.getenv("NOTIFY_ON_DELETE", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@MuhammadyusufUS").strip()
CHANNEL_LINK = f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"


# Cache
MAX_SAVED_HISTORY = 3000
saved_message_ids = set()
saved_message_order = deque()
message_cache = {}  # msg_id -> info
business_connections = {}  # connection_id -> owner_user_id
detected_owner_id = OWNER_ID
bot_info = {}


class TelegramBotAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"
        self.session = None

    async def init_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def request(self, method: str, data: dict = None, files: dict = None):
        await self.init_session()
        url = f"{self.base_url}/{method}"

        try:
            if files:
                form_data = aiohttp.FormData()
                if data:
                    for k, v in data.items():
                        if v is not None:
                            form_data.add_field(k, str(v))
                for file_field, file_tuple in files.items():
                    filename, file_bytes, mime = file_tuple
                    form_data.add_field(
                        file_field,
                        file_bytes,
                        filename=filename,
                        content_type=mime,
                    )
                async with self.session.post(url, data=form_data) as resp:
                    return await resp.json()
            else:
                async with self.session.post(url, json=data or {}) as resp:
                    return await resp.json()
        except Exception as e:
            logger.error(f"API request error ({method}): {e}")
            return {"ok": False, "description": str(e)}

    async def get_me(self):
        return await self.request("getMe")

    async def get_updates(self, offset: int = None, timeout: int = 25):
        payload = {
            "timeout": timeout,
            "allowed_updates": [
                "message",
                "edited_message",
                "callback_query",
                "business_connection",
                "business_message",
                "edited_business_message",
                "deleted_business_messages",
            ],
        }
        if offset is not None:
            payload["offset"] = offset
        return await self.request("getUpdates", data=payload)

    async def get_file_path(self, file_id: str) -> str:
        res = await self.request("getFile", data={"file_id": file_id})
        if res.get("ok"):
            return res["result"].get("file_path")
        return None

    async def download_file_bytes(self, file_path: str) -> bytes:
        await self.init_session()
        url = f"{self.file_url}/{file_path}"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    logger.error(f"Faylni yuklab olishda server xatosi: status {resp.status}")
        except Exception as e:
            logger.error(f"Download error: {e}")
        return None

    async def get_chat_member(self, chat_id: str, user_id: int):
        return await self.request("getChatMember", data={"chat_id": chat_id, "user_id": user_id})

    async def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False):
        data = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            data["text"] = text
        return await self.request("answerCallbackQuery", data=data)

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML", reply_markup: dict = None):
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        return await self.request("sendMessage", data=data)

    async def send_photo(self, chat_id: int, photo_bytes, caption: str = None, parse_mode: str = "HTML"):
        files = {"photo": ("photo.jpg", photo_bytes, "image/jpeg")}
        data = {"chat_id": chat_id, "parse_mode": parse_mode}
        if caption:
            data["caption"] = caption[:1024]
        return await self.request("sendPhoto", data=data, files=files)

    async def send_video(self, chat_id: int, video_bytes, caption: str = None, parse_mode: str = "HTML"):
        files = {"video": ("video.mp4", video_bytes, "video/mp4")}
        data = {"chat_id": chat_id, "parse_mode": parse_mode}
        if caption:
            data["caption"] = caption[:1024]
        return await self.request("sendVideo", data=data, files=files)

    async def send_voice(self, chat_id: int, voice_bytes, caption: str = None, parse_mode: str = "HTML"):
        files = {"voice": ("voice.ogg", voice_bytes, "audio/ogg")}
        data = {"chat_id": chat_id, "parse_mode": parse_mode}
        if caption:
            data["caption"] = caption[:1024]
        return await self.request("sendVoice", data=data, files=files)

    async def send_video_note(self, chat_id: int, video_note_bytes):
        files = {"video_note": ("video_note.mp4", video_note_bytes, "video/mp4")}
        data = {"chat_id": chat_id}
        return await self.request("sendVideoNote", data=data, files=files)

    async def send_document(self, chat_id: int, doc_bytes, filename: str, caption: str = None, parse_mode: str = "HTML"):
        files = {"document": (filename, doc_bytes, "application/octet-stream")}
        data = {"chat_id": chat_id, "parse_mode": parse_mode}
        if caption:
            data["caption"] = caption[:1024]
        return await self.request("sendDocument", data=data, files=files)


bot = TelegramBotAPI(BOT_TOKEN)


def get_subscription_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "📢 Kanalga a'zo bo'lish", "url": CHANNEL_LINK}
            ],
            [
                {"text": "✅ A'zolikni tekshirish", "callback_data": "check_sub"}
            ]
        ]
    }


async def is_user_subscribed(user_id: int) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        res = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        if res.get("ok"):
            status = res["result"].get("status")
            if status in ["creator", "administrator", "member"]:
                return True
            if status == "restricted" and res["result"].get("is_member", True):
                return True
            return False
        else:
            logger.warning(f"⚠️ Kanal a'zoligini tekshirish xatosi ({REQUIRED_CHANNEL}): {res.get('description')}")
            return False
    except Exception as e:
        logger.error(f"Kanal a'zoligini tekshirishda xatolik: {e}")
        return False


async def send_subscription_warning(chat_id: int):
    text = (
        "⚠️ <b>Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'lishingiz shart!</b>\n\n"
        f"👉 <a href=\"{CHANNEL_LINK}\">Kanalimizga o'tish uchun bosing</a>\n\n"
        "Kanalga a'zo bo'lgach, quyidagi <b>«✅ A'zolikni tekshirish»</b> tugmasini bosing."
    )
    return await bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=get_subscription_keyboard()
    )


def format_sender(from_user: dict) -> str:
    if not isinstance(from_user, dict) or not from_user:
        return "Noma'lum foydalanuvchi"
    first_name = from_user.get("first_name", "")
    last_name = from_user.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() or "Foydalanuvchi"
    safe_name = html.escape(full_name)
    username = from_user.get("username")
    user_id = from_user.get("id")

    user_str = f" @{username}" if username else ""
    if user_id:
        return f'<a href="tg://user?id={user_id}">{safe_name}</a>{user_str} (<code>{user_id}</code>)'
    return f"{safe_name}{user_str}"


def build_caption(msg: dict) -> str:
    from_user = msg.get("from", {})
    sender_str = format_sender(from_user)
    date_ts = msg.get("date", 0)
    date_str = datetime.datetime.fromtimestamp(date_ts).strftime("%Y-%m-%d %H:%M:%S") if date_ts else ""

    lines = [
        "📸 <b>[Scout Bot - Saqlangan media]</b>",
        f"👤 <b>Asl yuboruvchi:</b> {sender_str}",
    ]
    if date_str:
        lines.append(f"🕒 <b>Vaqt:</b> <code>{date_str}</code>")

    original_text = msg.get("caption") or msg.get("text")
    if original_text and original_text.strip():
        safe_text = html.escape(original_text.strip())
        lines.append(f"\n📝 <b>Asl matn:</b>\n{safe_text}")

    return "\n".join(lines)


def extract_media_info(msg: dict):
    if not isinstance(msg, dict):
        return None

    # 1. Photo (including timed / view-once photos)
    if msg.get("photo"):
        photo_sizes = msg["photo"]
        if isinstance(photo_sizes, list) and photo_sizes:
            return ("photo", photo_sizes[-1]["file_id"], "photo.jpg")

    # 2. Video (including timed / view-once videos)
    if msg.get("video"):
        return ("video", msg["video"]["file_id"], "video.mp4")

    # 3. Voice
    if msg.get("voice"):
        return ("voice", msg["voice"]["file_id"], "voice.ogg")

    # 4. Video Note (Round video)
    if msg.get("video_note"):
        return ("video_note", msg["video_note"]["file_id"], "video_note.mp4")

    # 5. Document
    if msg.get("document"):
        doc = msg["document"]
        name = doc.get("file_name", "document.bin")
        return ("document", doc["file_id"], name)

    # 6. Animation (GIF)
    if msg.get("animation"):
        return ("animation", msg["animation"]["file_id"], "animation.mp4")

    # 7. Audio
    if msg.get("audio"):
        aud = msg["audio"]
        name = aud.get("file_name", "audio.mp3")
        return ("audio", aud["file_id"], name)

    # 8. Sticker
    if msg.get("sticker"):
        return ("sticker", msg["sticker"]["file_id"], "sticker.webp")

    # 9. Paid Media / Protected View-Once
    if msg.get("paid_media"):
        pm_items = msg["paid_media"].get("paid_media", [])
        if pm_items:
            first_item = pm_items[0]
            if first_item.get("photo"):
                return ("photo", first_item["photo"][-1]["file_id"], "photo.jpg")
            elif first_item.get("video"):
                return ("video", first_item["video"]["file_id"], "video.mp4")

    # 10. Story
    if msg.get("story"):
        story = msg["story"]
        if story.get("photo"):
            return ("photo", story["photo"][-1]["file_id"], "photo.jpg")
        elif story.get("video"):
            return ("video", story["video"]["file_id"], "video.mp4")

    # 11. Nested reply / quote
    if msg.get("reply_to_message") and isinstance(msg["reply_to_message"], dict):
        res = extract_media_info(msg["reply_to_message"])
        if res:
            return res

    # 12. Check any nested media with file_id
    for k, v in msg.items():
        if isinstance(v, dict) and "file_id" in v:
            return (k, v["file_id"], f"{k}.bin")

    return None


async def handle_reply_save(trigger_msg: dict, target_owner: int):
    chat_id = trigger_msg.get("chat", {}).get("id")
    reply_to = trigger_msg.get("reply_to_message")

    if not reply_to:
        logger.warning("⚠️ '🔥' yuborildi, lekin xabarga reply (javob) qilinmagan.")
        return

    reply_msg_id = reply_to.get("message_id")
    # Resolve message from memory cache or directly from reply_to
    target_msg = message_cache.get((chat_id, reply_msg_id)) or message_cache.get(reply_msg_id) or reply_to

    media_info = extract_media_info(target_msg) or extract_media_info(reply_to)

    if not media_info:
        logger.warning(f"⚠️ Reply qilingan xabarda media topilmadi: ID={reply_msg_id}")
        text_content = target_msg.get("text") or reply_to.get("text")
        if text_content:
            await bot.send_message(
                target_owner,
                f"📝 <b>[Saqlangan matnli xabar]</b>\n\n"
                f"👤 <b>Kimdan:</b> {format_sender(target_msg.get('from', {}))}\n\n"
                f"{html.escape(text_content)}"
            )
        return

    media_type, file_id, file_name = media_info
    file_path = await bot.get_file_path(file_id)
    if not file_path:
        logger.error(f"❌ Telegram serveridan file_path olinmadi (file_id: {file_id})")
        return

    ext = Path(file_path).suffix or Path(file_name).suffix or ".bin"
    output_filename = f"{media_type}_{reply_msg_id}{ext}"

    file_bytes = await bot.download_file_bytes(file_path)
    if not file_bytes:
        logger.error(f"❌ Faylni xotiraga (RAM) yuklab olishda xatolik: {file_path}")
        return

    caption = build_caption(target_msg)

    if FORCE_DOCUMENT or media_type in ["document", "sticker", "animation", "audio"]:
        res = await bot.send_document(target_owner, file_bytes, output_filename, caption=caption)
    elif media_type == "photo":
        res = await bot.send_photo(target_owner, file_bytes, caption=caption)
    elif media_type == "video":
        res = await bot.send_video(target_owner, file_bytes, caption=caption)
    elif media_type == "voice":
        res = await bot.send_voice(target_owner, file_bytes, caption=caption)
    elif media_type == "video_note":
        res = await bot.send_video_note(target_owner, file_bytes)
        await bot.send_message(target_owner, caption)
    else:
        res = await bot.send_document(target_owner, file_bytes, output_filename, caption=caption)

    # If sending failed (e.g. caption entity error), retry without caption
    if not res.get("ok"):
        logger.warning(f"⚠️ Caption bilan yuborishda xatolik ({res.get('description')}), captionsiz qayta yuborilmoqda...")
        if FORCE_DOCUMENT or media_type in ["document", "sticker", "animation", "audio"]:
            res = await bot.send_document(target_owner, file_bytes, output_filename)
        elif media_type == "photo":
            res = await bot.send_photo(target_owner, file_bytes)
        elif media_type == "video":
            res = await bot.send_video(target_owner, file_bytes)
        elif media_type == "voice":
            res = await bot.send_voice(target_owner, file_bytes)
        elif media_type == "video_note":
            res = await bot.send_video_note(target_owner, file_bytes)
        else:
            res = await bot.send_document(target_owner, file_bytes, output_filename)

    if res.get("ok"):
        logger.info(f"🔥 [Reply muvaffaqiyatli] {media_type.capitalize()} xotira (RAM) orqali to'g'ridan-to'g'ri botga yuborildi (Diskka saqlanmadi): {output_filename}")
    else:
        logger.error(f"❌ Egasiga yuborishda xatolik: {res.get('description')}")


async def process_update(update: dict):
    global detected_owner_id

    # 0. Callback Query (Subscription Verification)
    if "callback_query" in update:
        cq = update["callback_query"]
        cq_id = cq.get("id")
        user = cq.get("from", {})
        user_id = user.get("id")
        data = cq.get("data")
        msg = cq.get("message", {})
        chat_id = msg.get("chat", {}).get("id") or user_id

        if data == "check_sub":
            subscribed = await is_user_subscribed(user_id)
            if subscribed:
                await bot.answer_callback_query(cq_id, "✅ Rahmat! A'zoligingiz tasdiqlandi.", show_alert=True)
                detected_owner_id = user_id
                await bot.send_message(
                    chat_id,
                    "🎉 **A'zolik muvaffaqiyatli tasdiqlandi!**\n\n"
                    "Endi botdan to'liq foydalanishingiz mumkin.\n\n"
                    "🔥 Shaxsiy chatlaringizdagi xabarlarga javob (reply) qilib `🔥` yuborsangiz, "
                    "bot mediani sizga **o'chib ketmaydigan doimiy shaklda** tashlab beradi.",
                )
            else:
                await bot.answer_callback_query(
                    cq_id,
                    f"❌ Siz hali {REQUIRED_CHANNEL} kanaliga a'zo bo'lmadingiz! Iltimos, oldin kanalga a'zo bo'ling.",
                    show_alert=True
                )
        return

    # 1. Business Connection Update
    if "business_connection" in update:
        b_conn = update["business_connection"]
        conn_id = b_conn.get("id")
        user = b_conn.get("user", {})
        user_id = user.get("id")
        is_enabled = b_conn.get("is_enabled", False)

        if is_enabled:
            business_connections[conn_id] = user_id
            detected_owner_id = user_id
            logger.info(f"🔗 [Telegram Business] Chatbot ulandi! Egasi: {user.get('first_name')} (ID: {user_id})")
        else:
            business_connections.pop(conn_id, None)
            logger.info(f"🔌 [Telegram Business] Chatbot uzildi! ID: {conn_id}")

    # 2. Business Message Received
    elif "business_message" in update or "edited_business_message" in update:
        msg = update.get("business_message") or update.get("edited_business_message")
        conn_id = msg.get("business_connection_id")
        msg_id = msg.get("message_id")
        chat_id = msg.get("chat", {}).get("id")
        from_user = msg.get("from", {})
        text = (msg.get("text") or msg.get("caption") or "").strip()

        # Cache every message for reply lookups and delete tracking
        msg_key = (chat_id, msg_id)
        message_cache[msg_key] = msg
        message_cache[msg_id] = msg
        saved_message_order.append(msg_key)
        if len(saved_message_order) > MAX_SAVED_HISTORY:
            oldest = saved_message_order.popleft()
            message_cache.pop(oldest, None)

        target_owner = detected_owner_id or business_connections.get(conn_id) or OWNER_ID
        if not target_owner:
            logger.warning("⚠️ Bot egasi topilmadi! Iltimos, botingizga Telegram'dan /start bosing.")
            return

        # Check if user replied with 🔥 trigger
        if "🔥" in text or text == ".saveit":
            logger.info(f"🔥 [Chat Automation] '🔥' buyrug'i qabul qilindi! Kimdan: {from_user.get('first_name')}")
            
            # Channel subscription check
            if not await is_user_subscribed(target_owner):
                logger.warning(f"⚠️ Bot egasi {target_owner} {REQUIRED_CHANNEL} kanaliga a'zo emas!")
                await send_subscription_warning(target_owner)
                return

            try:
                await handle_reply_save(msg, target_owner)
            except Exception as e:
                logger.error(f"Reply saqlashda xatolik: {e}")
        else:
            # Automatic saving disabled - just caching
            media_info = extract_media_info(msg)
            media_label = f"Bor ({media_info[0]})" if media_info else "Yo`q"
            logger.info(f"📩 [Chat Automation] Xabar keshlandi (Reply '🔥' kutilmoqda): ID={msg_id}, Media={media_label}, Kimdan: {from_user.get('first_name')}")

    # 3. Deleted Business Messages (Anti-Delete & Timer expiration)
    elif "deleted_business_messages" in update:
        del_data = update["deleted_business_messages"]
        msg_ids = del_data.get("message_ids", [])
        conn_id = del_data.get("business_connection_id")

        target_owner = detected_owner_id or business_connections.get(conn_id) or OWNER_ID
        if not target_owner or not NOTIFY_ON_DELETE:
            return

        for mid in msg_ids:
            logger.info(f"🗑 [Chat Automation] Xabar o'chirildi: ID={mid}")
            cached = message_cache.get(mid)
            if cached:
                sender_str = format_sender(cached.get("sender", {}))
                cached_text = cached.get("text")
                text_info = f"\n📝 **O'chirilgan matn:** {cached_text}" if cached_text else ""

                try:
                    await bot.send_message(
                        target_owner,
                        f"🗑 <b>[Xabar o'chirildi / Taymer tugadi]</b>\n\n"
                        f"👤 <b>Yuboruvchi:</b> {sender_str}\n"
                        f"🆔 <b>Xabar ID:</b> <code>{mid}</code>{text_info}\n\n"
                        f"💡 <i>Yuboruvchi chatdagi xabarni o'chirdi (yoki taymer tugadi).</i>",
                    )
                except Exception as e:
                    logger.debug(f"Delete bildirishnomasi xatosi: {e}")

    # 4. Standard Direct Bot Messages (e.g. /start or direct media reply)
    elif "message" in update:
        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        from_user = msg.get("from", {})
        user_id = from_user.get("id") or chat_id
        text = (msg.get("text") or msg.get("caption") or "").strip()

        target_owner = detected_owner_id or OWNER_ID or chat_id

        # Mandatory channel subscription check
        if not await is_user_subscribed(user_id):
            await send_subscription_warning(chat_id)
            return

        if "🔥" in text or text == ".saveit":
            if msg.get("reply_to_message"):
                logger.info(f"🔥 [To'g'ridan-to'g'ri xabar] '🔥' reply buyrug'i qabul qilindi.")
                try:
                    await handle_reply_save(msg, target_owner)
                except Exception as e:
                    logger.error(f"Reply saqlashda xatolik: {e}")
            else:
                await bot.send_message(chat_id, "ℹ️ Rasm yoki videoga reply (javob) qilib <code>🔥</code> yuboring.")

        elif text.startswith("/start"):
            detected_owner_id = chat_id
            await bot.send_message(
                chat_id,
                "👋 <b>Salom! Men Scout Botman.</b>\n\n"
                f"✅ Siz bot egasi sifatida biriktirildingiz (ID: <code>{chat_id}</code>)!\n\n"
                "🔥 <b>Qanday ishlatiladi:</b>\n"
                "Shaxsiy chatlaringizga kelgan har qanday rasm, video yoki bir martalik mediani saqlash uchun "
                "o'sha xabarga <b>javob (reply) qilib <code>🔥</code> yuboring</b>!\n\n"
                "Bot darhol o'sha mediani xotiradan yuklab olib, sizga <b>o'chib ketmaydigan doimiy shaklda</b> tashlab beradi.",
            )
            logger.info(f"👤 Botga /start bosildi. Egasi ID: {chat_id}")

        elif text.startswith("/status"):
            await bot.send_message(
                chat_id,
                f"📊 <b>Scout Bot Holati:</b>\n\n"
                f"🤖 Bot: @{bot_info.get('username')}\n"
                f"👤 Egasi ID: <code>{detected_owner_id or OWNER_ID}</code>\n"
                f"📢 Majburiy kanal: <a href=\"{CHANNEL_LINK}\">{REQUIRED_CHANNEL}</a>\n"
                f"🔗 Faol ulanishlar soni: <code>{len(business_connections)}</code>\n"
                f"📁 Saqlangan kesh: <code>{len(message_cache)} ta xabar</code>\n"
                f"⚡️ Holat: <b>Faol (Online)</b>",
            )


async def main():
    global bot_info, detected_owner_id

    me_res = await bot.get_me()
    if not me_res.get("ok"):
        logger.error(f"Bot token noto'g'ri yoki Telegram serveriga ulanib bo'lmadi: {me_res}")
        return

    bot_info = me_res["result"]
    username = bot_info.get("username")
    bot_id = bot_info.get("id")

    logger.info("=" * 60)
    logger.info(f"🤖 Scout Bot ishga tushdi: @{username} (ID: {bot_id})")
    logger.info("📌 Chat Automation (Telegram Business) xabarlari kutilmoqda...")
    if OWNER_ID:
        logger.info(f"👤 Biriktirilgan bot egasi (OWNER_ID): {OWNER_ID}")
        detected_owner_id = OWNER_ID
        test_msg = await bot.send_message(OWNER_ID, "🚀 Scout Bot ishga tushdi va faol!")
        if not test_msg.get("ok"):
            logger.warning("!" * 60)
            logger.warning(f"⚠️ DIQQAT: Bot sizga (OWNER_ID: {OWNER_ID}) rasm/xabar yubora olmaydi!")
            logger.warning(f"❌ Sabab: {test_msg.get('description')}")
            logger.warning(f"👉 YECHIM: Telegram'da @{username} botiga kiring va /start tugmasini bosing!")
            logger.warning("!" * 60)
        else:
            logger.info("✅ Bot egasi bilan aloqa muvaffaqiyatli o'rnatildi!")
    else:
        logger.warning("⚠️ Diqqat: Bot egasini aniqlash uchun botingizga Telegram'dan /start bosing!")
    logger.info("⚙️ 100% Chat Automation rejimi faol!")
    logger.info("=" * 60)

    offset = None
    while True:
        try:
            updates_res = await bot.get_updates(offset=offset, timeout=25)
            if updates_res.get("ok"):
                updates = updates_res.get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    asyncio.create_task(process_update(update))
            else:
                logger.warning(f"getUpdates error: {updates_res}")
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Polling loop error: {e}")
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
