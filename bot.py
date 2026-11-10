import os
import re
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
REQUIRED_CHANNEL = "@Wallet_BANI"

CURRENCIES = {
    "ton":    {"name": "TON",    "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 0.03, "min_wd": 0.15, "wd_fee": 0.05, "min_cv": 0.07},
    "tron":   {"name": "TRON",   "wallet": "TZ6DHXDJACNxiXpQL7anhpWoc1Lux6PwnK",                  "min_dep": 0.1,  "min_wd": 1.3,  "wd_fee": 0.3,  "min_cv": 1},
    "tether": {"name": "TETHER", "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 0.04, "min_wd": 0.15, "wd_fee": 0.03, "min_cv": 0.06},
    "dogez":  {"name": "DOGEZ",  "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 100,  "min_wd": 0,    "wd_fee": 0,    "min_cv": 0},
    "not":    {"name": "NOT",    "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 10,   "min_wd": 30,   "wd_fee": 12,   "min_cv": 30},
    "stars":  {"name": "STARS",  "wallet": "@MMAD_Tek",                                          "min_dep": 0,    "min_wd": 15,   "wd_fee": 0,    "min_cv": 2},
}

def db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def query(sql, params=None, fetch=True):
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if fetch and cur.description:
                return cur.fetchall()
            conn.commit()
            return None
    finally:
        conn.close()

def get_user(user_id):
    r = query("select * from users where telegram_id=%s", (user_id,))
    return r[0] if r else None

def ensure_user(user_id, username):
    if not get_user(user_id):
        query("insert into users (telegram_id, username) values (%s,%s)", (user_id, username), fetch=False)

def get_state(user_id):
    r = query("select * from user_states where telegram_id=%s", (user_id,))
    return r[0] if r else None

def set_state(user_id, state, data=None):
    query("""
        insert into user_states (telegram_id, state, data) values (%s,%s,%s)
        on conflict (telegram_id) do update set state=excluded.state, data=excluded.data
    """, (user_id, state, Json(data or {})), fetch=False)

def clear_state(user_id):
    query("delete from user_states where telegram_id=%s", (user_id,), fetch=False)

# ============ منوها ============
main_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("👛 کیف پول", callback_data="wallet")],
    [InlineKeyboardButton("🎁 ایردراپ", callback_data="airdrop")],
    [InlineKeyboardButton("🎟 خرید گیفت", callback_data="gift")],
    [InlineKeyboardButton("💱 ارز ها", callback_data="currencies")],
])

wallet_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("📊 موجودی ها", callback_data="balances")],
    [InlineKeyboardButton("🔄 تبدیل", callback_data="convert")],
    [InlineKeyboardButton("📤 برداشت", callback_data="withdraw")],
    [InlineKeyboardButton("📥 واریز", callback_data="deposit")],
    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
])

deposit_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("TON", callback_data="dep_ton")],
    [InlineKeyboardButton("TRON", callback_data="dep_tron")],
    [InlineKeyboardButton("TETHER", callback_data="dep_tether")],
    [InlineKeyboardButton("DOGEZ", callback_data="dep_dogez")],
    [InlineKeyboardButton("NOT", callback_data="dep_not")],
    [InlineKeyboardButton("STARS", callback_data="dep_stars")],
    [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet")],
])

withdraw_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("TON", callback_data="wd_ton")],
    [InlineKeyboardButton("TRON", callback_data="wd_tron")],
    [InlineKeyboardButton("TETHER", callback_data="wd_tether")],
    [InlineKeyboardButton("NOT", callback_data="wd_not")],
    [InlineKeyboardButton("STARS", callback_data="wd_stars")],
    [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet")],
])

convert_from_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("TON", callback_data="cv_ton")],
    [InlineKeyboardButton("TRON", callback_data="cv_tron")],
    [InlineKeyboardButton("TETHER", callback_data="cv_tether")],
    [InlineKeyboardButton("NOT", callback_data="cv_not")],
    [InlineKeyboardButton("STARS", callback_data="cv_stars")],
    [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet")],
])

convert_to_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("TON", callback_data="cvt_ton")],
    [InlineKeyboardButton("TRON", callback_data="cvt_tron")],
    [InlineKeyboardButton("TETHER", callback_data="cvt_tether")],
    [InlineKeyboardButton("NOT", callback_data="cvt_not")],
    [InlineKeyboardButton("STARS", callback_data="cvt_stars")],
    [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet")],
])

def fmt_mention(u):
    return f"[{u.first_name or u.username or u.id}](tg://user?id={u.id})"

async def is_member(context, user_id):
    try:
        m = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ============ هندلرها ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username or "")
    if not await is_member(context, user.id):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_member")],
        ])
        await update.message.reply_text(
            f"برای استفاده از ربات ابتدا در کانال زیر عضو شوید:\n{REQUIRED_CHANNEL}",
            reply_markup=kb,
        )
        return
    clear_state(user.id)
    await update.message.reply_text("👋 خوش آمدید!\nاز منوی زیر انتخاب کنید:", reply_markup=main_menu)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data

    if data == "check_member":
        if await is_member(context, user_id):
            await q.edit_message_text("✅ عضویت تایید شد!", reply_markup=main_menu)
        else:
            await q.answer("هنوز عضو نشدی!", show_alert=True)
        return

    if data == "back_main":
        await q.edit_message_text("منوی اصلی:", reply_markup=main_menu); return
    if data == "wallet":
        await q.edit_message_text("👛 کیف پول:", reply_markup=wallet_menu); return
    if data == "airdrop":
        await q.edit_message_text("🎁 ایردراپ — به زودی!", reply_markup=main_menu); return
    if data == "gift":
        await q.edit_message_text("🎟 خرید گیفت — به زودی!", reply_markup=main_menu); return
    if data == "currencies":
        txt = "\n".join([f"💠 {c['name']} — حداقل واریز {c['min_dep']}" for c in CURRENCIES.values()])
        await q.edit_message_text(f"💱 ارزها:\n\n{txt}", reply_markup=main_menu); return

    if data == "balances":
        u = get_user(user_id)
        text = (
            f"📊 موجودی‌ها:\n\n"
            f"💎 TON: {u.get('balance_ton', 0)}\n"
            f"🔺 TRON: {u.get('balance_tron', 0)}\n"
            f"💵 TETHER: {u.get('balance_tether', 0)}\n"
            f"🐶 DOGEZ: {u.get('balance_dogez', 0)}\n"
            f"🪙 NOT: {u.get('balance_not', 0)}\n"
            f"⭐ STARS: {u.get('balance_stars', 0)}"
        )
        await q.edit_message_text(text, reply_markup=wallet_menu); return

    if data == "deposit":
        await q.edit_message_text("📥 ارز مورد نظر برای واریز:", reply_markup=deposit_menu); return

    if data.startswith("dep_"):
        cur = data[4:]; c = CURRENCIES[cur]
        set_state(user_id, "await_deposit_amount", {"currency": cur})
        if cur == "stars":
            await q.edit_message_text(
                f"⭐ واریز STARS\n\nلطفاً به آیدی {c['wallet']} گیفت استارز بزن و تعداد را وارد کن:",
                reply_markup=wallet_menu)
        else:
            await q.edit_message_text(
                f"📥 واریز {c['name']}\n\n👛 ولت: `{c['wallet']}`\n📉 حداقل: {c['min_dep']}\n\nمقدار را وارد کن:",
                reply_markup=wallet_menu, parse_mode="Markdown")
        return

    if data == "withdraw":
        await q.edit_message_text("📤 ارز مورد نظر برای برداشت:", reply_markup=withdraw_menu); return

    if data.startswith("wd_"):
        cur = data[3:]; c = CURRENCIES[cur]
        set_state(user_id, "await_withdraw_amount", {"currency": cur})
        await q.edit_message_text(
            f"📤 برداشت {c['name']}\n\n📉 حداقل: {c['min_wd']}\n💸 کارمزد: {c['wd_fee']}\n\nمقدار را وارد کن:",
            reply_markup=wallet_menu)
        return

    if data == "convert":
        await q.edit_message_text("🔄 از کدام ارز تبدیل می‌کنی؟", reply_markup=convert_from_menu); return

    if data.startswith("cv_"):
        frm = data[3:]
        set_state(user_id, "await_convert_to", {"from": frm})
        await q.edit_message_text(
            f"از {CURRENCIES[frm]['name']} — ارز مقصد را انتخاب کن:",
            reply_markup=convert_to_menu)
        return

    if data.startswith("cvt_"):
        to = data[4:]
        st = get_state(user_id)
        frm = (st["data"] or {}).get("from") if st else None
        if not frm:
            await q.edit_message_text("خطا. دوباره تلاش کن.", reply_markup=wallet_menu); return
        set_state(user_id, "await_convert_amount", {"from": frm, "to": to})
        await q.edit_message_text(
            f"🔄 {CURRENCIES[frm]['name']} → {CURRENCIES[to]['name']}\n\n"
            f"حداقل: {CURRENCIES[frm]['min_cv']}\nکارمزد: ۲٪\n\nمقدار را وارد کن:",
            reply_markup=wallet_menu)
        return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""

    if text.startswith("/start"):
        await start(update, context); return

    # انتقال در گپ: Wallet 400 dogs
    m = re.match(r"Wallet\s+([\d.]+)\s+(\w+)", text, re.IGNORECASE)
    if m:
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ باید روی پیام کاربر مقصد ریپلای کنی."); return
        amount = float(m.group(1)); cur = m.group(2).lower()
        if cur in ("dogs","doge"): cur = "dogez"
        if cur not in CURRENCIES:
            await update.message.reply_text("❌ ارز نامعتبر. مثال: Wallet 400 dogs"); return
        to_user = update.message.reply_to_message.from_user
        if to_user.id == user.id:
            await update.message.reply_text("❌ نمی‌تونی به خودت انتقال بدی."); return
        from_db = get_user(user.id)
        if not from_db:
            await update.message.reply_text("❌ اول /start بزن."); return
        to_db = get_user(to_user.id)
        if not to_db:
            ensure_user(to_user.id, to_user.username or ""); to_db = get_user(to_user.id)
        key = f"balance_{cur}"
        fb = float(from_db.get(key) or 0)
        if fb < amount:
            await update.message.reply_text(f"❌ موجودی کافی نیست. موجودی: {fb} {CURRENCIES[cur]['name']}"); return
        query(f"update users set {key}=%s where telegram_id=%s", (fb-amount, user.id), fetch=False)
        query(f"update users set {key}=%s where telegram_id=%s", (float(to_db.get(key) or 0)+amount, to_user.id), fetch=False)
        query("insert into transactions (telegram_id,type,currency,amount,status,extra) values (%s,%s,%s,%s,%s,%s)",
              (user.id,"transfer",cur,amount,"approved",f"به {to_user.id}"), fetch=False)
        query("insert into transactions (telegram_id,type,currency,amount,status,extra) values (%s,%s,%s,%s,%s,%s)",
              (to_user.id,"transfer",cur,amount,"approved",f"از {user.id}"), fetch=False)
        await update.message.reply_text(
            f"✅ {amount} {CURRENCIES[cur]['name']} به {fmt_mention(to_user)} ارسال شد.",
            parse_mode="Markdown")
        await context.bot.send_message(
            to_user.id,
            f"💰 {amount} {CURRENCIES[cur]['name']} از طرف {fmt_mention(user)} دریافت کردی.",
            parse_mode="Markdown")
        return

    st = get_state(user.id)
    if not st: return
    state = st["state"]
    sd = st["data"] or {}

    if state == "await_deposit_amount":
        try: amt = float(text)
        except: await update.message.reply_text("❌ عدد معتبر بفرست."); return
        cur = sd["currency"]; c = CURRENCIES[cur]
        if amt < c["min_dep"]:
            await update.message.reply_text(f"❌ حداقل واریز {c['name']}: {c['min_dep']}"); return
        set_state(user.id, "await_hash", {"currency": cur, "amount": amt})
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 ارسال هش", callback_data="send_hash")],
            [InlineKeyboardButton("❌ رد شدن", callback_data="reject_deposit")],
        ])
        await update.message.reply_text(f"مقدار {amt} {c['name']} ثبت شد.\nهش تراکنش را بفرست:", reply_markup=kb)
        return

    if state == "await_hash":
        query("insert into transactions (telegram_id,type,currency,amount,tx_hash,status) values (%s,%s,%s,%s,%s,%s)",
              (user.id,"deposit",sd["currency"],sd["amount"],text,"pending"), fetch=False)
        clear_state(user.id)
        await update.message.reply_text("✅ هش ثبت شد. در انتظار تایید مدیر.")
        await context.bot.send_message(OWNER_ID,
            f"🔔 واریز جدید\n👤 {user.id}\n💱 {sd['currency'].upper()}\n💰 {sd['amount']}\n🔗 {text}")
        return

    if state == "await_withdraw_amount":
        try: amt = float(text)
        except: await update.message.reply_text("❌ عدد معتبر بفرست."); return
        cur = sd["currency"]; c = CURRENCIES[cur]
        if amt < c["min_wd"]:
            await update.message.reply_text(f"❌ حداقل برداشت {c['name']}: {c['min_wd']}"); return
        set_state(user.id, "await_withdraw_address", {"currency": cur, "amount": amt})
        prompt = "آدرس TRON خود را بفرست:" if cur=="tron" else ("تعداد STARS را بفرست:" if cur=="stars" else "آدرس TON خود را بفرست:")
        await update.message.reply_text(prompt); return

    if state == "await_withdraw_address":
        cur = sd["currency"]; amt = sd["amount"]; c = CURRENCIES[cur]
        u = get_user(user.id)
        if float(u.get(f"balance_{cur}") or 0) < amt:
            clear_state(user.id); await update.message.reply_text("❌ موجودی کافی نیست."); return
        query("insert into transactions (telegram_id,type,currency,amount,fee,extra,status) values (%s,%s,%s,%s,%s,%s,%s)",
              (user.id,"withdraw",cur,amt,c["wd_fee"],text,"pending"), fetch=False)
        clear_state(user.id)
        await update.message.reply_text("✅ درخواست برداشت ثبت شد. در انتظار تایید مدیر.")
        await context.bot.send_message(OWNER_ID,
            f"🔔 برداشت\n👤 {user.id}\n💱 {cur.upper()}\n💰 {amt}\n💸 کارمزد: {c['wd_fee']}\n📍 {text}")
        return

    if state == "await_convert_amount":
        try: amt = float(text)
        except: await update.message.reply_text("❌ عدد معتبر بفرست."); return
        frm = sd["from"]; to = sd["to"]; c = CURRENCIES[frm]
        if amt < c["min_cv"]:
            await update.message.reply_text(f"❌ حداقل تبدیل {c['name']}: {c['min_cv']}"); return
        u = get_user(user.id)
        if float(u.get(f"balance_{frm}") or 0) < amt:
            clear_state(user.id); await update.message.reply_text("❌ موجودی کافی نیست."); return
        net = amt * 0.98
        query(f"update users set balance_{frm}=%s, balance_{to}=%s where telegram_id=%s",
              (float(u.get(f"balance_{frm}") or 0)-amt, float(u.get(f"balance_{to}") or 0)+net, user.id), fetch=False)
        query("insert into transactions (telegram_id,type,currency,amount,fee,status) values (%s,%s,%s,%s,%s,%s)",
              (user.id,"convert",f"{frm}->{to}",amt,amt*0.02,"approved"), fetch=False)
        clear_state(user.id)
        await update.message.reply_text(
            f"✅ {amt} {c['name']} → {net:.4f} {CURRENCIES[to]['name']}\nکارمزد ۲٪")
        return

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
