"""SQLite-backed cache storage utilities for API payloads."""

import json
import os
import sqlite3
import time


class SQLiteCache:
    """Persist cached API responses in a local SQLite database.

    Parameters:
        db_path: Path to the SQLite database file.
        default_ttl_seconds: Fallback TTL for entries without explicit TTL.

    Returns:
        None

    Raises:
        sqlite3.Error: If the database cannot be initialized.

    Edge Cases:
        Creates directories for nested database paths.
    """

    def __init__(self, db_path, default_ttl_seconds=600):
        """Initialize the cache and ensure schema exists.

        Parameters:
            db_path: Path to the SQLite database file.
            default_ttl_seconds: Default time-to-live in seconds.

        Returns:
            None

        Raises:
            sqlite3.Error: If the database cannot be initialized.

        Edge Cases:
            Creates the database file if it doesn't exist.
        """
        self.db_path = db_path
        self.default_ttl_seconds = default_ttl_seconds
        self._ensure_db()

    def _ensure_db(self):
        """Create the cache table if it does not exist.

        Parameters:
            None

        Returns:
            None

        Raises:
            sqlite3.Error: If the database cannot be initialized.

        Edge Cases:
            Safe to call multiple times.
        """
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    endpoint TEXT,
                    payload TEXT NOT NULL,
                    fetched_at INTEGER NOT NULL,
                    ttl_seconds INTEGER NOT NULL
                )
                """
            )

    def _now(self):
        """Return the current epoch time in seconds.

        Parameters:
            None

        Returns:
            int: Current Unix timestamp.

        Raises:
            None

        Edge Cases:
            None
        """
        return int(time.time())

    def save(self, cache_key, payload, ttl_seconds=None, endpoint=None):
        """Persist a payload to the cache.

        Parameters:
            cache_key: Unique identifier for the cached entry.
            payload: JSON-serializable data to store.
            ttl_seconds: Optional TTL override in seconds.
            endpoint: Optional logical endpoint label.

        Returns:
            None

        Raises:
            sqlite3.Error: If the write fails.
            TypeError: If payload is not JSON-serializable.

        Edge Cases:
            Overwrites any existing entry with the same cache key.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_entries
                (cache_key, endpoint, payload, fetched_at, ttl_seconds)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cache_key, endpoint, json.dumps(payload), self._now(), ttl),
            )

    def get(self, cache_key, allow_stale=False):
        """Fetch a cached payload by key.

        Parameters:
            cache_key: Unique identifier for the cached entry.
            allow_stale: If True, return stale entries with metadata.

        Returns:
            dict | None: Cached payload metadata or None when missing/expired.

        Raises:
            sqlite3.Error: If the read fails.

        Edge Cases:
            Returns None when data is stale and allow_stale is False.
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT payload, fetched_at, ttl_seconds
                FROM cache_entries
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()

        if not row:
            return None

        payload_json, fetched_at, ttl_seconds = row
        age = self._now() - fetched_at
        is_stale = age > ttl_seconds

        if is_stale and not allow_stale:
            return None

        return {
            "payload": json.loads(payload_json),
            "fetched_at": fetched_at,
            "ttl_seconds": ttl_seconds,
            "stale": is_stale,
        }
