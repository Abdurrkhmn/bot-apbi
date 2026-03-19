import telebot
import google.generativeai as genai
import pandas as pd
import requests
import os  # Tambahan untuk membaca sistem keamanan
from io import StringIO
from telebot import types

# --- KONFIGURASI AMAN (PRO LEVEL) ---
# Bot akan mengambil TOKEN dan API KEY dari "Variables" Railway.
# Jika tidak ada (misal di laptop), dia akan pakai nilai default di bawah.
TOKEN_TELEGRAM = os.getenv('TOKEN_TELEGRAM', '8613320694:AAGt5OXlwu632uLM-wjcOoT-DI8-hAPYL60')
API_KEY_GEMINI = os.getenv('API_KEY_GEMINI', 'AIzaSyCois6xAZxXhS7pcLVO4iZ_Qm-OHfdRFEY')
SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSDjdSSIYNX8l2gEsyHZrghM4I7eNeGvO3yj8_oH8aJONArO-KSNBs0iund2rEJp6nPFpk5lv58Tbtz/pub?output=csv'

# Inisialisasi
bot = telebot.TeleBot(TOKEN_TELEGRAM)
genai.configure(api_key=API_KEY_GEMINI)

# Pilih Model Gemini
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-pro')

# Database sederhana untuk membatasi kuota (Limit 5 tanya per user)
user_usage = {}

def ambil_data_sheets():
    try:
        response = requests.get(SHEET_CSV_URL)
        df = pd.read_csv(StringIO(response.text))
        return df
    except:
        return None

@bot.message_handler(commands=['start'])
def welcome(message):
    pesan = (
        "🌟 **Bot Beasiswa APBI**\n\n"
        "Tulis beasiswa atau negara yang kamu cari.\n"
        "Contoh: 'Jepang' atau 'LPDP'\n\n"
        "Limit gratis: 5 pertanyaan/hari."
    )
    bot.reply_to(message, pesan, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.from_user.id
    query = message.text.lower()

    # 1. CEK LIMIT
    user_usage[user_id] = user_usage.get(user_id, 0) + 1
    if user_usage[user_id] > 5:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔓 Buka Akses Unlimited", url="https://saweria.co/apbi"))
        bot.reply_to(message, "⚠️ **Limit Tercapai!**\nUntuk lanjut mencari & konsultasi, silakan aktivasi Premium.", reply_markup=markup)
        return

    # 2. CARI DI GOOGLE SHEETS
    df = ambil_data_sheets()
    found = False
    pesan_hasil = ""

    if df is not None:
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        results = df[mask]
        
        if not results.empty:
            found = True
            pesan_hasil = "✅ **Data Ditemukan di APBI:**\n\n"
            for _, row in results.head(3).iterrows():
                pesan_hasil += f"🎓 *{row['Nama_Beasiswa']}*\n📍 {row['Negara']} | ⏳ {row['Deadline']}\n🔗 [Klik Info]({row['Link_Info']})\n\n"

    # 3. JIKA TIDAK ADA DI SHEETS, TANYA AI
    if not found:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            response = model.generate_content(f"Berikan info singkat beasiswa {query} dan sarankan mentoring di APBI.")
            pesan_hasil = f"🔍 **Info AI:**\n\n{response.text}"
        except Exception as e:
            pesan_hasil = "❌ AI sedang sibuk. Coba cari kata kunci lain."

    # 4. CTA MENTORING (BISNIS KONVERSI)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💎 Daftar Mentoring (Berbayar)", url="https://wa.me/628123456789"))
    
    bot.reply_to(message, pesan_hasil, reply_markup=markup, parse_mode="Markdown")

print("🚀 Bot APBI Berjalan Aman & Autopilot...")
bot.polling()