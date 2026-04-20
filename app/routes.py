from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from pathlib import Path
import dotenv

from .queries import UserQueries, BookQueries, LogQueries

bp = Blueprint("main", __name__)
ALLOWED_EXTENSIONS = set(dotenv.dotenv_values().get("ALLOWED_EXTENSIONS", "pdf,png,jpg,jpeg").split(","))

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
        user = UserQueries.get_user_by_email(conn, email)

        if user:
            # check password hash
            if check_password_hash(user[3], password):
                session["user_id"] = user[0]   # store logged-in user ID
                session["user_name"] = user[1]
                session["user_role"] = user[4]
                flash("Login successful!", "success")
                if session["user_role"] == 'admin':
                    return redirect(url_for("main.admin_dashboard"))
                else:
                    return redirect(url_for("main.dashboard"))
            else:
                flash("Incorrect password.", "danger")
        else:
            flash("Email or user not found.", "danger")
    return render_template("login.html")

@bp.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = current_app.get_db()
        user = UserQueries.get_user_by_email(conn, email)

        if user and user[4] == "admin":  # Check if role is 'admin'
            # check password hash
            if check_password_hash(user[3], password):
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_role"] = user[4]
                flash("Admin login successful!", "success")
                return redirect(url_for("main.admin_dashboard"))
            else:
                flash("Incorrect password.", "danger")
        else:
            flash("Admin account not found or insufficient permissions.", "danger")
    
    return render_template("adminlogin.html")

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
        success, error = UserQueries.create_user(conn, name, email, hashed_pw)

        if success:
            flash("Signup successful! Please log in.", "success")
        else:
            flash("Error: " + error, "danger")

        return redirect(url_for("main.index"))  # redirect after signup
    return render_template("signup.html")

@bp.route("/update_password", methods=["GET", "POST"])
def update_password():
    if request.method == "POST":
        password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        conn = current_app.get_db()
        user = UserQueries.get_user_by_id(conn, session["user_id"])

        if user:
            # check password hash
            if check_password_hash(user[3] if isinstance(user, tuple) else user['pw_hash'], password):
                hashed_new_password = generate_password_hash(new_password)
                success = UserQueries.update_password(conn, session["user_id"], hashed_new_password)
                
                if success:
                    flash("Update password successful!", "success")
                    return redirect(url_for("main.profile"))
                else:
                    flash("Error updating password.", "danger")
            else:
                flash("Wrong password. Please use the correct active password.", "danger")
        else:
            flash("Invalid Account.", "danger")
    
    conn = current_app.get_db()
    user = UserQueries.get_user_profile(conn, session.get("user_id"))
    user_data = {"username": user[0], "email": user[1], "picture": user[2]} if user else None
    return render_template("profile.html", user=user_data)


@bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    
    conn = current_app.get_db()
    user = UserQueries.get_user_by_id(conn, session["user_id"])
    books = BookQueries.get_all_books(conn)

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
    user = UserQueries.get_user_profile(conn, user_id)

    user_data = {"username": user[0], "email": user[1], "picture": user[2]} if user else None

    return render_template("profile.html", user=user_data)


@bp.route("/profile_picture", methods=["GET", "POST"])
def profile_picture():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    
    if request.method == "POST":
        picture = request.files.get("picture")
  
        if picture and allowed_file(picture.filename):
            filename = secure_filename(picture.filename)

            upload_folder = Path(current_app.root_path) / "static" / "profilepicture"
            upload_folder.mkdir(parents=True, exist_ok=True)
            picture_path = upload_folder / filename
            picture.save(picture_path)

            conn = current_app.get_db()
            picture_url = f"/static/profilepicture/{filename}"
            success = UserQueries.update_profile_picture(conn, session["user_id"], picture_url)

            if success:
                flash("Profile picture added successfully!")
            else:
                flash("Error updating profile picture.")
            
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
    books_data = BookQueries.get_all_books(conn)
    
    return render_template("books.html", books=books_data)

@bp.route("/bookview/<int:book_id>")
def bookview(book_id):
    conn = current_app.get_db()
    book = BookQueries.get_book_by_id(conn, book_id)

    if not book:
        return "Book not found", 404
    return render_template("bookview.html", book=book)


@bp.route("/uploads/<filename>")
def view_file(filename):
    uploads_path = Path(current_app.root_path) / "static" / "uploads"
    return send_from_directory(uploads_path, filename)


@bp.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    
    conn = current_app.get_db()
    user = UserQueries.get_user_by_id(conn, session["user_id"])

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
            upload_folder = Path(current_app.root_path) / "static" / "uploads"
            upload_folder.mkdir(parents=True, exist_ok=True)

            file_path = upload_folder / filename
            file.save(file_path)
            
            # Add book to database
            success, book_id, error = BookQueries.add_book(
                conn, title, author, year, genre, language, overview, 
                f"static/uploads/{filename}"
            )

            if success:
                # Add log entry
                LogQueries.add_log(conn, session.get('user_id'), book_id, 'uploaded')
                flash("Book uploaded successfully!")
            else:
                flash(f"Error uploading book: {error}")
            
            return redirect(url_for("main.upload"))
        else:
            flash("Invalid file type. Please upload a PDF.")
            return redirect(request.url)

    return render_template("upload.html", username=user["username"],
        email=user["email"])

@bp.route("/search")
def search():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("main.login"))
    
    query = request.args.get("q", "").strip()
    conn = current_app.get_db()
    results = BookQueries.search_books(conn, query)

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

        conn = current_app.get_db()
        results = BookQueries.advanced_search(conn, title, author, year, genre, language)

    return render_template("advanced.html", results=results)


# ==================== ADMIN ROUTES ====================

@bp.route("/admin_dashboard")
def admin_dashboard():
    """Admin dashboard - view all users and books"""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("main.login"))
    
    conn = current_app.get_db()
    users = UserQueries.get_all_users(conn)
    books = BookQueries.get_all_books(conn)
    
    return render_template("admin_dashboard.html", users=users, books=books)


@bp.route("/admin/users")
def admin_users():
    """Manage users"""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("main.login"))
    
    conn = current_app.get_db()
    users = UserQueries.get_all_users(conn)
    
    return render_template("admin_users.html", users=users)


@bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):
    """Delete a user"""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("main.login"))
    
    if session["user_id"] == user_id:
        flash("Cannot delete your own account.", "warning")
        return redirect(url_for("main.admin_users"))
    
    conn = current_app.get_db()
    success = UserQueries.delete_user(conn, user_id)
    
    if success:
        flash("User deleted successfully!", "success")
    else:
        flash("Error deleting user.", "danger")
    
    return redirect(url_for("main.admin_users"))


@bp.route("/admin/users/<int:user_id>/role", methods=["POST"])
def admin_update_user_role(user_id):
    """Update user role (admin/user)"""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("main.login"))
    
    new_role = request.form.get("role")
    if new_role not in ["admin", "user"]:
        flash("Invalid role.", "danger")
        return redirect(url_for("main.admin_users"))
    
    conn = current_app.get_db()
    success = UserQueries.update_user_role(conn, user_id, new_role)
    
    if success:
        flash(f"User role updated to {new_role}!", "success")
    else:
        flash("Error updating user role.", "danger")
    
    return redirect(url_for("main.admin_users"))


@bp.route("/admin/books")
def admin_books():
    """Manage books"""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("main.login"))
    
    conn = current_app.get_db()
    books = BookQueries.get_all_books(conn)
    
    return render_template("admin_books.html", books=books)


@bp.route("/admin/books/<int:book_id>/delete", methods=["POST"])
def admin_delete_book(book_id):
    """Delete a book"""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("main.login"))
    
    conn = current_app.get_db()
    success = BookQueries.delete_book(conn, book_id)
    
    if success:
        flash("Book deleted successfully!", "success")
    else:
        flash("Error deleting book.", "danger")
    
    return redirect(url_for("main.admin_books"))


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
