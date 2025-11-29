from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///comments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 留言資料表
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    message = db.Column(db.Text)

# 初始化資料庫（第一次跑才要）
@app.before_first_request
def create_tables():
    db.create_all()

# 主頁
@app.route("/")
def index():
    comments = Comment.query.order_by(Comment.id.desc()).all()
    return render_template("comments.html", comments=comments)

# 新增留言
@app.route("/add_comment", methods=["POST"])
def add_comment():
    name = request.form.get("name")
    message = request.form.get("message")
    if not name or not message:
        return jsonify({"status": "error"})
    new_comment = Comment(name=name, message=message)
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({"status": "success"})

# 刪除留言
@app.route("/delete_comment/<int:id>", methods=["POST"])
def delete_comment(id):
    comment = Comment.query.get(id)
    if comment:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({"status": "deleted"})
    return jsonify({"status": "error"})

if __name__ == "__main__":
    app.run(debug=True)
