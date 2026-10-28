
import re
import sqlite3
from pathlib import Path


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

DB_PATH = Path(__file__).resolve().parent / "timothy_memory.db"

RECENT_DAYS = 5
DEFAULT_RECENT_LIMIT = 20


def get_connection():
    """Open Timothy's local SQLite database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# --------------------------------------------------
# INITIALISE DATABASE
# --------------------------------------------------

def initialise_database():
    """
    Create the conversation archive and dedicated memory table.
    Preserve all existing conversation records.
    """
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact TEXT NOT NULL,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, fact)
            )
        """)

        # Starter profile: inserted only if a fact does not
        # already exist. Running this repeatedly won't duplicate it.
        starter_memories = [
            (
                "faith",
                "The user identifies as a devout Christian.",
                "starter_profile",
            ),
            (
                "faith",
                "The user is Catholic.",
                "starter_profile",
            ),
            (
                "favorite_superhero",
                "The user's favourite superhero is Spider-Man.",
                "starter_profile",
            ),
            (
                "favorite_film",
                "The user's favourite film is Interstellar.",
                "starter_profile",
            ),
            (
                "robotics",
                "The user wants to build robotics projects, "
                "including an Iron Man-style wrist flashlight.",
                "starter_profile",
            ),
            (
                "education",
                "The user is studying for a BCA Honours degree.",
                "starter_profile",
            ),
        ]

        connection.executemany("""
            INSERT OR IGNORE INTO memories
                (category, fact, source)
            VALUES (?, ?, ?)
        """, starter_memories)


# --------------------------------------------------
# CONVERSATION ARCHIVE
# --------------------------------------------------

def save_message(role, content):
    """Save a conversation message."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO conversations (role, content)
            VALUES (?, ?)
        """, (role, content))


def get_recent_messages(limit=DEFAULT_RECENT_LIMIT, days=RECENT_DAYS):
    """
    Retrieve recent conversation messages in chronological order.

    By default, return at most 20 messages from the last five days.
    Older messages remain stored in the database.
    """
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT role, content, timestamp
            FROM conversations
            WHERE timestamp >= datetime('now', ?)
            ORDER BY id DESC
            LIMIT ?
        """, (f"-{max(0, int(days))} days", max(0, int(limit)))).fetchall()

    return [dict(row) for row in reversed(rows)]


def get_message_count():
    """Return the total number of archived messages."""
    with get_connection() as connection:
        row = connection.execute("""
            SELECT COUNT(*) FROM conversations
        """).fetchone()

    return row[0]


# --------------------------------------------------
# PERMANENT FACT MEMORY
# --------------------------------------------------

def remember_fact(category, fact, source="explicit_remember"):
    """
    Save one fact to permanent memory.

    Returns the saved memory record.
    Duplicate category/fact pairs are not inserted twice.
    """
    category = category.strip().lower()
    fact = fact.strip()

    if not category or not fact:
        raise ValueError("Both category and fact are required.")

    with get_connection() as connection:
        connection.execute("""
            INSERT OR IGNORE INTO memories
                (category, fact, source)
            VALUES (?, ?, ?)
        """, (category, fact, source))

        row = connection.execute("""
            SELECT id, category, fact, source, created_at, updated_at
            FROM memories
            WHERE category = ? AND fact = ?
        """, (category, fact)).fetchone()

    return dict(row)


def get_all_memories():
    """Return every saved fact, newest records first."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, category, fact, source, created_at, updated_at
            FROM memories
            ORDER BY id DESC
        """).fetchall()

    return [dict(row) for row in rows]


def update_memory(memory_id, fact, category=None):
    """Update an existing saved fact."""
    fact = fact.strip()

    if not fact:
        raise ValueError("The fact cannot be empty.")

    with get_connection() as connection:
        if category is None:
            connection.execute("""
                UPDATE memories
                SET fact = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (fact, memory_id))
        else:
            connection.execute("""
                UPDATE memories
                SET category = ?, fact = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (category.strip().lower(), fact, memory_id))

        row = connection.execute("""
            SELECT id, category, fact, source, created_at, updated_at
            FROM memories
            WHERE id = ?
        """, (memory_id,)).fetchone()

    return dict(row) if row else None


def delete_memory(memory_id):
    """Delete one saved fact. Returns True if a record was deleted."""
    with get_connection() as connection:
        cursor = connection.execute("""
            DELETE FROM memories WHERE id = ?
        """, (memory_id,))

    return cursor.rowcount > 0


# --------------------------------------------------
# MEMORY RETRIEVAL
# --------------------------------------------------

# These are categories, not instructions for the language model.
# Different question wording can map to the same category.
CATEGORY_TERMS = {
    "faith": {
        "faith", "belief", "beliefs", "religion", "religious",
        "christian", "christianity", "catholic", "catholicism",
        "church", "jesus",
    },
    "favorite_superhero": {
        "hero", "heroes", "superhero", "superheroes",
        "spiderman", "spider-man",
    },
    "favorite_film": {
        "film", "films", "movie", "movies", "cinema",
        "interstellar",
    },
    "robotics": {
        "robotics", "robot", "robots", "arduino", "sensor",
        "sensors", "flashlight", "ironman", "iron-man",
    },
    "education": {
        "education", "college", "degree", "bca", "studies",
        "studying", "course",
    },
}


def _normalise_words(text):
    """Extract lowercase words, normalising common spelling variants."""
    words = set(re.findall(r"[a-z0-9]+", text.lower()))

    if "spiderman" in words:
        words.add("spider-man")

    if "favourite" in words:
        words.add("favorite")

    return words



def find_relevant_memories(query, limit=5):
    """
    Retrieve facts by category first.
    If a category is recognised, do not return unrelated categories.
    Otherwise, fall back to basic keyword matching.
    """
    query_words = _normalise_words(query)

    if not query_words:
        return []

    matching_categories = {
        category
        for category, terms in CATEGORY_TERMS.items()
        if query_words.intersection(terms)
    }

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, category, fact, source, created_at, updated_at
            FROM memories
            ORDER BY id DESC
        """).fetchall()

    scored = []

    for row in rows:
        memory = dict(row)

        # A recognised category takes priority.
        if matching_categories:
            if memory["category"] not in matching_categories:
                continue

            score = 100
        else:
            fact_words = _normalise_words(
                memory["category"] + " " + memory["fact"]
            )
            score = len(query_words.intersection(fact_words))

            if score == 0:
                continue

        scored.append((score, memory))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        memory
        for _, memory in scored[:max(0, int(limit))]
    ]



# --------------------------------------------------
# LEGACY CONVERSATION SEARCH
# Keep this function until main.py is updated.
# --------------------------------------------------

def search_relevant_messages(query, limit=10):
    """
    Basic keyword search over the conversation archive.

    This is retained for compatibility with the existing main.py.
    The new permanent fact memory uses find_relevant_memories().
    """
    stop_words = {
        "i", "me", "my", "you", "your", "the", "a", "an",
        "is", "was", "were", "am", "are", "do", "did",
        "have", "has", "had", "who", "what", "when", "where",
        "which", "how", "why", "tell", "said", "say", "about",
        "to", "of", "in", "on", "for", "and", "or", "that",
        "this", "it", "he", "she", "they", "we",
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
        rows = connection.execute("""
            SELECT id, role, content, timestamp
            FROM conversations
            ORDER BY id DESC
            LIMIT 2000
        """).fetchall()

    scored = []

    for row in rows:
        content = row["content"].lower()

        if content.strip() == query.strip().lower():
            continue

        content_words = set(re.findall(r"[a-z0-9]+", content))

        score = sum(
            1 for keyword in keywords
            if keyword in content_words
            or keyword.replace("-", "") in content_words
        )

        if score:
            scored.append((score, dict(row)))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        {
            "role": row["role"],
            "content": row["content"],
        }
        for _, row in scored[:max(0, int(limit))]
    ]


# --------------------------------------------------
# TEST / INSPECTION
# --------------------------------------------------

if __name__ == "__main__":
    initialise_database()

    print("Timothy's memory database is ready!")
    print(f"Database location: {DB_PATH}")

    print("\n--- PERMANENT FACT MEMORIES ---")
    for memory in get_all_memories():
        print(
            f"[{memory['id']}] "
            f"{memory['category']}: {memory['fact']}"
        )

    print("\n--- RECENT CONVERSATION ---")
    for message in get_recent_messages():
        print(f"{message['role']}: {message['content']}")

    print(f"\nTotal archived messages: {get_message_count()}")
