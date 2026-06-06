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
import asyncio
# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()



cursor.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE
)
""")
conn.commit()

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
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

try:
    cursor.execute("ALTER TABLE categories ADD COLUMN code TEXT")
except:
    pass



cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

conn.commit()

# ================= CONFIG =================
TOKEN = "8913519612:AAGb9xRpB1ECQN0TEY9Qyg_teTPfq3cA-xA"

# ==========================================

async def is_admin(user_id):
    cursor.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None


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

    # 🔒 قفل ادمین
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی نداری")
        return

    if len(context.args) < 2:
        await update.message.reply_text("استفاده: /addchannel @id 24")
        return

    chat_id = context.args[0].strip()

    try:
        hours = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❗️ ساعت باید عدد باشه")
        return

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

    # 🔥 لینک /start cat_1
    if len(parts) > 1:

        code = parts[1].strip()

        # 📁 اگر دسته بود
        if code.startswith("cat_"):

            cursor.execute(
                "SELECT file_id, type FROM media WHERE category = ?",
                (code,)
            )
            files = cursor.fetchall()

            if not files:
                await update.message.reply_text("❌ این دسته خالیه")
                return

            media_group = []

            for file_id, ftype in files:
                if ftype == "photo":
                    media_group.append(InputMediaPhoto(file_id))
                elif ftype == "video":
                    media_group.append(InputMediaVideo(file_id))

            sent_messages = []

            if media_group:
                for i in range(0, len(media_group), 10):
                    msgs = await context.bot.send_media_group(
                        chat_id=update.effective_chat.id,
                        media=media_group[i:i+10]
                    )
                    sent_messages.extend(msgs)

            warn = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ فایل‌ها تا ۱۵ ثانیه دیگر حذف می‌شوند"
            )

            await asyncio.sleep(15)

            for msg in sent_messages:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=msg.message_id
                    )
                except:
                    pass

            try:
                await warn.delete()
            except:
                pass

            return

        # 🔒 اگر چیز دیگه بود (مثل سیستم قبلی)
        context.user_data["category"] = code

    # 🔒 چک عضویت
    user_id = update.effective_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)",(user_id,))
    conn.commit()
    ok = await check_membership(context.bot, user_id)

    if not ok:
        await send_join_gate(update, context)
        return

    # 🎛 منوی اصلی
    keyboard = [
        [
            InlineKeyboardButton("📷 تصاویر", callback_data="photos"),
            InlineKeyboardButton("🎥 ویدیو", callback_data="video")
        ],
        [
            InlineKeyboardButton("📢 عضویت در کانال‌ها", callback_data="join"),
            InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")
        ]
    ]

    await update.message.reply_text(
        "🎬 خوش اومدی!\n\nیکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    # 📷 photos
    if query.data == "photos":
        await query.message.reply_text("📷 برای دیدن دسته‌ها /start دسته_اسم بزن")
        return

    # 🎥 video
    elif query.data == "video":
        await query.message.reply_text("🎥 فعلاً ویدیو آماده نیست 😎")
        return

    # 📢 join channels
    elif query.data == "join":

        channels = await get_active_channels()

        if not channels:
            await query.message.reply_text("❌ هیچ کانالی تنظیم نشده")
            return

        keyboard = []

        for ch in channels:
            url = f"https://t.me/{ch[1:]}" if ch.startswith("@") else ch

            keyboard.append([
                InlineKeyboardButton("🔥 عضویت در کانال", url=url)
            ])

        keyboard.append([
            InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")
        ])

        await query.message.edit_text(
            "📢 برای دسترسی باید عضو کانال‌ها بشی:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ✅ check membership
    elif query.data == "check_membership":

        ok = await check_membership(context.bot, query.from_user.id)

        if ok:
            try:
                await query.message.delete()
            except:
                pass

            category = context.user_data.get("category")

            if category:
                await send_category(update, context, category)
            else:
                await query.message.reply_text("✅ عضویت تایید شد")

        else:
            await query.answer("❌ هنوز عضو نشدی", show_alert=True)

        return

    # 🛠 ADMIN MAIN
    elif query.data == "admin_main":

        keyboard = [
            [InlineKeyboardButton("📁 مدیریت دسته‌ها", callback_data="admin_categories")],
            [InlineKeyboardButton("📢 مدیریت کانال‌ها", callback_data="admin_channels")],
            [InlineKeyboardButton("👮 مدیریت ادمین‌ها", callback_data="admin_admins")],
            [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")]
        ]

        await query.message.edit_text(
            "🛠 پنل مدیریت",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 📢 CHANNELS
    elif query.data == "admin_channels":

        keyboard = [
            [InlineKeyboardButton("➕ افزودن کانال", callback_data="add_channel")],
            [InlineKeyboardButton("🗑 حذف کانال", callback_data="remove_channel")],
            [InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="list_channels")],
            [InlineKeyboardButton("⬅️ برگشت", callback_data="admin_main")]
        ]

        await query.message.edit_text(
            "📢 مدیریت کانال‌ها:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif query.data == "list_channels":

        channels = await get_active_channels()

        if not channels:
            await query.message.edit_text("❌ هیچ کانالی ثبت نشده")
            return

        text = "📋 کانال‌های فعال:\n\n"

        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch}\n"

        keyboard = [
            [InlineKeyboardButton("⬅️ برگشت", callback_data="admin_channels")]
        ]

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif query.data == "add_channel":

        context.user_data["action"] = "add_channel"

        await query.message.edit_text(
            "➕ کانال + زمان (ساعت) رو بفرست:\n\nمثال:\n@mychannel 24"
        )
        return

    elif query.data == "remove_channel":

        context.user_data["action"] = "remove_channel"

        await query.message.edit_text(
            "🗑 آیدی کانال رو بفرست:\n\nمثال:\n@mychannel"
        )
        return

    # 📁 CATEGORIES
    elif query.data == "admin_categories":

        keyboard = [
            [InlineKeyboardButton("➕ افزودن دسته", callback_data="add_category")],
            [InlineKeyboardButton("📤 افزودن فایل", callback_data="add_media")],
            [InlineKeyboardButton("🗑 حذف دسته", callback_data="remove_category")],
            [InlineKeyboardButton("📋 لیست دسته‌ها", callback_data="list_categories")],
            [InlineKeyboardButton("⬅️ برگشت", callback_data="admin_main")]
        ]

        await query.message.edit_text(
            "📁 مدیریت دسته‌ها:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif query.data == "add_category":

        context.user_data["action"] = "add_category"

        await query.message.edit_text("➕ اسم دسته رو بفرست:")
        return

    elif query.data == "remove_category":

        context.user_data["action"] = "remove_category"

        await query.message.edit_text("🗑 اسم دسته برای حذف رو بفرست:")
        return

    elif query.data == "list_categories":

        cursor.execute("SELECT name FROM categories")
        cats = cursor.fetchall()

        if not cats:
            await query.message.edit_text("❌ هیچ دسته‌ای وجود ندارد")
            return

        text = "📋 لیست دسته‌ها:\n\n"

        for i, c in enumerate(cats, 1):
            text += f"{i}. {c[0]}\n"

        keyboard = [
            [InlineKeyboardButton("⬅️ برگشت", callback_data="admin_categories")]
        ]

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # 👮 ADMINS
    elif query.data == "admin_admins":

        keyboard = [
            [InlineKeyboardButton("+ افزودن ادمین", callback_data="add_admin")],
            [InlineKeyboardButton("🗑 حذف ادمین", callback_data="remove_admin")],
            [InlineKeyboardButton("📋 لیست ادمین‌ها", callback_data="list_admins")],
            [InlineKeyboardButton("⬅️ برگشت", callback_data="admin_main")]
        ]

        await query.message.edit_text(
            "👮 مدیریت ادمین‌ها:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif query.data == "admin_stats":
        cursor.execute("SELECT COUNT(*) FROM users"); users=cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM media"); media=cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM categories"); cats=cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM channels"); chans=cursor.fetchone()[0]
        await query.message.edit_text(f"📊 آمار\n\n👥 کاربران: {users}\n📁 دسته‌ها: {cats}\n🎞 فایل‌ها: {media}\n📢 کانال‌ها: {chans}")
        return

    elif query.data == "add_admin":

        context.user_data["action"] = "add_admin"

        await query.message.edit_text("➕ آیدی عددی کاربر رو بفرست:")
        return

    elif query.data == "remove_admin":

        context.user_data["action"] = "remove_admin"

        await query.message.edit_text("🗑 آیدی عددی ادمین رو بفرست:")
        return

    elif query.data == "list_admins":

        admins = await get_admins()

        if not admins:
            await query.message.edit_text("❌ هیچ ادمینی ثبت نشده")
            return

        text = "👮 لیست ادمین‌ها:\n\n"

        for i, a in enumerate(admins, 1):
            text += f"{i}. {a[0]}\n"

        keyboard = [
            [InlineKeyboardButton("⬅️ برگشت", callback_data="admin_admins")]
        ]

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
        
    elif query.data == "add_media":

        context.user_data["action"] = "select_media_category"

        await query.message.edit_text(
            "📤 کد دسته را بفرست:\nمثال:\ncat_1"
        )
        return


    elif query.data == "add_media":

        context.user_data["action"] = "waiting_media"
        context.user_data["media_category"] = None  # یا اگر دسته داری اینجا ست کن

        await query.message.edit_text(
            "📤 اول اسم دسته رو بفرست (مثلاً: cat_1)"
        )
        return
   
    elif query.data == "add_media":

        context.user_data["action"] = "waiting_media"
        context.user_data["media_category"] = None

        await query.message.edit_text(
            "📁 اسم دسته رو بفرست (مثلاً: cat_1)"
        )
        return
    

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):




    if context.user_data.get("action") == "waiting_media" and not context.user_data.get("media_category"):

        context.user_data["media_category"] = update.message.text.strip()

        await update.message.reply_text("📤 حالا عکس یا ویدیو رو بفرست")
        return

    if context.user_data.get("action") == "waiting_media":

        category = context.user_data.get("media_category")

        file_id = None
        file_type = None


    # 📤 WAITING MEDIA
    if context.user_data.get("action") == "waiting_media":

        category = context.user_data.get("media_category")

        file_id = None
        file_type = None

        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_type = "photo"

        elif update.message.video:
            file_id = update.message.video.file_id
            file_type = "video"

        elif update.message.document:
            file_id = update.message.document.file_id
            file_type = "document"

        else:
            await update.message.reply_text("❌ فقط عکس یا ویدیو بفرست")
            return

        cursor.execute(
            "INSERT INTO media (category, file_id, type) VALUES (?, ?, ?)",
            (category, file_id, file_type)
        )
        conn.commit()

        await update.message.reply_text("✅ فایل ذخیره شد، فایل بعدی را هم ارسال کن")

        return


    action = context.user_data.get("action")

    if not action:
        return

    text = update.message.text.strip()

    # ➕ ADD CHANNEL
    if action == "add_channel":

        try:
            chat_id, hours = text.split()
            hours = int(hours)

            expire = int(time.time()) + hours * 3600

            cursor.execute(
                "INSERT INTO channels (chat_id, expire_time) VALUES (?, ?)",
                (chat_id, expire)
            )
            conn.commit()

            await update.message.reply_text("✅ کانال اضافه شد")

        except:
            await update.message.reply_text("❌ فرمت اشتباهه (مثال: @channel 24)")

        context.user_data["action"] = None
        return


    # 🗑 REMOVE CHANNEL
    elif action == "remove_channel":

        cursor.execute(
            "DELETE FROM channels WHERE chat_id = ?",
            (text,)
        )
        conn.commit()

        await update.message.reply_text("🗑 کانال حذف شد")

        context.user_data["action"] = None
        return


    # ➕ ADD ADMIN
    elif action == "add_admin":

        if not text.isdigit():
            await update.message.reply_text("❌ فقط آیدی عددی بفرست")
            return

        user_id = int(text)

        cursor.execute(
            "INSERT OR IGNORE INTO admins (user_id) VALUES (?)",
            (user_id,)
        )
        conn.commit()

        await update.message.reply_text("✅ ادمین اضافه شد")

        context.user_data["action"] = None
        return


    # 🗑 REMOVE ADMIN
    elif action == "remove_admin":

        if not text.isdigit():
            await update.message.reply_text("❌ فقط آیدی عددی بفرست")
            return

        user_id = int(text)

        cursor.execute(
            "DELETE FROM admins WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()

        await update.message.reply_text("🗑 ادمین حذف شد")

        context.user_data["action"] = None
        return


    # ➕ ADD CATEGORY
    elif action == "add_category":

        name = text.strip()

        cursor.execute(
            "INSERT INTO categories (name) VALUES (?)",
            (name,)
        )
        conn.commit()

        cat_id = cursor.lastrowid

        code = f"cat_{cat_id}"

        cursor.execute(
            "UPDATE categories SET code = ? WHERE id = ?",
            (code, cat_id)
        )
        conn.commit()

        bot_username = (await context.bot.get_me()).username

        link = f"https://t.me/{bot_username}?start={code}"

        await update.message.reply_text(
            f"✅ دسته ساخته شد\n\n🔗 لینک دسته:\n{link}"
        )

        context.user_data["action"] = None
        return
        
        
        await update.message.reply_text("📁 دسته اضافه شد")

        context.user_data["action"] = None
        return


    # 🗑 REMOVE CATEGORY
    elif action == "remove_category":

        category_name = text.strip()

        cursor.execute(
            "SELECT code FROM categories WHERE name = ?",
            (category_name,)
        )
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text("❌ چنین دسته‌ای پیدا نشد")
            return

        category_code = row[0]

        cursor.execute(
            "DELETE FROM media WHERE category = ?",
            (category_code,)
        )

        cursor.execute(
            "DELETE FROM categories WHERE name = ?",
            (category_name,)
        )

        conn.commit()

        await update.message.reply_text("🗑 دسته و فایل‌های آن حذف شدند")

        context.user_data["action"] = None
        return
    
    elif action == "select_media_category":

        category_name = text.strip()

        cursor.execute(
            "SELECT code FROM categories WHERE name = ?",
            (category_name,)
        )
        row = cursor.fetchone()

        if not row:
            await update.message.reply_text("❌ چنین دسته‌ای پیدا نشد")
            return

        context.user_data["media_category"] = row[0]
        context.user_data["action"] = "waiting_media"

        await update.message.reply_text(
            "📤 حالا عکس یا ویدیو بفرست"
        )
        return
    
async def get_admins():
    cursor.execute("SELECT user_id FROM admins")
    return cursor.fetchall()    
    
async def send_join_gate(update, context):

    channels = await get_active_channels()

    if not channels:
        await update.message.reply_text("❗️ هیچ کانالی تنظیم نشده")
        return

    keyboard = []

    for ch in channels:

        # اگر username داری
        if ch.startswith("@"):
            url = f"https://t.me/{ch[1:]}"
        else:
            # اگر invite link داری
            url = ch

        keyboard.append([
            InlineKeyboardButton("📢 عضویت در کانال", url=url)
        ])

    keyboard.append([
        InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")
    ])

    await update.message.reply_text(
        "❗️ برای استفاده از ربات باید عضو کانال‌های زیر بشی:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def send_category(update, context, category):

    user_id = update.effective_user.id

    # 🔒 چک عضویت
    ok = await check_membership(context.bot, user_id)

    if not ok:

        channels = await get_active_channels()

        keyboard = []

        for ch in channels:
            if ch.startswith("@"):
                url = f"https://t.me/{ch[1:]}"
            else:
                url = ch  # invite link

            keyboard.append([
                InlineKeyboardButton("📢 عضویت در کانال", url=url)
            ])

        keyboard.append([
            InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")
        ])

        await update.message.reply_text(
            "❗️ برای دریافت فایل باید عضو کانال‌های زیر بشی:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 📦 گرفتن فایل‌ها
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

    sent_messages = []

    for i in range(0, len(media_group), 10):
        msgs = await context.bot.send_media_group(
            chat_id=update.effective_chat.id,
            media=media_group[i:i+10]
        )
        sent_messages.extend(msgs)

    warn = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚠️ فایل‌ها تا ۱۵ ثانیه دیگر حذف می‌شوند"
    )

    await asyncio.sleep(15)

    for msg in sent_messages:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id
            )
        except:
            pass

    try:
        await warn.delete()
    except:
        pass



async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 🔒 قفل ادمین
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی نداری")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /removechannel @id")
        return

    chat_id = context.args[0].strip()

    cursor.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
    conn.commit()

    await update.message.reply_text("🗑 کانال حذف شد")


async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 🔒 قفل ادمین
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی نداری")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /set ana_photos")
        return

    category = context.args[0].strip()
    context.user_data["category"] = category

    await update.message.reply_text(
        f"✅ دسته فعال شد: {category}\n\n"
        "حالا عکس یا ویدیو بفرست"
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی نداری")
        return

    keyboard = [
        [InlineKeyboardButton("📁 مدیریت دسته‌ها", callback_data="admin_categories")],
        [InlineKeyboardButton("📢 مدیریت کانال‌ها", callback_data="admin_channels")],
        [InlineKeyboardButton("👮 مدیریت ادمین‌ها", callback_data="admin_admins")],
        [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")]
    ]

    await update.message.reply_text(
        "🛠 پنل مدیریت",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 🔒 قفل ادمین
    if not await is_admin(update.effective_user.id):
        return  # یا می‌تونی پیام بدی: "⛔ دسترسی نداری"

    category = context.user_data.get("category")

    if not category:
        await update.message.reply_text("❗️ اول /set بزن و دسته انتخاب کن")
        return

    # 📷 عکس
    if update.message.photo:

        file_id = update.message.photo[-1].file_id

        cursor.execute(
            "INSERT INTO media (category, file_id, type) VALUES (?, ?, ?)",
            (category, file_id, "photo")
        )
        conn.commit()

        await update.message.reply_text("✅ عکس ذخیره شد")

    # 🎥 ویدیو
    elif update.message.video:

        file_id = update.message.video.file_id

        cursor.execute(
            "INSERT INTO media (category, file_id, type) VALUES (?, ?, ?)",
            (category, file_id, "video")
        )
        conn.commit()

        await update.message.reply_text("✅ ویدیو ذخیره شد")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, text_handler))
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(CommandHandler("addchannel", add_channel))
app.add_handler(CommandHandler("listchannels", list_channels))
app.add_handler(CommandHandler("removechannel", remove_channel))
cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", ( 6503127920,))
conn.commit()
app.run_polling()
