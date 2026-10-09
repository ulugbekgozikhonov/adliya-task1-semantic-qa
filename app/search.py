"""Foydalanuvchi savoliga javob topish: vektor -> Qdrant -> qaror -> PostgreSQL."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, HasIdCondition
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Answer, engine
from app.embedder import embed_one

Status = Literal["found", "ambiguous", "not_found"]


@dataclass
class Candidate:
    answer_id: int
    score: float
    matched_question: str


@dataclass
class Match:
    answer_id: int
    score: float
    matched_question: str
    answer: str


@dataclass
class SearchResult:
    status: Status
    matches: list[Match]


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def retrieve(vector, limit: int = 3, exclude_ids: list[int] | None = None) -> list[Candidate]:
    """B1-B2: vektorga eng yaqin javoblar (har javobdan eng yaxshi bitta savol)."""
    query_filter = None
    if exclude_ids:
        query_filter = Filter(must_not=[HasIdCondition(has_id=exclude_ids)])
    groups = _client().query_points_groups(
        settings.qdrant_collection,
        query=list(map(float, vector)),
        group_by="answer_id",
        limit=limit,
        group_size=1,
        query_filter=query_filter,
    ).groups
    return [
        Candidate(int(g.id), g.hits[0].score, g.hits[0].payload["question"])
        for g in groups
    ]


def decide(cands: list[Candidate], threshold: float, margin: float) -> tuple[Status, list[Candidate]]:
    """B3: chegara va farq bo'yicha qaror."""
    if not cands or cands[0].score < threshold:
        return "not_found", []
    close = [c for c in cands if cands[0].score - c.score < margin]
    return ("found" if len(close) == 1 else "ambiguous"), close


def _answer_texts(ids: list[int]) -> dict[int, str]:
    stmt = select(Answer.id, Answer.answer).where(Answer.id.in_(ids), Answer.is_active)
    with Session(engine) as s:
        return {row.id: row.answer for row in s.execute(stmt)}


def search(query: str) -> SearchResult:
    _, cands = decide(
        retrieve(embed_one(query)), settings.search_threshold, settings.search_margin
    )
    # B4: javob matnlari PostgreSQL'dan
    texts = _answer_texts([c.answer_id for c in cands]) if cands else {}
    matches = [
        Match(c.answer_id, round(c.score, 3), c.matched_question, texts[c.answer_id])
        for c in cands
        if c.answer_id in texts
    ]
    if not matches:
        return SearchResult("not_found", [])
    return SearchResult("found" if len(matches) == 1 else "ambiguous", matches)
