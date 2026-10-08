"""CSV/Excel -> PostgreSQL.

Qayta ishga tushirilsa, eski ma'lumot o'chiriladi va fayldan qaytadan yoziladi.
Ishlatish:  python -m scripts.load_db
"""

import re
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.db import Answer, Base, Question, engine

DATA = Path("data")


def read_table(name: str) -> pd.DataFrame:
    """data/ ichidan .xlsx yoki .csv faylni o'qiydi (qaysi biri bo'lsa)."""
    for ext in (".xlsx", ".csv"):
        path = DATA / f"{name}{ext}"
        if path.exists():
            if ext == ".xlsx":
                return pd.read_excel(path)
            return pd.read_csv(path)
    raise FileNotFoundError(f"data/{name}.xlsx yoki data/{name}.csv topilmadi")


def to_bool(col: pd.Series, true_value: str) -> pd.Series:
    return col.astype(str).str.strip().str.lower().eq(true_value)


# Lotin so'z ichiga yashirinib qolgan kirill harfi (masalan "egа" — oxiridagi "а" kirill)
MIXED = re.compile(r"\b(?=\w*[a-zA-Z])(?=\w*[а-яА-ЯёЁ])\w+\b")


def quality_report(ans: pd.DataFrame, qs: pd.DataFrame) -> None:
    ans_ids = set(ans["id"])
    orphans = qs[~qs["answer_id"].isin(ans_ids)]
    no_questions = ans_ids - set(qs["answer_id"])
    dup = qs["question"].str.strip().str.lower().duplicated().sum()
    mixed = [(row.id, m) for row in ans.itertuples() for m in MIXED.findall(row.answer)]
    print(f"Javoblar: {len(ans)}, savollar: {len(qs)}")
    print(f"Javobi yo'q savollar: {len(orphans)}")
    print(f"Savoli yo'q javoblar: {len(no_questions)}")
    print(f"Takroriy savollar: {dup}")
    print(f"Lotin/kirill aralash so'zlar: {mixed or 'yo`q'}")
    print(
        "Savollar soni (javob boshiga):",
        qs.groupby("answer_id").size().value_counts().sort_index().to_dict(),
    )


def main() -> None:
    ans = read_table("answers")
    qs = read_table("questions")
    quality_report(ans, qs)

    answers = [
        {
            "id": int(r.id),
            "category_id": int(r.category_id),
            "topic_id": int(r.topic_id),
            "answer": str(r.answer).strip(),
            "is_active": active,
        }
        for r, active in zip(ans.itertuples(), to_bool(ans["status"], "active"))
    ]
    questions = [
        {
            "id": int(r.id),
            "answer_id": int(r.answer_id),
            "question": str(r.question).strip(),
            "is_active": active,
        }
        for r, active in zip(qs.itertuples(), to_bool(qs["is_active"], "true"))
    ]

    Base.metadata.create_all(engine)
    with Session(engine) as s, s.begin():
        s.execute(delete(Question))
        s.execute(delete(Answer))
        s.execute(insert(Answer), answers)
        s.execute(insert(Question), questions)
    print(f"\nPostgreSQL'ga yozildi: {len(answers)} javob, {len(questions)} savol")


if __name__ == "__main__":
    main()
