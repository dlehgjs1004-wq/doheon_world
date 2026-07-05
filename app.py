from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, send
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "doheon_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")

DB_NAME = "database.db"


def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        nickname TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        content TEXT,
        likes INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        content TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT,
        message TEXT
    )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    init_db()

    if "user_id" not in session:
        return render_template("index.html", page="home")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id=?", (session["user_id"],))
    user = cur.fetchone()

    cur.execute("SELECT * FROM memos WHERE user_id=?", (session["user_id"],))
    memo = cur.fetchone()

    cur.execute("SELECT * FROM todos WHERE user_id=?", (session["user_id"],))
    todos = cur.fetchall()

    cur.execute("""
        SELECT posts.id, posts.title, posts.content, posts.likes, users.nickname
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """)
    posts = cur.fetchall()

    cur.execute("""
        SELECT comments.id, comments.post_id, comments.content, users.nickname
        FROM comments
        JOIN users ON comments.user_id = users.id
    """)
    comments = cur.fetchall()

    cur.execute("SELECT * FROM notices ORDER BY id DESC")
    notices = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM posts")
    post_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM comments")
    comment_count = cur.fetchone()[0]

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
        user_count=user_count,
        post_count=post_count,
        comment_count=comment_count
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

    conn = db()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (email, password, nickname) VALUES (?, ?, ?)",
            (email, password, nickname)
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
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = cur.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        return redirect("/")

    return "로그인 실패"


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/profile", methods=["POST"])
def profile():
    nickname = request.form["nickname"].strip()

    if "user_id" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/memo", methods=["POST"])
def memo():
    if "user_id" not in session:
        return redirect("/")

    content = request.form["content"]

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM memos WHERE user_id=?", (session["user_id"],))
    old = cur.fetchone()

    if old:
        cur.execute("UPDATE memos SET content=? WHERE user_id=?", (content, session["user_id"]))
    else:
        cur.execute("INSERT INTO memos (user_id, content) VALUES (?, ?)", (session["user_id"], content))

    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/todo/add", methods=["POST"])
def add_todo():
    if "user_id" not in session:
        return redirect("/")

    content = request.form["content"].strip()

    if content:
        conn = db()
        cur = conn.cursor()
        cur.execute("INSERT INTO todos (user_id, content) VALUES (?, ?)", (session["user_id"], content))
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/todo/delete/<int:todo_id>")
def delete_todo(todo_id):
    if "user_id" not in session:
        return redirect("/")

    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id=? AND user_id=?", (todo_id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/post/add", methods=["POST"])
def add_post():
    if "user_id" not in session:
        return redirect("/")

    title = request.form["title"].strip()
    content = request.form["content"].strip()

    if title and content:
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
            (session["user_id"], title, content)
        )
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/post/like/<int:post_id>")
def like_post(post_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/comment/add/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    if "user_id" not in session:
        return redirect("/")

    content = request.form["content"].strip()

    if content:
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
            (post_id, session["user_id"], content)
        )
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/notice/add", methods=["POST"])
def add_notice():
    if "user_id" not in session:
        return redirect("/")

    title = request.form["title"].strip()
    content = request.form["content"].strip()

    if title and content:
        conn = db()
        cur = conn.cursor()
        cur.execute("INSERT INTO notices (title, content) VALUES (?, ?)", (title, content))
        conn.commit()
        conn.close()

    return redirect("/")


@app.route("/dev")
def dev_page():
    if request.remote_addr not in ["127.0.0.1", "::1"]:
        return "개발자 페이지는 내 컴퓨터에서만 접속 가능합니다."

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")
    users = cur.fetchall()

    cur.execute("SELECT * FROM posts")
    posts = cur.fetchall()

    cur.execute("SELECT * FROM comments")
    comments = cur.fetchall()

    conn.close()

    return render_template("dev.html", users=users, posts=posts, comments=comments)


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
    nickname = data.get("nickname", "익명")
    message = data.get("message", "")

    if message.strip() == "":
        return

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_messages (nickname, message) VALUES (?, ?)",
        (nickname, message)
    )
    conn.commit()
    conn.close()

    send({"nickname": nickname, "message": message}, broadcast=True)


init_db()

if __name__ == "__main__":
    socketio.run(app, debug=True)