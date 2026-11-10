import os, json
import psycopg2
from psycopg2.extras import RealDictCursor
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from init_data_py import validate_by_hash, errors

DATABASE_URL = os.environ["SUPABASE_URL"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

def _user(uid):
    c = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        with c.cursor() as cur:
            cur.execute("select * from users where telegram_id=%s", (uid,))
            return cur.fetchone()
    finally: c.close()

def _upd(uid, val):
    c = psycopg2.connect(DATABASE_URL)
    try:
        with c.cursor() as cur:
            cur.execute("update users set balance_ton=%s where telegram_id=%s", (val, uid))
            c.commit()
    finally: c.close()

@csrf_exempt
def balance(req):
    if req.method != "POST": return JsonResponse({}, status=405)
    d = json.loads(req.body)
    try:
        p = validate_by_hash(d["initData"], BOT_TOKEN)
        uid = p.user.id
    except: return JsonResponse({"error":"auth"}, status=403)
    u = _user(uid)
    return JsonResponse({"ton": float(u["balance_ton"] or 0) if u else 0})

@csrf_exempt
def bet(req):
    if req.method != "POST": return JsonResponse({}, status=405)
    d = json.loads(req.body)
    try:
        p = validate_by_hash(d["initData"], BOT_TOKEN)
        uid = p.user.id
    except: return JsonResponse({"error":"auth"}, status=403)
    amt = float(d["amount"])
    mult = float(d.get("multiplier", 0))
    win = d.get("win", False)
    u = _user(uid)
    bal = float(u["balance_ton"] or 0)
    if bal < amt: return JsonResponse({"error":"balance"}, status=400)
    new_bal = bal - amt + (amt * mult if win else 0)
    _upd(uid, new_bal)
    return JsonResponse({"balance": new_bal})
