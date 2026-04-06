"""
Memory-efficient RAG engine using sqlite-vec.
Optimized for Raspberry Pi 3 with lazy embedding generation.
"""
import json
import logging
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval-Augmented Generation engine with sqlite-vec.

    Memory optimizations:
    - Embeddings generated on-demand (not cached in memory)
    - Batch operations minimized
    - Lazy sqlite-vec loading
    """

    # Embedding model dimensions
    EMBEDDING_DIM = 384  # all-MiniLM-L6-v2

    def __init__(self, db=None):
        self._db = db
        self._vec_available = None

    def _check_vec_available(self, conn: sqlite3.Connection) -> bool:
        """Check if sqlite-vec is available."""
        if self._vec_available is not None:
            return self._vec_available

        try:
            conn.enable_load_extension(True)
            conn.execute("SELECT load_extension('sqlite_vec')")
            conn.enable_load_extension(False)
            self._vec_available = True
            logger.info("sqlite-vec loaded successfully")
        except sqlite3.OperationalError as e:
            logger.warning(f"sqlite-vec not available: {e}")
            self._vec_available = False

        return self._vec_available

    def _get_embedding(self, text: str) -> Optional[bytes]:
        """
        Generate embedding for text.
        Uses local model to avoid API calls (memory/speed optimization).
        """
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tobytes()
        except ImportError:
            logger.warning("sentence-transformers not installed, skipping embeddings")
            return None
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def save_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
    ) -> str:
        """Save conversation turn with optional embedding."""
        conv_id = str(uuid.uuid4())

        if self._db is None:
            logger.warning("No database available for RAG")
            return conv_id

        with self._db.transaction() as conn:
            # Check sqlite-vec availability
            vec_available = self._check_vec_available(conn)

            # Generate embedding (optional, non-blocking)
            embedding = None
            if vec_available:
                embedding = self._get_embedding(content)

            # Insert conversation
            conn.execute("""
                INSERT INTO conversations (id, user_id, role, content, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (conv_id, user_id, role, content, embedding))

        return conv_id

    async def save_conversation_async(
        self,
        user_id: str,
        role: str,
        content: str,
    ) -> str:
        """Async version - saves conversation without blocking."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.save_conversation,
            user_id, role, content
        )

    def search(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search conversations using semantic similarity.
        Falls back to keyword search if sqlite-vec unavailable.
        """
        if self._db is None:
            logger.warning("No database available for RAG")
            return []

        results = []

        with self._db.connection() as conn:
            vec_available = self._check_vec_available(conn)

            if vec_available:
                # Semantic search with sqlite-vec
                query_embedding = self._get_embedding(query)
                if query_embedding:
                    try:
                        # sqlite-vec cosine similarity
                        cursor = conn.execute("""
                            SELECT id, user_id, role, content, created_at,
                                   vec_distance_cosine(embedding, ?) as similarity
                            FROM conversations
                            WHERE user_id = ?
                            ORDER BY similarity ASC
                            LIMIT ?
                        """, (query_embedding, user_id, limit))
                        results = [
                            {
                                "id": row["id"],
                                "role": row["role"],
                                "content": row["content"],
                                "similarity": 1 - row["similarity"],  # Convert distance to similarity
                            }
                            for row in cursor.fetchall()
                        ]
                    except sqlite3.OperationalError as e:
                        logger.error(f"Semantic search failed: {e}")
                        vec_available = False

            if not vec_available:
                # Fallback to keyword search
                cursor = conn.execute("""
                    SELECT id, user_id, role, content, created_at
                    FROM conversations
                    WHERE user_id = ? AND content LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, f"%{query}%", limit))
                results = [
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "content": row["content"],
                        "match_type": "keyword",
                    }
                    for row in cursor.fetchall()
                ]

        return results

    def get_user_context(
        self,
        user_id: str,
        max_turns: int = 10,
    ) -> str:
        """
        Get recent conversation context for a user.
        Used to provide conversation history to LLM without full memory.
        """
        if self._db is None:
            return ""

        with self._db.connection() as conn:
            cursor = conn.execute("""
                SELECT role, content FROM conversations
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, max_turns * 2))  # 2 turns = user + assistant

            turns = list(cursor.fetchall())
            turns.reverse()  # Chronological order

        if not turns:
            return ""

        context_lines = []
        for turn in turns:
            context_lines.append(f"{turn['role']}: {turn['content']}")

        return "\n".join(context_lines)
