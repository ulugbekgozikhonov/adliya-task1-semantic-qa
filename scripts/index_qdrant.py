"""PostgreSQL'dagi savollar -> bge-m3 vektorlari -> Qdrant.

Kolleksiya har safar noldan qayta quriladi (idempotent).
Ishlatish:  python -m scripts.index_qdrant
"""

import argparse
import time

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Answer, Question, engine
from app.embedder import dimension, embed


def load_questions() -> list[dict]:
    stmt = (
        select(
            Question.id,
            Question.question,
            Question.answer_id,
            Answer.category_id,
            Answer.topic_id,
        )
        .join(Answer, Answer.id == Question.answer_id)
        .where(Question.is_active, Answer.is_active)
        .order_by(Question.id)
    )
    with Session(engine) as s:
        return [r._asdict() for r in s.execute(stmt)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Savollarni Qdrant'ga indekslash")
    parser.add_argument("--force", action="store_true", help="kolleksiyani baribir qayta qurish")
    args = parser.parse_args()

    rows = load_questions()
    print(f"PostgreSQL'dan olindi: {len(rows)} ta faol savol")

    client = QdrantClient(url=settings.qdrant_url)
    name = settings.qdrant_collection
    if (
        not args.force
        and client.collection_exists(name)
        and client.count(name).count == len(rows)
    ):
        print(f"'{name}' allaqachon indekslangan, o'tkazib yuborildi (--force bilan qayta quriladi)")
        return

    t = time.time()
    vectors = embed([r["question"] for r in rows], show_progress=True)
    print(f"Vektorga aylantirildi: {vectors.shape}, {time.time() - t:.0f} s")

    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(
        name,
        vectors_config=VectorParams(size=dimension(), distance=Distance.COSINE),
    )
    client.upload_points(
        name,
        points=[
            PointStruct(id=r["id"], vector=v.tolist(), payload=r)
            for r, v in zip(rows, vectors)
        ],
        batch_size=256,
    )
    print(f"Qdrant'ga yozildi: {client.count(name).count} ta nuqta ('{name}' kolleksiyasi)")

if __name__ == "__main__":
    main()
