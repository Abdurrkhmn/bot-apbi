import telebot
import google.generativeai as genai
import pandas as pd
import requests
import os
from io import StringIO
from telebot import types

# ==========================================================
# 1. KONFIGURASI API & SERVER
# ==========================================================
# Mengambil token dari Environment Variables (Lebih Aman)
TOKEN_TELEGRAM = os.getenv('TOKEN_TELEGRAM')
API_KEY_GEMINI = os.getenv('API_KEY_GEMINI')
SHEET_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSDjdSSIYNX8l2gEsyHZrghM4I7eNeGvO3yj8_oH8aJONArO-KSNBs0iund2rEJp6nPFpk5lv58Tbtz/pub?output=csv'

# Proteksi: Jika variabel kosong, program berhenti dengan pesan jelas
if not TOKEN_TELEGRAM or not API_KEY_GEMINI:
    raise ValueError("❌ ERROR: TOKEN_TELEGRAM atau API_KEY_GEMINI belum diatur di server!")

bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Inisialisasi AI Gemini
genai.configure(api_key=API_KEY_GEMINI)
model = genai.GenerativeModel('gemini-1.5-flash')

# Database sementara untuk limit user (Reset jika bot restart)
user_usage = {}

# ==========================================================
# 2. FUNGSI PENGAMBILAN DATA (GOOGLE SHEETS)
# ==========================================================
def ambil_data_sheets():
    """Fungsi untuk menarik data dari Google Sheets CSV secara Real-time"""
    try:
        # Ditambahkan timeout 10 detik agar bot tidak 'hang' jika koneksi lambat
        response = requests.get(SHEET_CSV_URL, timeout=10)
        df = pd.read_csv(StringIO(response.text))
        return df
    except Exception as e:
        print(f"❌ Error saat sinkronisasi data Sheets: {e}")
        return None

# ==========================================================
# 3. HANDLER PERINTAH /START
# ==========================================================
@bot.message_handler(commands=['start'])
def welcome(message):
    pesan = (
        "🌟 **Asisten Pintar Beasiswa APBI**\n\n"
        "Halo! Silakan ketik nama beasiswa atau negara tujuan.\n"
        "Contoh: 'Jepang' atau 'LPDP'\n\n"
        "🎁 **Limit Gratis:** 5 pertanyaan/hari."
    )
    bot.reply_to(message, pesan, parse_mode="Markdown")

# ==========================================================
# 4. HANDLER PESAN TEKS (LOGIKA UTAMA)
# ==========================================================
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.from_user.id
    query = message.text.lower()

    # --- STRATEGI BISNIS: PEMBATASAN KUOTA ---
    user_usage[user_id] = user_usage.get(user_id, 0) + 1
    if user_usage[user_id] > 5:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔓 Aktifkan Akses Premium", url="https://www.instagram.com/apbiinternasional/"))
        bot.reply_to(message, "⚠️ **Limit Tercapai!**\nSilakan hubungi admin untuk mendapatkan akses unlimited.", reply_markup=markup, parse_mode="Markdown")
        return

    # --- PENCARIAN DI DATA INTERNAL (GOOGLE SHEETS) ---
    df = ambil_data_sheets()
    found = False
    pesan_hasil = ""

    if df is not None:
        # Mencari keyword di seluruh kolom secara cerdas (case insensitive)
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        results = df[mask]
        
        if not results.empty:
            found = True
            pesan_hasil = "✅ **Data Ditemukan di Database APBI:**\n\n"
            for _, row in results.head(3).iterrows():
                # Membersihkan data dari nilai kosong (NaN) agar tampilan rapi
                nama = row.get('Nama_Beasiswa', 'Beasiswa')
                negara = row.get('Negara', '-')
                deadline = row.get('Deadline', '-')
                link = row.get('Link_Info', '#')
                
                pesan_hasil += (
                    f"🎓 *{nama}*\n"
                    f"📍 Negara: {negara}\n"
                    f"⏳ Deadline: {deadline}\n"
                    f"🔗 [Info Selengkapnya]({link})\n\n"
                )

    # --- BACKUP: JIKA TIDAK ADA DI SHEETS, GUNAKAN AI ---
    if not found:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            prompt = f"Berikan info singkat tentang beasiswa {query} dan sarankan mentoring di APBI."
            response = model.generate_content(prompt)
            # Batasi teks AI agar tidak melebihi limit pesan Telegram
            pesan_hasil = f"🔍 **Hasil Analisis AI:**\n\n{response.text[:3500]}"
        except Exception:
            pesan_hasil = "❌ Sistem AI sedang sibuk. Silakan coba lagi nanti atau hubungi Admin."

    # --- STRATEGI KONVERSI: TOMBOL EMAIL ---
    # Perubahan dari WhatsApp ke Email sesuai request Anda
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💎 Daftar Mentoring Sekarang", url="mailto:apbiinternasional@gmail.com"))
    
    # --- PENGIRIMAN PESAN FINAL ---
    try:
        bot.reply_to(message, pesan_hasil, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        # Fallback: Jika Markdown gagal (karena ada karakter aneh dari AI), kirim teks biasa
        bot.reply_to(message, pesan_hasil, reply_markup=markup)

# ==========================================================
# 5. MENJALANKAN BOT
# ==========================================================
print("🚀 Bot APBI Berhasil Dijalankan (Mode Email CTA)...")
# Menggunakan infinity_polling agar bot otomatis restart jika terjadi error ringan
bot.infinity_polling()