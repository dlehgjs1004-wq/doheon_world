from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "doheon_secret_key"


def db():
    return sqlite3.connect("database.db")


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

    conn.commit()
    conn.close()


@app.route("/")
def home():
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

    conn.close()

    return render_template(
        "index.html",
        page="portal",
        user=user,
        memo=memo,
        todos=todos,
        posts=posts,
        comments=comments
    )


@app.route("/signup", methods=["POST"])
def signup():
    email = request.form["email"]
    password = request.form["password"]
    nickname = request.form["nickname"]

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
    email = request.form["email"]
    password = request.form["password"]

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


@app.route("/memo", methods=["POST"])
def memo():
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
    content = request.form["content"]

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO todos (user_id, content) VALUES (?, ?)", (session["user_id"], content))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/todo/delete/<int:todo_id>")
def delete_todo(todo_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id=? AND user_id=?", (todo_id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/post/add", methods=["POST"])
def add_post():
    title = request.form["title"]
    content = request.form["content"]

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
    content = request.form["content"]

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (post_id, session["user_id"], content)
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/profile", methods=["POST"])
def profile():
    nickname = request.form["nickname"]

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)