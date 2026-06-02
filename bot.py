from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import sqlite3

import time
# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    file_id TEXT,
    type TEXT
)
""")

conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT,
    expire_time INTEGER
)
""")
conn.commit()

# ================= CONFIG =================
TOKEN = "8913519612:AAGwQY8FDd9uzYAazdKizk9POtXhZgpjW14"
CHANNEL_1 = -1003967540137
CHANNEL_2 = -1004293009722
CHANNEL_LINK_1 = "https://t.me/+XXXXXXX1"
CHANNEL_LINK_2 = "https://t.me/+XXXXXXX2"
# ==========================================


async def check_membership(bot, user_id):

    channels = await get_active_channels()

    if not channels:
        return True

    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, user_id)

            print(f"CHECK {channel} -> {member.status}")

            if member.status not in ["member", "administrator", "creator"]:
                return False

        except Exception as e:
            print(f"SKIP CHANNEL ERROR {channel}: {e}")
            continue  # 👈 مهم

    return True


import time

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT chat_id, expire_time FROM channels")
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("❌ هیچ کانالی ثبت نشده")
        return

    text = "📢 لیست کانال‌ها:\n\n"

    for chat_id, expire in rows:
        text += f"{chat_id} | expire: {expire}\n"

    await update.message.reply_text(text)


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 2:
        await update.message.reply_text("استفاده: /addchannel id 24")
        return

    chat_id = context.args[0]
    hours = int(context.args[1])

    expire = int(time.time()) + hours * 3600

    cursor.execute(
        "INSERT INTO channels (chat_id, expire_time) VALUES (?, ?)",
        (chat_id, expire)
    )
    conn.commit()

    await update.message.reply_text("✅ کانال اضافه شد")


async def get_active_channels():
    now = int(time.time())

    cursor.execute(
        "SELECT chat_id FROM channels WHERE expire_time > ?",
        (now,)
    )

    return [row[0] for row in cursor.fetchall()]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text or ""
    parts = text.split()

    # 🔥 اگر لینک یا /start با دسته بود
    if len(parts) > 1:
        category = parts[1].strip()
        await send_category(update, context, category)
        return

    # 🎛 منوی اصلی
    keyboard = [
        [
            InlineKeyboardButton("📷 تصاویر", callback_data="photos"),
            InlineKeyboardButton("🎥 ویدیو", callback_data="video")
        ],
        [
            InlineKeyboardButton("📢 عضویت در کانال‌ها", callback_data="join"),
            InlineKeyboardButton("✅ بررسی عضویت", callback_data="check")
        ]
    ]

    await update.message.reply_text(
        "🎬 خوش اومدی!\n\nیکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "photos":
        await query.message.reply_text("📷 برای دیدن دسته‌ها /start دسته_اسم بزن")

    elif query.data == "video":
        await query.message.reply_text("🎥 فعلاً ویدیو آماده نیست 😎")

    elif query.data == "join":
        keyboard = [[
            InlineKeyboardButton("🔥 کانال فیلم", url=CHANNEL_LINK_1),
            InlineKeyboardButton("🎬 کانال VIP", url=CHANNEL_LINK_2)
        ]]

        await query.message.reply_text(
            "📢 برای دسترسی عضو شوید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "check":
        user_id = query.from_user.id

        try:
            m1 = await context.bot.get_chat_member(CHANNEL_1, user_id)
            m2 = await context.bot.get_chat_member(CHANNEL_2, user_id)

            ok1 = m1.status in ["member", "administrator", "creator"]
            ok2 = m2.status in ["member", "administrator", "creator"]

            if ok1 and ok2:
                await query.message.reply_text("✅ تایید شد")
            else:
                await query.message.reply_text("❌ عضو کانال‌ها نیستی")

        except Exception as e:
            await query.message.reply_text(f"⚠️ خطا:\n{e}")


async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("استفاده: /set ana_photos")
        return

    context.user_data["category"] = context.args[0]

    await update.message.reply_text(
        f"✅ دسته فعال شد: {context.user_data['category']}\n\nحالا عکس یا ویدیو بفرست"
    )


async def send_category(update, context, category):

    cursor.execute(
        "SELECT file_id, type FROM media WHERE category=?",
        (category,)
    )

    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("❌ چیزی پیدا نشد")
        return

    media_group = []

    for file_id, media_type in rows:

        if media_type == "photo":
            media_group.append(InputMediaPhoto(file_id))

        elif media_type == "video":
            media_group.append(InputMediaVideo(file_id))

    await context.bot.send_media_group(
        chat_id=update.effective_chat.id,
        media=media_group
    )

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("استفاده: /removechannel id")
        return

    chat_id = context.args[0]

    cursor.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
    conn.commit()

    await update.message.reply_text("🗑 کانال حذف شد")


async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):

    category = context.user_data.get("category")

    if not category:
        await update.message.reply_text("❗️ اول /set بزن و دسته انتخاب کن")
        return

    if update.message.photo:

        file_id = update.message.photo[-1].file_id

        cursor.execute(
            "INSERT INTO media (category, file_id, type) VALUES (?, ?, ?)",
            (category, file_id, "photo")
        )
        conn.commit()

        await update.message.reply_text("✅ عکس ذخیره شد")

    elif update.message.video:

        file_id = update.message.video.file_id

        cursor.execute(
            "INSERT INTO media (category, file_id, type) VALUES (?, ?, ?)",
            (category, file_id, "video")
        )
        conn.commit()

        await update.message.reply_text("✅ ویدیو ذخیره شد")


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("set", set_category))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, save_media))
app.add_handler(CommandHandler("addchannel", add_channel))
app.add_handler(CommandHandler("listchannels", list_channels))
app.add_handler(CommandHandler("removechannel", remove_channel))
app.run_polling()
