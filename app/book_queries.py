"""Database query operations for book data."""

import psycopg2.extras


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
    def get_user_bookshelf(conn, user_id):
        """Get books uploaded or saved by a user."""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT b.id, b.title, b.author, b.year, b.genre, b.language, b.overview
            FROM books b
            WHERE EXISTS (
                SELECT 1 FROM logs l
                WHERE l.book_id = b.id AND l.user_id = %s
                    AND l.action IN ('uploaded', 'favorite')
            )
            ORDER BY b.title;
            """,
            (user_id,),
        )
        books = cur.fetchall()
        cur.close()
        return books

    @staticmethod
    def get_user_uploaded_books(conn, user_id):
        """Get books uploaded by a user."""
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT DISTINCT b.id, b.title, b.author, b.year, b.genre, b.language,
                b.overview
            FROM books b
            JOIN logs l ON l.book_id = b.id
            WHERE l.user_id = %s AND l.action = 'uploaded'
            ORDER BY b.title;
            """,
            (user_id,),
        )
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

    @staticmethod
    def is_book_favorite(conn, user_id, book_id):
        """Check whether a book is saved by a user."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM logs
                WHERE user_id = %s AND book_id = %s AND action = 'favorite'
            );
            """,
            (user_id, book_id),
        )
        is_favorite = cur.fetchone()[0]
        cur.close()
        return is_favorite
