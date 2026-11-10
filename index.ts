import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const BOT_TOKEN = Deno.env.get("BOT_TOKEN")!;
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const OWNER_ID = parseInt(Deno.env.get("OWNER_ID")!);
const REQUIRED_CHANNEL = "@Wallet_BANI";
const BOT_USERNAME = "BANIWallet_bot";

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
const API = `https://api.telegram.org/bot${BOT_TOKEN}`;

async function call(method: string, body: any) {
  const r = await fetch(`${API}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

async function isMember(userId: number, channel: string): Promise<boolean> {
  const ch = channel.startsWith("@") ? channel : `@${channel}`;
  const r = await call("getChatMember", { chat_id: ch, user_id: userId });
  if (!r.ok) return false;
  return ["member", "administrator", "creator"].includes(r.result?.status);
}

async function getState(userId: number) {
  const { data } = await supabase.from("user_states").select("*").eq("telegram_id", userId).single();
  return data;
}
async function setState(userId: number, state: string, data: any = {}) {
  await supabase.from("user_states").upsert({ telegram_id: userId, state, data });
}
async function clearState(userId: number) {
  await supabase.from("user_states").delete().eq("telegram_id", userId);
}
async function ensureUser(userId: number, username: string, referredBy?: number) {
  const { data } = await supabase.from("users").select("telegram_id").eq("telegram_id", userId).single();
  if (!data) {
    await supabase.from("users").insert({ telegram_id: userId, username, referred_by: referredBy || null });
  } else {
    await supabase.from("users").update({ username }).eq("telegram_id", userId);
  }
}

const mainMenu = { inline_keyboard: [
  [{ text: "👛 کیف پول", callback_data: "wallet", style: "success" }],
  [{ text: "🎁 ایردراپ", callback_data: "airdrop", style: "success" }],
  [{ text: "🎟 خرید گیفت تلگرام", callback_data: "gift", style: "success" }],
  [{ text: "💱 ارز ها", callback_data: "currencies", style: "success" }],
  [{ text: "⚙️ پنل ادمین", callback_data: "admin", style: "danger" }],
]};

const walletMenu = { inline_keyboard: [
  [{ text: "📊 مشاهده موجودی ها", callback_data: "balances", style: "success" }],
  [{ text: "🔄 تبدیل", callback_data: "convert", style: "success" }],
  [{ text: "📤 برداشت", callback_data: "withdraw", style: "success" }],
  [{ text: "📥 واریز", callback_data: "deposit", style: "success" }],
  [{ text: "🔙 بازگشت", callback_data: "back_main", style: "danger" }],
]};

const depositMenu = { inline_keyboard: [
  [{ text: "TON", callback_data: "dep_ton", style: "success" }],
  [{ text: "TRON", callback_data: "dep_tron", style: "success" }],
  [{ text: "TETHER (TON)", callback_data: "dep_tether", style: "success" }],
  [{ text: "DOGEZ", callback_data: "dep_dogez", style: "success" }],
  [{ text: "NOT", callback_data: "dep_not", style: "success" }],
  [{ text: "STARS", callback_data: "dep_stars", style: "success" }],
  [{ text: "🔙 بازگشت", callback_data: "wallet", style: "danger" }],
]};

const withdrawMenu = { inline_keyboard: [
  [{ text: "TON", callback_data: "wd_ton", style: "success" }],
  [{ text: "TRON", callback_data: "wd_tron", style: "success" }],
  [{ text: "TETHER", callback_data: "wd_tether", style: "success" }],
  [{ text: "NOT", callback_data: "wd_not", style: "success" }],
  [{ text: "STARS", callback_data: "wd_stars", style: "success" }],
  [{ text: "🔙 بازگشت", callback_data: "wallet", style: "danger" }],
]};

const convertFromMenu = { inline_keyboard: [
  [{ text: "TON", callback_data: "cv_ton", style: "success" }],
  [{ text: "TRON", callback_data: "cv_tron", style: "success" }],
  [{ text: "TETHER", callback_data: "cv_tether", style: "success" }],
  [{ text: "NOT", callback_data: "cv_not", style: "success" }],
  [{ text: "STARS", callback_data: "cv_stars", style: "success" }],
  [{ text: "🔙 بازگشت", callback_data: "wallet", style: "danger" }],
]};

const convertToMenu = { inline_keyboard: [
  [{ text: "TON", callback_data: "cvt_ton", style: "success" }],
  [{ text: "TRON", callback_data: "cvt_tron", style: "success" }],
  [{ text: "TETHER", callback_data: "cvt_tether", style: "success" }],
  [{ text: "NOT", callback_data: "cvt_not", style: "success" }],
  [{ text: "STARS", callback_data: "cvt_stars", style: "success" }],
  [{ text: "🔙 بازگشت", callback_data: "wallet", style: "danger" }],
]};

const airdropMenu = { inline_keyboard: [
  [{ text: "➕ ساخت ایردراپ", callback_data: "ad_create", style: "success" }],
  [{ text: "📋 ایردراپ های من", callback_data: "ad_mine", style: "success" }],
  [{ text: "🔙 بازگشت", callback_data: "back_main", style: "danger" }],
]};

const adminMenu = { inline_keyboard: [
  [{ text: "➕ اضافه موجودی به خودم", callback_data: "adm_add", style: "success" }],
  [{ text: "📥 واریزی ها", callback_data: "adm_deposits", style: "success" }],
  [{ text: "📤 برداشتی ها", callback_data: "adm_withdraws", style: "success" }],
  [{ text: "🔙 بازگشت", callback_data: "back_main", style: "danger" }],
]};

const CURRENCIES: Record<string, any> = {
  ton:    { name: "TON",    wallet: "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", network: "TON",  minDep: 0.03, minWd: 0.15, wdFee: 0.05, minCv: 0.07 },
  tron:   { name: "TRON",   wallet: "TZ6DHXDJACNxiXpQL7anhpWoc1Lux6PwnK",                  network: "TRON", minDep: 0.1,  minWd: 1.3,  wdFee: 0.3,  minCv: 1 },
  tether: { name: "TETHER", wallet: "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", network: "TON",  minDep: 0.04, minWd: 0.15, wdFee: 0.03, minCv: 0.06 },
  dogez:  { name: "DOGEZ",  wallet: "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", network: "TON",  minDep: 100,  minWd: 0,    wdFee: 0,    minCv: 0 },
  not:    { name: "NOT",    wallet: "UQA9sAdUajvpJd7iIBSKuhppy34ZPXReecKGLHiwdna8qOi_", network: "TON",  minDep: 10,   minWd: 30,   wdFee: 12,   minCv: 30 },
  stars:  { name: "STARS",  wallet: "@MMAD_Tek",                                          network: "Gift", minDep: 0,    minWd: 15,   wdFee: 0,    minCv: 2 },
};

async function sendToOwner(text: string, buttons: any[] = []) {
  await call("sendMessage", {
    chat_id: OWNER_ID, text,
    reply_markup: buttons.length ? { inline_keyboard: [buttons] } : undefined,
  });
}

function mention(id: number, name?: string) {
  return `[${name || id}](tg://user?id=${id})`;
}

// ============ پیام‌ها ============
async function handleMessage(msg: any) {
  const userId = msg.from.id;
  const text = msg.text || "";
  const username = msg.from.username || "";
  const firstName = msg.from.first_name || "";

  if (text.startsWith("/start")) {
    const parts = text.split(" ");
    const payload = parts[1];
    let referredBy: number | undefined;
    if (payload) {
      const { data: ad } = await supabase.from("airdrops").select("*").eq("code", payload).eq("active", true).single();
      if (ad) {
        referredBy = ad.owner_id;
        const { data: existing } = await supabase.from("airdrop_joins").select("id").eq("airdrop_id", ad.id).eq("telegram_id", userId).single();
        if (!existing) {
          await supabase.from("airdrop_joins").insert({ airdrop_id: ad.id, telegram_id: userId });
          await supabase.from("airdrops").update({ joined: ad.joined + 1 }).eq("id", ad.id);
          if (ad.join_reward > 0) {
            const { data: owner } = await supabase.from("users").select("*").eq("telegram_id", ad.owner_id).single();
            if (owner) {
              const key = `balance_${ad.currency}`;
              await supabase.from("users").update({ [key]: (owner[key] || 0) + ad.join_reward }).eq("telegram_id", ad.owner_id);
              await call("sendMessage", { chat_id: ad.owner_id, text: `🎉 کاربر جدید از لینک شما وارد شد! +${ad.join_reward} ${ad.currency.toUpperCase()}` });
            }
          }
        }
      }
    }
    await ensureUser(userId, username, referredBy);
    if (!(await isMember(userId, REQUIRED_CHANNEL))) {
      await call("sendMessage", {
        chat_id: userId,
        text: `برای استفاده از ربات ابتدا در کانال زیر عضو شوید:\n${REQUIRED_CHANNEL}`,
        reply_markup: { inline_keyboard: [
          [{ text: "📢 عضویت در کانال", url: "https://t.me/Wallet_BANI", style: "success" }],
          [{ text: "✅ عضو شدم", callback_data: "check_member", style: "success" }],
        ]},
      });
      return;
    }
    await clearState(userId);
    await call("sendMessage", { chat_id: userId, text: "👋 خوش آمدید!\nاز منوی زیر انتخاب کنید:", reply_markup: mainMenu });
    return;
  }

  // ===== انتقال ارز در گپ: Wallet 400 dogs =====
  const transferMatch = text.match(/^Wallet\s+([\d.]+)\s+(\w+)$/i);
  if (transferMatch) {
    const amount = parseFloat(transferMatch[1]);
    let cur = transferMatch[2].toLowerCase();
    if (cur === "dogs" || cur === "doge") cur = "dogez";
    if (!CURRENCIES[cur]) {
      await call("sendMessage", { chat_id: userId, text: "❌ ارز نامعتبر. مثال: `Wallet 400 dogs`", parse_mode: "Markdown" });
      return;
    }
    if (!msg.reply_to_message) {
      await call("sendMessage", { chat_id: userId, text: "❌ باید روی پیام کاربر مقصد ریپلای کنی." });
      return;
    }
    const toUser = msg.reply_to_message.from;
    const toId = toUser.id;
    if (toId === userId) {
      await call("sendMessage", { chat_id: userId, text: "❌ نمی‌تونی به خودت انتقال بدی." });
      return;
    }
    // اطمینان از وجود هر دو کاربر در دیتابیس
    const { data: fromUser } = await supabase.from("users").select("*").eq("telegram_id", userId).single();
    if (!fromUser) {
      await call("sendMessage", { chat_id: userId, text: "❌ اول ربات رو با /start استارت کن." });
      return;
    }
    let { data: toUserDb } = await supabase.from("users").select("*").eq("telegram_id", toId).single();
    if (!toUserDb) {
      await supabase.from("users").insert({ telegram_id: toId, username: toUser.username || "" });
      const r = await supabase.from("users").select("*").eq("telegram_id", toId).single();
      toUserDb = r.data;
    }
    const key = `balance_${cur}`;
    const fromBal = Number(fromUser[key] || 0);
    if (fromBal < amount) {
      await call("sendMessage", { chat_id: userId, text: `❌ موجودی کافی نیست. موجودی فعلی تو: ${fromBal} ${CURRENCIES[cur].name}` });
      return;
    }
    // کسر از فرستنده و واریز به گیرنده
    await supabase.from("users").update({ [key]: fromBal - amount }).eq("telegram_id", userId);
    await supabase.from("users").update({ [key]: Number(toUserDb[key] || 0) + amount }).eq("telegram_id", toId);
    await supabase.from("transactions").insert([
      { telegram_id: userId, type: "transfer", currency: cur, amount, status: "approved", extra: `به ${toId}` },
      { telegram_id: toId, type: "transfer", currency: cur, amount, status: "approved", extra: `از ${userId}` },
    ]);

    // پیام به فرستنده با تگ گیرنده
    await call("sendMessage", {
      chat_id: userId,
      text: `✅ ${amount} ${CURRENCIES[cur].name} به ${mention(toId, toUser.first_name || toUser.username)} ارسال شد.`,
      parse_mode: "Markdown",
    });

    // پیام به گیرنده با تگ فرستنده
    await call("sendMessage", {
      chat_id: toId,
      text: `💰 ${amount} ${CURRENCIES[cur].name} از طرف ${mention(userId, firstName || username)} دریافت کردی.`,
      parse_mode: "Markdown",
    });
    return;
  }

  const st = await getState(userId);
  if (!st) return;

  if (st.state === "await_hash") {
    if (st.data.reject) { await clearState(userId); await call("sendMessage", { chat_id: userId, text: "❌ لغو شد." }); return; }
    const { data: tx } = await supabase.from("transactions").insert({
      telegram_id: userId, type: "deposit", currency: st.data.currency,
      amount: st.data.amount || 0, tx_hash: text, status: "pending",
    }).select().single();
    await clearState(userId);
    await call("sendMessage", { chat_id: userId, text: "✅ هش ثبت شد. در انتظار تایید مدیر." });
    if (tx) await sendToOwner(`🔔 واریز\n👤 ${userId}\n💱 ${st.data.currency.toUpperCase()}\n💰 ${st.data.amount}\n🔗 ${text}\n🆔 ${tx.id}`,
      [{ text: "✅ تایید", callback_data: `app_${tx.id}`, style: "success" }, { text: "❌ رد", callback_data: `rej_${tx.id}`, style: "danger" }]);
    return;
  }

  if (st.state === "await_deposit_amount") {
    const amt = parseFloat(text);
    const c = CURRENCIES[st.data.currency];
    if (isNaN(amt) || amt < c.minDep) { await call("sendMessage", { chat_id: userId, text: `❌ حداقل واریز ${c.name}: ${c.minDep}` }); return; }
    await setState(userId, "await_hash", { currency: st.data.currency, amount: amt, reject: false });
    await call("sendMessage", { chat_id: userId, text: `مقدار ${amt} ${c.name} ثبت شد.\nهش یا لینک تراکنش را بفرست:`,
      reply_markup: { inline_keyboard: [
        [{ text: "📤 ارسال هش", callback_data: "send_hash", style: "success" }],
        [{ text: "❌ رد شدن", callback_data: "reject_deposit", style: "danger" }],
      ]}});
    return;
  }

  if (st.state === "await_withdraw_amount") {
    const amt = parseFloat(text);
    const c = CURRENCIES[st.data.currency];
    if (isNaN(amt) || amt < c.minWd) { await call("sendMessage", { chat_id: userId, text: `❌ حداقل برداشت ${c.name}: ${c.minWd}` }); return; }
    await setState(userId, "await_withdraw_address", { ...st.data, amount: amt });
    const prompt = st.data.currency === "tron" ? "آدرس TRON خود را بفرست:" : st.data.currency === "stars" ? "تعداد STARS را بفرست:" : "آدرس TON خود را بفرست:";
    await call("sendMessage", { chat_id: userId, text: prompt });
    return;
  }

  if (st.state === "await_withdraw_address") {
    const { data: user } = await supabase.from("users").select("*").eq("telegram_id", userId).single();
    const c = CURRENCIES[st.data.currency];
    const balKey = `balance_${st.data.currency}`;
    if (Number(user[balKey] || 0) < st.data.amount) { await clearState(userId); await call("sendMessage", { chat_id: userId, text: "❌ موجودی کافی نیست." }); return; }
    const { data: tx } = await supabase.from("transactions").insert({
      telegram_id: userId, type: "withdraw", currency: st.data.currency,
      amount: st.data.amount, fee: c.wdFee, status: "pending", extra: text,
    }).select().single();
    await clearState(userId);
    await call("sendMessage", { chat_id: userId, text: "✅ درخواست برداشت ثبت شد. در انتظار تایید مدیر." });
    if (tx) await sendToOwner(`🔔 برداشت\n👤 ${userId}\n💱 ${st.data.currency.toUpperCase()}\n💰 ${st.data.amount}\n💸 کارمزد: ${c.wdFee}\n📍 آدرس: ${text}\n🆔 ${tx.id}`,
      [{ text: "✅ تایید", callback_data: `app_${tx.id}`, style: "success" }, { text: "❌ رد", callback_data: `rej_${tx.id}`, style: "danger" }]);
    return;
  }

  if (st.state === "await_convert_amount") {
    const amt = parseFloat(text);
    const from = CURRENCIES[st.data.from];
    if (isNaN(amt) || amt < from.minCv) { await call("sendMessage", { chat_id: userId, text: `❌ حداقل تبدیل ${from.name}: ${from.minCv}` }); return; }
    const { data: user } = await supabase.from("users").select("*").eq("telegram_id", userId).single();
    if (Number(user[`balance_${st.data.from}`] || 0) < amt) { await clearState(userId); await call("sendMessage", { chat_id: userId, text: "❌ موجودی کافی نیست." }); return; }
    const net = amt * 0.98;
    await supabase.from("users").update({
      [`balance_${st.data.from}`]: Number(user[`balance_${st.data.from}`]) - amt,
      [`balance_${st.data.to}`]: Number(user[`balance_${st.data.to}`] || 0) + net,
    }).eq("telegram_id", userId);
    await supabase.from("transactions").insert({ telegram_id: userId, type: "convert", currency: `${st.data.from}->${st.data.to}`, amount: amt, fee: amt * 0.02, status: "approved" });
    await clearState(userId);
    await call("sendMessage", { chat_id: userId, text: `✅ ${amt} ${from.name} → ${net.toFixed(4)} ${CURRENCIES[st.data.to].name}\nکارمزد ۲٪` });
    return;
  }

  if (st.state === "ad_capacity") {
    const cap = parseInt(text);
    if (isNaN(cap) || cap <= 0) { await call("sendMessage", { chat_id: userId, text: "❌ عدد معتبر بفرست." }); return; }
    await setState(userId, "ad_join_reward", { capacity: cap });
    await call("sendMessage", { chat_id: userId, text: "پاداش هر زیرمجموعه (به داگز) چقدر باشد؟ (اگه صفر می‌خوای بنویس 0)" });
    return;
  }
  if (st.state === "ad_join_reward") {
    const r = parseFloat(text);
    if (isNaN(r) || r < 0) { await call("sendMessage", { chat_id: userId, text: "❌ عدد معتبر." }); return; }
    await setState(userId, "ad_reward", { ...st.data, join_reward: r });
    await call("sendMessage", { chat_id: userId, text: "پاداش هر استارت/عضو شدن چقدر باشد؟" });
    return;
  }
  if (st.state === "ad_reward") {
    const r = parseFloat(text);
    if (isNaN(r) || r < 0) { await call("sendMessage", { chat_id: userId, text: "❌ عدد معتبر." }); return; }
    await setState(userId, "ad_finish", { ...st.data, reward: r });
    await call("sendMessage", { chat_id: userId, text: "کپچا فعال باشد؟",
      reply_markup: { inline_keyboard: [
        [{ text: "بله", callback_data: "ad_cap_yes", style: "success" }],
        [{ text: "خیر", callback_data: "ad_cap_no", style: "danger" }],
      ]}});
    return;
  }

  if (st.state === "adm_add_amount") {
    const amt = parseFloat(text);
    const cur = st.data.currency;
    if (isNaN(amt)) { await call("sendMessage", { chat_id: userId, text: "❌ عدد معتبر." }); return; }
    const { data: u } = await supabase.from("users").select("*").eq("telegram_id", OWNER_ID).single();
    const key = `balance_${cur}`;
    await supabase.from("users").update({ [key]: Number(u[key] || 0) + amt }).eq("telegram_id", OWNER_ID);
    await supabase.from("transactions").insert({ telegram_id: OWNER_ID, type: "admin_add", currency: cur, amount: amt, status: "approved" });
    await clearState(userId);
    await call("sendMessage", { chat_id: userId, text: `✅ ${amt} ${CURRENCIES[cur].name} اضافه شد.` });
    return;
  }

  if (st.state === "gift_name") {
    await setState(userId, "gift_id", { name: text });
    await call("sendMessage", { chat_id: userId, text: "آیدی تلگرام گیرنده را بفرست:" });
    return;
  }
  if (st.state === "gift_id") {
    await setState(userId, "gift_pay", { ...st.data, recipient: text });
    await call("sendMessage", { chat_id: userId, text: "ارز پرداخت را انتخاب کن:",
      reply_markup: { inline_keyboard: [
        [{ text: "TON", callback_data: "giftpay_ton", style: "success" }],
        [{ text: "TRON", callback_data: "giftpay_tron", style: "success" }],
        [{ text: "TETHER", callback_data: "giftpay_tether", style: "success" }],
        [{ text: "STARS", callback_data: "giftpay_stars", style: "success" }],
      ]}});
    return;
  }
}

// ============ کال‌بک‌ها ============
async function handleCallback(cb: any) {
  const userId = cb.from.id;
  const data = cb.data;
  await call("answerCallbackQuery", { callback_query_id: cb.id });

  const edit = async (text: string, markup: any) => {
    try {
      await call("editMessageText", { chat_id: userId, message_id: cb.message.message_id, text, reply_markup: markup });
    } catch {
      await call("sendMessage", { chat_id: userId, text, reply_markup: markup });
    }
  };

  if (data === "check_member") {
    if (await isMember(userId, REQUIRED_CHANNEL)) await edit("✅ عضویت تایید شد!", mainMenu);
    else await call("answerCallbackQuery", { callback_query_id: cb.id, text: "هنوز عضو نشدی!", show_alert: true });
    return;
  }

  if (data === "back_main") return edit("منوی اصلی:", mainMenu);
  if (data === "wallet") return edit("👛 کیف پول:", walletMenu);
  if (data === "airdrop") return edit("🎁 ایردراپ:", airdropMenu);
  if (data === "gift") {
    await setState(userId, "gift_name", {});
    return edit("🎟 نام گیفت را بنویس (مثل: تدی، قلب، گل، کادو، موشک، کیک، الماس):", walletMenu);
  }
  if (data === "currencies") {
    const txt = Object.entries(CURRENCIES).map(([k, c]: any) => `💠 ${c.name} — شبکه ${c.network} — حداقل واریز ${c.minDep}`).join("\n");
    return edit(`💱 ارزهای پشتیبانی‌شده:\n\n${txt}`, mainMenu);
  }
  if (data === "admin") {
    if (userId !== OWNER_ID) return;
    return edit("⚙️ پنل ادمین:", adminMenu);
  }

  if (data === "balances") {
    const { data: u } = await supabase.from("users").select("*").eq("telegram_id", userId).single();
    return edit(
      `📊 موجودی‌های شما:\n\n` +
      `💎 TON: ${u.balance_ton}\n🔺 TRON: ${u.balance_tron}\n💵 TETHER: ${u.balance_tether}\n` +
      `🐶 DOGEZ: ${u.balance_dogez}\n🪙 NOT: ${u.balance_not}\n⭐ STARS: ${u.balance_stars}`,
      walletMenu
    );
  }

  if (data === "deposit") return edit("📥 ارز مورد نظر برای واریز:", depositMenu);
  if (data.startsWith("dep_")) {
    const cur = data.slice(4);
    const c = CURRENCIES[cur];
    await setState(userId, "await_deposit_amount", { currency: cur });
    if (cur === "stars") {
      return edit(`⭐ واریز STARS\n\nلطفاً به آیدی ${c.wallet} گیفت استارز بزن و تعداد را وارد کن:`, walletMenu);
    }
    return edit(`📥 واریز ${c.name}\n\n👛 ولت: \`${c.wallet}\`\n🌐 شبکه: ${c.network}\n📉 حداقل واریز: ${c.minDep}\n\nمقدار واریزی را وارد کن:`, walletMenu);
  }

  if (data === "withdraw") return edit("📤 ارز مورد نظر برای برداشت:", withdrawMenu);
  if (data.startsWith("wd_")) {
    const cur = data.slice(3);
    const c = CURRENCIES[cur];
    await setState(userId, "await_withdraw_amount", { currency: cur });
    return edit(`📤 برداشت ${c.name}\n\n📉 حداقل: ${c.minWd}\n💸 کارمزد: ${c.wdFee}\n\nمقدار را وارد کن:`, walletMenu);
  }

  if (data === "convert") return edit("🔄 از کدام ارز تبدیل می‌کنی؟", convertFromMenu);
  if (data.startsWith("cv_")) {
    const from = data.slice(3);
    await setState(userId, "await_convert_from", { from });
    return edit(`از ${CURRENCIES[from].name} — ارز مقصد را انتخاب کن:`, convertToMenu);
  }
  if (data.startsWith("cvt_")) {
    const to = data.slice(4);
    const st = await getState(userId);
    const from = st?.data?.from;
    if (!from) return edit("خطا. دوباره تلاش کن.", walletMenu);
    await setState(userId, "await_convert_amount", { from, to });
    return edit(`🔄 ${CURRENCIES[from].name} → ${CURRENCIES[to].name}\n\nحداقل: ${CURRENCIES[from].minCv}\nکارمزد: ۲٪\n\nمقدار را وارد کن:`, walletMenu);
  }

  if (data === "send_hash") {
    const st = await getState(userId);
    await setState(userId, "await_hash", { ...(st?.data || {}), reject: false });
    return edit("📤 هش یا لینک تراکنش را بفرست:", walletMenu);
  }
  if (data === "reject_deposit") {
    await clearState(userId);
    return edit("❌ واریز لغو شد.", walletMenu);
  }

  // ایردراپ
  if (data === "ad_create") {
    await setState(userId, "ad_capacity", {});
    return edit("➕ ساخت ایردراپ\n\nظرفیت چند نفر باشد؟ (عدد بفرست)", airdropMenu);
  }
  if (data === "ad_cap_yes" || data === "ad_cap_no" || data === "ad_phone_yes" || data === "ad_phone_no") {
    const st = await getState(userId);
    const captcha = data === "ad_cap_yes";
    const phone = data === "ad_phone_yes";
    const code = `ad_${Date.now()}_${userId}`;
    const { data: ad } = await supabase.from("airdrops").insert({
      owner_id: userId, capacity: st.data.capacity, require_phone: phone,
      require_captcha: captcha, join_reward: st.data.join_reward || 0,
      reward_amount: st.data.reward || 0, currency: "dogez", code, active: true,
    }).select().single();
    await clearState(userId);
    const link = `https://t.me/${BOT_USERNAME}?start=${code}`;
    const txt = `🎆 یک ایردراپ به مبلغ ${st.data.reward || 0} DOGS در ربات ایجاد شده.\n\n` +
      `🎁 پاداش زیرمجموعه‌گیری: ${st.data.join_reward || 0} DOGS 🐶\n` +
      `🔋 ظرفیت ایردراپ: 0/${st.data.capacity}\n` +
      `🔄 کپچا: ${captcha ? "فعال ✅" : "غیرفعال 📴"}\n` +
      `🔐 تایید شماره: ${phone ? "🇮🇷 Iran" : "غیرفعال"}\n\n` +
      `🩵 لینک ایردراپ:\n${link}`;
    return edit(txt, airdropMenu);
  }
  if (data === "ad_mine") {
    const { data: ads } = await supabase.from("airdrops").select("*").eq("owner_id", userId).eq("active", true);
    if (!ads || ads.length === 0) return edit("📋 ایردراپ فعالی نداری.", airdropMenu);
    for (const ad of ads) {
      const link = `https://t.me/${BOT_USERNAME}?start=${ad.code}`;
      await call("sendMessage", {
        chat_id: userId,
        text: `🎆 ایردراپ #${ad.id}\n💰 پاداش: ${ad.reward_amount} DOGS\n🔋 ظرفیت: ${ad.joined}/${ad.capacity}\n🔗 ${link}`,
        reply_markup: { inline_keyboard: [[{ text: "🗑 حذف", callback_data: `ad_del_${ad.id}`, style: "danger" }]] },
      });
    }
    return;
  }
  if (data.startsWith("ad_del_")) {
    const id = parseInt(data.split("_")[2]);
    await supabase.from("airdrops").update({ active: false }).eq("id", id).eq("owner_id", userId);
    return edit("✅ ایردراپ حذف شد.", airdropMenu);
  }

  // پنل ادمین
  if (data === "adm_add") {
    if (userId !== OWNER_ID) return;
    return edit("کدام ارز را اضافه کنم؟",
      { inline_keyboard: [
        [{ text: "TON", callback_data: "admadd_ton", style: "success" }, { text: "TRON", callback_data: "admadd_tron", style: "success" }],
        [{ text: "TETHER", callback_data: "admadd_tether", style: "success" }, { text: "DOGEZ", callback_data: "admadd_dogez", style: "success" }],
        [{ text: "NOT", callback_data: "admadd_not", style: "success" }, { text: "STARS", callback_data: "admadd_stars", style: "success" }],
      ]});
  }
  if (data.startsWith("admadd_")) {
    if (userId !== OWNER_ID) return;
    const cur = data.slice(7);
    await setState(userId, "adm_add_amount", { currency: cur });
    return edit(`چقدر ${CURRENCIES[cur].name} اضافه شود؟`, adminMenu);
  }
  if (data === "adm_deposits") {
    const { data: txs } = await supabase.from("transactions").select("*").eq("type", "deposit").order("id", { ascending: false }).limit(20);
    const txt = (txs || []).map((t: any) => `#${t.id} | ${t.telegram_id} | ${t.amount} ${t.currency} | ${t.status}`).join("\n") || "خالی";
    return edit(`📥 آخرین واریزی‌ها:\n\n${txt}`, adminMenu);
  }
  if (data === "adm_withdraws") {
    const { data: txs } = await supabase.from("transactions").select("*").eq("type", "withdraw").order("id", { ascending: false }).limit(20);
    const txt = (txs || []).map((t: any) => `#${t.id} | ${t.telegram_id} | ${t.amount} ${t.currency} | ${t.status}`).join("\n") || "خالی";
    return edit(`📤 آخرین برداشتی‌ها:\n\n${txt}`, adminMenu);
  }

  // تایید/رد توسط مالک
  if (data.startsWith("app_") || data.startsWith("rej_")) {
    if (userId !== OWNER_ID) return;
    const approve = data.startsWith("app_");
    const txId = parseInt(data.split("_")[1]);
    const { data: tx } = await supabase.from("transactions").select("*").eq("id", txId).single();
    if (!tx) return;
    if (approve) {
      await supabase.from("transactions").update({ status: "approved" }).eq("id", txId);
      const { data: u } = await supabase.from("users").select("*").eq("telegram_id", tx.telegram_id).single();
      if (tx.type === "deposit") {
        await supabase.from("users").update({ [`balance_${tx.currency}`]: Number(u[`balance_${tx.currency}`] || 0) + Number(tx.amount) }).eq("telegram_id", tx.telegram_id);
        await call("sendMessage", { chat_id: tx.telegram_id, text: `✅ واریز ${tx.amount} ${tx.currency.toUpperCase()} تایید شد.` });
      } else if (tx.type === "withdraw") {
        await supabase.from("users").update({ [`balance_${tx.currency}`]: Number(u[`balance_${tx.currency}`] || 0) - Number(tx.amount) }).eq("telegram_id", tx.telegram_id);
        await call("sendMessage", { chat_id: tx.telegram_id, text: `✅ برداشت ${tx.amount} ${tx.currency.toUpperCase()} تایید شد.` });
      }
      await edit(`✅ تراکنش ${txId} تایید شد.`, { inline_keyboard: [] });
    } else {
      await supabase.from("transactions").update({ status: "rejected" }).eq("id", txId);
      await call("sendMessage", { chat_id: tx.telegram_id, text: `❌ درخواست شما رد شد.` });
      await edit(`❌ تراکنش ${txId} رد شد.`, { inline_keyboard: [] });
    }
    return;
  }
}

// ============ Webhook ============
serve(async (req) => {
  if (req.method !== "POST") return new Response("OK");
  try {
    const update = await req.json();
    if (update.message) await handleMessage(update.message);
    else if (update.callback_query) await handleCallback(update.callback_query);
  } catch (e) {
    console.error(e);
  }
  return new Response("OK");
});
