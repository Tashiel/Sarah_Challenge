import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List


class InsightStorage:
    def __init__(self, db_path: str = "data/social_insights.db") -> None:
        self.db_path = db_path
        self.connection = None

    def initialize(self) -> None:
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        assert self.connection is not None
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_posts (
                id TEXT PRIMARY KEY,
                text TEXT,
                author TEXT,
                created_at TEXT,
                source TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cleaned_posts (
                id TEXT PRIMARY KEY,
                text TEXT,
                author TEXT,
                createdAt TEXT,
                source TEXT,
                sentiment TEXT,
                sentimentScore REAL,
                processedAt TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trending_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                count INTEGER,
                source TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    def save_posts(self, posts: Iterable[Dict[str, Any]]) -> None:
        assert self.connection is not None
        cursor = self.connection.cursor()
        for post in posts:
            cursor.execute(
                """
                INSERT OR REPLACE INTO raw_posts (id, text, author, created_at, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    post["id"],
                    post["text"],
                    post.get("author"),
                    post.get("created_at"),
                    post.get("source"),
                ),
            )
        self.connection.commit()

    def save_trending_topics(self, topics: List[Dict[str, Any]], source: str) -> None:
        assert self.connection is not None
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM trending_topics WHERE source = ?", (source,))
        for topic in topics:
            cursor.execute(
                "INSERT INTO trending_topics (topic, count, source) VALUES (?, ?, ?)",
                (topic["topic"], topic["count"], source),
            )
        self.connection.commit()

    def load_recent_trending(self, source: str) -> List[Dict[str, Any]]:
        assert self.connection is not None
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT topic, count, updated_at FROM trending_topics WHERE source = ? ORDER BY count DESC LIMIT 20",
            (source,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def save_cleaned_posts(self, posts: Iterable[Dict[str, Any]]) -> None:
        assert self.connection is not None
        cursor = self.connection.cursor()
        for post in posts:
            cursor.execute(
                """
                INSERT OR REPLACE INTO cleaned_posts (id, text, author, createdAt, source, sentiment, sentimentScore)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post["id"],
                    post["text"],
                    post.get("author"),
                    post.get("createdAt"),
                    post.get("source"),
                    post.get("sentiment"),
                    post.get("sentimentScore"),
                ),
            )
        self.connection.commit()

    def load_unprocessed_raw_posts(self) -> List[Dict[str, Any]]:
        """Load raw posts that haven't been cleaned yet."""
        assert self.connection is not None
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT r.* FROM raw_posts r
            LEFT JOIN cleaned_posts c ON r.id = c.id
            WHERE c.id IS NULL
            """
        )
        return [dict(row) for row in cursor.fetchall()]
