from flask import Flask, request, jsonify, send_from_directory, render_template, abort
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
import json, os
from flask_socketio import SocketIO, emit





app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change_this_secret_key")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

QUESTION_DIR = os.path.join(BASE_DIR, "questions")
QUESTIONS_FILE = os.path.join(QUESTION_DIR, "questions.json")
socketio = SocketIO(app, async_mode="threading")


# CSRF
csrf = CSRFProtect(app)

# Rate limiting (memory backend để tránh warning khi dev)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=["100 per 5 minutes"]
)

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_DIR = BASE_DIR / "questions"
RESULTS_DIR = BASE_DIR / "results"
STATIC_DIR = BASE_DIR / "static"

USERS_FILE = STATIC_DIR / "users.json"      # Học sinh
ADMIN_FILE = STATIC_DIR / "users1.json"     # Quản trị viên

RESULTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
QUESTIONS_DIR.mkdir(exist_ok=True)

# --- Helpers ---
def load_users(file_path: Path):
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def list_exam_codes():
    codes = []
    pattern = re.compile(r'^questions(\d{3,})\.json$')
    for p in QUESTIONS_DIR.glob("questions*.json"):
        m = pattern.match(p.name)
        if m:
            code = m.group(1)
            if code.isdigit():
                codes.append(code)
    codes = sorted(set(codes), key=lambda x: int(x))
    return codes

# --- Route: Save answers and calculate score ---
def tinh_diem_va_luu_bai_lam(bai_lam, de_thi):
    so_cau_dung = 0
    tong_cau_trac_nghiem = 0
    ket_qua = []

    for i, cau_hoi in enumerate(de_thi):
        item = cau_hoi.copy()
        ma_cau = f"cau_{i}"
        tra_loi = bai_lam.get(ma_cau)

        if cau_hoi.get("kieu_cau_hoi") == "tu_luan":
            item["tra_loi_hoc_sinh"] = tra_loi or ""
        elif "lua_chon" in cau_hoi and "dap_an_dung" in cau_hoi:
            tong_cau_trac_nghiem += 1
            if tra_loi == cau_hoi["dap_an_dung"]:
                so_cau_dung += 1
            item["tra_loi_hoc_sinh"] = tra_loi or ""
        else:
            item["tra_loi_hoc_sinh"] = tra_loi or ""

        ket_qua.append(item)

    diem = round((so_cau_dung / max(tong_cau_trac_nghiem, 1)) * 10, 2)

    return {
        "diem": diem,
        "so_cau_dung": so_cau_dung,
        "tong_cau_trac_nghiem": tong_cau_trac_nghiem,
        "bai_lam_chi_tiet": ket_qua
    }


@app.route('/alochat')
def alochat():
    return render_template('alochat.html')

@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, broadcast=True)

@socketio.on('signal')
def handle_signal(data):
    emit('signal', data, broadcast=True, include_self=False)


# --- Routes (views) ---
@app.route('/favicon.ico')
def favicon():
    icon_path = STATIC_DIR / "favicon.ico"
    if icon_path.exists():
        return send_from_directory(STATIC_DIR, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    return '', 204  # Không có favicon

@app.route('/xuka')
def xuka():
    return render_template('xuka.html')

@app.route('/huongdan')
def huongdan():
    return render_template('huongdan.html')

@app.route('/tronde')
def tronde():
    return render_template('ao.html')

@app.route('/h2')
def h2():
    return render_template('h2.html')

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/")
def web():
    return render_template("index_web.html")

@app.route("/mobile")
def mobile():
    return render_template("index_mobile.html")

# --- API: Danh sách mã đề ---
@app.get("/api/made")
def api_made():
    return jsonify(list_exam_codes())

# --- API LOGIN ---
@app.post("/api/login")
@csrf.exempt
@limiter.limit("10/minute")
def api_login():
    try:
        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", "")).strip()

        if not username or not password:
            return jsonify({"status": "error", "msg": "Thiếu username hoặc password"}), 400

        admins = load_users(ADMIN_FILE)
        if any(u.get("username") == username and u.get("password") == password for u in admins):
            return jsonify({"status": "success", "role": "admin"}), 200

        users = load_users(USERS_FILE)
        if any(u.get("username") == username and u.get("password") == password for u in users):
            return jsonify({"status": "success", "role": "user"}), 200

        return jsonify({"status": "fail", "msg": "Sai tài khoản hoặc mật khẩu"}), 401

    except Exception:
        app.logger.exception("Lỗi đăng nhập")
        return jsonify({"error": "internal_error"}), 500

# --- API REGISTER ---
@app.post("/api/register")
@csrf.exempt
@limiter.limit("5/minute")
def api_register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not username or not password:
        return jsonify({"status": "error", "msg": "Thiếu username hoặc password"}), 400

    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            users = json.load(f)
        except json.JSONDecodeError:
            users = []

    if any(u.get("username") == username for u in users):
        return jsonify({"status": "error", "msg": "Tài khoản đã tồn tại"}), 400

    users.append({"username": username, "password": password})
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "success", "msg": "Đăng ký thành công"})

# --- Token ---
@app.post("/api/generate-token")
@csrf.exempt
def api_generate_token():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    if not username:
        return jsonify({"status": "error", "msg": "Thiếu username"}), 400

    token = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return jsonify({"status": "success", "token": token})

@app.get("/api/list_made")
def api_list_made():
    made_list = []
    for f in QUESTIONS_DIR.glob("questions*.json"):
        code = f.stem.replace("questions", "")
        if code.isdigit():
            made_list.append(code)
    return jsonify(sorted(made_list))

# --- Lấy đề thi ---
@app.route("/questions")
def get_questions():
    made = request.args.get("made", "000")
    try:
        filename = f"questions{made}.json"
        filepath = QUESTIONS_DIR / filename
        with open(filepath, encoding="utf-8") as f:
            questions = json.load(f)

        processed_questions = []
        for i, q in enumerate(questions, 1):
            q_processed = {
                "cau": i,
                "noi_dung": q.get("noi_dung", ""),
            }
            if q.get("kieu_cau_hoi") == "tu_luan":
                q_processed["kieu_cau_hoi"] = "tu_luan"
                q_processed["tra_loi_hoc_sinh"] = q.get("tra_loi_hoc_sinh", "")
                q_processed["goi_y_dap_an"] = q.get("goi_y_dap_an", "")
            else:
                q_processed["lua_chon"] = q.get("lua_chon", {})
                q_processed["dap_an_dung"] = q.get("dap_an_dung", "")
            processed_questions.append(q_processed)

        return jsonify(processed_questions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Download kết quả ---
@app.get('/download/<path:filename>')
def download_file(filename):
    safe = secure_filename(filename)
    file_path = RESULTS_DIR / safe
    if not file_path.exists():
        abort(404)
    return send_from_directory(RESULTS_DIR, safe, as_attachment=True)

@app.route("/save_result", methods=["POST"])
@csrf.exempt
def save_result():
    data = request.get_json(silent=True) or {}

    hoten = str(data.get("hoten", "unknown")).strip()
    sbd = str(data.get("sbd", "N/A")).strip()
    ngaysinh = str(data.get("ngaysinh", "N/A")).strip()
    made = str(data.get("made", "000")).strip()
    diem = str(data.get("diem", "0.00")).strip()
    answers = data.get("answers", [])

    if not answers:
        return jsonify({"status": "error", "msg": "Không có câu trả lời nào được gửi"}), 400

    # Load đề thi theo mã đề
    filename_de = f"questions{made}.json"
    filepath_de = QUESTIONS_DIR / filename_de
    question_data = []
    if filepath_de.exists():
        try:
            with open(filepath_de, "r", encoding="utf-8") as f:
                question_data = json.load(f)
        except Exception as e:
            app.logger.error(f"Lỗi đọc file đề: {e}")
            question_data = []

    # Tạo file kết quả
    timestamp = datetime.now().strftime("%H:%M:%S, %d/%m/%Y")
    safe_name = secure_filename(hoten.replace(" ", "_")) or "unknown"
    filename = f"KQ_{safe_name}_{made}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = RESULTS_DIR / filename

    lines = [
        "KẾT QUẢ BÀI THI",
        f"Họ tên: {hoten}",
        f"SBD: {sbd}",
        f"Ngày sinh: {ngaysinh}",
        f"Mã đề: {made}",
        f"Điểm: {diem}/10",
        f"Nộp lúc: {timestamp}",
        ""
    ]

    # Ghi kết quả từng câu
    for a in answers:
        cau = a.get("cau", "N/A")
        noi_dung = a.get("noi_dung", "Không có nội dung")
        kieu = a.get("kieu_cau_hoi", "").lower()

        try:
            idx = int(cau) - 1
            if 0 <= idx < len(question_data):
                cau_goc = question_data[idx]
            else:
                cau_goc = {}
        except (ValueError, TypeError):
            cau_goc = {}

        lines.append(f"Câu {cau}: {noi_dung}")

        if kieu == "tu_luan":
            tra_loi = a.get("tra_loi_hoc_sinh", "").strip() or "[Chưa trả lời]"
            goi_y = a.get("goi_y_dap_an", "").strip()
            lines.append(f"  Bạn chọn: {tra_loi}")
            if goi_y:
                lines.append(f"  Gợi ý đáp án: {goi_y}")
        elif kieu == "trac_nghiem":
            da_chon = a.get("da_chon", "(chưa chọn)")
            dap_an_dung = cau_goc.get("dap_an_dung")
            lines.append(f"  Bạn chọn: {da_chon}")
            if dap_an_dung is not None:
                lines.append(f"  Đáp án đúng: {dap_an_dung}")
        else:
            tra_loi = a.get("tra_loi_hoc_sinh", a.get("da_chon", "(chưa trả lời)"))
            lines.append(f"  Bạn trả lời: {tra_loi}")

        lines.append("")

    # Ghi ra file
    try:
        filepath.write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        return jsonify({"status": "error", "msg": f"Lỗi ghi file: {str(e)}"}), 500

    return jsonify({
        "status": "saved",
        "text": "\n".join(lines),
        "download": f"/download/{filename}"
    })


# --- Giải mã QR ---
@app.post("/api/decrypt_qr")
@csrf.exempt
def api_decrypt_qr():
    try:
        data = request.get_json(silent=True) or {}
        qr_value = data.get("qr_value", "").strip()

        if not qr_value:
            return jsonify({"status": "error", "msg": "Thiếu dữ liệu QR"}), 400

        # TODO: Thực hiện validate/giải mã thực tế ở đây
        return jsonify({"status": "success", "decoded": qr_value}), 200

    except Exception:
        app.logger.exception("Lỗi giải mã QR")
        return jsonify({"status": "error", "msg": "Lỗi giải mã QR"}), 500

# --- Error handler ---
@app.errorhandler(Exception)
def handle_all(e):
    app.logger.exception(e)
    return jsonify({"error": "internal_error"}), 500

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
