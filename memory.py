
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


def get_message_count():
    """Return the total number of stored messages."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM conversations"
        ).fetchone()

    return row[0]


def inspect_oldest_messages(limit=15):
    """Show the oldest stored messages."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content, timestamp
            FROM conversations
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    for row in rows:
        print(f"\nID: {row['id']} | {row['role']} | {row['timestamp']}")
        print(row['content'])



import re

def search_relevant_messages(query, limit=10):
    stop_words = {
        "i", "me", "my", "you", "your", "the", "a", "an",
        "is", "was", "were", "am", "are", "do", "did",
        "have", "has", "had", "who", "what", "when", "where",
        "which", "how", "why", "tell", "said", "say", "about",
        "to", "of", "in", "on", "for", "and", "or", "that",
        "this", "it", "he", "she", "they", "we", "me"
    }

    synonyms = {
        "superhero": "hero",
        "superheroes": "hero",
        "favorite": "favourite",
        "favourites": "favourite",
        "spiderman": "spider-man",
    }

    words = re.findall(r"[a-z0-9]+", query.lower())
    keywords = {
        synonyms.get(word, word)
        for word in words
        if word not in stop_words and len(word) > 2
    }

    if not keywords:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content
            FROM conversations
            ORDER BY id DESC
            LIMIT 2000
            """
        ).fetchall()

    rows = list(reversed(rows))
    scored = []

    for index, row in enumerate(rows):
        content = row["content"].lower()

        # Avoid retrieving the current question as a false match.
        if content.strip().lower() == query.strip().lower():
            continue

        content_words = set(re.findall(r"[a-z0-9]+", content))

        score = sum(
            1 for keyword in keywords
            if keyword in content_words
            or keyword.replace("-", "") in content_words
        )

        if score:
            scored.append((score, index))

    # Prefer messages matching more of the search terms.
    scored.sort(key=lambda item: item[0], reverse=True)

    selected_indices = set()

    # Include nearby messages so the matching fact retains its context.
    for _, index in scored[:3]:
        for nearby in range(
            max(0, index - 2),
            min(len(rows), index + 3)
        ):
            selected_indices.add(nearby)

    selected = sorted(selected_indices)

    # Limit the amount of old history sent to the model.
    if len(selected) > limit:
        selected = selected[-limit:]

    return [
        {
            "role": rows[index]["role"],
            "content": rows[index]["content"],
        }
        for index in selected
    ]


if __name__ == "__main__":
    initialise_database()
    print("Timothy's memory database is ready!")
    print(f"Location: {DB_PATH}")

    messages = get_recent_messages()

    print("\nRecent memories:")
    for message in messages:
        print(f"{message['role']}: {message['content']}")
    print(f"Total stored messages: {get_message_count()}")
    inspect_oldest_messages()