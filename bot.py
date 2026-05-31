current_category = None
from telegram.ext import CommandHandler

async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_category

    if not context.args:
        await update.message.reply_text(
            "استفاده:\n/set اسم_دسته"
        )
        return

    current_category = context.args[0]

    await update.message.reply_text(
        f"✅ دسته فعال شد: {current_category}"
    )
from telegram.ext import MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
TOKEN = "8913519612:AAGwQY8FDd9uzYAazdKizk9POtXhZgpjW14"

CHANNEL_1 = -1003967540137
CHANNEL_2 = -1004293009722

CHANNEL_LINK_1 = "https://t.me/+XXXXXXX1"
CHANNEL_LINK_2 = "https://t.me/+XXXXXXX2"
# =========================================


# 🚀 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

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

    # 📷 Photos
    if query.data == "photos":
        await query.message.reply_text("📷 فعلاً عکس‌ها آماده نیست 😎")

    # 🎥 Video
    elif query.data == "video":
        await query.message.reply_text("🎥 فعلاً ویدیو آماده نیست 😎")

    # 📢 Join channels
    elif query.data == "join":

        keyboard = [
            [InlineKeyboardButton("🔥 کانال فیلم", url=CHANNEL_LINK_1),
            InlineKeyboardButton("🎬 کانال VIP", url=CHANNEL_LINK_2)]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(
            "📢 برای دسترسی به محتوا در کانال‌ها عضو شوید:",
            reply_markup=reply_markup
        )

    # ✅ Check membership
    elif query.data == "check":

        user_id = query.from_user.id

        try:
            member1 = await context.bot.get_chat_member(CHANNEL_1, user_id)
            member2 = await context.bot.get_chat_member(CHANNEL_2, user_id)

            ok1 = member1.status in ["member", "administrator", "creator"]
            ok2 = member2.status in ["member", "administrator", "creator"]

            if ok1 and ok2:
                await query.message.reply_text("✅ عضویت شما تایید شد!")
            else:
                await query.message.reply_text("بچه کونی عضو شو دیگه 🤓☝🏻")

        except Exception as e:
            await query.message.reply_text(f"⚠️ خطا:\n{e}")

async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.photo:
        file_id = update.message.photo[-1].file_id

        await update.message.reply_text(
            f"📷 Photo ID:\n\n{file_id}"
        )

    elif update.message.video:
        file_id = update.message.video.file_id

        await update.message.reply_text(
            f"🎥 Video ID:\n\n{file_id}"
        )

# 🚀 RUN BOT
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("set", set_category))

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

app.add_handler(
    MessageHandler(filters.PHOTO | filters.VIDEO, save_media)
)
app.run_polling()