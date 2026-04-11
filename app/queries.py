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
        """Get user info by user ID"""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT username, email FROM users WHERE id = %s;", (user_id,))
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
    def create_user(conn, username, email, password_hash):
        """Create a new user account"""
        cur = conn.cursor()
        try:
            cur.execute(
                """INSERT INTO users (username, email, pw_hash, role) VALUES (%s, %s, %s, %s);""",
                (username, email, password_hash, "user")
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
        cur.execute("SELECT id, title, author, file FROM books WHERE id = %s;", (book_id,))
        book = cur.fetchone()
        cur.close()
        return book
    
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
