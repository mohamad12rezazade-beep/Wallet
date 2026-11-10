import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from supabase import create_client

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
REQUIRED_CHANNEL = "@Wallet_BANI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CURRENCIES = {
    "ton":    {"name": "TON",    "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 0.03, "min_wd": 0.15, "wd_fee": 0.05, "min_cv": 0.07},
    "tron":   {"name": "TRON",   "wallet": "TZ6DHXDJACNxiXpQL7anhpWoc1Lux6PwnK",                  "min_dep": 0.1,  "min_wd": 1.3,  "wd_fee": 0.3,  "min_cv": 1},
    "tether": {"name": "TETHER", "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 0.04, "min_wd": 0.15, "wd_fee": 0.03, "min_cv": 0.06},
    "dogez":  {"name": "DOGEZ",  "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 100,  "min_wd": 0,    "wd_fee": 0,    "min_cv": 0},
    "not":    {"name": "NOT",    "wallet": "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", "min_dep": 10,   "min_wd": 30,   "wd_fee": 12,   "min_cv": 30},
    "stars":  {"name": "STARS",  "wallet": "@MMAD_Tek",                                          "min_dep": 0,    "min_wd": 15,   "wd_fee": 0,    "min_cv": 2},
}

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


async def is_member(context, user_id):
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def get_user(user_id):
    res = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
    return res.data[0] if res.data else None


def ensure_user(user_id, username):
    if not get_user(user_id):
        supabase.table("users").insert({"telegram_id": user_id, "username": username}).execute()


def get_state(user_id):
    res = supabase.table("user_states").select("*").eq("telegram_id", user_id).execute()
    return res.data[0] if res.data else None


def set_state(user_id, state, data=None):
    supabase.table("user_states").upsert({"telegram_id": user_id, "state": state, "data": data or {}}).execute()


def clear_state(user_id):
    supabase.table("user_states").delete().eq("telegram_id", user_id).execute()


def fmt_mention(user):
    return f"[{user.first_name or user.username or user.id}](tg://user?id={user.id})"


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


async def check_member_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await is_member(context, query.from_user.id):
        await query.edit_message_text("✅ عضویت تایید شد!", reply_markup=main_menu)
    else:
        await query.answer("هنوز عضو نشدی!", show_alert=True)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "check_member":
        await check_member_cb(update, context)
        return

    if data == "back_main":
        await query.edit_message_text("منوی اصلی:", reply_markup=main_menu)
        return
    if data == "wallet":
        await query.edit_message_text("👛 کیف پول:", reply_markup=wallet_menu)
        return
    if data == "airdrop":
        await query.edit_message_text("🎁 ایردراپ — به زودی!", reply_markup=main_menu)
        return
    if data == "gift":
        await query.edit_message_text("🎟 خرید گیفت — به زودی!", reply_markup=main_menu)
        return
    if data == "currencies":
        txt = "\n".join([f"💠 {c['name']} — حداقل واریز {c['min_dep']}" for c in CURRENCIES.values()])
        await query.edit_message_text(f"💱 ارزها:\n\n{txt}", reply_markup=main_menu)
        return

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
        await query.edit_message_text(text, reply_markup=wallet_menu)
        return

    if data == "deposit":
        await query.edit_message_text("📥 ارز مورد نظر برای واریز:", reply_markup=deposit_menu)
        return

    if data.startswith("dep_"):
        cur = data[4:]
        c = CURRENCIES[cur]
        set_state(user_id, "await_deposit_amount", {"currency": cur})
        if cur == "stars":
            await query.edit_message_text(
                f"⭐ واریز STARS\n\nلطفاً به آیدی {c['wallet']} گیفت استارز بزن و تعداد را وارد کن:",
                reply_markup=wallet_menu,
            )
        else:
            await query.edit_message_text(
                f"📥 واریز {c['name']}\n\n👛 ولت: `{c['wallet']}`\n📉 حداقل: {c['min_dep']}\n\nمقدار را وارد کن:",
                reply_markup=wallet_menu,
                parse_mode="Markdown",
            )
        return

    if data == "withdraw":
        await query.edit_message_text("📤 ارز مورد نظر برای برداشت:", reply_markup=withdraw_menu)
        return

    if data.startswith("wd_"):
        cur = data[3:]
        c = CURRENCIES[cur]
        set_state(user_id, "await_withdraw_amount", {"currency": cur})
        await query.edit_message_text(
            f"📤 برداشت {c['name']}\n\n📉 حداقل: {c['min_wd']}\n💸 کارمزد: {c['wd_fee']}\n\nمقدار را وارد کن:",
            reply_markup=wallet_menu,
        )
        return

    if data == "convert":
        await query.edit_message_text("🔄 از کدام ارز تبدیل می‌کنی؟", reply_markup=convert_from_menu)
        return

    if data.startswith("cv_"):
        frm = data[3:]
        set_state(user_id, "await_convert_to", {"from": frm})
        await query.edit_message_text(
            f"از {CURRENCIES[frm]['name']} — ارز مقصد را انتخاب کن:",
            reply_markup=convert_to_menu,
        )
        return

    if data.startswith("cvt_"):
        to = data[4:]
        st = get_state(user_id)
        frm = st["data"].get("from") if st else None
        if not frm:
            await query.edit_message_text("خطا. دوباره تلاش کن.", reply_markup=wallet_menu)
            return
        set_state(user_id, "await_convert_amount", {"from": frm, "to": to})
        await query.edit_message_text(
            f"🔄 {CURRENCIES[frm]['name']} → {CURRENCIES[to]['name']}\n\n"
            f"حداقل: {CURRENCIES[frm]['min_cv']}\nکارمزد: ۲٪\n\nمقدار را وارد کن:",
            reply_markup=wallet_menu,
        )
        return


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""

    if text.startswith("/start"):
        await start(update, context)
        return

    # انتقال در گپ: Wallet 400 dogs
    match = re.match(r"Wallet\s+([\d.]+)\s+(\w+)", text, re.IGNORECASE)
    if match:
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ باید روی پیام کاربر مقصد ریپلای کنی.")
            return
        amount = float(match.group(1))
        cur = match.group(2).lower()
        if cur in ("dogs", "doge"):
            cur = "dogez"
        if cur not in CURRENCIES:
            await update.message.reply_text("❌ ارز نامعتبر. مثال: Wallet 400 dogs")
            return

        to_user = update.message.reply_to_message.from_user
        if to_user.id == user.id:
            await update.message.reply_text("❌ نمی‌تونی به خودت انتقال بدی.")
            return

        from_db = get_user(user.id)
        if not from_db:
            await update.message.reply_text("❌ اول /start بزن.")
            return
        to_db = get_user(to_user.id)
        if not to_db:
            ensure_user(to_user.id, to_user.username or "")
            to_db = get_user(to_user.id)

        key = f"balance_{cur}"
        from_bal = float(from_db.get(key) or 0)
        if from_bal < amount:
            await update.message.reply_text(f"❌ موجودی کافی نیست. موجودی: {from_bal} {CURRENCIES[cur]['name']}")
            return

        supabase.table("users").update({key: from_bal - amount}).eq("telegram_id", user.id).execute()
        supabase.table("users").update({key: float(to_db.get(key) or 0) + amount}).eq("telegram_id", to_user.id).execute()
        supabase.table("transactions").insert([
            {"telegram_id": user.id, "type": "transfer", "currency": cur, "amount": amount, "status": "approved", "extra": f"به {to_user.id}"},
            {"telegram_id": to_user.id, "type": "transfer", "currency": cur, "amount": amount, "status": "approved", "extra": f"از {user.id}"},
        ]).execute()

        await update.message.reply_text(
            f"✅ {amount} {CURRENCIES[cur]['name']} به {fmt_mention(to_user)} ارسال شد.",
            parse_mode="Markdown",
        )
        await context.bot.send_message(
            to_user.id,
            f"💰 {amount} {CURRENCIES[cur]['name']} از طرف {fmt_mention(user)} دریافت کردی.",
            parse_mode="Markdown",
        )
        return

    st = get_state(user.id)
    if not st:
        return

    if st["state"] == "await_deposit_amount":
        try:
            amt = float(text)
        except:
            await update.message.reply_text("❌ عدد معتبر بفرست.")
            return
        cur = st["data"]["currency"]
        c = CURRENCIES[cur]
        if amt < c["min_dep"]:
            await update.message.reply_text(f"❌ حداقل واریز {c['name']}: {c['min_dep']}")
            return
        set_state(user.id, "await_hash", {"currency": cur, "amount": amt})
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 ارسال هش", callback_data="send_hash")],
            [InlineKeyboardButton("❌ رد شدن", callback_data="reject_deposit")],
        ])
        await update.message.reply_text(f"مقدار {amt} {c['name']} ثبت شد.\nهش تراکنش را بفرست:", reply_markup=kb)
        return

    if st["state"] == "await_hash":
        data = st["data"]
        supabase.table("transactions").insert({
            "telegram_id": user.id, "type": "deposit", "currency": data["currency"],
            "amount": data["amount"], "tx_hash": text, "status": "pending",
        }).execute()
        clear_state(user.id)
        await update.message.reply_text("✅ هش ثبت شد. در انتظار تایید مدیر.")
        await context.bot.send_message(
            OWNER_ID,
            f"🔔 واریز جدید\n👤 {user.id}\n💱 {data['currency'].upper()}\n💰 {data['amount']}\n🔗 {text}",
        )
        return

    if st["state"] == "await_withdraw_amount":
        try:
            amt = float(text)
        except:
            await update.message.reply_text("❌ عدد معتبر بفرست.")
            return
        cur = st["data"]["currency"]
        c = CURRENCIES[cur]
        if amt < c["min_wd"]:
            await update.message.reply_text(f"❌ حداقل برداشت {c['name']}: {c['min_wd']}")
            return
        set_state(user.id, "await_withdraw_address", {"currency": cur, "amount": amt})
        prompt = "آدرس TRON خود را بفرست:" if cur == "tron" else ("تعداد STARS را بفرست:" if cur == "stars" else "آدرس TON خود را بفرست:")
        await update.message.reply_text(prompt)
        return

    if st["state"] == "await_withdraw_address":
        cur = st["data"]["currency"]
        amt = st["data"]["amount"]
        c = CURRENCIES[cur]
        u = get_user(user.id)
        if float(u.get(f"balance_{cur}") or 0) < amt:
            clear_state(user.id)
            await update.message.reply_text("❌ موجودی کافی نیست.")
            return
        supabase.table("transactions").insert({
            "telegram_id": user.id, "type": "withdraw", "currency": cur,
            "amount": amt, "fee": c["wd_fee"], "status": "pending", "extra": text,
        }).execute()
        clear_state(user.id)
        await update.message.reply_text("✅ درخواست برداشت ثبت شد. در انتظار تایید مدیر.")
        await context.bot.send_message(
            OWNER_ID,
            f"🔔 برداشت\n👤 {user.id}\n💱 {cur.upper()}\n💰 {amt}\n💸 کارمزد: {c['wd_fee']}\n📍 {text}",
        )
        return

    if st["state"] == "await_convert_amount":
        try:
            amt = float(text)
        except:
            await update.message.reply_text("❌ عدد معتبر بفرست.")
            return
        frm = st["data"]["from"]
        to = st["data"]["to"]
        c = CURRENCIES[frm]
        if amt < c["min_cv"]:
            await update.message.reply_text(f"❌ حداقل تبدیل {c['name']}: {c['min_cv']}")
            return
        u = get_user(user.id)
        if float(u.get(f"balance_{frm}") or 0) < amt:
            clear_state(user.id)
            await update.message.reply_text("❌ موجودی کافی نیست.")
            return
        net = amt * 0.98
        supabase.table("users").update({
            f"balance_{frm}": float(u.get(f"balance_{frm}") or 0) - amt,
            f"balance_{to}": float(u.get(f"balance_{to}") or 0) + net,
        }).eq("telegram_id", user.id).execute()
        supabase.table("transactions").insert({
            "telegram_id": user.id, "type": "convert", "currency": f"{frm}->{to}",
            "amount": amt, "fee": amt * 0.02, "status": "approved",
        }).execute()
        clear_state(user.id)
        await update.message.reply_text(
            f"✅ {amt} {c['name']} → {net:.4f} {CURRENCIES[to]['name']}\nکارمزد ۲٪"
        )
        return


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()
