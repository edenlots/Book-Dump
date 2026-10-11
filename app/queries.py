"""
Database query operations for the Book-Dump application.
All SQL queries are centralized here to keep routes.py clean.
"""

import psycopg2.extras


class UserQueries:
    """User-related database queries"""
    
    @staticmethod
    def get_user_by_email(conn, email):
        """Get user by email address"""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        return user
    
    @staticmethod
    def get_user_by_id(conn, user_id):
        """Get user info by user ID, including password hash and profile picture."""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            "SELECT id, username, email, pw_hash, role, picture FROM users WHERE id = %s;",
            (user_id,)
        )
        user = cur.fetchone()
        cur.close()
        return user
    
    @staticmethod
    def get_user_profile(conn, user_id):
        """Get user profile including picture"""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT username, email, picture FROM users WHERE id = %s;", (user_id,))
        user = cur.fetchone()
        cur.close()
        return user
    
    @staticmethod
    def create_user(conn, username, email, password_hash, actor_username=None):
        """Create a user and record the account addition atomically."""
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO users (username, email, pw_hash, role)
                VALUES (%s, %s, %s, %s);
                """,
                (username, email, password_hash, "user")
            )
            cur.execute(
                """
                INSERT INTO account_history
                    (action, actor_username, target_username, target_email)
                VALUES (%s, %s, %s, %s);
                """,
                (
                    "user_added",
                    actor_username or "Self-registration",
                    username,
                    email,
                ),
            )
            conn.commit()
            cur.close()
            return True, None
        except Exception as e:
            conn.rollback()
            cur.close()
            return False, str(e)
    
    @staticmethod
    def update_password(conn, user_id, new_password_hash):
        """Update user password"""
        cur = conn.cursor()
        try:
            cur.execute(
                """UPDATE users SET pw_hash = %s WHERE id = %s;""",
                (new_password_hash, user_id)
            )
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            conn.rollback()
            cur.close()
            return False
    
    @staticmethod
    def update_profile_picture(conn, user_id, picture_path):
        """Update user profile picture"""
        cur = conn.cursor()
        try:
            cur.execute(
                """UPDATE users SET picture = %s WHERE id = %s;""",
                (picture_path, user_id)
            )
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            conn.rollback()
            cur.close()
            return False
    
    @staticmethod
    def get_all_users(conn):
        """Get all users (admin function)"""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id, username, email, role, picture FROM users ORDER BY username;")
        users = cur.fetchall()
        cur.close()
        return users
    
    @staticmethod
    def delete_user(conn, user_id, actor_username):
        """Record and delete a user atomically (admin function)."""
        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM users WHERE id = %s RETURNING username, email;",
                (user_id,),
            )
            deleted_user = cur.fetchone()
            if deleted_user:
                cur.execute(
                    """
                    INSERT INTO account_history
                        (action, actor_username, target_username, target_email)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        "user_deleted",
                        actor_username,
                        deleted_user[0],
                        deleted_user[1],
                    ),
                )
            conn.commit()
            cur.close()
            return deleted_user is not None
        except Exception as e:
            conn.rollback()
            cur.close()
            return False
    
    @staticmethod
    def update_user_role(conn, user_id, new_role):
        """Update user role (admin function)"""
        cur = conn.cursor()
        try:
            cur.execute("UPDATE users SET role = %s WHERE id = %s;", (new_role, user_id))
            conn.commit()
            cur.close()
            return True
        except Exception as e:
            conn.rollback()
            cur.close()
            return False


class BookQueries:
    """Book-related database queries"""
    
    @staticmethod
    def get_all_books(conn):
        """Get all books ordered by title"""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM books ORDER BY title ASC;")
        books = cur.fetchall()
        cur.close()
        return books
    
    @staticmethod
    def get_book_by_id(conn, book_id):
        """Get book details by ID"""
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, author, file, year, genre "
            "FROM books WHERE id = %s;",
            (book_id,),
        )
        book = cur.fetchone()
        cur.close()
        return book

    @staticmethod
    def get_book_file_by_id(conn, book_id):
        """Get a book's stored file path."""
        cur = conn.cursor()
        cur.execute("SELECT file FROM books WHERE id = %s;", (book_id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None

    @staticmethod
    def get_book_id_by_file(conn, file_path):
        """Get a book ID from its stored file path."""
        cur = conn.cursor()
        cur.execute("SELECT id FROM books WHERE file = %s;", (file_path,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    
    @staticmethod
    def add_book(conn, title, author, year, genre, language, overview, file_path):
        """Add a new book to the database"""
        cur = conn.cursor()
        try:
            add_book_query = """
                INSERT INTO books (title, author, year, genre, language, overview, file)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """
            cur.execute(add_book_query, (title, author, year, genre, language, overview, file_path))
            book_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return True, book_id, None
        except Exception as e:
            conn.rollback()
            cur.close()
            return False, None, str(e)
    
    @staticmethod
    def search_books(conn, query):
        """Search books by query (title, author, genre, year, language)"""
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, author, year, genre, language
            FROM books
            WHERE 
                title ILIKE %s OR
                author ILIKE %s OR
                genre ILIKE %s OR
                CAST(year AS TEXT) ILIKE %s OR
                language ILIKE %s
            ORDER BY title;
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
        
        results = cur.fetchall()
        cur.close()
        return results
    
    @staticmethod
    def advanced_search(conn, title="", author="", year="", genre="", language=""):
        """Advanced search with multiple filters"""
        filters = []
        values = []

        if title:
            filters.append("title ILIKE %s")
            values.append(f"%{title}%")
        if author:
            filters.append("author ILIKE %s")
            values.append(f"%{author}%")
        if year:
            filters.append("CAST(year AS TEXT) ILIKE %s")
            values.append(f"%{year}%")
        if genre:
            filters.append("genre ILIKE %s")
            values.append(f"%{genre}%")
        if language:
            filters.append("language ILIKE %s")
            values.append(f"%{language}%")

        query = "SELECT id, title, author, year, genre, language FROM books"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY title;"

        cur = conn.cursor()
        cur.execute(query, tuple(values))
        results = cur.fetchall()
        cur.close()
        return results
    
    @staticmethod
    def delete_book(conn, book_id):
        """Delete a book and return its stored file reference."""
        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM books WHERE id = %s RETURNING file;",
                (book_id,)
            )
            row = cur.fetchone()
            conn.commit()
            cur.close()
            return True, row[0] if row else None, None
        except Exception as e:
            conn.rollback()
            cur.close()
            return False, None, str(e)


class LogQueries:
    """Log-related database queries"""
    
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
