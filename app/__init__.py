from flask import Flask, g
import pathlib, dotenv
import psycopg2
import psycopg2.extras

dotenv.load_dotenv()                   

def create_app():
    app = Flask(__name__,
                static_folder="static",
                template_folder="templates")
    app.config.update(
        SECRET_KEY=dotenv.dotenv_values().get("SECRET_KEY", "dev"),
        DATABASE_URL=dotenv.dotenv_values().get("DATABASE_URL")
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
