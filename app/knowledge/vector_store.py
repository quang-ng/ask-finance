import asyncio
import json
import os
import logging

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data/knowledge")
EMBEDDING_DIM = 3072
EMBEDDING_MODEL = "gemini-embedding-001"


async def _embed(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    result = await asyncio.to_thread(
        client.models.embed_content,
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return [e.values for e in result.embeddings]


async def init_vector_store(pool) -> None:
    """Create the knowledge_docs table and load documents if empty."""
    async with pool.connection() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id      TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector({EMBEDDING_DIM})
            )
        """)
        result = await conn.execute("SELECT COUNT(*) FROM knowledge_docs")
        row = await result.fetchone()

        if row[0] == 0:
            await _load_documents(conn)

        await conn.commit()
    logger.info("Knowledge base ready (pgvector)")


async def _load_documents(conn) -> None:
    docs = []
    for filename in ["finance_glossary.json", "budget_policy.json"]:
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            with open(path) as f:
                docs.extend(json.load(f))

    if not docs:
        return

    texts = [d["text"] for d in docs]
    embeddings = await _embed(texts)

    for doc, emb in zip(docs, embeddings):
        await conn.execute(
            """
            INSERT INTO knowledge_docs (id, content, embedding)
            VALUES (%s, %s, %s::vector)
            ON CONFLICT (id) DO NOTHING
            """,
            (doc["id"], doc["text"], str(emb)),
        )

    logger.info(f"Loaded {len(docs)} documents into pgvector")


async def search_knowledge(query: str, n_results: int = 3) -> str:
    from app.db import get_pool

    query_emb = await _embed([query], task_type="RETRIEVAL_QUERY")
    pool = get_pool()
    query_vec = str(query_emb[0])

    async with pool.connection() as conn:
        result = await conn.execute(
            """
            SELECT content
            FROM knowledge_docs
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_vec, n_results),
        )
        rows = await result.fetchall()

    if not rows:
        return "No relevant information found in the knowledge base."
    return "\n\n".join(row[0] for row in rows)
