from flask import Flask, request, jsonify, render_template
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ------------------------------------------------------
# 永久資料庫設定：使用 Render 的 Disk
# 假設你在 Render 上建立的 Disk 名字叫 comments，Mount Path: /var/data
DB_PATH = "/var/data/comments.db"
print(f"使用永久 SQLite 資料庫: {DB_PATH}")
# ------------------------------------------------------

# 資料庫連線函式
def get_db_connection():
    return sqlite3.connect(DB_PATH)

# 初始化資料庫：創建表格（只執行一次）
def init_db():
    conn = get_db_connection()
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

# ------------------------------------------------------
# Flask 路由
# ------------------------------------------------------

@app.route("/")
def home():
    return render_template("commend.html")

# 新增留言
@app.route("/add", methods=["POST"])
def add():
    data = request.json
    name = data.get("name", "").strip()
    message = data.get("message", "").strip()
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not name or not message:
        return jsonify({"status": "error", "message": "請輸入名字和留言內容"}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO comments (name, message, time, visible) VALUES (?, ?, ?, ?)",
            (name, message, time, 1)
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("新增留言錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# 取得留言列表（只顯示未刪除）
@app.route("/list", methods=["GET"])
def list_comments():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, message, time FROM comments WHERE visible=1 ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        print("查詢留言錯誤:", e)
        return jsonify([])

# 假刪除留言
@app.route("/delete/<int:id>", methods=["DELETE"])
def delete_comment(id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE comments SET visible=0 WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("刪除留言錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
