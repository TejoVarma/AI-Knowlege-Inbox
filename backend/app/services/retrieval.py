import json
from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.models import Chunk, Item
from app.services.embeddings import cosine_similarity, embed_text


@dataclass
class RetrievedChunk:
    chunk: Chunk
    item: Item
    similarity: float


def retrieve_top_chunks(db: Session, question: str, top_k: int | None = None) -> list[RetrievedChunk]:
    # brute force cosine scan - fine at this scale, would move to pgvector/faiss if this grew large
    k = top_k or settings.top_k_chunks

    all_chunks = db.query(Chunk).options(joinedload(Chunk.item)).all()
    if not all_chunks:
        return []

    question_vector = embed_text(question)

    scored = [
        RetrievedChunk(
            chunk=chunk,
            item=chunk.item,
            similarity=cosine_similarity(question_vector, json.loads(chunk.embedding)),
        )
        for chunk in all_chunks
    ]
    scored.sort(key=lambda r: r.similarity, reverse=True)
    relevant = [r for r in scored if r.similarity >= settings.min_similarity]
    return relevant[:k]
