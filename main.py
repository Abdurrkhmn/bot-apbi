import telebot
import google.generativeai as genai
import pandas as pd
import requests
import os  # Digunakan untuk membaca Variables dari server
from io import StringIO
from telebot import types

# --- KONFIGURASI AMAN (STANDAR INDUSTRI) ---
# Kode ini tidak menyimpan angka token secara langsung. 
# Server (Railway/Koyeb) akan mengisi nilai ini secara otomatis.
TOKEN_TELEGRAM = os.getenv('TOKEN_TELEGRAM')
API_KEY_GEMINI = os.getenv('API_KEY_GEMINI')
SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSDjdSSIYNX8l2gEsyHZrghM4I7eNeGvO3yj8_oH8aJONArO-KSNBs0iund2rEJp6nPFpk5lv58Tbtz/pub?output=csv'

# Inisialisasi Bot dan AI
# Jika TOKEN atau API_KEY kosong, bot akan memberikan peringatan di log server
if not TOKEN_TELEGRAM or not API_KEY_GEMINI:
    print("❌ ERROR: TOKEN_TELEGRAM atau API_KEY_GEMINI belum diisi di Variables server!")

bot = telebot.TeleBot(TOKEN_TELEGRAM)
genai.configure(api_key=API_KEY_GEMINI)

# Pilih Model Gemini (Flash 1.5 lebih cepat dan murah)
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
    except Exception as e:
        print(f"❌ Error ambil data Sheets: {e}")
        return None

@bot.message_handler(commands=['start'])
def welcome(message):
    pesan = (
        "🌟 **Asisten Pintar Beasiswa APBI**\n\n"
        "Tulis beasiswa atau negara nang pian cari.\n"
        "Contoh: 'Jepang' atau 'LPDP'\n\n"
        "🎁Limit gratis: 5 pertanyaan/hari."
    )
    bot.reply_to(message, pesan, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.from_user.id
    query = message.text.lower()

    # 1. CEK LIMIT (STRATEGI BISNIS: PEMBATASAN)
    user_usage[user_id] = user_usage.get(user_id, 0) + 1
    if user_usage[user_id] > 5:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔓 Buka Akses Unlimited", url="https://www.instagram.com/apbiinternasional/"))
        bot.reply_to(message, "⚠️ **Limit Tercapai!**\nUntuk lanjut mencari & konsultasi, silakan aktivasi Premium.", reply_markup=markup)
        return

    # 2. CARI DI GOOGLE SHEETS (DATA UTAMA APBI)
    df = ambil_data_sheets()
    found = False
    pesan_hasil = ""

    if df is not None:
        # Mencari keyword di seluruh kolom secara cerdas
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        results = df[mask]
        
        if not results.empty:
            found = True
            pesan_hasil = "✅ **Data Ditemukan di APBI:**\n\n"
            for _, row in results.head(3).iterrows():
                # Pastikan nama kolom di Google Sheets kamu sesuai (Nama_Beasiswa, Negara, Deadline, Link_Info)
                pesan_hasil += f"🎓 *{row.get('Nama_Beasiswa', 'Beasiswa')}*\n📍 {row.get('Negara', '-')} | ⏳ {row.get('Deadline', '-')}\n🔗 [Klik Info]({row.get('Link_Info', '#')})\n\n"

    # 3. JIKA TIDAK ADA DI SHEETS, GUNAKAN AI (BACKUP)
    if not found:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            response = model.generate_content(f"Berikan info singkat beasiswa {query} dan sarankan mentoring di APBI.")
            pesan_hasil = f"🔍 **Info AI:**\n\n{response.text}"
        except Exception as e:
            pesan_hasil = "❌ AI sedang sibuk. Coba cari kata kunci lain atau hubungi admin."

    # 4. CTA MENTORING (STRATEGI BISNIS: KONVERSI)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💎 Daftar Mentoring (Berbayar)", url="https://wa.me/6285821854972"))
    
    bot.reply_to(message, pesan_hasil, reply_markup=markup, parse_mode="Markdown")

# Jalankan Bot
print("🚀 Bot APBI Berjalan Aman & Autopilot...")
bot.polling(none_stop=True)