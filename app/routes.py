from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
import hashlib
import psycopg2.extras

bp = Blueprint("main", __name__)

# HTML view ----------------------------------
@bp.route("/")
def index():
    # books is a list of DictRows, Jinja can handle dict-style access
    return render_template("index.html")

@bp.route("/login")
def login():
    return render_template("login.html")

@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # hash password (never store plain text passwords!)
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        # connect to DB
        conn = current_app.get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # insert into users table (make sure this table exists!)
        try:
            cur.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_pw)
            )
            conn.commit()
            flash("Signup successful! Please log in.", "success")
        except Exception as e:
            conn.rollback()
            flash("Error: " + str(e), "danger")

        cur.close()

        return redirect(url_for("main.index"))  # redirect after signup
    return render_template("signup.html")

@bp.route("/dashboard")
def dashboard():
        conn = current_app.get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM books ORDER BY title;")
        books = cur.fetchall()
        cur.close()
        return render_template("dashboard.html", books=books)

# REST endpoints -----------------------------
@bp.route("/api/books", methods=["GET"])
def api_books():
    q = request.args.get("search", "")

    conn = current_app.get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if q:
        cur.execute(
            "SELECT id, title, author, year, genre, language FROM books WHERE title ILIKE %s;",
            (f"%{q}%",)
        )
    else:
        cur.execute(
            "SELECT id, title, author, year, genre, language FROM books;"
        )

    rows = cur.fetchall()
    cur.close()

    return jsonify([dict(r) for r in rows])
