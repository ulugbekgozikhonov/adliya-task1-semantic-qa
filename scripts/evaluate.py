"""Qidiruv sifatini o'lchash va hisobotni reports/eval_report.md ga yozish.

To'plamlar:
  holdout      - bazadan: har javobdan 1 ta savol (o'zi qidiruvdan chiqarib tashlanadi)
  real         - data/eval/real_questions.csv: jonli uslubdagi savollar
  real CAPS    - real, KATTA harflarda
  real aralash - real, harflar tasodifan katta yoki kichik
  ood          - data/eval/out_of_scope.csv: bazaga aloqasiz savollar
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
REPORT = Path("reports/eval_report.md")
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


def pct(x: float) -> str:
    return f"{x:.1%}"


def md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Markdown jadval: ustunlar tekislangan (raw ko'rinishda ham o'qiladi), sonlar o'ngda."""
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    numeric = [
        all(cell.rstrip("%").replace(".", "", 1).isdigit() for cell in col)
        for col in zip(*rows, strict=True)
    ]

    def line(cells: list[str]) -> str:
        parts = [
            c.rjust(w) if num else c.ljust(w)
            for c, w, num in zip(cells, widths, numeric, strict=True)
        ]
        return "| " + " | ".join(parts) + " |"

    sep = (
        "| "
        + " | ".join(
            "-" * (w - 1) + ":" if num else "-" * w
            for w, num in zip(widths, numeric, strict=True)
        )
        + " |"
    )
    return [line(headers), sep, *(line(r) for r in rows)]


def main() -> None:
    holdout, holdout_ids = load_holdout()
    real, ood = load_csv("real_questions.csv"), load_csv("out_of_scope.csv")
    caps = [(q.upper(), gold) for q, gold in real]
    rnd = random.Random(1)
    mixed = [
        ("".join(ch.upper() if rnd.random() < 0.5 else ch.lower() for ch in q), gold)
        for q, gold in real
    ]
    sets = [
        ("holdout", holdout, run(holdout, exclude_ids=holdout_ids)),
        ("real", real, run(real)),
        ("real CAPS", caps, run(caps)),
        ("real aralash", mixed, run(mixed)),
    ]
    res_o = run(ood)
    _, _, res_h = sets[0]
    _, _, res_r = sets[1]
    t, m = settings.search_threshold, settings.search_margin

    md: list[str] = [
        "# Qidiruv sifati hisoboti",
        "",
        "`python -m scripts.evaluate` tomonidan yaratilgan.",
        "",
        f"Joriy sozlama: **threshold {t}**, **margin {m}**.",
        "",
        "## 1. Test to'plamlari",
        "",
        *md_table(
            ["To'plam", "Hajmi", "Tavsif"],
            [
                [
                    "holdout",
                    str(len(holdout)),
                    "har javobdan 1 ta savol, o'zi qidiruvdan chiqarilgan",
                ],
                [
                    "real",
                    str(len(real)),
                    "jonli uslubdagi savollar (data/eval/real_questions.csv)",
                ],
                ["real CAPS", str(len(caps)), "real, KATTA harflarda"],
                [
                    "real aralash",
                    str(len(mixed)),
                    "real, harflar tasodifan katta/kichik",
                ],
                [
                    "ood",
                    str(len(ood)),
                    "bazaga aloqasiz savollar (data/eval/out_of_scope.csv)",
                ],
            ],
        ),
        "",
        "## 2. Qidiruv (qarorsiz)",
        "",
        "To'g'ri javob 1-o'rinda (Top-1) yoki eng yaxshi 3 talikda (Top-3).",
        "",
        *md_table(
            ["To'plam", "Top-1", "Top-3"],
            [
                [name, *map(pct, retrieval_metrics(items, res))]
                for name, items, res in sets
            ],
        ),
        "",
        "## 3. Joriy sozlamadagi natija",
        "",
        "- **to'g'ri**: bitta javob berildi va u to'g'ri",
        "- **aniqlashtirish**: bir nechta variant ko'rsatildi, to'g'risi ular orasida",
        "- **xato**: javob berildi, lekin noto'g'ri",
        '- **o\'tkazdi**: "topilmadi" deyildi, aslida javob bor edi',
        "",
    ]
    rows = []
    for name, items, res in sets:
        x = rate(items, res, t, m)
        useful = x.get("correct", 0) + x.get("clarify", 0)
        rows.append(
            [
                name,
                pct(x.get("correct", 0)),
                pct(x.get("clarify", 0)),
                pct(x.get("wrong", 0)),
                pct(x.get("missed", 0)),
                pct(useful),
            ]
        )
    md += md_table(
        ["To'plam", "To'g'ri", "Aniqlashtirish", "Xato", "O'tkazdi", "Foydali jami"],
        rows,
    )
    false_rate = rate(ood, res_o, t, m).get("false_answer", 0)
    md += [
        "",
        (
            f"Bazaga aloqasiz savollarga noto'g'ri javob: **{pct(false_rate)}** "
            f"({round(false_rate * len(ood))} / {len(ood)})."
        ),
        "",
        "## 4. Chegara (threshold) va farq (margin) jadvali",
        "",
        "REAL va HOLDOUT ustunlari: foiz. OOD: begona savollarga noto'g'ri javob.",
        "",
    ]
    grid = []
    for th in THRESHOLDS:
        for mg in MARGINS:
            r, h, oo = (
                rate(real, res_r, th, mg),
                rate(holdout, res_h, th, mg),
                rate(ood, res_o, th, mg),
            )
            mark = "<- joriy" if (th, mg) == (t, m) else ""
            grid.append(
                [
                    f"{th:.2f}",
                    f"{mg:.2f}",
                    pct(r.get("correct", 0)),
                    pct(r.get("clarify", 0)),
                    pct(r.get("wrong", 0)),
                    pct(r.get("missed", 0)),
                    pct(h.get("correct", 0)),
                    pct(oo.get("false_answer", 0)),
                    mark,
                ]
            )
    md += md_table(
        [
            "Threshold",
            "Margin",
            "REAL to'g'ri",
            "REAL aniqlash",
            "REAL xato",
            "REAL o'tkazdi",
            "HOLDOUT to'g'ri",
            "OOD javob",
            "",
        ],
        grid,
    )
    md += ["", "## 5. Xatolar (joriy sozlama, real va ood)", ""]
    labels = {"wrong": "xato", "missed": "o'tkazdi", "false_answer": "begonaga javob"}
    errors = []
    for (q, gold), cands in zip(real + ood, res_r + res_o, strict=True):
        res = outcome(gold, cands, t, m)
        if res in labels:
            top = ", ".join(f"#{x.answer_id} ({x.score:.3f})" for x in cands)
            errors.append(
                [labels[res], q, ", ".join(map(str, sorted(gold))) or "-", top]
            )
    md += (
        md_table(["Natija", "Savol", "Kutilgan", "Topildi (ball)"], errors)
        if errors
        else ["Xato yo'q."]
    )

    text = "\n".join(md) + "\n"
    print(text)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    print(f"Hisobot saqlandi: {REPORT}")


if __name__ == "__main__":
    main()
