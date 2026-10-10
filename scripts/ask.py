"""Qidiruvni terminaldan sinash.

Ishlatish:  python -m scripts.ask "Oyligimdan qancha soliq ketadi?"
"""

import sys

from app.search import search


def main() -> None:
    result = search(" ".join(sys.argv[1:]))
    print(f"Holat: {result.status}")
    for m in result.matches:
        print(
            f"\n{m.score:.3f}  #{m.answer_id}  (o'xshash savol: {m.matched_question})"
        )
        print(f"  {m.answer}")


if __name__ == "__main__":
    main()
