from flask import Flask, request, jsonify, send_from_directory, render_template
import json, os

app = Flask(__name__)

@app.route('/huongdan')
def huongdan():
    return render_template('huongdan.html')

@app.route('/xuka')
def xuka():
    return render_template('xuka.html')

@app.route('/tronde')
def tronde():
    return render_template('tronde.html')

@app.route('/')
def index():
    return render_template('k.html')

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
    hoten = data.get("hoten", "unknown")
    sbd = data.get("sbd", "N/A")
    ngaysinh = data.get("ngaysinh", "N/A")
    made = data.get("made", "000")
    diem = data.get("diem", "0.00")
    answers = data.get("answers", [])

    # Đọc đề thi
    filename_de = f"questions{made}.json"
    filepath_de = os.path.join("questions", filename_de)
    if os.path.exists(filepath_de):
        with open(filepath_de, "r", encoding="utf-8") as f:
            question_data = json.load(f)
    else:
        question_data = []

    # Gán nội dung câu hỏi
    for a in answers:
        cau_so = a.get("cau")
        cau_hoi = next((q for q in question_data if q.get("cau") == cau_so), None)
        if cau_hoi:
            a["noi_dung"] = cau_hoi.get("question", "")

    # Ghi file
    os.makedirs("results", exist_ok=True)
    filename = f"KQ_{hoten.replace(' ', '_')}_{made}.txt"
    filepath = os.path.join("results", filename)

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

    # Ghi ra file nếu muốn lưu
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(result_text)

    return jsonify({
        "status": "saved",
        "text": result_text
    })


if __name__ == '__main__':
    app.run(debug=True)
