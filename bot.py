import os, logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["SUPABASE_URL"]
OWNER_ID = int(os.environ["OWNER_ID"])

def q(sql, p=None, fetch=True):
    c = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        with c.cursor() as cur:
            cur.execute(sql, p or ())
            if fetch and cur.description: return cur.fetchall()
            c.commit()
    finally: c.close()

def get_user(uid):
    r = q("select * from users where telegram_id=%s", (uid,))
    return r[0] if r else None

def ensure_user(uid, un):
    if not get_user(uid):
        q("insert into users (telegram_id,username) values (%s,%s) on conflict do nothing", (uid, un), fetch=False)

def get_state(uid):
    r = q("select * from user_states where telegram_id=%s", (uid,))
    return r[0] if r else None

def set_state(uid, s, d=None):
    q("insert into user_states (telegram_id,state,data) values (%s,%s,%s) on conflict (telegram_id) do update set state=excluded.state,data=excluded.data",
      (uid, s, Json(d or {})), fetch=False)

def clear_state(uid):
    q("delete from user_states where telegram_id=%s", (uid,), fetch=False)

WALLET = "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_"
MIN_AMOUNT = 0.1
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-app.vercel.app")

main_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎮 بازی", web_app=WebAppInfo(url=WEBAPP_URL))],
    [InlineKeyboardButton("📥 واریز", callback_data="deposit")],
    [InlineKeyboardButton("📤 برداشت", callback_data="withdraw")],
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ensure_user(u.id, u.username or "")
    clear_state(u.id)
    await update.message.reply_text(
        f"👋 سلام {u.first_name}!\n\n"
        f"💰 موجودی TON: {get_user(u.id).get('balance_ton', 0)}\n\n"
        "از منوی زیر انتخاب کن:",
        reply_markup=main_menu
    )

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qq = update.callback_query
    await qq.answer()
    uid = qq.from_user.id
    d = qq.data

    if d == "deposit":
        set_state(uid, "await_hash", {})
        await qq.edit_message_text(
            f"📥 واریز TON\n\n"
            f"👛 ولت: `{WALLET}`\n"
            f"📉 حداقل: {MIN_AMOUNT} TON\n\n"
            "بعد از واریز، هش یا لینک تراکنش رو بفرست:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
        )
        return

    if d == "withdraw":
        set_state(uid, "await_wd_amount", {})
        await qq.edit_message_text(
            f"📤 برداشت TON\n\n"
            f"📉 حداقل: {MIN_AMOUNT} TON\n\n"
            "مقدار درخواستی رو وارد کن:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
        )
        return

    if d == "back":
        clear_state(uid)
        await qq.edit_message_text("منوی اصلی:", reply_markup=main_menu)
        return

    if d.startswith("app_") or d.startswith("rej_"):
        if uid != OWNER_ID: return
        tx_id = int(d.split("_")[1])
        approve = d.startswith("app_")
        tx = q("select * from transactions where id=%s", (tx_id,))[0]
        if approve:
            q("update transactions set status='approved' where id=%s", (tx_id,), fetch=False)
            if tx["type"] == "deposit":
                u = get_user(tx["telegram_id"])
                q("update users set balance_ton=%s where telegram_id=%s",
                  (float(u["balance_ton"] or 0) + float(tx["amount"]), tx["telegram_id"]), fetch=False)
                await context.bot.send_message(tx["telegram_id"], f"✅ واریز {tx['amount']} TON تایید شد.")
            else:
                u = get_user(tx["telegram_id"])
                q("update users set balance_ton=%s where telegram_id=%s",
                  (float(u["balance_ton"] or 0) - float(tx["amount"]), tx["telegram_id"]), fetch=False)
                await context.bot.send_message(tx["telegram_id"], f"✅ برداشت {tx['amount']} TON تایید شد.")
        else:
            q("update transactions set status='rejected' where id=%s", (tx_id,), fetch=False)
            await context.bot.send_message(tx["telegram_id"], "❌ درخواست شما رد شد.")
        await qq.edit_message_text(f"{'✅' if approve else '❌'} تراکنش #{tx_id}", reply_markup=None)
        return

async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    t = update.message.text or ""
    if t.startswith("/start"):
        await start(update, context); return
    st = get_state(u.id)
    if not st: return
    s = st["state"]

    if s == "await_hash":
        q("insert into transactions (telegram_id,type,currency,amount,tx_hash,status) values (%s,'deposit','ton',%s,%s,'pending')",
          (u.id, MIN_AMOUNT, t), fetch=False)
        tx = q("select id from transactions where telegram_id=%s order by id desc limit 1", (u.id,))[0]
        clear_state(u.id)
        await update.message.reply_text("✅ ثبت شد. در انتظار تایید مدیر.")
        await context.bot.send_message(OWNER_ID,
            f"🔔 واریز جدید\n👤 {u.id}\n💰 {MIN_AMOUNT} TON\n🔗 {t}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"app_{tx['id']}"),
                InlineKeyboardButton("❌ رد", callback_data=f"rej_{tx['id']}")
            ]]))
        return

    if s == "await_wd_amount":
        try: amt = float(t)
        except: await update.message.reply_text("❌ عدد معتبر."); return
        if amt < MIN_AMOUNT:
            await update.message.reply_text(f"❌ حداقل {MIN_AMOUNT} TON"); return
        u_db = get_user(u.id)
        if float(u_db["balance_ton"] or 0) < amt:
            await update.message.reply_text("❌ موجودی کم."); return
        set_state(u.id, "await_wd_wallet", {"amount": amt})
        await update.message.reply_text("آدرس ولت TON خودت رو بفرست:")
        return

    if s == "await_wd_wallet":
        amt = st["data"]["amount"]
        q("insert into transactions (telegram_id,type,currency,amount,extra,status) values (%s,'withdraw','ton',%s,%s,'pending')",
          (u.id, amt, t), fetch=False)
        tx = q("select id from transactions where telegram_id=%s order by id desc limit 1", (u.id,))[0]
        clear_state(u.id)
        await update.message.reply_text("✅ درخواست ثبت شد. در انتظار تایید.")
        await context.bot.send_message(OWNER_ID,
            f"🔔 برداشت\n👤 {u.id}\n💰 {amt} TON\n📍 {t}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"app_{tx['id']}"),
                InlineKeyboardButton("❌ رد", callback_data=f"rej_{tx['id']}")
            ]]))
        return

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
