from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, send
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "doheon_world_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")

DB_NAME = "database.db"
ADMIN_EMAIL = "dlehgjs@gmail.com"


def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        nickname TEXT,
        is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        updated_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        done INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        content TEXT,
        likes INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        nickname TEXT,
        message TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_type TEXT,
        target_id INTEGER,
        reason TEXT,
        reporter_id INTEGER,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def get_user():
    if "user_id" not in session:
        return None

    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user


def admin_required():
    user = get_user()
    return user and user["is_admin"] == 1


@app.route("/")
def home():
    init_db()
    user = get_user()

    if not user:
        return render_template("index.html", page="home")

    conn = db()

    memo = conn.execute("SELECT * FROM memos WHERE user_id=?", (user["id"],)).fetchone()
    todos = conn.execute("SELECT * FROM todos WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()

    posts = conn.execute("""
        SELECT posts.*, users.nickname
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()

    comments = conn.execute("""
        SELECT comments.*, users.nickname
        FROM comments
        JOIN users ON comments.user_id = users.id
        ORDER BY comments.id ASC
    """).fetchall()

    notices = conn.execute("SELECT * FROM notices ORDER BY id DESC").fetchall()
    chats = conn.execute("SELECT * FROM chat_messages ORDER BY id DESC LIMIT 50").fetchall()

    stats = {
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "posts": conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
        "comments": conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
        "todos": conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0],
        "chats": conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0],
        "reports": conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
    }

    conn.close()

    return render_template(
        "index.html",
        page="portal",
        user=user,
        memo=memo,
        todos=todos,
        posts=posts,
        comments=comments,
        notices=notices,
        chats=reversed(chats),
        stats=stats
    )


@app.route("/signup", methods=["POST"])
def signup():
    email = request.form["email"].strip()
    password = request.form["password"].strip()
    nickname = request.form["nickname"].strip()

    if not email.endswith("@gmail.com"):
        return "이메일은 @gmail.com으로 끝나야 합니다."

    if len(password) < 8:
        return "비밀번호는 8자리 이상이어야 합니다."

    is_admin = 1 if email == ADMIN_EMAIL else 0

    conn = db()

    try:
        conn.execute(
            "INSERT INTO users (email, password, nickname, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
            (email, generate_password_hash(password), nickname, is_admin, now())
        )
        conn.commit()
    except:
        conn.close()
        return "이미 가입된 이메일입니다."

    conn.close()
    return redirect("/")


@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"].strip()
    password = request.form["password"].strip()

    conn = db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    if not user:
        return "가입되지 않은 이메일입니다."

    if user["is_banned"] == 1:
        return "정지된 회원입니다."

    if check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        return redirect("/")

    return "비밀번호가 틀렸습니다."


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/profile", methods=["POST"])
def profile():
    user = get_user()
    if not user:
        return redirect("/")

    nickname = request.form["nickname"].strip()
    if nickname:
        conn = db()
        conn.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, user["id"]))
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/memo", methods=["POST"])
def memo():
    user = get_user()
    if not user:
        return redirect("/")

    content = request.form["content"]

    conn = db()
    old = conn.execute("SELECT * FROM memos WHERE user_id=?", (user["id"],)).fetchone()

    if old:
        conn.execute("UPDATE memos SET content=?, updated_at=? WHERE user_id=?", (content, now(), user["id"]))
    else:
        conn.execute("INSERT INTO memos (user_id, content, updated_at) VALUES (?, ?, ?)", (user["id"], content, now()))

    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/todo/add", methods=["POST"])
def add_todo():
    user = get_user()
    if not user:
        return redirect("/")

    content = request.form["content"].strip()

    if content:
        conn = db()
        conn.execute("INSERT INTO todos (user_id, content, created_at) VALUES (?, ?, ?)", (user["id"], content, now()))
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/todo/toggle/<int:todo_id>")
def toggle_todo(todo_id):
    user = get_user()
    if not user:
        return redirect("/")

    conn = db()
    todo = conn.execute("SELECT * FROM todos WHERE id=? AND user_id=?", (todo_id, user["id"])).fetchone()

    if todo:
        new_done = 0 if todo["done"] else 1
        conn.execute("UPDATE todos SET done=? WHERE id=?", (new_done, todo_id))
        conn.commit()

    conn.close()
    return redirect("/")


@app.route("/todo/delete/<int:todo_id>")
def delete_todo(todo_id):
    user = get_user()
    if not user:
        return redirect("/")

    conn = db()
    conn.execute("DELETE FROM todos WHERE id=? AND user_id=?", (todo_id, user["id"]))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/post/add", methods=["POST"])
def add_post():
    user = get_user()
    if not user:
        return redirect("/")

    title = request.form["title"].strip()
    content = request.form["content"].strip()

    if title and content:
        conn = db()
        conn.execute(
            "INSERT INTO posts (user_id, title, content, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], title, content, now())
        )
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/post/like/<int:post_id>")
def like_post(post_id):
    conn = db()
    conn.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/comment/add/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    user = get_user()
    if not user:
        return redirect("/")

    content = request.form["content"].strip()

    if content:
        conn = db()
        conn.execute(
            "INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
            (post_id, user["id"], content, now())
        )
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/notice/add", methods=["POST"])
def add_notice():
    if not admin_required():
        return "관리자만 공지 작성 가능"

    title = request.form["title"].strip()
    content = request.form["content"].strip()

    conn = db()
    conn.execute("INSERT INTO notices (title, content, created_at) VALUES (?, ?, ?)", (title, content, now()))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/report", methods=["POST"])
def report():
    user = get_user()
    if not user:
        return redirect("/")

    target_type = request.form["target_type"]
    target_id = int(request.form["target_id"])
    reason = request.form["reason"].strip()

    conn = db()
    conn.execute(
        "INSERT INTO reports (target_type, target_id, reason, reporter_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (target_type, target_id, reason, user["id"], now())
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/admin")
def admin():
    if not admin_required():
        return "관리자만 접속 가능합니다."

    conn = db()

    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    posts = conn.execute("""
        SELECT posts.*, users.nickname
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """).fetchall()
    comments = conn.execute("""
        SELECT comments.*, users.nickname
        FROM comments
        JOIN users ON comments.user_id = users.id
        ORDER BY comments.id DESC
    """).fetchall()
    notices = conn.execute("SELECT * FROM notices ORDER BY id DESC").fetchall()
    reports = conn.execute("""
        SELECT reports.*, users.nickname
        FROM reports
        LEFT JOIN users ON reports.reporter_id = users.id
        ORDER BY reports.id DESC
    """).fetchall()

    stats = {
        "users": len(users),
        "posts": len(posts),
        "comments": len(comments),
        "notices": len(notices),
        "reports": len(reports),
    }

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        posts=posts,
        comments=comments,
        notices=notices,
        reports=reports,
        stats=stats
    )


@app.route("/admin/user/ban/<int:user_id>")
def admin_ban_user(user_id):
    if not admin_required():
        return "접근 불가"

    conn = db()
    conn.execute("UPDATE users SET is_banned=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/admin/user/unban/<int:user_id>")
def admin_unban_user(user_id):
    if not admin_required():
        return "접근 불가"

    conn = db()
    conn.execute("UPDATE users SET is_banned=0 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/admin/user/delete/<int:user_id>")
def admin_delete_user(user_id):
    if not admin_required():
        return "접근 불가"

    conn = db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/admin/post/delete/<int:post_id>")
def admin_delete_post(post_id):
    if not admin_required():
        return "접근 불가"

    conn = db()
    conn.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
    conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/admin/comment/delete/<int:comment_id>")
def admin_delete_comment(comment_id):
    if not admin_required():
        return "접근 불가"

    conn = db()
    conn.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/admin/notice/delete/<int:notice_id>")
def admin_delete_notice(notice_id):
    if not admin_required():
        return "접근 불가"

    conn = db()
    conn.execute("DELETE FROM notices WHERE id=?", (notice_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")


@app.route("/dev")
def dev_page():
    if request.remote_addr not in ["127.0.0.1", "::1"]:
        return "개발자 페이지는 내 컴퓨터에서만 접속 가능합니다."

    return render_template("dev.html")


@app.route("/dev/reset")
def dev_reset():
    if request.remote_addr not in ["127.0.0.1", "::1"]:
        return "접근 불가"

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    init_db()
    return redirect("/dev")


@socketio.on("message")
def handle_message(data):
    user = get_user()
    if not user:
        return

    message = data.get("message", "").strip()
    if not message:
        return

    conn = db()
    conn.execute(
        "INSERT INTO chat_messages (user_id, nickname, message, created_at) VALUES (?, ?, ?, ?)",
        (user["id"], user["nickname"], message, now())
    )
    conn.commit()
    conn.close()

    send({
        "nickname": user["nickname"],
        "message": message,
        "time": now()
    }, broadcast=True)


init_db()

if __name__ == "__main__":
    socketio.run(app, debug=True)