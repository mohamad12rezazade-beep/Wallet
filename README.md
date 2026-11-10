# Telegram Wallet Bot

ربات کیف پول تلگرام با پشتیبانی از TON, TRON, TETHER, DOGEZ, NOT, STARS

## پیش‌نیازها

- حساب Supabase (رایگان)
- ربات تلگرام از @BotFather
- کانال اجباری `@Wallet_BANI`
- ربات باید **ادمین کانال** باشد (برای چک عضویت)

---

## راه‌اندازی مرحله به مرحله

### ۱. ساخت ربات در BotFather
1. برو به `@BotFather` در تلگرام
2. دستور `/newbot` → اسم و یوزرنیم بده
3. توکن رو کپی کن (مثل `123456:ABC-DEF...`)
4. دستور `/setprivacy` → ربات رو انتخاب کن → **Disable**
   (برای اینکه ربات پیام‌های گروه رو ببینه)

### ۲. ساخت کانال
1. کانال `@Wallet_BANI` رو بساز (یا اگه داری استفاده کن)
2. ربات رو **ادمین** کانال کن

### ۳. دیتابیس Supabase
1. برو `supabase.com` → New Project
2. توی **SQL Editor** → محتوای `schema.sql` رو پیست کن → **Run**

### ۴. Edge Function
1. توی Supabase → **Edge Functions** → **New Function**
2. اسم: `telegram-bot`
3. محتوای `supabase/functions/telegram-bot/index.ts` رو پیست کن
4. **Deploy** کن

### ۵. Secrets
توی Supabase → **Edge Functions → Secrets**:
- `BOT_TOKEN` = توکن ربات از BotFather
- `OWNER_ID` = آیدی عددی خودت (از `@userinfobot` بگیر)

### ۶. Webhook
این URL رو توی مرورگر باز کن (TOKEN و PROJECT_REF رو عوض کن):
