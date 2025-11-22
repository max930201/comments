from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)

DB_PATH = r"C:\Users\USER\OneDrive\Desktop\我做的網站\思淼生日快樂\comments.db"
print("Flask 使用的資料庫路徑：", DB_PATH)

# 初始化資料庫
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            time TEXT NOT NULL,
            visible INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return render_template("commend.html")

@app.route("/add", methods=["POST"])
def add():
    data = request.json
    print("收到留言:", data)
    name = data.get("name", "").strip()
    message = data.get("message", "").strip()
    time = data.get("time", "")

    if not name or not message:
        return jsonify({"status": "error", "message": "請輸入名字和留言內容"}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO comments (name, message, time, visible) VALUES (?, ?, ?, 1)",
                  (name, message, time))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("新增留言錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/list", methods=["GET"])
def list_comments():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 只抓 visible = 1 的留言
    c.execute("SELECT id, name, message, time FROM comments WHERE visible=1 ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    print("抓到的留言資料:", rows)
    return jsonify(rows)

@app.route("/delete/<int:id>", methods=["DELETE"])
def delete_comment(id):
    # 改成只更新 visible=0，不刪資料
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE comments SET visible=0 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("使用資料庫路徑：", DB_PATH)
    app.run(host="0.0.0.0", port=5000, debug=True)
