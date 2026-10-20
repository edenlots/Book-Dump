from flask import Blueprint, render_template, request, current_app, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from pathlib import Path

from .file_utils import allowed_file
from .log_queries import LogQueries
from .user_queries import UserQueries

bp = Blueprint("main", __name__)

# HTML view ----------- The Routes include direct queries to PSQL using psycopg2
@bp.route("/")
def index():
    # books is a list of DictRows, Jinja can handle dict-style access
    return render_template("index.html")

@bp.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    conn = current_app.get_db()
    user = UserQueries.get_user_profile(conn, user_id)
    uploads = LogQueries.get_user_activity_history(conn, user_id, 'uploaded')
    downloads = LogQueries.get_user_activity_history(conn, user_id, 'downloaded')

    user_data = {"username": user[0], "email": user[1], "picture": user[2]} if user else None

    return render_template(
        "profile.html",
        user=user_data,
        uploads=uploads,
        downloads=downloads,
    )


@bp.route("/profile_picture", methods=["GET", "POST"])
def profile_picture():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))
    
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
