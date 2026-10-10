"""Matnni qidiruvdan oldin bir xil ko'rinishga keltirish.

Bir xil funksiya IKKI joyda ishlatiladi: bazadagi savollarni indekslashda va
foydalanuvchi savolini qidirishda. Aks holda ikki tomon har xil ko'rinishda bo'lib qoladi.
"""

import re

APOSTROPHES = str.maketrans({c: "'" for c in "ʻʼ‘’`´"})

# O'zbek kirill -> lotin (rasmiy alifbo asosida, soddalashtirilgan)
CYR2LAT = {
    "ў": "o'",
    "қ": "q",
    "ғ": "g'",
    "ҳ": "h",
    "ё": "yo",
    "ю": "yu",
    "я": "ya",
    "ш": "sh",
    "ч": "ch",
    "щ": "sh",
    "ц": "ts",
    "ж": "j",
    "й": "y",
    "ъ": "'",
    "ь": "",
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "з": "z",
    "и": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "x",
    "э": "e",
    "ы": "i",
}


def cyr_to_lat(text: str) -> str:
    # So'z boshidagi "е" lotinda "ye" bo'ladi: "ер" -> "yer"
    text = re.sub(r"\bе", "ye", text)
    text = re.sub(r"\bЕ", "Ye", text)
    out = []
    for ch in text:
        low = ch.lower()
        if low in CYR2LAT:
            lat = CYR2LAT[low]
            out.append(lat.capitalize() if ch != low else lat)
        else:
            out.append(ch)
    return "".join(out)


def normalize(text: str) -> str:
    text = cyr_to_lat(text)
    text = text.translate(APOSTROPHES)
    return re.sub(r"\s+", " ", text).strip()
