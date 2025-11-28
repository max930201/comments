from flask import Flask, request, jsonify, render_template
import os
import psycopg2 # 新增：用於 PostgreSQL
import sqlite3  # 舊有：用於本地 SQLite
from datetime import datetime

app = Flask(__name__)

# --- 【 資料庫設定：從環境變數讀取或使用本地 SQLite 】 ---

# 檢查 Render 環境變數 ASE_URL 是否存在
DATABASE_URL = os.environ.get('ASE_URL')

# 判斷使用哪種資料庫連線函式
USE_POSTGRESQL = bool(DATABASE_URL)

if USE_POSTGRESQL:
    # Render 有時使用 postgres:// 格式，但 psycopg2 需要 postgresql://
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # 打印資訊，確認使用 PostgreSQL
    print("使用 PostgreSQL 資料庫 (從 ASE_URL 讀取)")
else:
    # 本地開發時使用 SQLite
    DB_PATH = "comments.db" # 使用相對路徑，避免硬編碼您的個人電腦路徑
    print(f"使用本地 SQLite 資料庫檔案: {DB_PATH}")


# 資料庫連線函式
def get_db_connection():
    if USE_POSTGRESQL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect(DB_PATH)

# 初始化資料庫：創建表格
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    if USE_POSTGRESQL:
        # PostgreSQL 語法：使用 SERIAL PRIMARY KEY
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
        # SQLite 語法
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

# 首次運行時初始化資料庫
init_db()

# --- 【 Flask 路由及函式 】 ---

@app.route("/")
def home():
    return render_template("commend.html")

# --- 【 修正點 1：/add 函式確保同時兼容 PostgreSQL (%s) 和 SQLite (?) 】 ---
@app.route("/add", methods=["POST"])
def add():
    data = request.json
    print("收到留言:", data)
    name = data.get("name", "").strip()
    message = data.get("message", "").strip()
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not name or not message:
        return jsonify({"status": "error", "message": "請輸入名字和留言內容"}), 400

    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        table_name = "public.comments" if USE_POSTGRESQL else "comments"
        
        # 根據資料庫類型使用正確的佔位符
        if USE_POSTGRESQL:
            # PostgreSQL/psycopg2 使用 %s 佔位符
            sql_query = f"INSERT INTO {table_name} (name, message, time, visible) VALUES (%s, %s, %s, %s)"
        else:
            # SQLite (sqlite3) 使用 ? 佔位符
            sql_query = f"INSERT INTO {table_name} (name, message, time, visible) VALUES (?, ?, ?, ?)"
            
        params = (name, message, time, 1)
        
        c.execute(sql_query, params)
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("新增留言錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
# ----------------------------------------------------------------------

@app.route("/list", methods=["GET"])
def list_comments():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        table_name = "public.comments" if USE_POSTGRESQL else "comments"
        
        c.execute(f"SELECT id, name, message, time FROM {table_name} WHERE visible=1 ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        
        # 為了保持與原來的 jsonify 格式一致，需要處理 PostgreSQL 的 time 欄位
        if USE_POSTGRESQL:
            processed_rows = []
            for row in rows:
                # 將 datetime 物件轉換為字串
                time_str = row[3].strftime("%Y/%m/%d %H:%M:%S") if isinstance(row[3], datetime) else str(row[3])
                processed_rows.append((row[0], row[1], row[2], time_str))
            rows = processed_rows

        print("抓到的留言資料:", rows)
        return jsonify(rows)

    except Exception as e:
        print("查詢留言錯誤:", e)
        # 如果是找不到表格，可能是表格還沒創建，回傳空列表
        return jsonify([])

# --- 【 修正點 2：/delete 函式確保同時兼容 PostgreSQL (%s) 和 SQLite (?) 】 ---
@app.route("/delete/<int:id>", methods=["DELETE"])
def delete_comment(id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        table_name = "public.comments" if USE_POSTGRESQL else "comments"
        
        # 根據資料庫類型使用正確的佔位符
        if USE_POSTGRESQL:
            # PostgreSQL/psycopg2 使用 %s 佔位符
            sql_query = f"UPDATE {table_name} SET visible=0 WHERE id=%s"
        else:
            # SQLite (sqlite3) 使用 ? 佔位符
            sql_query = f"UPDATE {table_name} SET visible=0 WHERE id=?"
        
        # 參數 tuple
        c.execute(sql_query, (id,))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        print("刪除留言錯誤:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
# ----------------------------------------------------------------------


if __name__ == "__main__":
    print(f"使用資料庫：{'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
    app.run(host="0.0.0.0", port=5000, debug=True)
