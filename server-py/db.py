import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "chat.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    PRAGMA journal_mode = WAL;

    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rooms (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS room_members (
      user_id INTEGER NOT NULL,
      room_id INTEGER NOT NULL,
      PRIMARY KEY (user_id, room_id),
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      type TEXT NOT NULL CHECK(type IN ('room','dm')),
      room_id INTEGER,
      sender_id INTEGER NOT NULL,
      recipient_id INTEGER,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
      FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    # anexos (se já não existirem)
    if not _column_exists(cur, "messages", "attachment_url"):
        cur.execute("ALTER TABLE messages ADD COLUMN attachment_url TEXT")
    if not _column_exists(cur, "messages", "attachment_type"):
        cur.execute("ALTER TABLE messages ADD COLUMN attachment_type TEXT")

    # ---- NOVO: contatos de DM salvos ----
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dm_contacts (
      user_id INTEGER NOT NULL,
      other_id INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      PRIMARY KEY (user_id, other_id),
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (other_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Sala inicial "Geral"
    has_rooms = cur.execute("SELECT COUNT(1) FROM rooms").fetchone()[0]
    if not has_rooms:
        cur.execute(
            "INSERT INTO rooms (name, created_at) VALUES (?, ?)",
            ("Geral", datetime.utcnow().isoformat())
        )

    conn.commit()
    conn.close()

def get_room_by_name(name: str):
    with get_conn() as c:
        row = c.execute("SELECT id, name FROM rooms WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

def find_user_by_email(email: str):
    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

def find_user_by_id(uid: int):
    with get_conn() as c:
        row = c.execute("SELECT id, name, email FROM users WHERE id = ?", (uid,)).fetchone()
        return dict(row) if row else None

def insert_user(name, email, password_hash):
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash, datetime.utcnow().isoformat())
        )
        return cur.lastrowid

def list_my_rooms(my_id: int):
    with get_conn() as c:
        rows = c.execute("""
            SELECT r.id, r.name
            FROM rooms r
            JOIN room_members m ON m.room_id = r.id
            WHERE m.user_id = ?
            ORDER BY r.name
        """, (my_id,)).fetchall()
        return [dict(r) for r in rows]

def create_room(name: str):
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO rooms (name, created_at) VALUES (?, ?)",
            (name, datetime.utcnow().isoformat())
        )
        return cur.lastrowid

def join_room(user_id: int, room_id: int):
    with get_conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO room_members (user_id, room_id) VALUES (?, ?)",
            (user_id, room_id)
        )

def leave_room(user_id: int, room_id: int):
    with get_conn() as c:
        c.execute("DELETE FROM room_members WHERE user_id = ? AND room_id = ?", (user_id, room_id))

def room_exists(room_id: int) -> bool:
    with get_conn() as c:
        row = c.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
        return bool(row)

def is_member(user_id: int, room_id: int) -> bool:
    with get_conn() as c:
        row = c.execute(
            "SELECT 1 FROM room_members WHERE user_id = ? AND room_id = ?",
            (user_id, room_id)
        ).fetchone()
        return bool(row)

def insert_room_message(room_id: int, sender_id: int, content: str, attachment_url=None, attachment_type=None):
    with get_conn() as c:
        cur = c.execute("""
            INSERT INTO messages (type, room_id, sender_id, content, created_at, attachment_url, attachment_type)
            VALUES ('room', ?, ?, ?, ?, ?, ?)
        """, (room_id, sender_id, content, datetime.utcnow().isoformat(), attachment_url, attachment_type))
        return cur.lastrowid

def insert_dm(sender_id: int, recipient_id: int, content: str, attachment_url=None, attachment_type=None):
    with get_conn() as c:
        cur = c.execute("""
            INSERT INTO messages (type, sender_id, recipient_id, content, created_at, attachment_url, attachment_type)
            VALUES ('dm', ?, ?, ?, ?, ?, ?)
        """, (sender_id, recipient_id, content, datetime.utcnow().isoformat(), attachment_url, attachment_type))
        return cur.lastrowid

def room_history(room_id: int):
    with get_conn() as c:
        rows = c.execute("""
            SELECT m.*, u.name AS sender_name
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.type = 'room' AND m.room_id = ?
            ORDER BY m.id ASC
            LIMIT 300
        """, (room_id,)).fetchall()
        return [dict(r) for r in rows]

def dm_history(a: int, b: int):
    with get_conn() as c:
        rows = c.execute("""
            SELECT m.*, u.name AS sender_name
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.type = 'dm'
              AND ((m.sender_id = ? AND m.recipient_id = ?) OR (m.sender_id = ? AND m.recipient_id = ?))
            ORDER BY m.id ASC
            LIMIT 300
        """, (a, b, b, a)).fetchall()
        return [dict(r) for r in rows]

# ---------- DMs salvas ----------
def add_dm_contact(user_id: int, other_id: int):
    with get_conn() as c:
        c.execute("""
        INSERT OR IGNORE INTO dm_contacts (user_id, other_id, created_at)
        VALUES (?, ?, ?)
        """, (user_id, other_id, datetime.utcnow().isoformat()))

def list_dm_contacts(user_id: int):
    with get_conn() as c:
        rows = c.execute("""
        SELECT u.id, u.name, u.email
        FROM dm_contacts d
        JOIN users u ON u.id = d.other_id
        WHERE d.user_id = ?
        ORDER BY u.name
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]

def remove_dm_contact(user_id: int, other_id: int):
    with get_conn() as c:
        c.execute("DELETE FROM dm_contacts WHERE user_id = ? AND other_id = ?", (user_id, other_id))
