from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from .book_queries import BookQueries
from .file_utils import allowed_file
from .log_queries import LogQueries
from .user_queries import UserQueries

bp = Blueprint("book", __name__)


@bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    user = UserQueries.get_user_by_id(conn, session["user_id"])
    books = BookQueries.get_user_bookshelf(conn, session["user_id"])
    recent_activities = LogQueries.get_recent_user_logs(conn, session["user_id"], 3)

    return render_template(
        "dashboard.html",
        username=user["username"],
        email=user["email"],
        picture=user["picture"],
        books=books,
        recent_activities=recent_activities,
    )


@bp.route("/bookshelf")
def bookshelf():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    uploaded_books = BookQueries.get_user_uploaded_books(conn, user_id)
    favorite_books = LogQueries.get_user_favorite_books(conn, user_id)
    return render_template(
        "bookshelf.html",
        uploaded_books=uploaded_books,
        favorite_books=favorite_books,
    )


@bp.route("/books")
def books():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    books_data = BookQueries.get_all_books(conn)

    return render_template("books.html", books=books_data)


@bp.route("/bookview/<int:book_id>")
def bookview(book_id):
    conn = current_app.get_db()
    book = BookQueries.get_book_by_id(conn, book_id)

    if not book:
        return "Book not found", 404
    user_id = session.get("user_id")
    is_favorite = (
        BookQueries.is_book_favorite(conn, user_id, book_id)
        if user_id
        else False
    )
    return render_template("bookview.html", book=book, is_favorite=is_favorite)


@bp.route("/books/<int:book_id>/favorite", methods=["POST"])
def favorite_book(book_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    if not BookQueries.get_book_by_id(conn, book_id):
        return "Book not found", 404

    action = request.form.get("action")
    if action == "save":
        LogQueries.save_favorite(conn, user_id, book_id)
        flash("Book saved to your bookshelf.", "success")
    elif action == "remove":
        LogQueries.remove_favorite(conn, user_id, book_id)
        flash("Book removed from your saved books.", "success")
    else:
        flash("Invalid bookshelf action.", "danger")

    if request.form.get("return_to") == "bookshelf":
        return redirect(url_for("book.bookshelf"))
    return redirect(url_for("book.bookview", book_id=book_id))


def _get_upload_filename(file_reference):
    """Resolve legacy book file references to a basename under static/uploads."""
    if not file_reference:
        return None

    path_parts = str(file_reference).replace("\\", "/").split("/")
    path_parts = [part for part in path_parts if part]
    if len(path_parts) >= 3 and path_parts[-3:-1] == ["static", "uploads"]:
        filename = path_parts[-1]
    elif len(path_parts) == 2 and path_parts[0] == "uploads":
        filename = path_parts[-1]
    elif len(path_parts) == 1:
        filename = path_parts[0]
    else:
        return None

    if filename in (".", ".."):
        return None
    return filename


def _send_book_file(book_id, as_attachment=False):
    conn = current_app.get_db()
    file_reference = BookQueries.get_book_file_by_id(conn, book_id)
    filename = _get_upload_filename(file_reference)
    if not filename:
        current_app.logger.warning(
            "Book %s has an unsupported file reference: %r",
            book_id,
            file_reference,
        )
        return "Book file not found", 404

    uploads_path = Path(current_app.root_path) / "static" / "uploads"
    stored_file = uploads_path / filename
    if not stored_file.is_file():
        current_app.logger.warning(
            "Stored file for book %s does not exist: %s", book_id, stored_file
        )
        return "Book file not found", 404

    if as_attachment and session.get("user_id"):
        if not LogQueries.add_log(conn, session["user_id"], book_id, "downloaded"):
            current_app.logger.error(
                "Could not record download of book %s by user %s",
                book_id,
                session["user_id"],
            )

    return send_from_directory(uploads_path, filename, as_attachment=as_attachment)


@bp.route("/books/<int:book_id>/file")
def book_file(book_id):
    return _send_book_file(book_id, request.args.get("download") == "1")


@bp.route("/uploads/<path:filename>")
def view_file(filename):
    filename = _get_upload_filename(filename)
    if not filename:
        return "File not found", 404

    conn = current_app.get_db()
    book_id = BookQueries.get_book_id_by_file(
        conn, f"static/uploads/{filename}"
    )
    if book_id is None:
        book_id = BookQueries.get_book_id_by_file(conn, filename)
    if book_id is not None:
        return _send_book_file(book_id, request.args.get("download") == "1")

    uploads_path = Path(current_app.root_path) / "static" / "uploads"
    if not (uploads_path / filename).is_file():
        return "File not found", 404
    return send_from_directory(uploads_path, filename)


@bp.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

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

            upload_folder = Path(current_app.root_path) / "static" / "uploads"
            upload_folder.mkdir(parents=True, exist_ok=True)

            file_path = upload_folder / filename
            file.save(file_path)

            success, book_id, error = BookQueries.add_book(
                conn,
                title,
                author,
                year,
                genre,
                language,
                overview,
                f"static/uploads/{filename}",
            )

            if success:
                if LogQueries.add_log(
                    conn, session.get("user_id"), book_id, "uploaded"
                ):
                    flash("Book uploaded successfully!")
                else:
                    current_app.logger.error(
                        "Book %s was uploaded, but its activity could not be recorded.",
                        book_id,
                    )
                    flash(
                        "Book uploaded, but its activity history could not be recorded.",
                        "warning",
                    )
            else:
                flash(f"Error uploading book: {error}")

            return redirect(url_for("book.upload"))
        else:
            flash("Invalid file type. Please upload a PDF.")
            return redirect(request.url)

    return render_template(
        "upload.html", username=user["username"], email=user["email"]
    )


@bp.route("/search")
def search():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    query = request.args.get("q", "").strip()
    filters = {
        "title": request.args.get("title", "").strip(),
        "author": request.args.get("author", "").strip(),
        "year": request.args.get("year", "").strip(),
        "genre": request.args.get("genre", "").strip(),
        "language": request.args.get("language", "").strip(),
    }
    search_performed = bool(query or any(filters.values()))
    conn = current_app.get_db()
    results = (
        BookQueries.search_catalog(conn, query=query, **filters)
        if search_performed
        else []
    )

    return render_template(
        "search.html",
        query=query,
        filters=filters,
        search_performed=search_performed,
        results=results,
    )


@bp.route("/advanced", methods=["GET", "POST"])
def advanced_search_redirect():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    filters = {
        name: request.values.get(name, "").strip()
        for name in ("title", "author", "year", "genre", "language")
    }
    return redirect(url_for("book.search", **filters))
