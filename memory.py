import json
import math
import re
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

DB_PATH = Path(__file__).resolve().parent / "timothy_memory.db"

RECENT_DAYS = 5
DEFAULT_RECENT_LIMIT = 20

# --------------------------------------------------
# EMBEDDING CONFIGURATION
# --------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_TIMEOUT = 60


def generate_embeddings(texts):
    """
    Convert one or more text strings into numerical embeddings
    using the local Ollama embedding model.

    Returns a list of vectors, one for each input string.
    Raises an exception if Ollama cannot generate the embeddings.
    """
    if isinstance(texts, str):
        texts = [texts]

    if not texts:
        return []

    payload = json.dumps({
        "model": EMBEDDING_MODEL,
        "input": texts,
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=EMBEDDING_TIMEOUT,
    ) as response:
        result = json.loads(response.read().decode("utf-8"))

    embeddings = result.get("embeddings")

    if not isinstance(embeddings, list):
        raise ValueError("Ollama returned no embeddings.")

    if len(embeddings) != len(texts):
        raise ValueError("Ollama returned an unexpected number of embeddings.")

    return embeddings


def cosine_similarity(vector_a, vector_b):
    """Measure the cosine similarity between two embedding vectors."""
    if len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def backfill_memory_embeddings(batch_size=32):
    """Generate embeddings for memories that do not have them."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, fact
            FROM memories
            WHERE embedding IS NULL OR embedding = ''
            ORDER BY id
        """).fetchall()

    if not rows:
        print("All memories already have embeddings.")
        return 0

    updated = 0

    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        vectors = generate_embeddings(
            [row["fact"] for row in batch]
        )

        with get_connection() as connection:
            connection.executemany("""
                UPDATE memories
                SET embedding = ?
                WHERE id = ?
            """, [
                (json.dumps(vector), row["id"])
                for row, vector in zip(batch, vectors)
            ])

        updated += len(batch)

    print(f"Generated embeddings for {updated} memories.")
    return updated



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

        # Create the memories table before checking its columns.
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

        # Safely add embedding storage to an existing database.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(memories)"
            ).fetchall()
        }

        if "embedding" not in columns:
            connection.execute("""
                ALTER TABLE memories
                ADD COLUMN embedding TEXT
            """)

        # Starter memories are inserted only if absent.
        starter_memories = [
            ("faith", "The user identifies as a devout Christian.", "starter_profile"),
            ("faith", "The user is Catholic.", "starter_profile"),
            ("favorite_superhero", "The user's favourite superhero is Spider-Man.", "starter_profile"),
            ("favorite_film", "The user's favourite film is Interstellar.", "starter_profile"),
            (
                "robotics",
                "The user wants to build robotics projects, including an Iron Man-style wrist flashlight.",
                "starter_profile",
            ),
            ("education", "The user is studying for a BCA Honours degree.", "starter_profile"),
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
    """Save a fact and its embedding to permanent memory."""
    category = category.strip().lower()
    fact = fact.strip()

    if not category or not fact:
        raise ValueError("Both category and fact are required.")

    # Generate the embedding before writing to the database.
    embedding = json.dumps(generate_embeddings(fact)[0])

    with get_connection() as connection:
        connection.execute("""
            INSERT OR IGNORE INTO memories
                (category, fact, source, embedding)
            VALUES (?, ?, ?, ?)
        """, (category, fact, source, embedding))

        # Also populate a missing embedding if this fact already exists.
        connection.execute("""
            UPDATE memories
            SET embedding = ?
            WHERE category = ? AND fact = ?
              AND embedding IS NULL
        """, (embedding, category, fact))

        row = connection.execute("""
            SELECT id, category, fact, source,
                   created_at, updated_at
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
    Retrieve memories by semantic similarity across all categories.
    Fall back to keyword matching if embeddings are unavailable.
    """
    query = query.strip()

    if not query or limit <= 0:
        return []

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, category, fact, source,
                   created_at, updated_at, embedding
            FROM memories
            ORDER BY id DESC
        """).fetchall()

    if not rows:
        return []

    # Try semantic retrieval first.
    try:
        query_embedding = generate_embeddings(query)[0]
        scored = []

        for row in rows:
            memory = dict(row)
            stored_embedding = memory.get("embedding")

            if not stored_embedding:
                continue

            try:
                vector = json.loads(stored_embedding)
                score = cosine_similarity(query_embedding, vector)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue

            scored.append((score, memory))

        # Similarity is a ranking signal, not proof of relevance.
        scored.sort(key=lambda item: item[0], reverse=True)

        relevant = [
            memory
            for score, memory in scored
            if score >= 0.35
        ]

        if relevant:
            return [
                {key: value for key, value in memory.items()
                 if key != "embedding"}
                for memory in relevant[:int(limit)]
            ]

    except Exception as error:
        print(f"Semantic memory search unavailable: {error}")

    # Fallback: basic keyword matching across every category.
    query_words = _normalise_words(query)

    if not query_words:
        return []

    scored = []


def find_relevant_memories(query, limit=5):
    """
    Retrieve memories by semantic similarity across all categories.
    Fall back to keyword matching if embeddings are unavailable.
    """
    query = query.strip()

    if not query or limit <= 0:
        return []

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, category, fact, source,
                   created_at, updated_at, embedding
            FROM memories
            ORDER BY id DESC
        """).fetchall()

    if not rows:
        return []

    # Try semantic retrieval first.
    try:
        query_embedding = generate_embeddings(query)[0]
        scored = []

        for row in rows:
            memory = dict(row)
            stored_embedding = memory.get("embedding")

            if not stored_embedding:
                continue

            try:
                vector = json.loads(stored_embedding)
                score = cosine_similarity(query_embedding, vector)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue

            scored.append((score, memory))

        scored.sort(key=lambda item: item[0], reverse=True)

        # Diagnostic output for semantic retrieval.
        print("\n--- SEMANTIC MEMORY SIMILARITY SCORES ---")
        for score, memory in scored:
            print(
                f"{score:.3f} | "
                f"[{memory['category']}] {memory['fact']}"
            )

 # Diagnostic output for semantic retrieval.
        print("\n--- SEMANTIC MEMORY SIMILARITY SCORES ---")
        for score, memory in scored:
            print(
                f"{score:.3f} | "
                f"[{memory['category']}] {memory['fact']}"
            )

        if scored:
            best_score = scored[0][0]

            # Keep memories close to the best match.
            relevance_gap = 0.20

            relevant = [
                memory
                for score, memory in scored
                if score >= 0.35
                and score >= best_score - relevance_gap
            ]

            if relevant:
                return [
                    {
                        key: value
                        for key, value in memory.items()
                        if key != "embedding"
                    }
                    for memory in relevant[:int(limit)]
                ]

    except Exception as error:
        print(f"Semantic memory search unavailable: {error}")


    except Exception as error:
        print(f"Semantic memory search unavailable: {error}")

    # Keyword fallback across all categories.
    query_words = _normalise_words(query)

    if not query_words:
        return []

    scored = []

    for row in rows:
        memory = dict(row)
        fact_words = _normalise_words(
            memory["category"] + " " + memory["fact"]
        )
        score = len(query_words.intersection(fact_words))

        if score > 0:
            scored.append((score, memory))

    scored.sort(key=lambda item: item[0], reverse=True)

    print("\n--- KEYWORD FALLBACK SCORES ---")
    for score, memory in scored:
        print(
            f"{score} | "
            f"[{memory['category']}] {memory['fact']}"
        )

    return [
        {
            key: value
            for key, value in memory.items()
            if key != "embedding"
        }
        for _, memory in scored[:int(limit)]
    ]





# --------------------------------------------------
# LEGACY CONVERSATION SEARCH
# Keep this function until main.py is updated.
# --------------------------------------------------



def search_relevant_messages(query, limit=10):
    """
    Search archived conversations using weighted keyword relevance.
    Prioritises user messages and reduces duplicate results.
    """

    if not query or limit <= 0:
        return []

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
    }

    def normalise_text(text):
        text = text.lower()
        text = re.sub(r"spider[\s-]*man", "spiderman", text)

        words = re.findall(r"[a-z0-9]+", text)

        return [
            synonyms.get(word, word)
            for word in words
            if word not in stop_words and len(word) > 2
        ]

    query_words = normalise_text(query)

    if not query_words:
        return []

    query_keywords = set(query_words)
    query_phrase = " ".join(query_words)

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, role, content, timestamp
            FROM conversations
            ORDER BY id DESC
            LIMIT 2000
        """).fetchall()

    scored = []
    seen_contents = set()

    for position, row in enumerate(rows):
        content = row["content"]
        normalised_content = " ".join(normalise_text(content))

        if not normalised_content:
            continue

        # Avoid returning identical messages repeatedly.
        if normalised_content in seen_contents:
            continue

        content_words = set(normalised_content.split())
        matched_words = query_keywords.intersection(content_words)

        if not matched_words:
            continue

        seen_contents.add(normalised_content)

        coverage = len(matched_words) / len(query_keywords)

        score = (
            len(matched_words) * 2
            + coverage * 5
        )

        if query_phrase in normalised_content:
            score += 5

        # Prefer original user statements.
        if row["role"] == "user":
            score += 3

        # Small recency preference.
        score += 0.5 / (position + 1)

        scored.append((score, dict(row)))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        {
            "role": row["role"],
            "content": row["content"],
        }
        for _, row in scored[:int(limit)]
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
