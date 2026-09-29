import os
from enum import StrEnum

import psycopg2
from psycopg2.extras import RealDictCursor

from t5_rag_advanced.embeddings.embeddings_client import EmbeddingsClient
from t5_rag_advanced.utils.text import chunk_text


class SearchMode(StrEnum):
    EUCLIDIAN_DISTANCE = "euclidean"  # Euclidean distance (<->)
    COSINE_DISTANCE = "cosine"  # Cosine distance (<=>)


class TextProcessor:
    """Processor for text documents that handles chunking, embedding, storing, and retrieval"""

    def __init__(self, embeddings_client: EmbeddingsClient, db_config: dict):
        self.embeddings_client = embeddings_client
        self.db_config = db_config

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )

    def process_text_file(
            self, file_path: str,
            chunk_size: int,
            overlap: int,
            dimensions: int,
            truncate: bool = True
    ) -> None:
        """Load a text file, split it into overlapping chunks and store their embeddings in the DB"""
        if truncate:
            self._truncate_table()

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_text(content, chunk_size, overlap)
        embeddings = self.embeddings_client.get_embeddings(chunks, dimensions=dimensions)

        document_name = os.path.basename(file_path)
        for index, chunk in enumerate(chunks):
            self._save_chunk(document_name, chunk, embeddings[index])

    def _truncate_table(self) -> None:
        """Remove all previously stored chunks/embeddings"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE vectors RESTART IDENTITY")
            conn.commit()

    def _save_chunk(self, document_name: str, text: str, embedding: list[float]) -> None:
        """Store a single text chunk with its embedding in the DB"""
        embedding_str = str(embedding)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO vectors (document_name, text, embedding)
                    VALUES (%s, %s, %s::vector)
                    """,
                    (document_name, text, embedding_str)
                )
            conn.commit()

    def search(
            self, mode: SearchMode,
            request: str,
            top_k: int,
            min_score: float,
            dimensions: int
    ) -> list[str]:
        """Find the most relevant stored chunks for the given user request"""
        query_embedding = self.embeddings_client.get_embeddings(request, dimensions=dimensions)[0]
        embedding_str = str(query_embedding)

        operator = "<->" if mode == SearchMode.EUCLIDIAN_DISTANCE else "<=>"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT text, embedding {operator} %s::vector AS distance
                    FROM vectors
                    WHERE embedding {operator} %s::vector <= %s
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (embedding_str, embedding_str, min_score, top_k)
                )
                rows = cur.fetchall()

        return [row["text"] for row in rows]


# SELECT text, embedding <->  '[0.23, -0.45, 0.67, ..., 0.12]'::vector AS distance
# FROM vectors
# WHERE embedding <->  '[0.23, -0.45, 0.67, ..., 0.12]'::vector <= {score}
# ORDER BY distance
# LIMIT {top_k};
