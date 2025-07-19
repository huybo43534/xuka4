from flask import Flask, request, jsonify, send_from_directory
import json, os
from flask import render_template



app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    with open("users.json", "r", encoding="utf-8") as f:
        users = json.load(f)

    for user in users:
        if user["username"] == username and user["password"] == password:
            return jsonify({"status": "success"})

    return jsonify({"status": "fail"}), 401

@app.route('/questions')
def get_questions():
    made = request.args.get("made", "101")
    filename = f"questions{made}.json"
    filepath = os.path.join("questions", filename)

    if not os.path.exists(filepath):
        return jsonify({"error": "Không tìm thấy đề thi."}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        questions = json.load(f)
    return jsonify(questions)
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('results', filename, as_attachment=True)

@app.route('/save_result', methods=['POST'])
def save_result():
    data = request.get_json()
    print("[DEBUG]", data)

    hoten = data.get("hoten", "unknown")
    sbd = data.get("sbd", "N/A")
    ngaysinh = data.get("ngaysinh", "N/A")
    made = data.get("made", "000")
    diem = data.get("diem", "0.00")
    answers = data.get("answers", [])

    os.makedirs("results", exist_ok=True)
    filename = f"KQ_{hoten.replace(' ', '_')}_{made}.txt"
    filepath = os.path.join("results", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Họ tên: {hoten}\n")
        f.write(f"Số báo danh: {sbd}\n")       # ✅ Dòng cần thêm
        f.write(f"Ngày sinh: {ngaysinh}\n")    # ✅ Dòng cần thêm
        f.write(f"Mã đề: {made}\n")
        f.write(f"Điểm: {diem}/10\n\n")
        f.write("Chi tiết:\n")
        for a in answers:
            cau = a.get("cau")
            da_chon = a.get("da_chon") or "(chưa chọn)"
            dung_chinh_xac = a.get("dung_chinh_xac")
            dung = a.get("dung")
            ketqua = "✓" if dung else "✗"
            f.write(f"Câu {cau}: Đã chọn: {da_chon} | Đúng: {dung_chinh_xac} {ketqua}\n")

    return jsonify({"status": "saved", "filename": filename})




if __name__ == '__main__':
    app.run(debug=True)
