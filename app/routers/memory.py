from fastapi import APIRouter, Query
from ..qdrant_store import search_memory

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/search")
async def memory_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, le=20),
):
    results = await search_memory(q, limit)
    return {"query": q, "results": results, "count": len(results)}
