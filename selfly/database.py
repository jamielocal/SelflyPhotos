# database.py
import sqlite3
import os

# Define the path to the database file
DATABASE_PATH = 'database.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            photo_dir TEXT,
            video_dir TEXT,
            is_admin BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user_by_username(username):
    """Retrieves a user by their username."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Retrieves a user by their ID."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def add_new_user(username, password, photo_dir, video_dir, is_admin=False):
    """Adds a new user to the database."""
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, password, photo_dir, video_dir, is_admin) VALUES (?, ?, ?, ?, ?)',
                     (username, password, photo_dir, video_dir, is_admin))
        conn.commit()
        # Create the user's directories
        if not os.path.exists(photo_dir):
            os.makedirs(photo_dir)
        if not os.path.exists(video_dir):
            os.makedirs(video_dir)
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_user_directories(user_id):
    """Returns the photo and video directories for a user."""
    conn = get_db_connection()
    user = conn.execute('SELECT photo_dir, video_dir FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def check_for_users():
    """Returns the number of users in the database."""
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    return count

def get_all_users():
    """Returns a list of all users."""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return users

def delete_user(user_id):
    """Deletes a user from the database."""
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

def update_user_password(user_id, new_password):
    """Updates a user's password."""
    conn = get_db_connection()
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
    conn.commit()
    conn.close()

def update_user_admin_status(user_id, is_admin):
    """Updates a user's admin status."""
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_admin = ? WHERE id = ?', (is_admin, user_id))
    conn.commit()
    conn.close()

def get_setting(key):
    """Retrieves a setting value by its key."""
    conn = get_db_connection()
    setting = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return setting['value'] if setting else None

def add_setting(key, value):
    """Inserts or updates a setting value."""
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()
