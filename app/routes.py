from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import psycopg2.extras, os

bp = Blueprint("main", __name__)
ALLOWED_EXTENSIONS = {"pdf","png","jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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
                flash("Incorrect password.", "danger")
        else:
            flash("Email or user not found.", "danger")
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

@bp.route("/update_password", methods=["GET", "POST"])
def update_password():
    if request.method == "POST":
        password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        conn = current_app.get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("SELECT * FROM users WHERE id = %s;", (session["user_id"],))
        user = cur.fetchone()

        if user:
            # check password hash
            if check_password_hash(user[3], password):
                hashed_new_password = generate_password_hash(new_password)
                cur.execute(
                """UPDATE users SET pw_hash = %s WHERE id = %s;""",
                (hashed_new_password, session["user_id"],)
                )
                conn.commit()
                cur.close()
                flash("Update password successful!", "success")
                return redirect(url_for("main.profile"))
            else:
                flash("Wrong password. Please use the correct active password.", "danger")
        else:
            flash("Invalid Account.", "danger")
    return render_template("profile.html")


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

@bp.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))

    conn = current_app.get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT username, email, picture FROM users WHERE id = %s;", (session["user_id"],))
    user = cur.fetchone()
    cur.close()

    user_data = {"username":user[0], "email": user[1], "picture":user[2]} if user else None

    return render_template("profile.html",user=user_data)


@bp.route("/profile_picture", methods=["GET", "POST"])
def profile_picture():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    
    if request.method == "POST":
        picture = request.files.get("picture")
  
        if picture and allowed_file(picture.filename):
            filename = secure_filename(picture.filename)

            upload_folder=os.path.join(current_app.root_path, "static/profilepicture")
            os.makedirs(upload_folder, exist_ok=True)
            picture_path = os.path.join(upload_folder, filename)
            picture.save(picture_path)

            conn = current_app.get_db()
            cur = conn.cursor()
            query = """ UPDATE users SET picture = %s WHERE id=%s; """
            picture_object = (f"/static/profilepicture/{filename}", (session["user_id"]))
            cur.execute(query,picture_object)

            conn.commit()
            cur.close()
            conn.close()

            flash("Profile picture addedd successfully!")
            return redirect(url_for("main.profile_picture"))
        else:
            flash("Invalid file type. Please try again.")
            return redirect(request.url)
        
    return render_template("profilepicture.html")


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
        
        return render_template("books.html",books=books)

@bp.route("/bookview/<int:book_id>")
def bookview(book_id):
    conn = current_app.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, author, file FROM books WHERE id = %s;", (book_id,))
    book = cur.fetchone()
    cur.close()

    if not book:
        return "Book not found", 404
    return render_template("bookview.html",book=book)


@bp.route("/uploads/<filename>")
def view_file(filename):
    uploads_path = os.path.join(current_app.root_path, "static/uploads")
    return send_from_directory(uploads_path, filename)


@bp.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        year = request.form.get("year")
        genre = request.form.get("genre")
        language = request.form.get("language")
        overview = request.form.get("overview")
        file = request.files.get("file")

        if not title or not author or not year or not genre or not language or not overview:
            flash("Please complete required fields.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # Ensure uploads folder exists
            upload_folder = os.path.join(current_app.root_path, "static/uploads")
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            # Save to database (PostgreSQL)
            conn = current_app.get_db()
            cur = conn.cursor()

            query = """
                INSERT INTO books (title, author, year, genre, language, overview, file)
                VALUES (%s, %s, %s,%s,%s,%s,%s);
            """
            book_object = (title, author, year, genre, language, overview, f"static/uploads/{filename}")
            cur.execute(query, book_object)
            #print("Debug:", book_object)
            conn.commit()

            cur.close()
            conn.close()

            flash("Book uploaded successfully!")
            return redirect(url_for("main.upload"))
        else:
            flash("Invalid file type. Please upload a PDF.")
            return redirect(request.url)

    return render_template("upload.html")

@bp.route("/search")
def search():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    query = request.args.get("q", "").strip()
    conn = current_app.get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, author, year, genre, language
        FROM books
        WHERE 
            title ILIKE %s OR
            author ILIKE %s OR
            genre ILIKE %s OR
            CAST(year AS TEXT) ILIKE %s OR
            language ILIKE %s
        ORDER BY title;
    """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
    
    results = cur.fetchall()
    cur.close()

    return render_template("search.html", query=query, results=results)

@bp.route("/advanced", methods=["GET", "POST"])
def advanced():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    results = []
    if request.method == "POST":
        title = request.form.get("title", "")
        author = request.form.get("author", "")
        year = request.form.get("year", "")
        genre = request.form.get("genre", "")
        language = request.form.get("language", "")

        filters = []
        values = []

        if title:
            filters.append("title ILIKE %s")
            values.append(f"%{title}%")
        if author:
            filters.append("author ILIKE %s")
            values.append(f"%{author}%")
        if year:
            filters.append("CAST(year AS TEXT) ILIKE %s")
            values.append(f"%{year}%")
        if genre:
            filters.append("genre ILIKE %s")
            values.append(f"%{genre}%")
        if language:
            filters.append("language ILIKE %s")
            values.append(f"%{language}%")

        query = "SELECT id, title, author, year, genre, language FROM books"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY title;"

        conn = current_app.get_db()
        cur = conn.cursor()
        cur.execute(query, tuple(values))
        results = cur.fetchall()
        cur.close()

    return render_template("advanced.html", results=results)


'''
# REST endpoints ------- 
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
    '''
