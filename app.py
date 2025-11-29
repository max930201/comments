from flask import Flask, request, jsonify, render_template
import os
import psycopg2  # PostgreSQL
import sqlite3   # SQLite
from datetime import datetime
import pytz      # 處理時區

app = Flask(__name__)

# --- 【資料庫設定】 ---
DATABASE_URL = os.environ.get('ASE_URL')  # Render 環境變數
USE_POSTGRESQL = bool(DATABASE_URL)

if USE_POSTGRESQL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("使用 PostgreSQL 資料庫 (從 ASE_URL 讀取)")
else:
    DB_PATH = "comments.db"
    print(f"使用本地 SQLite 資料庫檔案: {DB_PATH}")

# --- 【資料庫連線函式】 ---
def get_db_connection():
    if USE_POSTGRESQL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)

# --- 【初始化資料庫】 ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    if USE_POSTGRESQL:
        c.execute("""
            CREATE TABLE IF NOT EXISTS public.comments (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                message TEXT NOT NULL,
                time TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                visible INTEGER DEFAULT 1
            )
        """)
    else:
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

# --- 【時區設定】 ---
taiwan_tz = pytz.timezone('Asia/Taipei')

# --- 【Flask 路由】 ---
@app.route("/")
def home():
    return render_template("commend.html")

@app.route("/add", methods=["POST"])
def add():
    data = request.json
    print("收到留言:", data)
    name = data.get("name", "").strip()
    message = data.get("message", "").strip()

    if not name or not message:
        return jsonify({"status": "error", "message": "請輸入名字和留言內容"}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        table_name = "public.comments" if USE_POSTGRESQL else "comments"

        # --- 新增留言時使用正確時間 ---
        now = datetime.now(taiwan_tz)  # 取得台灣時間
        if USE_POSTGRESQL:
            c.execute(
                f"INSERT INTO {table_name} (name, message, time, visible) VALUES (%s, %s, %s, 1)",
                (name, message, now)
            )
        else:
            c.execute(
                f"INSERT INTO {table_name} (name, message, time, visible) VALUES (?, ?, ?, 1)",
                (name, message, now.strftime("%Y-%m-%d %H:%M:%S"))
            )

        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("新增留言錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/list", methods=["GET"])
def list_comments():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        table_name = "public.comments" if USE_POSTGRESQL else "comments"

        c.execute(f"SELECT id, name, message, time FROM {table_name} WHERE visible=1 ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        processed_rows = []
        for row in rows:
            if USE_POSTGRESQL and isinstance(row[3], datetime):
                time_str = row[3].astimezone(taiwan_tz).strftime("%Y/%m/%d %H:%M:%S")
            else:
                time_str = str(row[3])
            processed_rows.append((row[0], row[1], row[2], time_str))

        return jsonify(processed_rows)
    except Exception as e:
        print("查詢留言錯誤:", e)
        return jsonify([])

@app.route("/delete/<int:id>", methods=["DELETE"])
def delete_comment(id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        table_name = "public.comments" if USE_POSTGRESQL else "comments"

        if USE_POSTGRESQL:
            c.execute(f"UPDATE {table_name} SET visible=0 WHERE id=%s", (id,))
        else:
            c.execute(f"UPDATE {table_name} SET visible=0 WHERE id=?", (id,))

        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("刪除留言錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 【管理頁面 /admin】 ---
@app.route("/admin")
def admin():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        table_name = "public.comments" if USE_POSTGRESQL else "comments"

        c.execute(f"SELECT id, name, message, time, visible FROM {table_name} ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        processed_rows = []
        for row in rows:
            if USE_POSTGRESQL and isinstance(row[3], datetime):
                time_str = row[3].astimezone(taiwan_tz).strftime("%Y/%m/%d %H:%M:%S")
            else:
                time_str = str(row[3])
            processed_rows.append((row[0], row[1], row[2], time_str, row[4]))

        # 生成手機友善 HTML 表格
        html = """
        <h2>留言資料庫內容</h2>
        <div style="overflow-x:auto;">
        <table border='1' cellspacing='0' cellpadding='5'>
        <tr><th>ID</th><th>名字</th><th>留言</th><th>時間</th><th>Visible</th></tr>
        """
        for r in processed_rows:
            html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"
        html += "</table></div>"
        return html
    except Exception as e:
        print("查看資料庫錯誤:", e)
        return f"<p>發生錯誤: {str(e)}</p>"

if __name__ == "__main__":
    print(f"使用資料庫：{'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
    app.run(host="0.0.0.0", port=5000, debug=True)
