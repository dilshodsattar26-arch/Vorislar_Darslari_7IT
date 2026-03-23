import telebot
from telebot import types
import json, os, threading, time
from flask import Flask

TOKEN = "8762136939:AAHUcOgeHQBYf8MgMCFaC48EKhUNhb4jn88"
ADMIN_ID = 7253285947

bot = telebot.TeleBot(TOKEN)

# ===== DATABASE =====
if not os.path.exists("db.json"):
    with open("db.json", "w") as f:
        json.dump({"users": [], "movies": {}, "channels": []}, f)

def load():
    return json.load(open("db.json"))

def save(data):
    json.dump(data, open("db.json", "w"), indent=4)

# ===== FLASK (RENDER) =====
app = Flask(__name__)

@app.route('/')
def home():
    return "Alive"

def run():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run).start()

# ===== KEEP ALIVE (5 min) =====
def ping():
    while True:
        print("Bot alive...")
        time.sleep(300)

threading.Thread(target=ping).start()

# ===== USER ADD =====
def add_user(uid):
    db = load()
    if uid not in db["users"]:
        db["users"].append(uid)
        save(db)

# ===== OBUNA =====
def check_sub(uid):
    db = load()
    for ch in db["channels"]:
        try:
            st = bot.get_chat_member(ch, uid).status
            if st == "left":
                return False
        except:
            return False
    return True

def sub_menu():
    db = load()
    m = types.InlineKeyboardMarkup()
    for ch in db["channels"]:
        m.add(types.InlineKeyboardButton("📢 Obuna", url=f"https://t.me/{ch.replace('@','')}"))
    m.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
    return m

# ===== MENU =====
def menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kinolar", "📌 Saqlangan kinolar")
    kb.add("🏆 Reyting (Top 10)")
    bot.send_message(chat_id, "🎬 Kino kodini kiriting!", reply_markup=kb)

# ===== START =====
@bot.message_handler(commands=['start'])
def start(m):
    add_user(m.from_user.id)

    if not check_sub(m.from_user.id):
        bot.send_message(m.chat.id, "❗ Obuna bo‘ling", reply_markup=sub_menu())
        return

    menu(m.chat.id)

# ===== CHECK BUTTON =====
@bot.callback_query_handler(func=lambda c: c.data=="check")
def check(c):
    if check_sub(c.from_user.id):
        bot.send_message(c.message.chat.id, "✅ Tasdiqlandi")
        menu(c.message.chat.id)
    else:
        bot.answer_callback_query(c.id, "❗ Obuna bo‘ling")

# ===== KINOLAR BUTTON =====
@bot.message_handler(func=lambda m: m.text=="🎬 Kinolar")
def kinolar(m):
    bot.send_message(m.chat.id, "👉 Kanal:\nhttps://t.me/kinoworlduzchennel")

# ===== KINO KOD =====
@bot.message_handler(func=lambda m: m.text.isdigit())
def movie(m):
    db = load()
    if m.text in db["movies"]:
        mv = db["movies"][m.text]
        bot.send_video(m.chat.id, mv["file"], caption=f"{mv['name']}\n\n{mv['desc']}")
    else:
        bot.send_message(m.chat.id, "❌ Bunday kodli kino topilmadi")

# ===== ADMIN PANEL =====
@bot.message_handler(commands=['admin'])
def admin(m):
    if m.from_user.id != ADMIN_ID:
        return
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Statistika","➕ Kino qo‘shish")
    kb.add("❌ Kino o‘chirish")
    kb.add("➕ Kanal qo‘shish","❌ Kanal o‘chirish")
    bot.send_message(m.chat.id,"⚙️ Admin panel",reply_markup=kb)

# ===== STAT =====
@bot.message_handler(func=lambda m: m.text=="📊 Statistika")
def stat(m):
    db = load()
    bot.send_message(m.chat.id,
        f"👤 Users: {len(db['users'])}\n"
        f"🎬 Kinolar: {len(db['movies'])}\n"
        f"📢 Kanallar: {len(db['channels'])}"
    )

# ===== ADD MOVIE =====
@bot.message_handler(func=lambda m: m.text=="➕ Kino qo‘shish")
def add_movie(m):
    msg = bot.send_message(m.chat.id,"Kino nomi:")
    bot.register_next_step_handler(msg, name_step)

def name_step(m):
    msg = bot.send_message(m.chat.id,"Tavsif:")
    bot.register_next_step_handler(msg, desc_step, m.text)

def desc_step(m,name):
    msg = bot.send_message(m.chat.id,"Video yubor:")
    bot.register_next_step_handler(msg, video_step, name, m.text)

def video_step(m,name,desc):
    if not m.video:
        bot.send_message(m.chat.id,"Video yubor!")
        return
    
    db = load()
    code = str(len(db["movies"])+1)

    db["movies"][code]={
        "name":name,
        "desc":desc,
        "file":m.video.file_id
    }

    save(db)
    bot.send_message(m.chat.id,f"✅ Qo‘shildi\nKod: {code}")

# ===== DELETE MOVIE =====
@bot.message_handler(func=lambda m: m.text=="❌ Kino o‘chirish")
def del_movie(m):
    db = load()
    kb = types.InlineKeyboardMarkup()
    for c,v in db["movies"].items():
        kb.add(types.InlineKeyboardButton(v["name"],callback_data=f"del_{c}"))
    bot.send_message(m.chat.id,"Tanla:",reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_"))
def del_m(c):
    code = c.data.split("_")[1]
    db = load()
    del db["movies"][code]
    save(db)
    bot.answer_callback_query(c.id,"O‘chirildi")

# ===== ADD CHANNEL =====
@bot.message_handler(func=lambda m: m.text=="➕ Kanal qo‘shish")
def add_ch(m):
    msg = bot.send_message(m.chat.id,"@kanal username:")
    bot.register_next_step_handler(msg, save_ch)

def save_ch(m):
    db = load()
    db["channels"].append(m.text)
    save(db)
    bot.send_message(m.chat.id,"✅ Qo‘shildi")

# ===== DELETE CHANNEL =====
@bot.message_handler(func=lambda m: m.text=="❌ Kanal o‘chirish")
def del_ch(m):
    db = load()
    kb = types.InlineKeyboardMarkup()
    for ch in db["channels"]:
        kb.add(types.InlineKeyboardButton(ch,callback_data=f"delch_{ch}"))
    bot.send_message(m.chat.id,"Tanla:",reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delch_"))
def delc(c):
    ch = c.data.split("_")[1]
    db = load()
    db["channels"].remove(ch)
    save(db)
    bot.answer_callback_query(c.id,"O‘chirildi")

# ===== RUN =====
bot.infinity_polling()