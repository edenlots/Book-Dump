from flask import Flask, g
import os, pathlib, dotenv
import psycopg2
import psycopg2.extras


dotenv.load_dotenv()                       # pulls vars from .env

def create_app():
    app = Flask(__name__,
                static_folder="static",
                template_folder="templates")
    app.config.update(
        SECRET_KEY= os.getenv("SECRET_KEY", "dev"),
        DATABASE_URL=os.getenv("DATABASE_URL", "dbname=library user=postgres password=postgres host=localhost port=5432")
    )

# --- PostgreSQL connection helper ---
    def get_db():
        if "db" not in g:
            g.db = psycopg2.connect(app.config["DATABASE_URL"])
        return g.db

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # Example: attach db accessor to app
    app.get_db = get_db

    from . import routes       # noqa: after app ready
    app.register_blueprint(routes.bp)

    return app
