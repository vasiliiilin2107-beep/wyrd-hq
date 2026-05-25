import os
import json
import logging
import asyncio
from typing import Optional

QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
COLLECTION = "wyrd_events"
VECTOR_SIZE = 384  # BAAI/bge-small-en-v1.5

log = logging.getLogger(__name__)
_client = None
_embedder = None


def _load_embedder():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def _embed_sync(text: str, embedder) -> list:
    return list(embedder.embed([text]))[0].tolist()


async def init_qdrant() -> None:
    global _client, _embedder
    try:
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, VectorParams

        _client = AsyncQdrantClient(url=QDRANT_URL)
        collections = await _client.get_collections()
        names = [c.name for c in collections.collections]
        if COLLECTION not in names:
            await _client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            log.info(f"[Qdrant] created collection {COLLECTION}")

        loop = asyncio.get_running_loop()
        _embedder = await loop.run_in_executor(None, _load_embedder)
        log.info(f"[Qdrant] ready: {QDRANT_URL}")
    except Exception as e:
        log.warning(f"[Qdrant] init failed (memory disabled): {e}")
        _client = None
        _embedder = None


async def close_qdrant() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None


async def embed_and_store(event_id: int, branch: str, event_type: str, payload: dict | None) -> None:
    if _client is None or _embedder is None:
        return
    try:
        from qdrant_client.models import PointStruct

        text = f"{branch} {event_type}"
        if payload:
            text += " " + json.dumps(payload, ensure_ascii=False)[:500]

        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, _embed_sync, text, _embedder)

        await _client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(
                id=event_id,
                vector=vector,
                payload={"branch": branch, "type": event_type, "payload": payload},
            )],
        )
    except Exception as e:
        log.warning(f"[Qdrant] store error: {e}")


async def search_memory(query: str, limit: int = 5) -> list[dict]:
    if _client is None or _embedder is None:
        return []
    try:
        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, _embed_sync, query, _embedder)

        results = await _client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=limit,
        )
        return [{"score": round(r.score, 3), **r.payload} for r in results]
    except Exception as e:
        log.warning(f"[Qdrant] search error: {e}")
        return []
