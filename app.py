import threading
import time
import requests
import logging
import json
import os
import urllib3
import random
import warnings
from datetime import datetime

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Flask, request, jsonify
from flask_cors import CORS

warnings.filterwarnings("ignore")
urllib3.disable_warnings()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

K = b"Yg&tc%DEuh6%Zc^8"
IV = b"6oyZDr22E3ychjM%"

JWT_API_URL = os.getenv("JWT_API_URL", "http://76.13.78.159:5003/GeneRate-Jwt")

JWT_FILE = "jwt_cache.json"
ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", "abdouuu.txt")
UPDATE_INTERVAL = 6 * 60 * 60
JWT_VALIDITY_SECONDS = 6 * 60 * 60


def load_accounts(path=ACCOUNTS_FILE):
    """
    يقرأ الحسابات من الملف.
    كل سطر: uid,password  أو  uid:password  أو  uid password
    يتجاهل الأسطر الفارغة والتعليقات (#).
    """
    accounts = []
    if not os.path.exists(path):
        logger.error(f"❌ ملف الحسابات غير موجود: {path}")
        return accounts

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                if "," in line:
                    parts = [p.strip() for p in line.split(",", 1)]
                elif ":" in line:
                    parts = [p.strip() for p in line.split(":", 1)]
                else:
                    parts = line.split(None, 1)

                if len(parts) != 2 or not parts[0] or not parts[1]:
                    logger.warning(f"⚠️ سطر {line_no} بصيغة غير صحيحة: {line[:40]}")
                    continue

                uid, pw = parts[0], parts[1]
                if not uid.isdigit():
                    logger.warning(f"⚠️ سطر {line_no}: UID غير رقمي ({uid[:20]})")
                    continue

                accounts.append((uid, pw))

        logger.info(f"📂 تم تحميل {len(accounts)} حساب من {path}")
    except Exception as e:
        logger.error(f"❌ خطأ قراءة {path}: {e}")

    return accounts


l9bi7e_ToK = load_accounts()

JWT_ToKeNs = {}
TOKEN_FETCH_TIMES = {}
SpAm_RunNiNg = {}
spam_threads = {}
jwt_lock = threading.Lock()
running = True


def padB(d):
    n = 16 - (len(d) % 16)
    return d + bytes([n] * n)


def encrypt_api(plain_text_hex):
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(bytes.fromhex(plain_text_hex), AES.block_size))
    return cipher_text.hex()


def Encrypt_ID(number):
    number = int(number)
    encoded_bytes = []
    while True:
        byte = number & 0x7F
        number >>= 7
        if number:
            byte |= 0x80
        encoded_bytes.append(byte)
        if not number:
            break
    return bytes(encoded_bytes).hex()


def fetch_jwt_from_api(uid: str, password: str):
    url = f"{JWT_API_URL}?Uid={uid}&Pw={password}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G9650) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Connection": "close"
    }

    last_err = "API Failed"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=15, verify=False)
            if r.status_code == 200:
                try:
                    data = r.json()
                    if isinstance(data, dict):
                        for field in ["token", "jwt", "access_token", "Token", "JWT", "jwt_token"]:
                            tok = data.get(field)
                            if tok and isinstance(tok, str) and tok.startswith("ey") and len(tok) > 30:
                                return tok.strip(), "API_OK"
                        err_msg = data.get("error") or data.get("message") or data.get("msg")
                        if err_msg:
                            last_err = f"API: {str(err_msg)[:100]}"
                    elif isinstance(data, str) and data.startswith("ey") and len(data) > 30:
                        return data.strip(), "API_OK"
                except ValueError:
                    text = r.text.strip().strip('"').strip("'").strip()
                    if text.startswith("ey") and len(text) > 30:
                        return text, "API_OK"
                    last_err = f"API invalid: {text[:100]}"
            elif r.status_code == 429:
                last_err = "API 429"
                time.sleep(1.5)
                continue
            else:
                last_err = f"API HTTP {r.status_code}"
        except requests.exceptions.Timeout:
            last_err = "API Timeout"
        except requests.exceptions.ConnectionError:
            last_err = "API ConnErr"
        except Exception as e:
            last_err = f"API Err: {str(e)[:100]}"

        if attempt < 2:
            time.sleep(random.uniform(0.8, 1.5))

    return None, last_err


def is_token_recent(uid: str) -> bool:
    ts = TOKEN_FETCH_TIMES.get(str(uid))
    if not ts:
        return False
    return (time.time() - ts) < JWT_VALIDITY_SECONDS


def save_tokens_to_disk():
    try:
        with jwt_lock:
            data = {
                "tokens": JWT_ToKeNs,
                "times": TOKEN_FETCH_TIMES,
                "saved_at": time.time()
            }
        with open(JWT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 تم حفظ {len(JWT_ToKeNs)} توكن إلى {JWT_FILE}")
    except Exception as e:
        logger.error(f"خطأ حفظ التوكنات: {e}")


def load_tokens_from_disk():
    global JWT_ToKeNs, TOKEN_FETCH_TIMES
    try:
        if not os.path.exists(JWT_FILE):
            return False

        with open(JWT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        saved_at = data.get("saved_at", 0)
        age = time.time() - saved_at

        if age > JWT_VALIDITY_SECONDS:
            logger.info(f"⏰ ملف التوكنات قديم ({age/3600:.1f} ساعة) - سيتم تجاهله")
            return False

        with jwt_lock:
            JWT_ToKeNs = data.get("tokens", {})
            TOKEN_FETCH_TIMES = data.get("times", {})

        logger.info(f"♻️ تم تحميل {len(JWT_ToKeNs)} توكن من الملف (عمرها {age/60:.1f} دقيقة)")
        return True
    except Exception as e:
        logger.error(f"خطأ تحميل التوكنات: {e}")
        return False


def update_all_tokens(force=False):
    total = len(l9bi7e_ToK)
    logger.info(f"🔄 بدء تحديث التوكنات ({total} حساب)...")

    success = 0
    skipped = 0
    failed = 0

    for idx, (uid, pw) in enumerate(l9bi7e_ToK, 1):

        if not force and is_token_recent(uid):
            with jwt_lock:
                if uid in JWT_ToKeNs:
                    skipped += 1
                    continue

        try:
            token, status = fetch_jwt_from_api(uid, pw)
            if token:
                with jwt_lock:
                    JWT_ToKeNs[uid] = token
                    TOKEN_FETCH_TIMES[uid] = time.time()
                success += 1
                logger.info(f"[{idx:3d}/{total}] ✓ {uid[:6]}... ({status})")
            else:
                failed += 1
                logger.warning(f"[{idx:3d}/{total}] ✗ {uid[:6]}... ({status})")
        except Exception as e:
            failed += 1
            logger.error(f"[{idx:3d}/{total}] ✗ {uid[:6]}... ({e})")

        time.sleep(random.uniform(0.3, 0.7))

    logger.info(f"📊 تحديث التوكنات انتهى | نجح: {success} | متخطى: {skipped} | فشل: {failed}")
    save_tokens_to_disk()


def token_updater_loop():
    loaded = load_tokens_from_disk()

    if loaded:
        logger.info("✅ سيتم استخدام التوكنات المحفوظة حتى انتهاء صلاحيتها")
    else:
        update_all_tokens(force=True)

    while running:
        for _ in range(UPDATE_INTERVAL):
            if not running:
                return
            time.sleep(1)

        if running:
            logger.info("⏰ حان وقت التحديث الدوري (6 ساعات)")
            update_all_tokens(force=True)


def l9bi7e_SendFriend(target_uid, token, account_uid):
    try:
        enc_target = Encrypt_ID(target_uid)
        payload = f"08a7c4839f1e10{enc_target}1801"
        enc_payload = encrypt_api(payload)

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB55",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)"
        }

        response = requests.post(
            "https://clientbp.ppmainecoonghj.com/RequestAddingFriend",
            headers=headers,
            data=bytes.fromhex(enc_payload),
            timeout=10,
            verify=False
        )

        if response.status_code == 200:
            return response
        return None
    except Exception:
        return None


def l9bi7e_InfiniteSpam(target_uid, session_id, accounts_list=None):
    success = 0
    failed = 0
    accounts = accounts_list if accounts_list else l9bi7e_ToK
    SpAm_RunNiNg[session_id] = True

    logger.info(f"🚀 بدء سبام على {target_uid} ({len(accounts)} حساب)")

    while SpAm_RunNiNg.get(session_id):
        for uid, _ in accounts:
            if not SpAm_RunNiNg.get(session_id):
                break

            with jwt_lock:
                token = JWT_ToKeNs.get(uid)

            if not token:
                continue

            response = l9bi7e_SendFriend(target_uid, token, uid)

            if response is None:
                failed += 1
            else:
                success += 1

            if (success + failed) % 20 == 0:
                update_spam_status(session_id, target_uid, success, failed)

            time.sleep(0.15)

    SpAm_RunNiNg[session_id] = False
    update_spam_status(session_id, target_uid, success, failed, running=False)

    logger.info(f"🏁 انتهى سبام {target_uid}: نجاح {success} | فشل {failed}")
    return {"success": success, "failed": failed}


def update_spam_status(session_id, target_uid, success, failed, running=None):
    if running is None:
        running = SpAm_RunNiNg.get(session_id, False)
    spam_threads[session_id] = {
        "target_uid": target_uid,
        "success": success,
        "failed": failed,
        "running": running,
        "updated_at": datetime.now().isoformat()
    }


def cleanup_dead_sessions():
    now = time.time()
    to_delete = []

    for sid, info in list(spam_threads.items()):
        is_running = SpAm_RunNiNg.get(sid, False)

        if not is_running and info.get('running'):
            info['running'] = False
            info['stopped_at'] = datetime.now().isoformat()

        if not is_running:
            started_at = info.get('started_at') or info.get('updated_at', '')
            if started_at:
                try:
                    start_ts = datetime.fromisoformat(started_at).timestamp()
                    if now - start_ts > 3600:
                        to_delete.append(sid)
                except Exception:
                    pass

    for sid in to_delete:
        spam_threads.pop(sid, None)
        SpAm_RunNiNg.pop(sid, None)

    if to_delete:
        logger.info(f"🧹 تم حذف {len(to_delete)} جلسة قديمة من الذاكرة")


@app.route('/spm', methods=['GET'])
def start_spam():
    try:
        cleanup_dead_sessions()

        target_uid = request.args.get('uid')
        if not target_uid:
            return jsonify({"status": "error", "message": "الاستخدام: /spm?uid=الهدف"}), 400

        with jwt_lock:
            token_count = len(JWT_ToKeNs)

        if token_count == 0:
            return jsonify({
                "status": "error",
                "message": "لا توجد توكنات متاحة بعد، انتظر اكتمال التحديث الأولي"
            }), 503

        for sid, info in spam_threads.items():
            if info.get('target_uid') == target_uid and SpAm_RunNiNg.get(sid, False):
                return jsonify({
                    "status": "error",
                    "message": f"يوجد سبام نشط للـ UID {target_uid}",
                    "session_id": sid
                }), 409

        session_id = f"{target_uid}_{int(time.time())}"

        spam_threads[session_id] = {
            "target_uid": target_uid,
            "success": 0,
            "failed": 0,
            "running": True,
            "started_at": datetime.now().isoformat()
        }
        SpAm_RunNiNg[session_id] = True

        thread = threading.Thread(
            target=l9bi7e_InfiniteSpam,
            args=(target_uid, session_id, None),
            daemon=True
        )
        thread.start()

        return jsonify({
            "status": "success",
            "message": f"✅ تم بدء السبام على {target_uid}",
            "session_id": session_id,
            "active_tokens": token_count
        }), 200

    except Exception as e:
        logger.error(f"خطأ: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/stp', methods=['GET'])
def stop_spam():
    try:
        target_uid = request.args.get('uid')
        if not target_uid:
            return jsonify({"status": "error", "message": "الاستخدام: /stp?uid=الهدف"}), 400

        stopped_sessions = []
        for sid, info in spam_threads.items():
            if info.get('target_uid') == target_uid and SpAm_RunNiNg.get(sid, False):
                SpAm_RunNiNg[sid] = False
                spam_threads[sid]['running'] = False
                spam_threads[sid]['stopped_at'] = datetime.now().isoformat()
                stopped_sessions.append(sid)

        if stopped_sessions:
            return jsonify({
                "status": "success",
                "message": f"🛑 تم إيقاف {len(stopped_sessions)} جلسة سبام",
                "sessions": stopped_sessions
            }), 200

        return jsonify({"status": "error", "message": "❌ لا يوجد سبام نشط لهذا الـ UID"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/status', methods=['GET'])
def get_status():
    try:
        cleanup_dead_sessions()

        target_uid = request.args.get('uid')
        if target_uid:
            sessions = [
                {"session_id": sid, **info, "actually_running": SpAm_RunNiNg.get(sid, False)}
                for sid, info in spam_threads.items()
                if info.get('target_uid') == target_uid
            ]
            return jsonify({"status": "success", "data": sessions}), 200

        active = {
            sid: {**info, "actually_running": True}
            for sid, info in spam_threads.items()
            if SpAm_RunNiNg.get(sid, False)
        }

        with jwt_lock:
            token_count = len(JWT_ToKeNs)

        return jsonify({
            "status": "success",
            "active_sessions_count": len(active),
            "active_tokens": token_count,
            "total_accounts": len(l9bi7e_ToK),
            "data": active
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/tokens', methods=['GET'])
def show_tokens():
    with jwt_lock:
        token_count = len(JWT_ToKeNs)

        if TOKEN_FETCH_TIMES:
            oldest = min(TOKEN_FETCH_TIMES.values())
            newest = max(TOKEN_FETCH_TIMES.values())
            oldest_age_min = (time.time() - oldest) / 60
            newest_age_min = (time.time() - newest) / 60
        else:
            oldest_age_min = newest_age_min = 0

    return jsonify({
        "total_accounts": len(l9bi7e_ToK),
        "active_tokens": token_count,
        "oldest_token_age_minutes": round(oldest_age_min, 1),
        "newest_token_age_minutes": round(newest_age_min, 1),
        "next_update_in_hours": round(UPDATE_INTERVAL / 3600, 2),
        "status": "✅ جاهز" if token_count > 0 else "⏳ جاري التحديث الأولي..."
    }), 200


@app.route('/reload_tokens', methods=['GET'])
def reload_tokens():
    threading.Thread(target=update_all_tokens, args=(True,), daemon=True).start()
    with jwt_lock:
        count = len(JWT_ToKeNs)
    return jsonify({
        "status": "refresh_started",
        "current_tokens": count,
        "message": "سيتم جلب جميع التوكنات من جديد في الخلفية"
    }), 200


@app.route('/reload_accounts', methods=['GET'])
def reload_accounts_route():
    global l9bi7e_ToK
    new_accounts = load_accounts()
    if not new_accounts:
        return jsonify({
            "status": "error",
            "message": f"الملف {ACCOUNTS_FILE} فارغ أو غير موجود"
        }), 400
    l9bi7e_ToK = new_accounts
    threading.Thread(target=update_all_tokens, args=(True,), daemon=True).start()
    return jsonify({
        "status": "success",
        "loaded": len(l9bi7e_ToK),
        "message": "تم تحديث الحسابات وبدأ جلب التوكنات في الخلفية"
    }), 200


@app.route('/', methods=['GET'])
def home():
    with jwt_lock:
        token_count = len(JWT_ToKeNs)

    return jsonify({
        "name": "FreeFire Spam API (External JWT API)",
        "status": "running",
        "total_accounts": len(l9bi7e_ToK),
        "active_tokens": token_count,
        "token_update_interval_hours": UPDATE_INTERVAL / 3600,
        "commands": {
            "start": "/spm?uid=9763926639",
            "stop": "/stp?uid=9763926639",
            "status": "/status?uid=9763926639",
            "tokens": "/tokens",
            "reload_tokens": "/reload_tokens",
            "reload_accounts": "/reload_accounts"
        }
    }), 200


# ---------------- bootstrap ----------------
def _start_background():
    if not l9bi7e_ToK:
        logger.error(f"⚠️ لم يتم العثور على حسابات في {ACCOUNTS_FILE}")
    else:
        logger.info(f"📂 الحسابات المحمّلة: {len(l9bi7e_ToK)}")
    threading.Thread(target=token_updater_loop, daemon=True).start()


# يبدأ خيط تحديث التوكنات عند الاستيراد (gunicorn يستورد app ولا ينفّذ __main__)
_start_background()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5557"))
    print("=" * 55)
    print("l9bi7e Spam API")
    print("=" * 55)
    print(f"الخادم يعمل على المنفذ {port}")
    print(f"تحديث التوكنات كل {UPDATE_INTERVAL // 3600} ساعات")
    print(f"تخزين التوكنات في: {JWT_FILE}")
    print(f"تخزين الحسابات في: {ACCOUNTS_FILE}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)