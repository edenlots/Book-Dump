"""Database query operations for user data."""

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
        """Record the account deletion and delete the user atomically."""
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
