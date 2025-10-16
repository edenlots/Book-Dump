from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import psycopg2.extras, os

bp = Blueprint("main", __name__)
ALLOWED_EXTENSIONS = {"pdf"}

# HTML view ----------- The Routes include direct queries to PSQL using psycopg2
@bp.route("/")
def index():
    # books is a list of DictRows, Jinja can handle dict-style access
    return render_template("index.html")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = current_app.get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            # check password hash
            if check_password_hash(user[3], password):
                session["user_id"] = user[0]   # store logged-in user ID
                session["user_name"] = user[1]
                flash("Login successful!", "success")
                return redirect(url_for("main.dashboard"))
            else:
                flash("Invalid password.", "danger")
        else:
            flash("Email not found.", "danger")
    return render_template("login.html")

@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # hash password (never store plain text passwords!)
        hashed_pw = generate_password_hash(password)

        # connect to DB
        conn = current_app.get_db()
        cur = conn.cursor()

        # insert into users table (make sure this table exists!)
        try:
            cur.execute(
                """INSERT INTO users (username, email, pw_hash, role) VALUES (%s, %s, %s, %s);""",
                (name, email, hashed_pw, "reader")
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
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("main.login"))
        
        conn = current_app.get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT username, email FROM users WHERE id = %s;", (session["user_id"],))
        user = cur.fetchone()

        cur.execute("SELECT * FROM books ORDER BY title DESC LIMIT 10;")
        books = cur.fetchall()

        cur.close()
        
        return render_template(
        "dashboard.html",
        username=user["username"],
        email=user["email"],
        books=books
    )

@bp.route("/books")
def books():
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("main.login"))
        
        conn = current_app.get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM books ORDER BY title DESC LIMIT 15;")
        books = cur.fetchall()

        cur.close()
        
        return render_template(
        "books.html",
        books=books
    )


# REST endpoints ------- This is when you want to use JS data fetch on frontend, and only routes HTML templates
@bp.route("/api/books", methods=["GET"])
def api_books():
    q = request.args.get("search", "")

    conn = current_app.get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if q:
        cur.execute(
            "SELECT title, author, year, genre, language FROM books WHERE title ILIKE %s;",
            (f"%{q}%",)
        )
    else:
        cur.execute(
            "SELECT title, author, year, genre, language FROM books;"
        )

    rows = cur.fetchall()
    cur.close()

    return jsonify([dict(r) for r in rows])
