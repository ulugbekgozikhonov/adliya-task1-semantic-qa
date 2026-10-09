"""Foydalanuvchi savoliga javob topish: vektor -> Qdrant -> qaror -> PostgreSQL."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Answer, engine
from app.embedder import embed_one


@dataclass
class Match:
    answer_id: int
    score: float
    matched_question: str
    answer: str


@dataclass
class SearchResult:
    status: Literal["found", "ambiguous", "not_found"]
    matches: list[Match]


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def _answer_texts(ids: list[int]) -> dict[int, str]:
    stmt = select(Answer.id, Answer.answer).where(Answer.id.in_(ids), Answer.is_active)
    with Session(engine) as s:
        return {row.id: row.answer for row in s.execute(stmt)}


def search(query: str) -> SearchResult:
    # B1-B2: savol -> vektor -> Qdrant; natija javob (answer_id) bo'yicha guruhlangan
    groups = _client().query_points_groups(
        settings.qdrant_collection,
        query=embed_one(query).tolist(),
        group_by="answer_id",
        limit=3,
        group_size=1,
    ).groups

    # B3: qaror
    if not groups or groups[0].hits[0].score < settings.search_threshold:
        return SearchResult("not_found", [])
    best = groups[0].hits[0].score
    close = [g for g in groups if best - g.hits[0].score < settings.search_margin]

    # B4: javob matnlari PostgreSQL'dan
    texts = _answer_texts([g.id for g in close])
    matches = [
        Match(
            answer_id=g.id,
            score=round(g.hits[0].score, 3),
            matched_question=g.hits[0].payload["question"],
            answer=texts[g.id],
        )
        for g in close
        if g.id in texts
    ]
    if not matches:
        return SearchResult("not_found", [])
    return SearchResult("found" if len(matches) == 1 else "ambiguous", matches)
