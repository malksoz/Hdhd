import telebot
from telebot import types
import os
import subprocess
import time
import shutil
import json

# ========== الإعدادات ==========
TOKEN = "8862494857:AAHyYjVbSMQx8o3wBQp8FKvssH7A2OFf_aI"
DEVELOPER_ID =8182446916
DEVELOPER_USERNAME = "@HUIRDSU7"

UPLOAD_FOLDER = "uploaded_bots"
BANNED_FILE = "banned_users.txt"
ADMINS_FILE = "admins.txt"
STATS_FILE = "stats.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========== المتغيرات ==========
running_processes = {}  # filename -> process
banned_users = set()
admins = set([DEVELOPER_ID])
system_stats = {"total_bots_ran": 0, "total_files_uploaded": 0}
user_bots_count = {}

ITEMS_PER_PAGE = 5

# ========== تحميل البيانات ==========
def load_data():
    global banned_users, admins, system_stats, user_bots_count
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "r") as f:
            banned_users = set(int(line.strip()) for line in f if line.strip())
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r") as f:
            admins = admins.union(int(line.strip()) for line in f if line.strip())
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            data = json.load(f)
            system_stats = data.get("stats", system_stats)
            user_bots_count = data.get("users", {})

def save_data():
    with open(BANNED_FILE, "w") as f:
        for uid in banned_users:
            f.write(f"{uid}\n")
    with open(ADMINS_FILE, "w") as f:
        for aid in admins:
            f.write(f"{aid}\n")
    with open(STATS_FILE, "w") as f:
        json.dump({"stats": system_stats, "users": user_bots_count}, f)

load_data()

# ========== دوال المساعدة ==========
def is_banned(user_id):
    return user_id in banned_users

def is_admin(user_id):
    return user_id in admins

def get_all_files():
    if not os.path.exists(UPLOAD_FOLDER):
        return []
    return [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".py")]

# ========== عرض قائمة الملفات للحذف ==========
def show_files_for_deletion(chat_id, msg_id, page=0):
    files = get_all_files()
    
    if not files:
        bot.edit_message_text("📂 لا توجد ملفات لحذفها.", chat_id, msg_id, reply_markup=main_menu())
        return
    
    total_pages = (len(files) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_files = files[start:end]
    
    mar = types.InlineKeyboardMarkup(row_width=1)
    
    for f in current_files:
        status = "🟢" if f in running_processes else "🔴"
        size = os.path.getsize(os.path.join(UPLOAD_FOLDER, f)) // 1024
        mar.add(types.InlineKeyboardButton(f"{status} {f} ({size}KB)", callback_data=f"del_file_{f}"))
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("◀️ السابق", callback_data=f"del_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("التالي ▶️", callback_data=f"del_page_{page+1}"))
    
    if nav_buttons:
        mar.add(*nav_buttons)
    
    mar.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    
    bot.edit_message_text(
        f"🗑 <b>اختر الملف الذي تريد حذفه</b>\n\n"
        f"📁 صفحة {page+1} من {total_pages}\n"
        f"📊 إجمالي الملفات: {len(files)}",
        chat_id, msg_id, reply_markup=mar
    )

def confirm_delete(chat_id, msg_id, filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        bot.edit_message_text("❌ الملف غير موجود.", chat_id, msg_id, reply_markup=main_menu())
        return
    
    size = os.path.getsize(path) // 1024
    status = "🟢 شغال" if filename in running_processes else "🔴 متوقف"
    
    mar = types.InlineKeyboardMarkup()
    mar.add(
        types.InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"confirm_del_{filename}"),
        types.InlineKeyboardButton("❌ إلغاء", callback_data="back_to_delete")
    )
    
    bot.edit_message_text(
        f"⚠️ <b>تأكيد الحذف</b>\n\n"
        f"📄 الملف: {filename}\n"
        f"📦 الحجم: {size} KB\n"
        f"📊 الحالة: {status}\n\n"
        f"هل أنت متأكد من الحذف؟",
        chat_id, msg_id, reply_markup=mar
    )

# ========== القوائم ==========
def main_menu():
    mar = types.InlineKeyboardMarkup(row_width=2)
    mar.add(
        types.InlineKeyboardButton("📥 رفع ملف", callback_data="upload"),
        types.InlineKeyboardButton("🗑 حذف ملف", callback_data="delete_file"),
    )
    mar.add(
        types.InlineKeyboardButton("🛠 تثبيت مكتبة", callback_data="install_lib"),
        types.InlineKeyboardButton("📝 إنشاء بوت", callback_data="make_bot"),
    )
    mar.add(
        types.InlineKeyboardButton("⛔ إيقاف بوت", callback_data="stop_one"),
        types.InlineKeyboardButton("🟢 تشغيل بوت", callback_data="start_one"),
    )
    mar.add(
        types.InlineKeyboardButton("📂 ملفاتي", callback_data="list_files"),
        types.InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
    )
    mar.add(
        types.InlineKeyboardButton("👨🏻‍💻 المطور", callback_data="dev"),
        types.InlineKeyboardButton("🔐 لوحة الأدمن", callback_data="admin_panel"),
    )
    return mar

def admin_panel():
    mar = types.InlineKeyboardMarkup(row_width=2)
    mar.add(
        types.InlineKeyboardButton("🤖 البوتات المشغلة", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
    )
    mar.add(
        types.InlineKeyboardButton("🚫 المحظورين", callback_data="admin_banned"),
        types.InlineKeyboardButton("🗑 تنظيف الملفات", callback_data="admin_clean"),
    )
    mar.add(
        types.InlineKeyboardButton("🔄 إيقاف الكل", callback_data="admin_restart_all"),
        types.InlineKeyboardButton("💾 نسخة احتياطية", callback_data="admin_backup"),
    )
    mar.add(
        types.InlineKeyboardButton("➕ حظر مستخدم", callback_data="admin_ban"),
        types.InlineKeyboardButton("🔓 إلغاء حظر", callback_data="admin_unban"),
    )
    mar.add(
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back"),
    )
    return mar

# ========== بدء البوت ==========
@bot.message_handler(commands=["start"])
def start(message):
    if is_banned(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 تم حظرك من استخدام هذا البوت.")
        return
    bot.send_message(
        message.chat.id,
        "👋 أهلاً بك في <b>مدير البوتات المتطور</b>!\n\n"
        "🔽 استخدم الأزرار للتحكم:",
        reply_markup=main_menu(),
    )

# ========== معالجة الأزرار ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if is_banned(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 أنت محظور")
        return
    
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.id

    # ===== الأزرار العامة =====
    if data == "upload":
        bot.edit_message_text("📤 أرسل ملف Python (.py) لرفعه وتشغيله:", chat_id, msg_id)
    
    elif data == "delete_file":
        show_files_for_deletion(chat_id, msg_id, 0)
    
    elif data == "install_lib":
        bot.edit_message_text("📦 أرسل اسم المكتبة (مثال: requests):", chat_id, msg_id)
        bot.register_next_step_handler(call.message, install_lib_step)
    
    elif data == "make_bot":
        bot.edit_message_text("✏️ أرسل كود البوت كاملاً:", chat_id, msg_id)
        bot.register_next_step_handler(call.message, make_bot_step)
    
    elif data == "stop_one":
        bot.edit_message_text("⛔ أرسل اسم البوت الذي تريد إيقافه:", chat_id, msg_id)
        bot.register_next_step_handler(call.message, stop_one_step)
    
    elif data == "start_one":
        bot.edit_message_text("🟢 أرسل اسم البوت الذي تريد تشغيله:", chat_id, msg_id)
        bot.register_next_step_handler(call.message, start_one_step)
    
    elif data == "list_files":
        show_user_files(chat_id, msg_id)
    
    elif data == "my_stats":
        count = user_bots_count.get(call.from_user.id, 0)
        bot.edit_message_text(
            f"📊 <b>إحصائياتك</b>\n\n"
            f"• عدد البوتات التي قمت برفعها: {count}\n"
            f"• عدد البوتات المشغلة حالياً: {len(running_processes)}",
            chat_id, msg_id, reply_markup=main_menu()
        )
    
    elif data == "dev":
        bot.edit_message_text(
            f"👨🏻‍💻 <b>مبرمج البوت</b>\n\n"
            f"{DEVELOPER_USERNAME}\n"
            f"ايدي المطور: {DEVELOPER_ID}",
            chat_id, msg_id, reply_markup=main_menu()
        )
    
    elif data == "admin_panel":
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ هذا الأمر للمطورين فقط")
            return
        bot.edit_message_text("🔐 <b>لوحة تحكم الأدمن</b>\n\nاختر إحدى الخيارات:", chat_id, msg_id, reply_markup=admin_panel())
    
    elif data == "back":
        bot.edit_message_text("🔽 القائمة الرئيسية:", chat_id, msg_id, reply_markup=main_menu())
    
    # ===== أزرار الحذف =====
    elif data.startswith("del_page_"):
        page = int(data.split("_")[2])
        show_files_for_deletion(chat_id, msg_id, page)
    
    elif data.startswith("del_file_"):
        filename = data.replace("del_file_", "")
        confirm_delete(chat_id, msg_id, filename)
    
    elif data.startswith("confirm_del_"):
        filename = data.replace("confirm_del_", "")
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            if filename in running_processes:
                try:
                    running_processes[filename].terminate()
                except:
                    pass
                del running_processes[filename]
            os.remove(path)
            bot.edit_message_text(f"✅ تم حذف الملف: {filename}", chat_id, msg_id, reply_markup=main_menu())
        else:
            bot.edit_message_text("❌ الملف غير موجود.", chat_id, msg_id, reply_markup=main_menu())
    
    elif data == "back_to_delete":
        show_files_for_deletion(chat_id, msg_id, 0)
    
    # ===== أزرار الأدمن =====
    elif data.startswith("admin_"):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ غير مصرح")
            return
        handle_admin_panel(data, chat_id, msg_id, call)

# ========== عرض الملفات ==========
def show_user_files(chat_id, msg_id):
    files = get_all_files()
    if not files:
        bot.edit_message_text("📂 لا توجد ملفات مرفوعة.", chat_id, msg_id, reply_markup=main_menu())
        return
    msg = "📋 <b>قائمة البوتات</b>\n\n"
    for f in files:
        status = "🟢 شغال" if f in running_processes else "🔴 متوقف"
        size = os.path.getsize(os.path.join(UPLOAD_FOLDER, f)) // 1024
        msg += f"• {f} ({size} KB) — {status}\n"
    bot.edit_message_text(msg, chat_id, msg_id, reply_markup=main_menu())

# ========== تشغيل ملف بايثون ==========
def run_python_file(file_path, filename):
    try:
        process = subprocess.Popen(["python3", file_path])
        running_processes[filename] = process
        return True
    except Exception as e:
        return False

# ========== الأوامر ==========
def install_lib_step(message):
    lib = message.text.strip()
    try:
        subprocess.check_call(["pip", "install", lib])
        bot.reply_to(message, f"✅ تم تثبيت المكتبة: {lib}")
    except Exception as e:
        bot.reply_to(message, f"❌ فشل التثبيت: {e}")

def make_bot_step(message):
    code = message.text
    filename = f"userbot_{int(time.time())}.py"
    path = os.path.join(UPLOAD_FOLDER, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    
    success = run_python_file(path, filename)
    if success:
        user_bots_count[message.from_user.id] = user_bots_count.get(message.from_user.id, 0) + 1
        system_stats["total_bots_ran"] += 1
        save_data()
        bot.reply_to(message, f"✅ تم إنشاء وتشغيل البوت: {filename}")
    else:
        bot.reply_to(message, f"❌ فشل تشغيل البوت: {filename}")

def stop_one_step(message):
    filename = message.text.strip()
    if filename in running_processes:
        try:
            running_processes[filename].terminate()
        except:
            pass
        del running_processes[filename]
        bot.reply_to(message, f"⛔ تم إيقاف البوت: {filename}")
    else:
        bot.reply_to(message, "❌ البوت غير مشغل أو غير موجود.")

def start_one_step(message):
    filename = message.text.strip()
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        bot.reply_to(message, "❌ الملف غير موجود.")
        return
    if filename in running_processes:
        bot.reply_to(message, "⚠️ البوت يعمل بالفعل.")
        return
    success = run_python_file(path, filename)
    if success:
        bot.reply_to(message, f"🟢 تم تشغيل البوت: {filename}")
    else:
        bot.reply_to(message, f"❌ فشل تشغيل البوت: {filename}")

# ========== رفع الملفات ==========
@bot.message_handler(content_types=["document"])
def handle_document(message):
    if is_banned(message.from_user.id):
        return
    
    doc = message.document
    if not doc.file_name.endswith(".py"):
        bot.reply_to(message, "❌ يرجى رفع ملف Python فقط بامتداد .py")
        return
    
    msg = bot.reply_to(message, "⏳ جاري رفع الملف...")
    
    file_path = os.path.join(UPLOAD_FOLDER, doc.file_name)
    file_info = bot.get_file(doc.file_id)
    downloaded = bot.download_file(file_info.file_path)
    
    with open(file_path, "wb") as f:
        f.write(downloaded)
    
    # إيقاف النسخة القديمة إذا وجدت
    if doc.file_name in running_processes:
        try:
            running_processes[doc.file_name].terminate()
        except:
            pass
        del running_processes[doc.file_name]
    
    # تشغيل الملف الجديد
    success = run_python_file(file_path, doc.file_name)
    
    if success:
        user_bots_count[message.from_user.id] = user_bots_count.get(message.from_user.id, 0) + 1
        system_stats["total_files_uploaded"] += 1
        save_data()
        bot.edit_message_text(f"✅ تم رفع وتشغيل البوت: {doc.file_name}", message.chat.id, msg.id)
    else:
        bot.edit_message_text(f"⚠️ تم رفع الملف لكن فشل التشغيل!", message.chat.id, msg.id)
    
    # إشعار للمطور
    if message.from_user.id != DEVELOPER_ID:
        try:
            buttons = types.InlineKeyboardMarkup()
            buttons.add(types.InlineKeyboardButton("🗑 حذف الملف", callback_data=f"dev_delete_{doc.file_name}_{message.from_user.id}"))
            buttons.add(types.InlineKeyboardButton("🚫 حظر المستخدم", callback_data=f"dev_ban_{message.from_user.id}"))
            
            bot.send_message(
                DEVELOPER_ID,
                f"📤 <b>تم رفع ملف جديد!</b>\n\n"
                f"• اسم الملف: {doc.file_name}\n"
                f"• من: @{message.from_user.username or message.from_user.first_name}\n"
                f"• ايدي: {message.from_user.id}",
                reply_markup=buttons
            )
        except:
            pass

# ========== لوحة الأدمن ==========
def handle_admin_panel(data, chat_id, msg_id, call):
    if data == "admin_bots":
        total = len(running_processes)
        running_list = "\n".join(list(running_processes.keys())[:20]) if running_processes else "لا يوجد"
        bot.edit_message_text(f"🤖 <b>البوتات المشغلة</b>\n\nالعدد: {total}\n\n{running_list}", chat_id, msg_id, reply_markup=admin_panel())
    
    elif data == "admin_stats":
        total_files = len(get_all_files())
        stats = f"📊 <b>إحصائيات النظام</b>\n\n• الملفات المرفوعة: {system_stats['total_files_uploaded']}\n• البوتات المشغلة حالياً: {len(running_processes)}\n• إجمالي مرات التشغيل: {system_stats['total_bots_ran']}\n• المستخدمين المحظورين: {len(banned_users)}\n• المساحة المستخدمة: {get_folder_size()} MB"
        bot.edit_message_text(stats, chat_id, msg_id, reply_markup=admin_panel())
    
    elif data == "admin_banned":
        if banned_users:
            banned_list = "\n".join(str(uid) for uid in list(banned_users)[:30])
            bot.edit_message_text(f"🚫 <b>المستخدمين المحظورين</b>\n\n{banned_list}", chat_id, msg_id, reply_markup=admin_panel())
        else:
            bot.edit_message_text("✅ لا يوجد مستخدمين محظورين", chat_id, msg_id, reply_markup=admin_panel())
    
    elif data == "admin_clean":
        cleaned = 0
        for f in get_all_files():
            fp = os.path.join(UPLOAD_FOLDER, f)
            if os.path.getsize(fp) == 0:
                os.remove(fp)
                cleaned += 1
        bot.edit_message_text(f"🗑 تم تنظيف {cleaned} ملف تالف", chat_id, msg_id, reply_markup=admin_panel())
    
    elif data == "admin_restart_all":
        for proc in list(running_processes.values()):
            try:
                proc.terminate()
            except:
                pass
        running_processes.clear()
        bot.edit_message_text("🔄 تم إيقاف جميع البوتات", chat_id, msg_id, reply_markup=admin_panel())
    
    elif data == "admin_backup":
        backup_name = f"backup_{int(time.time())}"
        shutil.make_archive(backup_name, 'zip', UPLOAD_FOLDER)
        bot.edit_message_text(f"💾 تم إنشاء النسخة: {backup_name}.zip", chat_id, msg_id, reply_markup=admin_panel())
    
    elif data == "admin_ban":
        bot.edit_message_text("🚫 <b>حظر مستخدم</b>\nأرسل ايدي المستخدم:", chat_id, msg_id)
        bot.register_next_step_handler(call.message, admin_ban_user)
    
    elif data == "admin_unban":
        bot.edit_message_text("🔓 <b>إلغاء حظر مستخدم</b>\nأرسل ايدي المستخدم:", chat_id, msg_id)
        bot.register_next_step_handler(call.message, admin_unban_user)

def get_folder_size():
    total = 0
    if os.path.exists(UPLOAD_FOLDER):
        for f in os.listdir(UPLOAD_FOLDER):
            fp = os.path.join(UPLOAD_FOLDER, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return round(total / (1024 * 1024), 2)

def admin_ban_user(message):
    try:
        user_id = int(message.text.strip())
        banned_users.add(user_id)
        save_data()
        bot.reply_to(message, f"✅ تم حظر المستخدم {user_id}")
    except:
        bot.reply_to(message, "❌ ايدي غير صالح")

def admin_unban_user(message):
    try:
        user_id = int(message.text.strip())
        if user_id in banned_users:
            banned_users.remove(user_id)
            save_data()
            bot.reply_to(message, f"✅ تم إلغاء حظر المستخدم {user_id}")
        else:
            bot.reply_to(message, "❌ هذا المستخدم غير محظور")
    except:
        bot.reply_to(message, "❌ ايدي غير صالح")

# ========== أزرار المطور ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("dev_"))
def dev_controls(call):
    if call.from_user.id != DEVELOPER_ID:
        bot.answer_callback_query(call.id, "❌ أنت لست المطور.")
        return
    
    data = call.data
    if data.startswith("dev_delete_"):
        parts = data.split("_")
        filename = parts[2]
        user_id = int(parts[3])
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            if filename in running_processes:
                try:
                    running_processes[filename].terminate()
                except:
                    pass
                del running_processes[filename]
            os.remove(path)
            bot.edit_message_text(f"🗑 تم حذف الملف: {filename}", call.message.chat.id, call.message.id)
            try:
                bot.send_message(user_id, f"❌ تم حذف ملفك: {filename} بواسطة المطور.")
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ الملف غير موجود.")
    
    elif data.startswith("dev_ban_"):
        user_id = int(data.split("_")[2])
        banned_users.add(user_id)
        save_data()
        bot.edit_message_text(f"🚫 تم حظر المستخدم: {user_id}", call.message.chat.id, call.message.id)
        try:
            bot.send_message(user_id, "❌ تم حظرك من البوت بواسطة المطور.")
        except:
            pass

# ========== تشغيل البوت ==========
print("🚀 البوت يعمل الآن...")
print(f"📁 مجلد الرفع: {UPLOAD_FOLDER}")
print(f"👑 المطور: {DEVELOPER_ID}")
bot.infinity_polling()