"""User login and signup routes."""

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .user_queries import UserQueries

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = current_app.get_db()
        user = UserQueries.get_user_by_email(conn, email)

        if user:
            if check_password_hash(user[3], password):
                if user[4] == "admin":
                    flash(
                        "Administrators must sign in through the Admin Login page.",
                        "warning",
                    )
                    return redirect(url_for("admin.admin_login"))

                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["user_role"] = user[4]
                flash("Login successful!", "success")
                return redirect(url_for("main.dashboard"))
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

        hashed_password = generate_password_hash(password)
        conn = current_app.get_db()
        actor_username = (
            session.get("user_name")
            if session.get("user_role") == "admin"
            else None
        )
        success, error = UserQueries.create_user(
            conn, name, email, hashed_password, actor_username
        )

        if success:
            flash("Signup successful! Please log in.", "success")
        else:
            flash("Error: " + error, "danger")

        return redirect(url_for("main.index"))

    return render_template("signup.html")


@bp.route("/update_password", methods=["GET", "POST"])
def update_password():
    if request.method == "POST":
        password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        conn = current_app.get_db()
        user = UserQueries.get_user_by_id(conn, session["user_id"])

        if user:
            password_hash = (
                user[3] if isinstance(user, tuple) else user["pw_hash"]
            )
            if check_password_hash(password_hash, password):
                hashed_password = generate_password_hash(new_password)
                success = UserQueries.update_password(
                    conn, session["user_id"], hashed_password
                )

                if success:
                    flash("Update password successful!", "success")
                    return redirect(url_for("main.profile"))
                flash("Error updating password.", "danger")
            else:
                flash(
                    "Wrong password. Please use the correct active password.",
                    "danger",
                )
        else:
            flash("Invalid Account.", "danger")

    conn = current_app.get_db()
    user = UserQueries.get_user_profile(conn, session.get("user_id"))
    user_data = (
        {"username": user[0], "email": user[1], "picture": user[2]}
        if user
        else None
    )
    return render_template("profile.html", user=user_data)


@bp.route("/profile/delete", methods=["POST"])
def delete_own_account():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    success = UserQueries.delete_user(
        conn, user_id, session.get("user_name", "Self-deletion")
    )
    if not success:
        current_app.logger.error("Could not delete account for user %s.", user_id)
        flash("Could not delete your account. Please try again.", "danger")
        return redirect(url_for("main.profile"))

    session.clear()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("main.index"))
