from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import os
import sqlite3
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    file_id TEXT
)
""")

conn.commit()
# ================= CONFIG =================
TOKEN = "8913519612:AAGwQY8FDd9uzYAazdKizk9POtXhZgpjW14"
CHANNEL_1 = -1003967540137
CHANNEL_2 = -1004293009722
CHANNEL_LINK_1 = "https://t.me/+XXXXXXX1"
CHANNEL_LINK_2 = "https://t.me/+XXXXXXX2"
# =========================================


# 🚀 START (deep link support)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # اگر از کانال اومده (مثلا ana_photos)
    if context.args:
        category = context.args[0]
        await send_category(update, context, category)
        return

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

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎬 خوش اومدی!\n\nیکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=reply_markup
    )


# 🎛 BUTTON HANDLER
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "photos":
        await query.message.reply_text("📷 برای دیدن دسته‌ها /start دسته_اسم بزن")

    elif query.data == "video":
        await query.message.reply_text("🎥 فعلاً ویدیو آماده نیست 😎")

    elif query.data == "join":
        keyboard = [
            [
                InlineKeyboardButton("🔥 کانال فیلم", url=CHANNEL_LINK_1),
                InlineKeyboardButton("🎬 کانال VIP", url=CHANNEL_LINK_2)
            ]
        ]
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


# 🟢 SET CATEGORY (اصلاح شده)
async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استفاده: /set ana_photos")
        return

    context.user_data["category"] = context.args[0]

    await update.message.reply_text(
        f"✅ دسته فعال شد: {context.user_data['category']}\n\n"
        "حالا عکس بفرست"
    )


# 📸 SAVE MEDIA (اصلاح شده + واقعی)
import os

async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):

    category = context.user_data.get("category")

    if not category:
        await update.message.reply_text("❗️ اول /set بزن و دسته انتخاب کن")
        return

    # PHOTO
    if update.message.photo:
        file = await context.bot.get_file(update.message.photo[-1].file_id)

        path = f"photos/{category}"
        os.makedirs(path, exist_ok=True)

        file_path = f"{path}/{update.message.photo[-1].file_id}.jpg"
        await file.download_to_drive(file_path)

        await update.message.reply_text("✅ عکس ذخیره شد")

async def send_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category):

    path = f"photos/{category}"

    if not os.path.exists(path):
        await update.message.reply_text("❌ چیزی پیدا نشد")
        return

    files = os.listdir(path)

    if not files:
        await update.message.reply_text("❌ این دسته خالیه")
        return

    media = []

    for f in files[:10]:
        file_path = os.path.join(path, f)
        media.append(InputMediaPhoto(open(file_path, "rb")))

    await context.bot.send_media_group(
        chat_id=update.effective_chat.id,
        media=media
    )

# 🚀 RUN BOT
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("set", set_category))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, save_media))

app.run_polling()