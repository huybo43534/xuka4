from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
import json, os


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_DIR = BASE_DIR / "questions"
RESULTS_DIR = BASE_DIR / "results"
STATIC_DIR = BASE_DIR / "static"
USERS_FILE = STATIC_DIR / "users.json"

RESULTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)



# --- Cache users để tránh đọc file nhiều lần ---
_users_cache = None
def load_users():
    global _users_cache
    if _users_cache is None:
        if not USERS_FILE.exists():
            return []
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            _users_cache = json.load(f)
    return _users_cache


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

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

@app.route('/')
def index():
    return render_template('ht.html')

@app.post("/api/login")
def api_login():
    try:
        data = request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"status": "error", "msg": "Thiếu username hoặc password"}), 400

        if not USERS_FILE.exists():
            return jsonify({"status": "error", "msg": "users.json not found"}), 404

        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
            if not isinstance(users, list):
                return jsonify({"status": "error", "msg": "users.json không hợp lệ"}), 500
        except json.JSONDecodeError:
            return jsonify({"status": "error", "msg": "users.json bị lỗi định dạng"}), 500

        user = next((u for u in users if u.get("username") == username and u.get("password") == password), None)
        if user:
            return jsonify({"status": "success"}), 200

        return jsonify({"status": "fail", "msg": "Sai tài khoản hoặc mật khẩu"}), 401

    except Exception as e:
        app.logger.exception("Lỗi đăng nhập")
        return jsonify({"error": "internal_error"}), 500

@app.post("/api/register")
def api_register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"status": "error", "msg": "Thiếu username hoặc password"}), 400

    # Đọc file users.json
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

    if any(u["username"] == username for u in users):
        return jsonify({"status": "error", "msg": "Tài khoản đã tồn tại"}), 400

    users.append({"username": username, "password": password})

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "success", "msg": "Đăng ký thành công"})


@app.post("/api/generate-token")
def api_generate_token():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"status": "error", "msg": "Thiếu username"}), 400

    # Tạo token đơn giản (có thể dùng JWT sau)
    token = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return jsonify({"status": "success", "token": token})

@app.get('/questions')
def get_questions():
    made = request.args.get("made", "101")
    if not made.isdigit():
        return jsonify({"error": "Mã đề không hợp lệ"}), 400

    if not (101 <= int(made) <= 999):
        return jsonify({"error": "Mã đề không hợp lệ"}), 400

    filename = f"questions{made}.json"
    filepath = QUESTIONS_DIR / filename
    if not filepath.exists():
        return jsonify({"error": "Không tìm thấy đề thi."}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        questions = json.load(f)
    return jsonify(questions)

@app.get('/download/<path:filename>')
def download_file(filename):
    safe = secure_filename(filename)
    return send_from_directory(RESULTS_DIR, safe, as_attachment=True)

@app.post('/save_result')
def save_result():
    data = request.get_json(silent=True) or {}
    hoten = data.get("hoten", "unknown")
    sbd = data.get("sbd", "N/A")
    ngaysinh = data.get("ngaysinh", "N/A")
    made = data.get("made", "000")
    diem = data.get("diem", "0.00")
    answers = data.get("answers", [])

    filename_de = f"questions{made}.json"
    filepath_de = QUESTIONS_DIR / filename_de
    question_data = []
    if filepath_de.exists():
        with open(filepath_de, "r", encoding="utf-8") as f:
            question_data = json.load(f)

    noi_dung_map = {}
    for q in question_data:
        cau_so = q.get("cau")
        if cau_so is not None:
            noi_dung_map[cau_so] = q.get("noi_dung", q.get("question", ""))

    for a in answers:
        if not a.get("noi_dung"):
            cau_so = a.get("cau")
            a["noi_dung"] = noi_dung_map.get(cau_so, "Không có nội dung")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(hoten.replace(" ", "_")) or "unknown"
    filename = f"KQ_{safe_name}_{made}_{timestamp}.txt"
    filepath = RESULTS_DIR / filename

    lines = [
        f"Họ tên: {hoten}",
        f"Số báo danh: {sbd}",
        f"Ngày sinh: {ngaysinh}",
        f"Mã đề: {made}",
        f"Điểm: {diem}/10",
        "",
        "Chi tiết:"
    ]

    for a in answers:
        cau = a.get("cau")
        noi_dung = a.get("noi_dung", "Không có nội dung")
        da_chon = a.get("da_chon") or "(chưa chọn)"
        dung_chinh_xac = a.get("dung_chinh_xac")
        dung = a.get("dung")
        ketqua = "✓" if dung else "✗"
        lines.append(f"Câu {cau}: {noi_dung}")
        lines.append(f"  → Đã chọn: {da_chon} | Đúng: {dung_chinh_xac} {ketqua}")
        lines.append("")

    result_text = "\n".join(lines)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result_text)

    return jsonify({
        "status": "saved",
        "text": result_text,
        "download": f"/download/{filename}"
    })

@app.errorhandler(Exception)
def handle_all(e):
    app.logger.exception(e)
    return jsonify({"error": "internal_error"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)








