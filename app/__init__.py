import os
from pathlib import Path

from flask import Flask, g
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
    )

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

    from . import routes       # noqa: after app ready
    app.register_blueprint(routes.bp)

    return app
