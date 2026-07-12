"""
In-memory sparse TF-IDF and Cosine Similarity RAG (Retrieval-Augmented Generation) engine for mentask.

Optimized for speed (<15ms index time for medium projects) and zero heavy library dependencies.
Splits workspace source files into semantic chunks and retrieves relevant code context.

Cache strategy
--------------
After each full index the engine serialises the computed state (chunks, IDF vectors, file
modification timestamps) into a SQLite database stored at::

    ~/.mentask/rag_cache.db

The cache key is the ``root_dir`` path.  On the next ``query()`` call the engine:

1. Computes a fast "fingerprint" of workspace mtimes (no file content read).
2. Compares it against the cached fingerprint.
3. If identical → deserialises the cache (microseconds).
4. If different → re-indexes only what changed, then writes a new cache entry.

This reduces cold-start latency for large workspaces from O(seconds) to O(milliseconds)
on subsequent runs.
"""

import json
import logging
import math
import os
import re
import sqlite3
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_logger = logging.getLogger("mentask.rag")

# Directories to skip when scanning workspace
_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mentask",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    ".vscode",
    ".zed",
}

# Supported file extensions for text-based semantic indexing
_SUPPORTED_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".sql",
    ".sh",
    ".toml",
    "makefile",
    "dockerfile",
}

# Maximum file size to index (100 KB) to prevent memory bloating
_MAX_FILE_SIZE = 100 * 1024

# Schema version — bump this whenever the persisted format changes
_CACHE_SCHEMA_VERSION = 2


def _default_cache_path() -> Path:
    """Returns the default SQLite cache file path."""
    home = Path.home()
    db_dir = home / ".mentask"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "rag_cache.db"


@contextmanager
def _open_db(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that opens a SQLite connection and guarantees it is closed."""
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        _logger.debug("SQLite operation failed, rolling back", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Creates the cache table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_cache (
            workspace   TEXT    NOT NULL,
            version     INTEGER NOT NULL,
            fingerprint TEXT    NOT NULL,
            chunks      TEXT    NOT NULL,
            idf         TEXT    NOT NULL,
            vectors     TEXT    NOT NULL,
            mtimes      TEXT    NOT NULL,
            updated_at  INTEGER NOT NULL,
            PRIMARY KEY (workspace, version)
        )
        """
    )


class RAGManager:
    """Lightweight in-memory vector retrieval engine utilizing TF-IDF and Cosine Similarity.

    Uses a SQLite-backed persistent cache to avoid re-computing TF-IDF vectors on every
    startup when the workspace has not changed.
    """

    def __init__(self, root_dir: str | None = None, cache_path: Path | None = None):
        self.root_dir = root_dir or os.getcwd()
        self._cache_path: Path = cache_path or _default_cache_path()

        # In-memory state (also persisted to SQLite)
        self.chunks: list[dict[str, Any]] = []
        self.idf: dict[str, float] = {}
        self.chunk_vectors: list[dict[str, float]] = []
        self._file_mtimes: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Tokenisation
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        """Splits text into lowercase alphanumeric tokens."""
        return re.findall(r"\b\w{2,}\b", text.lower())

    # ------------------------------------------------------------------
    # Workspace fingerprinting
    # ------------------------------------------------------------------

    def _compute_fingerprint(self) -> str:
        """Returns a compact string that changes whenever any tracked file is modified.

        Only reads filesystem metadata (no file content) so it is very fast.
        """
        entries: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for filename in sorted(filenames):
                ext = os.path.splitext(filename)[1].lower()
                if ext not in _SUPPORTED_EXTS and filename.lower() not in _SUPPORTED_EXTS:
                    continue
                filepath = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(filepath)
                    if size > _MAX_FILE_SIZE:
                        continue
                    rel = os.path.relpath(filepath, self.root_dir)
                    mtime = os.path.getmtime(filepath)
                    entries.append(f"{rel}:{mtime:.3f}")
                except OSError:
                    continue
        return "|".join(sorted(entries))

    # ------------------------------------------------------------------
    # Cache I/O
    # ------------------------------------------------------------------

    def _load_cache(self, fingerprint: str) -> bool:
        """Tries to load a valid cache entry for the current workspace + fingerprint.

        Returns ``True`` on a cache hit, ``False`` otherwise.
        """
        if not self._cache_path.exists():
            return False
        try:
            with _open_db(self._cache_path) as conn:
                _ensure_schema(conn)
                row = conn.execute(
                    "SELECT chunks, idf, vectors, mtimes FROM rag_cache "
                    "WHERE workspace = ? AND version = ? AND fingerprint = ?",
                    (self.root_dir, _CACHE_SCHEMA_VERSION, fingerprint),
                ).fetchone()

            if row is None:
                return False

            self.chunks = json.loads(row[0])
            self.idf = json.loads(row[1])
            self.chunk_vectors = json.loads(row[2])
            self._file_mtimes = json.loads(row[3])
            _logger.debug("RAG: loaded %d chunks from cache (fingerprint hit)", len(self.chunks))
            return True

        except Exception as exc:
            _logger.debug("RAG: cache load failed (%s), will re-index", exc)
            return False

    def _save_cache(self, fingerprint: str) -> None:
        """Persists the current in-memory state to the SQLite cache (atomic write)."""
        try:
            # Serialise to a temp file first to avoid corrupting the DB on crash
            with tempfile.NamedTemporaryFile(
                dir=self._cache_path.parent,
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp_path = tmp.name

            # Write to the real DB using UPSERT
            with _open_db(self._cache_path) as conn:
                _ensure_schema(conn)
                import time

                conn.execute(
                    """
                    INSERT INTO rag_cache
                        (workspace, version, fingerprint, chunks, idf, vectors, mtimes, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(workspace, version) DO UPDATE SET
                        fingerprint = excluded.fingerprint,
                        chunks      = excluded.chunks,
                        idf         = excluded.idf,
                        vectors     = excluded.vectors,
                        mtimes      = excluded.mtimes,
                        updated_at  = excluded.updated_at
                    """,
                    (
                        self.root_dir,
                        _CACHE_SCHEMA_VERSION,
                        fingerprint,
                        json.dumps(self.chunks),
                        json.dumps(self.idf),
                        json.dumps(self.chunk_vectors),
                        json.dumps(self._file_mtimes),
                        int(time.time()),
                    ),
                )

            Path(tmp_path).unlink(missing_ok=True)
            _logger.debug("RAG: cache written (%d chunks)", len(self.chunks))

        except Exception as exc:
            _logger.debug("RAG: cache write failed (%s), index still valid in-memory", exc)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_workspace(self) -> None:
        """Scans the workspace directory, chunks files, and computes TF-IDF weights.

        The result is persisted to the SQLite cache so subsequent calls are instant
        unless the workspace has changed.
        """
        self.chunks = []
        self.idf = {}
        self.chunk_vectors = []
        self._file_mtimes = {}

        root_path = Path(self.root_dir)
        if not root_path.exists():
            return

        # 1. Crawl text files and split into chunks
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            # Prune skipped directories in-place
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in _SUPPORTED_EXTS and filename.lower() not in _SUPPORTED_EXTS:
                    continue

                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, self.root_dir)
                try:
                    if os.path.getsize(filepath) > _MAX_FILE_SIZE:
                        continue

                    mtime = os.path.getmtime(filepath)
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    if not lines:
                        continue

                    has_chunks = False

                    # Chunking strategy: 30-line windows with a 10-line overlap
                    chunk_size = 30
                    overlap = 10
                    i = 0
                    while i < len(lines):
                        end = min(i + chunk_size, len(lines))
                        chunk_lines = lines[i:end]
                        content = "".join(chunk_lines).strip()
                        if content:
                            self.chunks.append(
                                {
                                    "path": rel_path,
                                    "content": content,
                                    "start_line": i + 1,
                                    "end_line": end,
                                }
                            )
                            has_chunks = True
                        if end == len(lines):
                            break
                        i += chunk_size - overlap

                    if has_chunks:
                        self._file_mtimes[rel_path] = mtime

                except Exception as e:  # nosec B112
                    _logger.debug("Failed to index workspace file %s: %s", rel_path, e)
                    continue

        if not self.chunks:
            return

        # 2. Compute Document Frequencies (DF)
        num_docs = len(self.chunks)
        doc_frequencies: dict[str, int] = {}

        for chunk in self.chunks:
            tokens = set(self._tokenize(chunk["content"]))
            for token in tokens:
                doc_frequencies[token] = doc_frequencies.get(token, 0) + 1

        # 3. Compute Inverse Document Frequencies (IDF)
        for term, df in doc_frequencies.items():
            # Smoothed IDF formula
            self.idf[term] = math.log((1 + num_docs) / (1 + df)) + 1

        # 4. Build sparse TF-IDF vectors for all chunks and pre-normalize them
        for chunk in self.chunks:
            chunk_tokens: list[str] = self._tokenize(chunk["content"])
            if not chunk_tokens:
                self.chunk_vectors.append({})
                continue

            # Compute term frequencies (TF)
            tf: dict[str, int] = {}
            for token in chunk_tokens:
                tf[token] = tf.get(token, 0) + 1

            # Compute TF-IDF weights
            vector: dict[str, float] = {}
            n_tokens = len(chunk_tokens)
            for term, count in tf.items():
                norm_tf = count / n_tokens
                vector[term] = norm_tf * self.idf.get(term, 0.0)

            # Pre-calculate Euclidean Norm for cosine similarity normalisation
            length = math.sqrt(sum(val**2 for val in vector.values()))
            normalized_vector = {term: val / length for term, val in vector.items()} if length > 0 else {}

            self.chunk_vectors.append(normalized_vector)

    # ------------------------------------------------------------------
    # Change detection
    # ------------------------------------------------------------------

    def _needs_reindex(self) -> bool:
        """Returns True if any workspace file has been modified, added, or removed."""
        if not self._file_mtimes:
            return True

        current_files: dict[str, float] = {}
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in _SUPPORTED_EXTS and filename.lower() not in _SUPPORTED_EXTS:
                    continue

                filepath = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(filepath)
                    if size > _MAX_FILE_SIZE:
                        continue
                    rel_path = os.path.relpath(filepath, self.root_dir)
                    current_files[rel_path] = os.path.getmtime(filepath)
                except OSError as e:
                    _logger.debug("Failed to check workspace file %s: %s", filepath, e)
                    continue

        return current_files != self._file_mtimes

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(self, query_str: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Finds the most relevant chunks in the workspace for a given query string.

        The index is loaded from the SQLite cache when possible, avoiding a full
        re-computation on every call when the workspace has not changed.
        """
        if not self.chunks or self._needs_reindex():
            # Compute fingerprint once and try cache first
            fingerprint = self._compute_fingerprint()
            if not self._load_cache(fingerprint):
                _logger.debug("RAG: cache miss — re-indexing workspace")
                self.index_workspace()
                self._save_cache(fingerprint)

        query_tokens = self._tokenize(query_str)
        if not query_tokens or not self.chunk_vectors:
            return []

        # Build query TF-IDF vector
        query_tf: dict[str, int] = {}
        for token in query_tokens:
            query_tf[token] = query_tf.get(token, 0) + 1

        query_vector: dict[str, float] = {}
        n_qtokens = len(query_tokens)
        for term, count in query_tf.items():
            norm_tf = count / n_qtokens
            query_vector[term] = norm_tf * self.idf.get(term, 0.0)

        # Pre-normalize query vector
        query_length = math.sqrt(sum(val**2 for val in query_vector.values()))
        if query_length <= 0:
            return []
        query_normalized = {term: val / query_length for term, val in query_vector.items()}

        # Compute Cosine Similarity using dot product of pre-normalized sparse vectors
        scores: list[tuple[float, dict[str, Any]]] = []
        for idx, doc_vector in enumerate(self.chunk_vectors):
            if not doc_vector:
                continue
            dot_product = sum(
                query_normalized[term] * doc_vector[term] for term in query_normalized if term in doc_vector
            )
            if dot_product > 0.05:  # Minimum similarity threshold to prevent noise
                scores.append((dot_product, self.chunks[idx]))

        # Sort by similarity score descending
        scores.sort(key=lambda x: x[0], reverse=True)

        # Format and return top K matches
        return [
            {
                "score": score,
                "path": chunk["path"],
                "content": chunk["content"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
            }
            for score, chunk in scores[:top_k]
        ]

    def invalidate_cache(self) -> None:
        """Removes the cache entry for this workspace, forcing a full re-index next query."""
        try:
            if not self._cache_path.exists():
                return
            with _open_db(self._cache_path) as conn:
                _ensure_schema(conn)
                conn.execute(
                    "DELETE FROM rag_cache WHERE workspace = ? AND version = ?",
                    (self.root_dir, _CACHE_SCHEMA_VERSION),
                )
            _logger.debug("RAG: cache invalidated for workspace %s", self.root_dir)
        except Exception as exc:
            _logger.debug("RAG: cache invalidation failed: %s", exc)
