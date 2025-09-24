from flask import Blueprint, render_template, request, jsonify, current_app
import psycopg2.extras

bp = Blueprint("main", __name__)

# HTML view ----------------------------------
@bp.route("/")
def index():
    conn = current_app.get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM books ORDER BY title;")
    books = cur.fetchall()
    cur.close()

    # books is a list of DictRows, Jinja can handle dict-style access
    return render_template("index.html", books=books)


# REST endpoints -----------------------------
@bp.route("/api/books", methods=["GET"])
def api_books():
    q = request.args.get("search", "")

    conn = current_app.get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if q:
        cur.execute(
            "SELECT id, title, author, year, genre, language FROM books WHERE title ILIKE %s;",
            (f"%{q}%",)
        )
    else:
        cur.execute(
            "SELECT id, title, author, year, genre, language FROM books;"
        )

    rows = cur.fetchall()
    cur.close()

    return jsonify([dict(r) for r in rows])
