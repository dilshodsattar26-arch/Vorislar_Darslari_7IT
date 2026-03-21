import telebot
from telebot import types
import json
import os

TOKEN = "8762136939:AAHUcOgeHQBYf8MgMCFaC48EKhUNhb4jn88"
ADMIN_ID = 7253285947

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

# ---------------- LOAD / SAVE (AUTO FIX) ----------------
def load_data():
    default = {
        "users": [],
        "movies": {},
        "vip_movies": {},
        "channels": [],
        "force_sub": True,
        "vip_users": [],
        "referrals": {}
    }

    if not os.path.exists(DATA_FILE):
        return default

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    # 🔥 missing keylarni avtomatik qo‘shadi
    for key in default:
        if key not in data:
            data[key] = default[key]

    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ---------------- CHANNEL FIX ----------------
def normalize_channel(ch):
    if "t.me/" in ch:
        ch = ch.split("t.me/")[1]
    if not ch.startswith("@"):
        ch = "@" + ch
    return ch

# ---------------- SUB CHECK ----------------
def check_sub(user_id):
    if not data["force_sub"]:
        return True

    for ch in data["channels"]:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            continue
    return True

def join_channels(message):
    markup = types.InlineKeyboardMarkup()
    for ch in data["channels"]:
        link = f"https://t.me/{ch.replace('@','')}"
        markup.add(types.InlineKeyboardButton(f"📢 {ch}", url=link))

    bot.send_message(message.chat.id,
                     "❗ Kanallarga obuna bo‘ling",
                     reply_markup=markup)

# ---------------- START + REF ----------------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    if user_id not in data["users"]:
        data["users"].append(user_id)

        # referral
        args = message.text.split()
        if len(args) > 1:
            ref_id = args[1]
            if ref_id != str(user_id):
                data["referrals"].setdefault(ref_id, 0)
                data["referrals"][ref_id] += 1

        save_data(data)

    if not check_sub(user_id):
        return join_channels(message)

    bot.send_message(message.chat.id,
                     "🎬 KinoWorldUz ga hush kelibsiz!\n\n📥 Kino kodini yuboring")

# ---------------- SEND MOVIE ----------------
@bot.message_handler(func=lambda m: m.text and m.text.isdigit())
def send_movie(message):
    user_id = message.from_user.id

    if not check_sub(user_id):
        return join_channels(message)

    code = message.text

    if code in data["vip_movies"]:
        if user_id not in data["vip_users"]:
            return bot.send_message(message.chat.id, "🔒 Bu VIP kino!")

        movie = data["vip_movies"][code]

    elif code in data["movies"]:
        movie = data["movies"][code]

    else:
        return bot.send_message(message.chat.id, "❌ Bunday kod yo‘q")

    caption = f"{movie['name']}\n\n{movie['desc']}\n\n🎬 KinoWorldUz eng zori ⭐"

    bot.send_video(message.chat.id, movie["file_id"], caption=caption)

# ---------------- ADMIN PANEL ----------------
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "⛔ Ruxsat yo‘q")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Kino", "❌ O‘chirish")
    kb.add("⭐ VIP kino", "👑 VIP berish")
    kb.add("📊 Statistika")
    kb.add("📢 Kanal qo‘shish", "🗑 Kanal o‘chirish")
    kb.add("📄 Kanal list")
    kb.add("✅ Majburiy ON", "❌ Majburiy OFF")

    bot.send_message(message.chat.id, "⚙️ Admin panel", reply_markup=kb)

# ---------------- STAT ----------------
@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(
        message.chat.id,
        f"👥 Users: {len(data['users'])}\n🎬 Kinolar: {len(data['movies'])}\n⭐ VIP user: {len(data['vip_users'])}\n📢 Kanallar: {len(data['channels'])}"
    )

# ---------------- ADD MOVIE ----------------
@bot.message_handler(func=lambda m: m.text == "➕ Kino")
def add_movie(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "Kino kodi:")
    bot.register_next_step_handler(msg, ask_name)

def ask_name(message):
    code = message.text
    msg = bot.send_message(message.chat.id, "Kino nomi:")
    bot.register_next_step_handler(msg, lambda m: ask_desc(m, code))

def ask_desc(message, code):
    name = message.text
    msg = bot.send_message(message.chat.id, "Tavsif:")
    bot.register_next_step_handler(msg, lambda m: ask_video(m, code, name))

def ask_video(message, code, name):
    desc = message.text
    msg = bot.send_message(message.chat.id, "Video yubor:")
    bot.register_next_step_handler(msg, lambda m: save_movie(m, code, name, desc))

def save_movie(message, code, name, desc):
    if not message.video:
        return bot.send_message(message.chat.id, "❗ Video yubor!")

    data["movies"][code] = {
        "name": name,
        "desc": desc,
        "file_id": message.video.file_id
    }

    save_data(data)
    bot.send_message(message.chat.id, "✅ Kino qo‘shildi")

# ---------------- DELETE MOVIE ----------------
@bot.message_handler(func=lambda m: m.text == "❌ O‘chirish")
def delete_movie(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "Kino kodi:")
    bot.register_next_step_handler(msg, do_delete)

def do_delete(message):
    code = message.text

    if code in data["movies"]:
        del data["movies"][code]
        save_data(data)
        bot.send_message(message.chat.id, "❌ O‘chirildi")
    else:
        bot.send_message(message.chat.id, "Topilmadi")

# ---------------- VIP MOVIE ----------------
@bot.message_handler(func=lambda m: m.text == "⭐ VIP kino")
def add_vip_movie(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "VIP kod:")
    bot.register_next_step_handler(msg, ask_vip_name)

def ask_vip_name(message):
    code = message.text
    msg = bot.send_message(message.chat.id, "Nom:")
    bot.register_next_step_handler(msg, lambda m: ask_vip_desc(m, code))

def ask_vip_desc(message, code):
    name = message.text
    msg = bot.send_message(message.chat.id, "Tavsif:")
    bot.register_next_step_handler(msg, lambda m: ask_vip_video(m, code, name))

def ask_vip_video(message, code, name):
    desc = message.text
    msg = bot.send_message(message.chat.id, "Video:")
    bot.register_next_step_handler(msg, lambda m: save_vip(m, code, name, desc))

def save_vip(message, code, name, desc):
    if not message.video:
        return

    data["vip_movies"][code] = {
        "name": name,
        "desc": desc,
        "file_id": message.video.file_id
    }

    save_data(data)
    bot.send_message(message.chat.id, "⭐ VIP qo‘shildi")

# ---------------- VIP BERISH ----------------
@bot.message_handler(func=lambda m: m.text == "👑 VIP berish")
def give_vip(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "User ID:")
    bot.register_next_step_handler(msg, save_vip_user)

def save_vip_user(message):
    try:
        uid = int(message.text)
        if uid not in data["vip_users"]:
            data["vip_users"].append(uid)
            save_data(data)
            bot.send_message(message.chat.id, "👑 VIP berildi")
        else:
            bot.send_message(message.chat.id, "Bu user allaqachon VIP")
    except:
        bot.send_message(message.chat.id, "❌ Noto‘g‘ri ID")

# ---------------- ADD CHANNEL ----------------
@bot.message_handler(func=lambda m: m.text == "📢 Kanal qo‘shish")
def add_channel(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "Link yoki @username:")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):
    ch = normalize_channel(message.text)

    if ch not in data["channels"]:
        data["channels"].append(ch)
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Qo‘shildi: {ch}")
    else:
        bot.send_message(message.chat.id, "⚠️ Bu kanal bor")

# ---------------- DELETE CHANNEL ----------------
@bot.message_handler(func=lambda m: m.text == "🗑 Kanal o‘chirish")
def del_channel(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id, "Kanal yoz:")
    bot.register_next_step_handler(msg, remove_channel)

def remove_channel(message):
    ch = normalize_channel(message.text)

    if ch in data["channels"]:
        data["channels"].remove(ch)
        save_data(data)
        bot.send_message(message.chat.id, "🗑 O‘chirildi")
    else:
        bot.send_message(message.chat.id, "Topilmadi")

# ---------------- LIST CHANNEL ----------------
@bot.message_handler(func=lambda m: m.text == "📄 Kanal list")
def list_channels(message):
    if message.from_user.id != ADMIN_ID:
        return

    text = "📢 Kanallar:\n\n"
    for ch in data["channels"]:
        text += f"{ch}\n"

    bot.send_message(message.chat.id, text)

# ---------------- FORCE ----------------
@bot.message_handler(func=lambda m: m.text == "✅ Majburiy ON")
def force_on(message):
    if message.from_user.id != ADMIN_ID:
        return

    data["force_sub"] = True
    save_data(data)
    bot.send_message(message.chat.id, "✅ Yoqildi")

@bot.message_handler(func=lambda m: m.text == "❌ Majburiy OFF")
def force_off(message):
    if message.from_user.id != ADMIN_ID:
        return

    data["force_sub"] = False
    save_data(data)
    bot.send_message(message.chat.id, "❌ O‘chirildi")

# ---------------- RUN ----------------
print("🚀 STARTUP BOT ISHLADI")
bot.infinity_polling()