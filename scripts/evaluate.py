"""Qidiruv sifatini o'lchash.

Uch to'plam:
  holdout - bazadan: har javobdan 1 ta savol (o'zi qidiruvdan chiqarib tashlanadi)
  real    - data/eval/real_questions.csv: jonli uslubdagi savollar
  ood     - data/eval/out_of_scope.csv: bazaga aloqasiz savollar
Ishlatish:  python -m scripts.evaluate
"""

import csv
import random
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Question, engine
from app.search import Candidate, decide, retrieve_robust

EVAL = Path("data/eval")
REPORT = Path("reports/eval_results.txt")
THRESHOLDS = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
MARGINS = [0.0, 0.03, 0.06, 0.10]

Item = tuple[str, set[int]]  # (savol, to'g'ri javoblar; bo'sh = mavzudan tashqari)


def load_holdout(seed: int = 42) -> tuple[list[Item], list[int]]:
    with Session(engine) as s:
        rows = s.execute(
            select(Question.id, Question.answer_id, Question.question)
        ).all()
    by_answer = defaultdict(list)
    for r in rows:
        by_answer[r.answer_id].append(r)
    rnd = random.Random(seed)
    picked = [rnd.choice(qs) for _, qs in sorted(by_answer.items())]
    return [(r.question, {r.answer_id}) for r in picked], [r.id for r in picked]


def load_csv(name: str) -> list[Item]:
    with open(EVAL / name, encoding="utf-8") as f:
        return [
            (
                row["question"],
                {int(i) for i in row.get("answer_ids", "").split(";") if i},
            )
            for row in csv.DictReader(f)
        ]


def run(
    items: list[Item], exclude_ids: list[int] | None = None
) -> list[list[Candidate]]:
    return [retrieve_robust(q, exclude_ids=exclude_ids) for q, _ in items]


def outcome(
    gold: set[int], cands: list[Candidate], threshold: float, margin: float
) -> str:
    status, chosen = decide(cands, threshold, margin)
    if not gold:
        return "rejected" if status == "not_found" else "false_answer"
    if status == "not_found":
        return "missed"
    hit = any(c.answer_id in gold for c in chosen)
    if status == "found":
        return "correct" if hit else "wrong"
    return "clarify" if hit else "wrong"


def rate(
    items: list[Item], results: list[list[Candidate]], threshold: float, margin: float
) -> dict[str, float]:
    counts = defaultdict(int)
    for (_, gold), cands in zip(items, results):
        counts[outcome(gold, cands, threshold, margin)] += 1
    return {k: v / len(items) for k, v in counts.items()}


def retrieval_metrics(
    items: list[Item], results: list[list[Candidate]]
) -> tuple[float, float]:
    top1 = sum(bool(c) and c[0].answer_id in g for (_, g), c in zip(items, results))
    top3 = sum(any(x.answer_id in g for x in c) for (_, g), c in zip(items, results))
    return top1 / len(items), top3 / len(items)


def main() -> None:
    lines: list[str] = []

    def out(text: str = "") -> None:
        print(text)
        lines.append(text)

    holdout, holdout_ids = load_holdout()
    real, ood = load_csv("real_questions.csv"), load_csv("out_of_scope.csv")
    caps = [(q.upper(), gold) for q, gold in real]
    rnd = random.Random(1)
    mixed = [
        ("".join(ch.upper() if rnd.random() < 0.5 else ch.lower() for ch in q), gold)
        for q, gold in real
    ]
    out(
        f"To'plamlar: holdout={len(holdout)}, real={len(real)}, real CAPS={len(caps)}, "
        f"real aralash={len(mixed)}, ood={len(ood)}"
    )

    res_h = run(holdout, exclude_ids=holdout_ids)
    res_r = run(real)
    res_c = run(caps)
    res_m = run(mixed)
    res_o = run(ood)

    out("\n=== 1. QIDIRUV (qarorsiz): to'g'ri javob nechanchi o'rinda ===")
    for name, items, res in (
        ("holdout", holdout, res_h),
        ("real", real, res_r),
        ("real CAPS", caps, res_c),
        ("real aralash", mixed, res_m),
    ):
        t1, t3 = retrieval_metrics(items, res)
        out(f"  {name:12} Top-1: {t1:6.1%}   Top-3: {t3:6.1%}")

    out("\n=== 2. QAROR: chegara (threshold) va farq (margin) bo'yicha ===")
    out(
        "  thr   margin | REAL: to'g'ri aniqlash xato  o'tkazdi | HOLDOUT: to'g'ri xato | OOD: noto'g'ri javob"
    )
    for t in THRESHOLDS:
        for m in MARGINS:
            r, h, o = (
                rate(real, res_r, t, m),
                rate(holdout, res_h, t, m),
                rate(ood, res_o, t, m),
            )
            mark = (
                "  <- hozirgi"
                if (t, m) == (settings.search_threshold, settings.search_margin)
                else ""
            )
            out(
                f"  {t:.2f}  {m:.2f}   |  {r.get('correct', 0):6.1%} {r.get('clarify', 0):6.1%}"
                f" {r.get('wrong', 0):6.1%} {r.get('missed', 0):6.1%}  |"
                f"  {h.get('correct', 0):6.1%} {h.get('wrong', 0):6.1%}  |"
                f"  {o.get('false_answer', 0):6.1%}{mark}"
            )

    t, m = settings.search_threshold, settings.search_margin
    out(f"\n  Katta-kichik harf aralash yozuv (thr={t}, margin={m}):")
    for name, items, res in (
        ("real CAPS", caps, res_c),
        ("real aralash", mixed, res_m),
    ):
        x = rate(items, res, t, m)
        out(
            f"  {name:12} to'g'ri {x.get('correct', 0):.1%}, aniqlash {x.get('clarify', 0):.1%}, "
            f"xato {x.get('wrong', 0):.1%}, o'tkazdi {x.get('missed', 0):.1%}"
        )

    out(f"\n=== 3. XATOLAR (real va ood, hozirgi sozlama: thr={t}, margin={m}) ===")
    for (q, gold), cands in zip(real + ood, res_r + res_o):
        res = outcome(gold, cands, t, m)
        if res in ("correct", "clarify", "rejected"):
            continue
        top = ", ".join(f"#{x.answer_id}={x.score:.3f}" for x in cands)
        out(f"  [{res}] {q}  | kutilgan: {sorted(gold) or '-'} | topildi: {top}")

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nHisobot saqlandi: {REPORT}")


if __name__ == "__main__":
    main()
