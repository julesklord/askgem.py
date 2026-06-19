"""
In-memory sparse TF-IDF and Cosine Similarity RAG (Retrieval-Augmented Generation) engine for mentask.

Optimized for speed (<15ms index time for medium projects) and zero heavy library dependencies.
Splits workspace source files into semantic chunks and retrieves relevant code context.
"""

import logging
import math
import os
import re
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


class RAGManager:
    """Lightweight in-memory vector retrieval engine utilizing TF-IDF and Cosine Similarity."""

    def __init__(self, root_dir: str | None = None):
        self.root_dir = root_dir or os.getcwd()
        self.chunks: list[dict[str, Any]] = []      # list of dicts: {"path": str, "content": str, "start_line": int, "end_line": int}
        self.idf: dict[str, float] = {}         # term -> idf value
        self.chunk_vectors: list[dict[str, float]] = [] # list of dicts: term -> tf-idf weight (normalized sparse vector)
        self._file_mtimes: dict[str, float] = {}  # maps rel_path -> last modified timestamp

    def _tokenize(self, text: str) -> list[str]:
        """Splits text into lowercase alphanumeric tokens."""
        return re.findall(r"\b\w{2,}\b", text.lower())

    def index_workspace(self) -> None:
        """Scans the workspace directory, chunks files, and computes TF-IDF weights."""
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
                try:
                    if os.path.getsize(filepath) > _MAX_FILE_SIZE:
                        continue

                    mtime = os.path.getmtime(filepath)
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    if not lines:
                        continue

                    rel_path = os.path.relpath(filepath, self.root_dir)
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
                            self.chunks.append({
                                "path": rel_path,
                                "content": content,
                                "start_line": i + 1,
                                "end_line": end,
                            })
                            has_chunks = True
                        if end == len(lines):
                            break
                        i += (chunk_size - overlap)

                    if has_chunks:
                        self._file_mtimes[rel_path] = mtime
                except Exception as e:  # nosec B112
                    _logger.debug(f"Failed to index workspace file {rel_path}: {e}")
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
            vector = {}
            for term, count in tf.items():
                # Normalized TF * IDF
                norm_tf = count / len(tokens)
                vector[term] = norm_tf * self.idf.get(term, 0.0)

            # Pre-calculate Euclidean Norm (length) for cosine similarity normalization
            length = math.sqrt(sum(val ** 2 for val in vector.values()))
            normalized_vector = {term: val / length for term, val in vector.items()} if length > 0 else {}

            self.chunk_vectors.append(normalized_vector)

    def _needs_reindex(self) -> bool:
        """Determines if any workspace files have been modified, added, or removed."""
        if not self._file_mtimes:
            return True

        current_files = {}
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
                except Exception as e:  # nosec B112
                    _logger.debug(f"Failed to check workspace file {filepath}: {e}")
                    continue

        return current_files != self._file_mtimes

    def query(self, query_str: str, top_k: int = 3) -> list[dict]:
        """Finds the most relevant chunks in the workspace for a given query string."""
        if not self.chunks or not self.chunk_vectors or self._needs_reindex():
            # Proactively index/re-index if not done already or if changes are detected
            self.index_workspace()

        query_tokens = self._tokenize(query_str)
        if not query_tokens or not self.chunk_vectors:
            return []

        # Build query TF-IDF vector
        query_tf: dict[str, int] = {}
        for token in query_tokens:
            query_tf[token] = query_tf.get(token, 0) + 1

        query_vector = {}
        for term, count in query_tf.items():
            norm_tf = count / len(query_tokens)
            query_vector[term] = norm_tf * self.idf.get(term, 0.0)

        # Pre-normalize query vector
        query_length = math.sqrt(sum(val ** 2 for val in query_vector.values()))
        if query_length <= 0:
            return []
        query_normalized = {term: val / query_length for term, val in query_vector.items()}

        # Compute Cosine Similarity using dot product of pre-normalized sparse vectors
        scores = []
        for idx, doc_vector in enumerate(self.chunk_vectors):
            if not doc_vector:
                continue
            # Sparse dot product of normalized vectors
            dot_product = sum(query_normalized[term] * doc_vector[term] for term in query_normalized if term in doc_vector)
            if dot_product > 0.05: # Minimum similarity threshold to prevent noise
                scores.append((dot_product, self.chunks[idx]))

        # Sort by similarity score descending
        scores.sort(key=lambda x: x[0], reverse=True)

        # Format and return top K matches
        results = []
        for score, chunk in scores[:top_k]:
            results.append({
                "score": score,
                "path": chunk["path"],
                "content": chunk["content"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
            })
        return results
