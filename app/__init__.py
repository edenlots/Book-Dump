import hmac
import os
import secrets
from pathlib import Path

from flask import Flask, abort, g, request, session
import dotenv
import psycopg2
import psycopg2.extras

def create_app():
    app = Flask(__name__,
                static_folder="static",
                template_folder="templates")
    dotenv_path = Path(__file__).resolve().parent.parent / ".env"
    dotenv.load_dotenv(dotenv_path)
    file_config = dotenv.dotenv_values(dotenv_path)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or file_config.get("SECRET_KEY") or "dev",
        DATABASE_URL=os.environ.get("DATABASE_URL") or file_config.get("DATABASE_URL"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "").lower()
        in {"1", "true", "yes"},
    )

    @app.before_request
    def protect_state_changing_requests():
        if request.method == "POST":
            submitted_token = request.form.get("csrf_token", "")
            session_token = session.get("_csrf_token", "")
            if not session_token or not hmac.compare_digest(
                submitted_token, session_token
            ):
                abort(400, description="Invalid or missing CSRF token.")

    @app.context_processor
    def provide_csrf_token():
        def csrf_token():
            token = session.get("_csrf_token")
            if token is None:
                token = secrets.token_urlsafe(32)
                session["_csrf_token"] = token
            return token

        return {"csrf_token": csrf_token}

    def get_db():
        if "db" not in g:
            database_url = app.config.get("DATABASE_URL")
            if not database_url:
                raise RuntimeError(
                    "DATABASE_URL is not configured. Set it in the environment "
                    "or in the project .env file."
                )
            g.db = psycopg2.connect(database_url)
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    app.get_db = get_db

    from . import admin_routes, auth_routes, book_routes, routes  # noqa: after app ready
    app.register_blueprint(routes.bp)
    app.register_blueprint(book_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(auth_routes.bp)

    return app
