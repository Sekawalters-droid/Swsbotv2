import time
import json
import os
import logging
from datetime import datetime, timedelta
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Konfigurasi Token, Admin & QRIS
API_TOKEN = "9272114074:AAF1vGyC0-VeIy-tEWrSvZD6TiMpnlZIwi8"
ADMIN_ID = 8678227779             # Ganti dengan Telegram ID kamu (angka)
ADMIN_USERNAME = "SekaWalters"  # Ganti username Telegram admin (tanpa @)
QRIS_IMAGE_URL = "https://ibb.co.com/KjP6ZHqW"

bot = telebot.TeleBot(API_TOKEN)
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        initial_data = {"rentals": {}, "groups": {}, "schedules": {}}
        with open(DB_FILE, "w") as f:
            json.dump(initial_data, f, indent=4)
        return initial_data
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            rentals = {int(k): v for k, v in data.get("rentals", {}).items()}
            groups = {int(k): v for k, v in data.get("groups", {}).items()}
            schedules = {int(k): v for k, v in data.get("schedules", {}).items()}
            return {"rentals": rentals, "groups": groups, "schedules": schedules}
    except Exception as e:
        logging.error(f"Gagal membaca database: {e}")
        return {"rentals": {}, "groups": {}, "schedules": {}}

def save_db(data):
    formatted_data = {
        "rentals": {str(k): v for k, v in data["rentals"].items()},
        "groups": {str(k): v for k, v in data["groups"].items()},
        "schedules": {str(k): v for k, v in data["schedules"].items()}
    }
    with open(DB_FILE, "w") as f:
        json.dump(formatted_data, f, indent=4)

def get_main_menu(uid):
    is_admin = (uid == ADMIN_ID)
    db = load_db()
    
    is_client = False
    if uid in db["rentals"]:
        now = datetime.now()
        valid_rentals = [r for r in db["rentals"][uid] if datetime.fromisoformat(r["expired_at"]) > now]
        db["rentals"][uid] = valid_rentals
        save_db(db)
        if valid_rentals:
            is_client = True

    markup = InlineKeyboardMarkup()
    
    if is_client:
        markup.add(InlineKeyboardButton("⚙️ Atur Grup Tujuan Share (Max 10)", callback_data="client_manage_groups"))
        markup.add(InlineKeyboardButton("⏰ Atur Jadwal On/Off Otomatis", callback_data="client_schedule_menu"))
        markup.add(InlineKeyboardButton("📢 Kirim & Share Bahan Promosi", callback_data="client_share_menu"))
        markup.add(InlineKeyboardButton("⏳ Cek Sisa Masa Sewa Saya", callback_data="client_check_status"))
        markup.add(InlineKeyboardButton("🔄 Perpanjang Masa Sewa (QRIS)", callback_data="client_buy_qris"))
    else:
        markup.add(InlineKeyboardButton("🛒 Beli / Sewa Jasa Share (QRIS)", callback_data="client_buy_qris"))
        markup.add(InlineKeyboardButton("⭐ Upgrade Premium (Tanpa Watermark Rp 25rb)", url=f"https://t.me/{ADMIN_USERNAME}"))
        markup.add(InlineKeyboardButton("ℹ️ Status: Belum Punya Sewa Aktif", callback_data="client_check_status"))
        
    markup.add(InlineKeyboardButton("📞 Hubungi Admin SWSTORE", url=f"https://t.me/{ADMIN_USERNAME}"))
    
    if is_admin:
        markup.insert(InlineKeyboardButton("⚡ [PANEL ADMIN] Tambah Sewa Klien", callback_data="admin_add_rental"))
        
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    bot.send_message(
        uid,
        "🤖 **SWSTORE - JASA SEWA SHARE & BROADCAST**\n"
        "Pusat otomatisasi sebar promosi grup Telegram.\n"
        "Silakan gunakan tombol di bawah ini:",
        reply_markup=get_main_menu(uid),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def back_home(call):
    uid = call.from_user.id
    try:
        bot.edit_message_text(
            "🏠 **SWSTORE - Menu Utama**\nPilih menu di bawah:",
            chat_id=uid,
            message_id=call.message.message_id,
            reply_markup=get_main_menu(uid),
            parse_mode="Markdown"
        )
    except:
        bot.send_message(
            uid,
            "🏠 **SWSTORE - Menu Utama**",
            reply_markup=get_main_menu(uid),
            parse_mode="Markdown"
        )
    bot.answer_callback_query(call.id)

# --- MENU PEMBAYARAN QRIS (Ganti Pesan Tanpa Numpuk) ---
@bot.callback_query_handler(func=lambda call: call.data == "client_buy_qris")
def client_buy_qris(call):
    uid = call.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📸 Sudah Transfer & Kirim Bukti", callback_data="send_proof_prompt"))
    markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="back_home"))
    
    qris_text = (
        "💳 **PEMBAYARAN QRIS / DANA - SWSTORE**\n\n"
        "• Sewa Regular (Dengan Watermark SWSTORE)\n"
        "• Sewa Premium (Tanpa Watermark): **Rp 25.000 / Bulan**\n\n"
        "Silakan scan QR di atas atau transfer sesuai paket, lalu klik tombol di bawah."
    )
    try:
        # Hapus pesan teks sebelumnya dan kirim foto QRIS baru sebagai ganti pesan lama
        bot.delete_message(uid, call.message.message_id)
        bot.send_photo(uid, photo=QRIS_IMAGE_URL, caption=qris_text, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.edit_message_text(f"{qris_text}", chat_id=uid, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "send_proof_prompt")
def send_proof_prompt(call):
    uid = call.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Batal", callback_data="back_home"))
    
    # Jika sebelumnya berupa foto QRIS, hapus lalu kirim instruksi teks atau edit caption
    try:
        bot.delete_message(uid, call.message.message_id)
    except:
        pass
        
    msg = bot.send_message(
        uid,
        "📸 **Kirim Bukti Pembayaran**\n\n"
        "Silakan kirimkan **foto / screenshot bukti transfer** kamu ke chat ini:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_payment_proof)
    bot.answer_callback_query(call.id)

def process_payment_proof(message):
    uid = message.from_user.id
    if not message.photo:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="back_home"))
        msg = bot.send_message(uid, "❌ Mohon kirimkan dalam bentuk **FOTO / SCREENSHOT** bukti transfer, bukan teks.", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_payment_proof)
        return
        
    photo_file_id = message.photo[-1].file_id
    username = message.from_user.username or "Tanpa Username"
    
    bot.send_message(uid, "✅ Bukti pembayaran berhasil dikirim ke Admin SWSTORE! Mohon tunggu sebentar, admin akan segera memverifikasi akunmu.")
    
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(
        InlineKeyboardButton("✅ ACC Reg (1 Hari)", callback_data=f"acc_{uid}_1_False"),
        InlineKeyboardButton("✅ ACC Reg (30 Hari)", callback_data=f"acc_{uid}_30_False")
    )
    admin_markup.add(
        InlineKeyboardButton("⭐ ACC Premium (30 Hari)", callback_data=f"acc_{uid}_30_True"),
        InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{uid}")
    )
    
    bot.send_photo(
        ADMIN_ID,
        photo=photo_file_id,
        caption=f"🔔 **ADA BUKTI PEMBAYARAN MASUK!**\n\n"
                f"👤 Dari User ID: `{uid}`\n"
                f"🔗 Username: @{username}\n\n"
                f"Pilih jenis aktivasi paket untuk klien:",
        reply_markup=admin_markup,
        parse_mode="Markdown"
    )

# --- ADMIN ACC / REJECT ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(("acc_", "reject_")))
def admin_handle_payment(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak!", show_alert=True)
        return
        
    parts = call.data.split("_")
    action = parts[0]
    target_id = int(parts[1])
    
    if action == "acc":
        days = int(parts[2])
        is_premium = (parts[3] == "True")
        expired_time = datetime.now() + timedelta(days=days)
        status_label = "Premium (Tanpa Watermark)" if is_premium else "Regular"
        package_name = f"Paket {status_label} {days} Hari"
        
        db = load_db()
        if target_id not in db["rentals"]:
            db["rentals"][target_id] = []
            
        db["rentals"][target_id].append({
            "name": package_name,
            "expired_at": expired_time.isoformat(),
            "is_premium": is_premium
        })
        save_db(db)
        
        try:
            bot.edit_message_caption(
                caption=f"{call.message.caption}\n\n✅ **STATUS: DI-ACC ({status_label} - {days} HARI)**",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
        except:
            pass
            
        bot.answer_callback_query(call.id, "Berhasil mengaktifkan sewa klien!")
        try:
            bot.send_message(
                target_id,
                f"🎉 **Pembayaran Dikonfirmasi & Disetujui!**\n\n"
                f"📦 Paket: *{package_name}*\n"
                f"⏳ Masa Aktif: *{days} Hari*\n\n"
                f"Silakan buka bot dan atur grup target promosimu!",
                parse_mode="Markdown"
            )
        except:
            pass
    else:
        try:
            bot.edit_message_caption(
                caption=f"{call.message.caption}\n\n❌ **STATUS: DITOLAK / PEMBAYARAN TIDAK VALID**",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
        except:
            pass
        bot.answer_callback_query(call.id, "Pembayaran ditolak.")
        try:
            bot.send_message(target_id, "❌ **Maaf, bukti pembayaran kamu ditolak/tidak valid oleh Admin.**", parse_mode="Markdown")
        except:
            pass

# --- PENGATURAN GRUP TARGET (Max 10) ---
@bot.callback_query_handler(func=lambda call: call.data == "client_manage_groups")
def client_manage_groups(call):
    uid = call.from_user.id
    db = load_db()
    
    if uid not in db["groups"]:
        db["groups"][uid] = []
        save_db(db)
        
    groups = db["groups"][uid]
    text = f"⚙️ **Pengaturan Grup Target Share ({len(groups)}/10)**\n\n"
    if groups:
        text += "Daftar ID Grup Tersimpan:\n"
        for idx, g in enumerate(groups, 1):
            text += f"{idx}. `{g}`\n"
    else:
        text += "Belum ada grup yang ditambahkan.\n"
        
    markup = InlineKeyboardMarkup()
    if len(groups) < 10:
        markup.add(InlineKeyboardButton("➕ Tambah ID Grup", callback_data="add_group_prompt"))
    if groups:
        markup.add(InlineKeyboardButton("🗑️ Reset / Hapus Semua Grup", callback_data="reset_groups"))
    markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="back_home"))
    
    bot.edit_message_text(text, chat_id=uid, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "reset_groups")
def reset_groups(call):
    db = load_db()
    db["groups"][call.from_user.id] = []
    save_db(db)
    bot.answer_callback_query(call.id, "Semua ID grup berhasil dikosongkan!", show_alert=True)
    client_manage_groups(call)

@bot.callback_query_handler(func=lambda call: call.data == "add_group_prompt")
def add_group_prompt(call):
    uid = call.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Batal", callback_data="client_manage_groups"))
    
    bot.delete_message(uid, call.message.message_id)
    msg = bot.send_message(
        uid,
        "➕ **Tambah ID Grup Promosi**\n\n"
        "Silakan kirimkan **ID Grup** (contoh: `-1001234567890`) ke chat ini:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_client_group_input)
    bot.answer_callback_query(call.id)

def process_client_group_input(message):
    uid = message.from_user.id
    group_input = message.text.strip()
    
    db = load_db()
    if uid not in db["groups"]:
        db["groups"][uid] = []
        
    if len(db["groups"][uid]) >= 10:
        bot.send_message(uid, "❌ Maksimal penyimpanan grup sudah mencapai batas (10 grup).")
        return
        
    db["groups"][uid].append(group_input)
    save_db(db)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⚙️ Kembali ke Pengaturan Grup", callback_data="client_manage_groups"))
    markup.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="back_home"))
    
    bot.send_message(uid, f"✅ Berhasil menambahkan ID grup: `{group_input}`\nTotal tersimpan: {len(db['groups'][uid])}/10 grup.", reply_markup=markup, parse_mode="Markdown")

# --- JADWAL ON/OFF OTOMATIS ---
@bot.callback_query_handler(func=lambda call: call.data == "client_schedule_menu")
def client_schedule_menu(call):
    uid = call.from_user.id
    db = load_db()
    
    sched = db.get("schedules", {}).get(uid)
    text = "⏰ **Pengaturan Jadwal On/Off Otomatis Broadcast**\n\n"
    if sched:
        text += f"🟢 Status: *AKTIF*\n📥 Jam Mulai: `{sched['start']}`\n📤 Jam Berhenti: `{sched['end']}`\n\n"
    else:
        text += "🔴 Status: *BELUM DIATUR*\n\n"
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✏️ Set / Ubah Jadwal Jam", callback_data="set_schedule_prompt"))
    if sched:
        markup.add(InlineKeyboardButton("🗑️ Matikan / Hapus Jadwal", callback_data="remove_schedule"))
    markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="back_home"))
    
    bot.edit_message_text(text, chat_id=uid, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "remove_schedule")
def remove_schedule(call):
    uid = call.from_user.id
    db = load_db()
    if "schedules" in db and uid in db["schedules"]:
        del db["schedules"][uid]
        save_db(db)
    bot.answer_callback_query(call.id, "Jadwal otomatis berhasil dinonaktifkan!", show_alert=True)
    client_schedule_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "set_schedule_prompt")
def set_schedule_prompt(call):
    uid = call.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Batal", callback_data="client_schedule_menu"))
    
    bot.delete_message(uid, call.message.message_id)
    msg = bot.send_message(
        uid,
        "⏰ **Atur Jam Mulai Broadcast**\n\n"
        "Silakan masukkan **Jam Mulai** dalam format 24 jam (contoh: `06:00`):",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_start_time)
    bot.answer_callback_query(call.id)

def process_start_time(message):
    uid = message.from_user.id
    time_input = message.text.strip()
    if ":" not in time_input or len(time_input) != 5:
        msg = bot.send_message(uid, "❌ Format waktu salah! Gunakan format HH:MM (contoh: `06:00`). Masukkan ulang:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_start_time)
        return
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Batal", callback_data="client_schedule_menu"))
    msg = bot.send_message(uid, f"✅ Jam Mulai disetel: `{time_input}`\n\nSekarang masukkan **Jam Berhenti / Selesai** (contoh: `07:00`):", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: process_end_time(m, time_input))

def process_end_time(message, start_time):
    uid = message.from_user.id
    end_input = message.text.strip()
    if ":" not in end_input or len(end_input) != 5:
        msg = bot.send_message(uid, "❌ Format waktu salah! Gunakan format HH:MM (contoh: `07:00`). Masukkan ulang:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_end_time(m, start_time))
        return
        
    db = load_db()
    if "schedules" not in db:
        db["schedules"] = {}
    db["schedules"][uid] = {"start": start_time, "end": end_input}
    save_db(db)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⏰ Menu Jadwal", callback_data="client_schedule_menu"))
    markup.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="back_home"))
    
    bot.send_message(uid, f"🎉 **Berhasil Menyimpan Jadwal Otomatis!**\n🟢 Mulai: `{start_time}`\n🔴 Berhenti: `{end_input}`", reply_markup=markup, parse_mode="Markdown")

# --- BROADCAST & CEK STATUS ---
@bot.callback_query_handler(func=lambda call: call.data == "client_share_menu")
def client_share_menu(call):
    uid = call.from_user.id
    db = load_db()
    
    if not db["rentals"].get(uid):
        bot.answer_callback_query(call.id, "Masa sewa kamu sudah habis!", show_alert=True)
        return
    groups = db["groups"].get(uid, [])
    if not groups:
        bot.answer_callback_query(call.id, "Kamu belum memasukkan ID grup target sama sekali!", show_alert=True)
        return
        
    scheds = db.get("schedules", {})
    if uid in scheds:
        now_time_str = datetime.now().strftime("%H:%M")
        start_t = scheds[uid]["start"]
        end_t = scheds[uid]["end"]
        if not (start_t <= now_time_str <= end_t):
            bot.answer_callback_query(call.id, f"⏰ Jadwal aktif antara {start_t} s.d {end_t}. Sekarang jam {now_time_str}.", show_alert=True)
            return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛡️ Auto-Aman (Smart Anti-Spam / Delay 15s)", callback_data="speed_15"))
    markup.add(InlineKeyboardButton("⚡ Fast (10 Detik / Pesan)", callback_data="speed_10"))
    markup.add(InlineKeyboardButton("🛡️ Normal (3 Menit / Pesan)", callback_data="speed_180"))
    markup.add(InlineKeyboardButton("🐢 Slow (10 Menit / Pesan)", callback_data="speed_600"))
    markup.add(InlineKeyboardButton("❌ Batal", callback_data="back_home"))
    
    bot.edit_message_text("⏱️ **Pilih Mode Kecepatan / Jeda Waktu Share**:", chat_id=uid, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("speed_"))
def process_speed_selection(call):
    uid = call.from_user.id
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Batal", callback_data="back_home"))
    
    bot.delete_message(uid, call.message.message_id)
    msg = bot.send_message(
        uid,
        f"📢 **Kirim Bahan Promosi Kamu**\n\n"
        f"Silakan kirimkan teks, foto, atau poster promosi yang ingin disebar sekarang:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    # Ambil nilai jeda berdasarkan callback data
    delay_seconds = int(call.data.replace("speed_", ""))
    bot.register_next_step_handler(msg, lambda m: process_client_broadcast(m, delay_seconds))
    bot.answer_callback_query(call.id)

def process_client_broadcast(message, delay_seconds):
    uid = message.from_user.id
    db = load_db()
    groups = db["groups"].get(uid, [])
    
    now = datetime.now()
    is_premium = False
    if uid in db["rentals"]:
        for r in db["rentals"][uid]:
            if datetime.fromisoformat(r["expired_at"]) > now and r.get("is_premium", False):
                is_premium = True
                break

    status_msg = bot.send_message(uid, f"🚀 **Memulai Broadcast...**\nTarget: {len(groups)} Grup.", parse_mode="Markdown")
    
    success = 0
    fail = 0
    for idx, gid in enumerate(groups, 1):
        try:
            target_gid = int(gid) if gid.startswith("-") or gid.isdigit() else gid
            if message.text and not is_premium:
                watermarked_text = message.text + f"\n\n──────────────────\n🚀 *Broadcast by SWSTORE*\n👉 Sewa Bot Promosi? Hubungi: @{ADMIN_USERNAME}"
                bot.send_message(target_gid, watermarked_text, parse_mode="Markdown")
            else:
                sent_msg = bot.copy_message(target_gid, uid, message.message_id)
                if not is_premium and sent_msg:
                    try:
                        bot.edit_message_caption(
                            chat_id=target_gid,
                            message_id=sent_msg.message_id,
                            caption=(message.caption or "") + f"\n\n──────────────────\n🚀 *Broadcast by SWSTORE*\n👉 @{ADMIN_USERNAME}",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
            success += 1
            if idx < len(groups):
                time.sleep(delay_seconds)
        except Exception as e:
            logging.error(f"Gagal kirim ke {gid}: {e}")
            fail += 1
            
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏠 Menu Utama", callback_data="back_home"))
    bot.send_message(uid, f"✅ **Broadcast Selesai!**\n✔️ Berhasil: {success}\n❌ Gagal: {fail}", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "client_check_status")
def client_check_status(call):
    uid = call.from_user.id
    db = load_db()
    
    if uid in db["rentals"]:
        now = datetime.now()
        db["rentals"][uid] = [r for r in db["rentals"][uid] if datetime.fromisoformat(r["expired_at"]) > now]
        save_db(db)
        
    rentals = db["rentals"].get(uid, [])
    markup = InlineKeyboardMarkup()
    
    if not rentals:
        markup.add(InlineKeyboardButton("🛒 Beli / Sewa Jasa Share (QRIS)", callback_data="client_buy_qris"))
        markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="back_home"))
        bot.edit_message_text("📭 Kamu tidak memiliki paket sewa aktif.", chat_id=uid, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        return
        
    text = "⏳ **Status Masa Sewa Jasa Share Kamu:**\n\n"
    for r in rentals:
        sisa = datetime.fromisoformat(r["expired_at"]) - datetime.now()
        status_paket = "⭐ Premium (Tanpa Watermark)" if r.get("is_premium", False) else "📌 Regular"
        text += f"📦 *{r['name']}*\n🏷️ {status_paket}\n⏳ Sisa: {sisa.days} hari {sisa.seconds//3600} jam lagi\n\n"
        
    markup.add(InlineKeyboardButton("🔙 Kembali", callback_data="back_home"))
    bot.edit_message_text(text, chat_id=uid, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- PANEL ADMIN ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_rental")
def admin_add_rental(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Akses ditolak!", show_alert=True)
        return
    bot.delete_message(ADMIN_ID, call.message.message_id)
    msg = bot.send_message(ADMIN_ID, "👤 Masukkan **Telegram ID Klien** (berupa angka):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_get_id)
    bot.answer_callback_query(call.id)

def admin_get_id(message):
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Harus berupa angka! Masukkan ID klien lagi:")
        bot.register_next_step_handler(msg, admin_get_id)
        return
    target_id = int(message.text)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1 Hari", callback_data=f"setdays_{target_id}_1"), InlineKeyboardButton("3 Hari", callback_data=f"setdays_{target_id}_3"))
    markup.add(InlineKeyboardButton("7 Hari", callback_data=f"setdays_{target_id}_7"), InlineKeyboardButton("30 Hari", callback_data=f"setdays_{target_id}_30"))
    bot.send_message(message.chat.id, "⏳ Pilih **Durasi Hari** sewa klien:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("setdays_"))
def admin_get_days(call):
    parts = call.data.split("_")
    target_id = parts[1]
    days = parts[2]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📌 Regular (Watermark)", callback_data=f"setprem_{target_id}_{days}_False"))
    markup.add(InlineKeyboardButton("⭐ Premium (Tanpa Watermark)", callback_data=f"setprem_{target_id}_{days}_True"))
    bot.edit_message_text("⭐ Pilih **Tipe Paket** untuk klien:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("setprem_"))
def admin_get_premium(call):
    parts = call.data.split("_")
    target_id, days, is_premium = parts[1], int(parts[2]), (parts[3] == "True")
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, "📦 Ketik nama paket jasa share (contoh: *Paket SWSTORE 10 Grup*):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: admin_finish_rental(m, target_id, days, is_premium))
    bot.answer_callback_query(call.id)

def admin_finish_rental(message, target_id, duration_days, is_premium):
    target_id = int(target_id)
    package_name = message.text
    expired_time = datetime.now() + timedelta(days=duration_days)
    
    db = load_db()
    if target_id not in db["rentals"]:
        db["rentals"][target_id] = []
        
    db["rentals"][target_id].append({
        "name": package_name,
        "expired_at": expired_time.isoformat(),
        "is_premium": is_premium
    })
    save_db(db)
    
    status_type = "⭐ Premium (Tanpa Watermark)" if is_premium else "📌 Regular"
    bot.send_message(message.chat.id, f"✅ **Berhasil Mengaktifkan Sewa!**\nID: `{target_id}`\nDurasi: {duration_days} Hari\nTipe: {status_type}", parse_mode="Markdown", reply_markup=get_main_menu(message.from_user.id))
    try:
        bot.send_message(target_id, f"🎉 **Paket Sewa Jasa Share SWSTORE Telah Aktif!**\n📦 Paket: *{package_name}*\n⏳ Durasi: *{duration_days} Hari*", parse_mode="Markdown")
    except:
        pass

if __name__ == "__main__":
    print("Bot SWSTORE (Telebot) Berjalan...")
    bot.infinity_polling()
