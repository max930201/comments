from flask import Flask, request, jsonify, render_template
from datetime import datetime
import os
import psycopg2
import sqlite3

app = Flask(__name__)

# ------------------------------
# 讀取 Render 的資料庫環境變數
# ------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
use_postgresql = bool(DATABASE_URL)

# 修正舊格式 postgres://
if use_postgresql and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


# ------------------------------
# 建立 PostgreSQL / SQLite 連線
# ------------------------------
def get_db_connection():
    if use_postgresql:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect("comments.db")


# ------------------------------
# 初始化資料表
# ------------------------------
def init_db():
    if use_postgresql:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS comments (
                        id SERIAL PRIMARY KEY,
                        name TEXT,
                        message TEXT,
                        created_at TIMESTAMP,
                        is_deleted BOOLEAN DEFAULT FALSE
                    );
                """)
            conn.commit()
    else:
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    message TEXT,
                    created_at TEXT,
                    is_deleted INTEGER DEFAULT 0
                );
            """)
            conn.commit()

init_db()


# ------------------------------
# 首頁
# ------------------------------
@app.route("/")
def home():
    return render_template("commend.html")


# ------------------------------
# 新增留言
# ------------------------------
@app.route("/add", methods=["POST"])
def add_comment():
    data = request.json
    name = data.get("name", "匿名")
    message = data.get("message", "")
    utc_time = datetime.utcnow()

    if use_postgresql:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO comments (name, message, created_at, is_deleted)
                    VALUES (%s, %s, %s, FALSE)
                """, (name, message, utc_time))
            conn.commit()
    else:
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO comments (name, message, created_at, is_deleted)
                VALUES (?, ?, ?, 0)
            """, (name, message, utc_time))
            conn.commit()

    return jsonify({"status": "success"})


# ------------------------------
# 前端：列出未刪除留言
# ------------------------------
@app.route("/list")
def list_comments():
    if use_postgresql:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, message, created_at
                    FROM comments
                    WHERE is_deleted = FALSE
                    ORDER BY created_at DESC
                """)
                rows = cur.fetchall()
    else:
        with get_db_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, message, created_at
                FROM comments
                WHERE is_deleted = 0
                ORDER BY created_at DESC
            """).fetchall()

    comments = []
    for r in rows:
        comments.append({
            "id": r[0],
            "name": r[1],
            "message": r[2],
            "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else r[3]
        })

    return jsonify(comments)


# ------------------------------
# 後台：列出所有留言（含刪除）
# ------------------------------
@app.route("/admin/list")
def admin_list():
    if use_postgresql:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, message, created_at, is_deleted
                    FROM comments
                    ORDER BY created_at DESC
                """)
                rows = cur.fetchall()
    else:
        with get_db_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, message, created_at, is_deleted
                FROM comments
                ORDER BY created_at DESC
            """).fetchall()

    comments = []
    for r in rows:
        comments.append({
            "id": r[0],
            "name": r[1],
            "message": r[2],
            "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else r[3],
            "is_deleted": bool(r[4])
        })

    return jsonify(comments)


# ------------------------------
# 軟刪除
# ------------------------------
@app.route("/delete/<int:cid>", methods=["POST"])
def delete_comment(cid):
    if use_postgresql:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE comments SET is_deleted = TRUE WHERE id = %s", (cid,))
            conn.commit()
    else:
        with get_db_connection() as conn:
            conn.execute("UPDATE comments SET is_deleted = 1 WHERE id = ?", (cid,))
            conn.commit()

    return jsonify({"status": "deleted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
