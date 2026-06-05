"""
EduTrack Pro — Flask Backend
Tech Stack: Python, Flask, scikit-learn, TensorFlow/Keras (deep learning), SQLite
"""

from flask import Flask, render_template, request, jsonify, session
import json, os, sqlite3, hashlib, datetime
from ml.performance_predictor import predict_grade, train_grade_model
from ml.attendance_risk import predict_attendance_risk, train_attendance_model
from ml.chatbot import get_chatbot_response

app = Flask(__name__)
app.secret_key = "edutrack_secret_2025"
DB = "edutrack.db"

# ─────────────────────────────────────────────
# DB INIT
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'tutor',
            secret_question TEXT,
            secret_answer TEXT
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class TEXT,
            parent TEXT,
            fees TEXT,
            password TEXT,
            fees_due_date TEXT
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(student_name, date)
        );
        CREATE TABLE IF NOT EXISTS test_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            subject TEXT,
            week TEXT,
            marks INTEGER,
            total INTEGER,
            pct REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            note TEXT,
            file_name TEXT,
            file_type TEXT,
            file_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            type TEXT,
            date TEXT
        );
    """)
    # Default tutor account
    pw = hashlib.sha256("1234".encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username,password,role,secret_question,secret_answer) VALUES (?,?,?,?,?)",
                  ("admin", pw, "tutor", "What is your school name?", "myschool"))
    except sqlite3.IntegrityError:
        pass
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    role = data.get("role", "tutor")
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = get_db()
    if role == "tutor":
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND role='tutor'",
                            (username, pw_hash)).fetchone()
        conn.close()
        if user:
            session["role"] = "tutor"
            session["username"] = username
            return jsonify({"ok": True, "role": "tutor", "username": username})
        return jsonify({"ok": False, "error": "Invalid credentials"})
    else:
        student = conn.execute("SELECT * FROM students WHERE LOWER(name)=LOWER(?)", (username,)).fetchone()
        conn.close()
        if not student:
            return jsonify({"ok": False, "error": "Student not found"})
        if student["password"] and student["password"] != password:
            return jsonify({"ok": False, "error": "Incorrect password"})
        session["role"] = "student"
        session["username"] = student["name"]
        return jsonify({"ok": True, "role": "student", "username": student["name"]})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/forgot_password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    role = data.get("role")
    conn = get_db()
    if role == "tutor":
        user = conn.execute("SELECT * FROM users WHERE role='tutor' AND username='admin'").fetchone()
        answer = data.get("answer", "").strip().lower()
        new_pw = data.get("new_password", "").strip()
        confirm = data.get("confirm_password", "").strip()
        if not user: conn.close(); return jsonify({"ok": False, "error": "User not found"})
        if answer != (user["secret_answer"] or "").lower(): conn.close(); return jsonify({"ok": False, "error": "Wrong answer"})
        if new_pw != confirm: conn.close(); return jsonify({"ok": False, "error": "Passwords don't match"})
        pw_hash = hashlib.sha256(new_pw.encode()).hexdigest()
        conn.execute("UPDATE users SET password=? WHERE username='admin'", (pw_hash,))
        conn.commit(); conn.close()
        return jsonify({"ok": True})
    else:
        sname = data.get("student_name", "").strip()
        parent = data.get("parent_name", "").strip()
        new_pw = data.get("new_password", "").strip()
        confirm = data.get("confirm_password", "").strip()
        student = conn.execute("SELECT * FROM students WHERE LOWER(name)=LOWER(?)", (sname,)).fetchone()
        if not student: conn.close(); return jsonify({"ok": False, "error": "Student not found"})
        if (student["parent"] or "").lower() != parent.lower(): conn.close(); return jsonify({"ok": False, "error": "Parent name mismatch"})
        if new_pw != confirm: conn.close(); return jsonify({"ok": False, "error": "Passwords don't match"})
        conn.execute("UPDATE students SET password=? WHERE LOWER(name)=LOWER(?)", (new_pw, sname))
        conn.commit(); conn.close()
        return jsonify({"ok": True})

@app.route("/api/change_password", methods=["POST"])
def change_password():
    if session.get("role") != "tutor":
        return jsonify({"ok": False, "error": "Unauthorized"})
    data = request.get_json()
    cur = data.get("current_password", "")
    new_pw = data.get("new_password", "")
    confirm = data.get("confirm_password", "")
    conn = get_db()
    cur_hash = hashlib.sha256(cur.encode()).hexdigest()
    user = conn.execute("SELECT * FROM users WHERE username='admin' AND password=?", (cur_hash,)).fetchone()
    if not user: conn.close(); return jsonify({"ok": False, "error": "Current password wrong"})
    if new_pw != confirm: conn.close(); return jsonify({"ok": False, "error": "Passwords don't match"})
    new_hash = hashlib.sha256(new_pw.encode()).hexdigest()
    conn.execute("UPDATE users SET password=? WHERE username='admin'", (new_hash,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ─────────────────────────────────────────────
# STUDENTS
# ─────────────────────────────────────────────
@app.route("/api/students", methods=["GET"])
def get_students():
    conn = get_db()
    rows = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/students", methods=["POST"])
def add_student():
    d = request.get_json()
    conn = get_db()
    conn.execute("INSERT INTO students (name,class,parent,fees,password,fees_due_date) VALUES (?,?,?,?,?,?)",
                 (d["name"], d.get("class",""), d.get("parent",""), d.get("fees",""),
                  d.get("password",""), d.get("fees_due_date","")))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/students/<int:sid>", methods=["DELETE"])
def delete_student(sid):
    conn = get_db()
    conn.execute("DELETE FROM students WHERE id=?", (sid,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/students/<int:sid>/due_date", methods=["PUT"])
def update_due_date(sid):
    d = request.get_json()
    conn = get_db()
    conn.execute("UPDATE students SET fees_due_date=? WHERE id=?", (d.get("fees_due_date",""), sid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ─────────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────────
@app.route("/api/attendance", methods=["GET"])
def get_attendance():
    conn = get_db()
    rows = conn.execute("SELECT * FROM attendance ORDER BY date").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/attendance", methods=["POST"])
def save_attendance():
    records = request.get_json()  # [{student_name, date, status}, ...]
    conn = get_db()
    for r in records:
        conn.execute("INSERT OR REPLACE INTO attendance (student_name,date,status) VALUES (?,?,?)",
                     (r["student_name"], r["date"], r["status"]))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ─────────────────────────────────────────────
# TEST MARKS
# ─────────────────────────────────────────────
@app.route("/api/marks", methods=["GET"])
def get_marks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM test_marks ORDER BY week,student_name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/marks", methods=["POST"])
def add_marks():
    d = request.get_json()
    marks = int(d.get("marks", 0))
    total = int(d.get("total", 1))
    pct   = round(marks / total * 100, 1) if total else 0
    conn  = get_db()
    conn.execute("INSERT INTO test_marks (student_name,subject,week,marks,total,pct) VALUES (?,?,?,?,?,?)",
                 (d["student_name"], d.get("subject",""), d.get("week",""), marks, total, pct))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/marks/<int:mid>", methods=["DELETE"])
def delete_marks(mid):
    conn = get_db()
    conn.execute("DELETE FROM test_marks WHERE id=?", (mid,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ─────────────────────────────────────────────
# NOTES
# ─────────────────────────────────────────────
@app.route("/api/notes", methods=["GET"])
def get_notes():
    conn = get_db()
    rows = conn.execute("SELECT id,student_name,note,file_name,file_type,created_at FROM notes ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/notes", methods=["POST"])
def add_note():
    d = request.get_json()
    conn = get_db()
    conn.execute("INSERT INTO notes (student_name,note,file_name,file_type,file_data) VALUES (?,?,?,?,?)",
                 (d["student_name"], d.get("note",""), d.get("file_name",""), d.get("file_type",""), d.get("file_data","")))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/notes/<int:nid>", methods=["DELETE"])
def delete_note(nid):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id=?", (nid,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/notes/<int:nid>/file")
def get_note_file(nid):
    conn = get_db()
    row = conn.execute("SELECT file_data, file_type, file_name FROM notes WHERE id=?", (nid,)).fetchone()
    conn.close()
    if not row or not row["file_data"]:
        return "Not found", 404
    import base64
    from flask import Response
    data = base64.b64decode(row["file_data"].split(",")[-1])
    return Response(data, mimetype=row["file_type"], headers={"Content-Disposition": f'attachment; filename="{row["file_name"]}"'})

# ─────────────────────────────────────────────
# ANNOUNCEMENTS
# ─────────────────────────────────────────────
@app.route("/api/announcements", methods=["GET"])
def get_announcements():
    conn = get_db()
    rows = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/announcements", methods=["POST"])
def add_announcement():
    d = request.get_json()
    today = datetime.date.today().isoformat()
    conn = get_db()
    conn.execute("INSERT INTO announcements (title,message,type,date) VALUES (?,?,?,?)",
                 (d["title"], d["message"], d.get("type","General"), today))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/announcements/<int:aid>", methods=["DELETE"])
def delete_announcement(aid):
    conn = get_db()
    conn.execute("DELETE FROM announcements WHERE id=?", (aid,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

# ─────────────────────────────────────────────
# ML ENDPOINTS
# ─────────────────────────────────────────────
@app.route("/api/ml/predict_grade", methods=["POST"])
def ml_predict_grade():
    """Predict a student's next test grade using ML (Random Forest + Neural Net ensemble)."""
    d = request.get_json()
    student = d.get("student_name", "")
    subject = d.get("subject", "")
    conn = get_db()
    marks = conn.execute(
        "SELECT marks, total, pct FROM test_marks WHERE student_name=? AND subject=? ORDER BY week",
        (student, subject)
    ).fetchall()
    conn.close()
    if len(marks) < 2:
        return jsonify({"ok": False, "error": "Not enough data (need ≥2 tests)"})
    result = predict_grade([dict(m) for m in marks])
    return jsonify({"ok": True, **result})

@app.route("/api/ml/attendance_risk", methods=["POST"])
def ml_attendance_risk():
    """Predict attendance dropout risk using Logistic Regression + Neural Net."""
    d = request.get_json()
    student = d.get("student_name", "")
    conn = get_db()
    att = conn.execute(
        "SELECT status FROM attendance WHERE student_name=? ORDER BY date", (student,)
    ).fetchall()
    marks = conn.execute(
        "SELECT pct FROM test_marks WHERE student_name=? ORDER BY week", (student,)
    ).fetchall()
    conn.close()
    result = predict_attendance_risk(
        [r["status"] for r in att],
        [r["pct"] for r in marks]
    )
    return jsonify({"ok": True, **result})

@app.route("/api/ml/class_insights", methods=["GET"])
def ml_class_insights():
    """Return ML-powered class-level insights."""
    conn = get_db()
    students = conn.execute("SELECT name FROM students").fetchall()
    insights = []
    for s in students:
        name = s["name"]
        att = conn.execute("SELECT status FROM attendance WHERE student_name=?", (name,)).fetchall()
        marks = conn.execute("SELECT pct FROM test_marks WHERE student_name=?", (name,)).fetchall()
        statuses = [r["status"] for r in att]
        pcts = [r["pct"] for r in marks]
        total = len(statuses)
        present = statuses.count("P")
        att_pct = round(present / total * 100, 1) if total else 0
        avg_marks = round(sum(pcts) / len(pcts), 1) if pcts else None
        risk = predict_attendance_risk(statuses, pcts) if total >= 3 else None
        insights.append({
            "name": name,
            "attendance_pct": att_pct,
            "avg_marks": avg_marks,
            "risk": risk
        })
    conn.close()
    return jsonify(insights)

@app.route("/api/ml/train", methods=["POST"])
def ml_train():
    """Re-train ML models with current data."""
    conn = get_db()
    marks_data = [dict(r) for r in conn.execute("SELECT * FROM test_marks").fetchall()]
    att_data = [dict(r) for r in conn.execute("SELECT * FROM attendance").fetchall()]
    conn.close()
    g_res = train_grade_model(marks_data)
    a_res = train_attendance_model(att_data)
    return jsonify({"ok": True, "grade_model": g_res, "attendance_model": a_res})

# ─────────────────────────────────────────────
# CHATBOT
# ─────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """AI chatbot using Anthropic API (via server-side call)."""
    d = request.get_json()
    message = d.get("message", "")
    history = d.get("history", [])
    api_key = d.get("api_key", "")

    # Build context from DB
    conn = get_db()
    students = [dict(r) for r in conn.execute("SELECT * FROM students").fetchall()]
    att_all = conn.execute("SELECT * FROM attendance").fetchall()
    marks_all = conn.execute("SELECT * FROM test_marks").fetchall()
    conn.close()

    context_parts = [f"Today: {datetime.date.today().isoformat()}", f"Total students: {len(students)}"]
    for s in students:
        name = s["name"]
        att_records = [r for r in att_all if r["student_name"] == name]
        p = sum(1 for r in att_records if r["status"] == "P")
        total = len(att_records)
        pct = f"{round(p/total*100)}%" if total else "N/A"
        student_marks = [r for r in marks_all if r["student_name"] == name]
        last_mark = student_marks[-1] if student_marks else None
        minfo = f"Latest: {last_mark['subject']} {last_mark['marks']}/{last_mark['total']} ({last_mark['pct']}%) week {last_mark['week']}" if last_mark else "No marks"
        context_parts.append(f"Student: {name} | Class: {s.get('class','?')} | Fees: {s.get('fees','?')} | Due: {s.get('fees_due_date','Not set')} | Attendance: {p}/{total} ({pct}) | {minfo}")

    context = "\n".join(context_parts)
    result = get_chatbot_response(message, history, context, api_key)
    return jsonify(result)

# ─────────────────────────────────────────────
# TUTOR SECRET QUESTION
# ─────────────────────────────────────────────
@app.route("/api/tutor_secret_question", methods=["GET"])
def get_secret_question():
    conn = get_db()
    user = conn.execute("SELECT secret_question FROM users WHERE role='tutor'").fetchone()
    conn.close()
    return jsonify({"question": user["secret_question"] if user else "What is your school name?"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
