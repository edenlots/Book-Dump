"""Administrator authentication and management routes."""

from pathlib import Path, PurePosixPath

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .book_queries import BookQueries
from .log_queries import LogQueries
from .user_queries import UserQueries

bp = Blueprint("admin", __name__)


@bp.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if session.get("user_role") == "admin":
        return redirect(url_for("admin.admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = current_app.get_db()
        user = UserQueries.get_user_by_email(conn, email)

        if user and user[4] == "admin":
            if check_password_hash(user[3], password):
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_role"] = user[4]
                flash("Admin login successful!", "success")
                return redirect(url_for("admin.admin_dashboard"))
            flash("Incorrect password.", "danger")
        else:
            flash("Admin account not found or insufficient permissions.", "danger")

    return render_template("adminlogin.html")


@bp.route("/admin_dashboard")
def admin_dashboard():
    """Admin dashboard - view all users and books."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    users = UserQueries.get_all_users(conn)
    books = BookQueries.get_all_books(conn)
    return render_template("admin_dashboard.html", users=users, books=books)


@bp.route("/admin/profile")
def admin_profile():
    """Show the admin account and its activity history."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("admin.admin_login"))

    conn = current_app.get_db()
    user = UserQueries.get_user_profile(conn, session["user_id"])
    if not user:
        session.clear()
        flash("Admin account not found. Please log in again.", "danger")
        return redirect(url_for("admin.admin_login"))

    uploads = LogQueries.get_user_activity_history(
        conn, session["user_id"], "uploaded"
    )
    downloads = LogQueries.get_user_activity_history(
        conn, session["user_id"], "downloaded"
    )
    account_history = LogQueries.get_account_history(conn)
    user_data = {"username": user[0], "email": user[1], "picture": user[2]}

    return render_template(
        "admin_profile.html",
        user=user_data,
        uploads=uploads,
        downloads=downloads,
        account_history=account_history,
    )


@bp.route("/admin/users")
def admin_users():
    """Manage users."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    users = UserQueries.get_all_users(conn)
    return render_template("admin_users.html", users=users)


@bp.route("/admin/users/add", methods=["POST"])
def admin_add_user():
    """Create a user from the admin user-management page."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("admin.admin_login"))

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    if not username or not email or not password:
        flash("Username, email, and password are required.", "warning")
        return redirect(url_for("admin.admin_users"))

    conn = current_app.get_db()
    success, error = UserQueries.create_user(
        conn,
        username,
        email,
        generate_password_hash(password),
        session.get("user_name", "Administrator"),
    )
    if success:
        flash(f"User {username} added successfully.", "success")
    else:
        current_app.logger.error("Admin user creation failed: %s", error)
        flash("Could not add user. Check the details and try again.", "danger")
    return redirect(url_for("admin.admin_users"))


@bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):
    """Delete a user."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("auth.login"))

    if session["user_id"] == user_id:
        flash("Cannot delete your own account.", "warning")
        return redirect(url_for("admin.admin_users"))

    conn = current_app.get_db()
    success = UserQueries.delete_user(
        conn, user_id, session.get("user_name", "Administrator")
    )
    if success:
        flash("User deleted successfully!", "success")
    else:
        flash("Error deleting user.", "danger")
    return redirect(url_for("admin.admin_users"))


@bp.route("/admin/users/<int:user_id>/role", methods=["POST"])
def admin_update_user_role(user_id):
    """Update user role (admin/user)."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("auth.login"))

    new_role = request.form.get("role")
    if new_role not in ["admin", "user"]:
        flash("Invalid role.", "danger")
        return redirect(url_for("admin.admin_users"))

    conn = current_app.get_db()
    success = UserQueries.update_user_role(conn, user_id, new_role)
    if success:
        flash(f"User role updated to {new_role}!", "success")
    else:
        flash("Error updating user role.", "danger")
    return redirect(url_for("admin.admin_users"))


@bp.route("/admin/books")
def admin_books():
    """Manage books."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    books = BookQueries.get_all_books(conn)
    return render_template("admin_books.html", books=books)


@bp.route("/admin/books/<int:book_id>/delete", methods=["POST"])
def admin_delete_book(book_id):
    """Delete a book."""
    if "user_id" not in session or session.get("user_role") != "admin":
        flash("Admin access required.", "danger")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    success, file_path, error = BookQueries.delete_book(conn, book_id)

    if success:
        if file_path:
            file_ref = PurePosixPath(str(file_path).replace("\\", "/"))
            if (
                len(file_ref.parts) != 3
                or file_ref.parts[:2] != ("static", "uploads")
                or file_ref.name in ("", ".", "..")
            ):
                current_app.logger.error(
                    "Book %s was deleted from the database, but its file reference "
                    "is outside the managed uploads directory: %r",
                    book_id,
                    file_path,
                )
                flash(
                    "Book record deleted, but its stored file was not removed "
                    "because its path is outside the uploads directory.",
                    "warning",
                )
                return redirect(url_for("admin.admin_books"))

            stored_file = (
                Path(current_app.root_path) / "static" / "uploads" / file_ref.name
            )
            try:
                stored_file.unlink(missing_ok=True)
            except OSError:
                current_app.logger.exception(
                    "Could not remove stored file for deleted book %s", book_id
                )
                flash(
                    "Book record deleted, but its stored file could not be removed. "
                    "Check the application logs.",
                    "danger",
                )
                return redirect(url_for("admin.admin_books"))

        flash("Book and stored file deleted successfully!", "success")
    else:
        current_app.logger.error("Could not delete book %s: %s", book_id, error)
        flash("Error deleting book from the database.", "danger")

    return redirect(url_for("admin.admin_books"))
