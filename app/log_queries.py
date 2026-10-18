"""Database query operations for log data."""

import psycopg2.extras


class LogQueries:
    """Log-related database queries"""

    @staticmethod
    def get_user_favorite_books(conn, user_id):
        """Get books saved by a user."""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT DISTINCT b.id, b.title, b.author, b.year, b.genre, b.language,
                b.overview
            FROM books b
            JOIN logs l ON l.book_id = b.id
            WHERE l.user_id = %s AND l.action = 'favorite'
            ORDER BY b.title;
            """,
            (user_id,),
        )
        books = cur.fetchall()
        cur.close()
        return books

    @staticmethod
    def save_favorite(conn, user_id, book_id):
        """Save a book without creating duplicate favorite records."""
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO logs (user_id, book_id, action)
            SELECT %s, %s, 'favorite'
            WHERE NOT EXISTS (
                SELECT 1 FROM logs
                WHERE user_id = %s AND book_id = %s AND action = 'favorite'
            );
            """,
            (user_id, book_id, user_id, book_id),
        )
        conn.commit()
        cur.close()

    @staticmethod
    def remove_favorite(conn, user_id, book_id):
        """Remove a user's saved-book record."""
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM logs
            WHERE user_id = %s AND book_id = %s AND action = 'favorite';
            """,
            (user_id, book_id),
        )
        conn.commit()
        cur.close()
    
    @staticmethod
    def add_log(conn, user_id, book_id, action):
        """Add an action log for user activity"""
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO logs (user_id, book_id, action, timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP);
            """, (user_id, book_id, action))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            conn.rollback()
            cur.close()
            return False

    @staticmethod
    def get_recent_user_logs(conn, user_id, limit=3):
        """Get the most recent activity records for a user."""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT l.id, l.action, l.timestamp, b.title AS book_title
            FROM logs l
            LEFT JOIN books b ON b.id = l.book_id
            WHERE l.user_id = %s
            ORDER BY l.timestamp DESC, l.id DESC
            LIMIT %s;
            """,
            (user_id, limit),
        )
        logs = cur.fetchall()
        cur.close()
        return logs

    @staticmethod
    def get_user_activity_history(conn, user_id, action=None):
        """Get user activity history joined with the books table."""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        base_query = """
            SELECT
                l.id,
                l.action,
                l.timestamp,
                b.id AS book_id,
                b.title,
                b.author,
                b.year,
                b.genre,
                b.language,
                b.file
            FROM logs l
            LEFT JOIN books b ON b.id = l.book_id
            WHERE l.user_id = %s
        """
        params = [user_id]

        if action:
            base_query += " AND l.action = %s"
            params.append(action)

        base_query += " ORDER BY l.timestamp DESC, l.id DESC;"

        cur.execute(base_query, tuple(params))
        history = cur.fetchall()
        cur.close()
        return history

    @staticmethod
    def get_account_history(conn):
        """Get account addition and deletion history."""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT action, actor_username, target_username, target_email, timestamp
            FROM account_history
            ORDER BY timestamp DESC, id DESC;
            """
        )
        history = cur.fetchall()
        cur.close()
        return history
