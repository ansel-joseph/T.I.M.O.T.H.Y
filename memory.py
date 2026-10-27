
import sqlite3
from pathlib import Path

# Store Timothy's memory in the project directory.
DB_PATH = Path(__file__).resolve().parent / "timothy_memory.db"


def get_connection():
    """Open a connection to Timothy's local memory database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_database():
    """Create the conversation table if it doesn't exist."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_message(role, content):
    """Save one user or assistant message."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO conversations (role, content) VALUES (?, ?)",
            (role, content)
        )


def get_recent_messages(limit=20):
    """Retrieve the most recent messages in chronological order."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content, timestamp
            FROM conversations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return [dict(row) for row in reversed(rows)]


if __name__ == "__main__":
    initialise_database()
    print("Timothy's memory database is ready!")
    print(f"Location: {DB_PATH}")

    messages = get_recent_messages()

    print("\nRecent memories:")
    for message in messages:
        print(f"{message['role']}: {message['content']}")
