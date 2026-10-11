# Semantik savol-javob tizimi

Foydalanuvchi savolni o'z so'zlari bilan yozadi, tizim esa 505 ta tayyor javobdan ma'no
jihatidan eng mosini topadi. Mos javob bo'lmasa, buni ochiq aytadi.

Hammasi lokal ishlaydi: tashqi AI xizmatlariga hech qanday so'rov yuborilmaydi.

| Qism            | Texnologiya         |
| --------------- | ------------------- |
| Embedding       | bge-m3 (lokal, CPU) |
| Vektor baza     | Qdrant              |
| Asosiy baza     | PostgreSQL          |
| API             | FastAPI             |
| Telegram bot    | aiogram 3           |
| Ishga tushirish | Docker Compose      |

**Asosiy natija** (jonli uslubdagi 44 ta test savoli): **86.4%** savolda foydalanuvchi
to'g'ri javobni oladi, **0%** savol o'tkazib yuboriladi, bazaga aloqasiz savollarning
**3.3%** iga noto'g'ri javob beriladi. Batafsil: [Sifatni tekshirish](#sifatni-tekshirish).

---

## Mundarija

1. [Tezkor ishga tushirish](#tezkor-ishga-tushirish)
2. [Qanday ishlaydi](#qanday-ishlaydi)
3. [Texnik qarorlar](#texnik-qarorlar)
4. [Ma'lumot sifati](#malumot-sifati)
5. [Sifatni tekshirish](#sifatni-tekshirish)
6. [Cheklovlar va keyingi qadamlar](#cheklovlar-va-keyingi-qadamlar)
7. [API](#api)
8. [Docker'siz ishga tushirish](#dockersiz-ishga-tushirish)
9. [Loyiha tuzilmasi](#loyiha-tuzilmasi)

---

## Tezkor ishga tushirish

Talablar: Docker Desktop (yoki Docker + Compose v2), ~6 GB bo'sh joy.

**1. Sozlamalar faylini yarating:**

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

`.env` ichida `BOT_TOKEN` ga @BotFather bergan tokenni yozing.

**2. Ishga tushiring:**

```bash
docker compose up -d --build
```

Birinchi marta bge-m3 modeli (~2.2 GB) `~/.cache/huggingface` papkasiga yuklab olinadi va
3048 ta savol indekslanadi (~5 daqiqa, CPU). Shundan keyin `.env` da `HF_OFFLINE=true`
qilish mumkin: tizim internetsiz ishlaydi.

**3. Foydalaning:**

| Nima          | Qayerda                         |
| ------------- | ------------------------------- |
| API hujjati   | http://localhost:8000/docs      |
| Qdrant paneli | http://localhost:6333/dashboard |
| Telegram bot  | botingizga savol yozing         |
| Holat         | `docker compose ps`             |
| Loglar        | `docker compose logs -f api`    |

> `BOT_TOKEN` ko'rsatilmasa, bot konteyneri ishga tusha olmaydi va qayta-qayta urinadi.
> API baribir ishlaydi.

---

## Qanday ishlaydi

```
TAYYORLASH  (init xizmati, bir marta)

  data/*.csv yoki *.xlsx
        │
        ▼
  PostgreSQL ─────────────►  normalize ──► bge-m3 ──► Qdrant
  (asl savol va javoblar)                             (3048 vektor + answer_id)


JAVOB BERISH  (har bir savolda)

  Telegram bot ──► API  POST /ask
                          │
                          ▼
                normalize ──► bge-m3 ──► Qdrant: eng yaqin 3 ta javob
                (asl matn va kichik harfli variant, har javob uchun eng yaxshi ball)
                          │
                          ▼
                Qaror:  found  |  ambiguous  |  not_found
                          │
                          ▼
                PostgreSQL'dan javob matni ──► foydalanuvchiga
```

| Xizmat     | Vazifasi                                                       |
| ---------- | -------------------------------------------------------------- |
| `postgres` | Haqiqat manbai: savollar va javoblarning asl matni             |
| `qdrant`   | Savollar vektorlari va ular bo'yicha qidiruv                   |
| `init`     | CSV/Excel → PostgreSQL → Qdrant. Indeks bo'lsa, qayta qurmaydi |
| `api`      | FastAPI: `/ask`, `/answers/{id}`, `/health`                    |
| `bot`      | Telegram bot. API orqali ishlaydi, modelni o'zi yuklamaydi     |

**Uch xil javob:**

| Holat       | Qachon                                | Bot nima qiladi                     |
| ----------- | ------------------------------------- | ----------------------------------- |
| `found`     | Bitta javob aniq yetakchi             | Javobni yuboradi                    |
| `ambiguous` | Bir nechta javobning balli juda yaqin | "Qaysi biri?" tugmalarini chiqaradi |
| `not_found` | Eng yaxshi ball ham chegaradan past   | "Ma'lumot topilmadi" deydi          |

---

## Texnik qarorlar

### 1. Javoblar emas, savollar indekslanadi

Ko'p javob matnlarida mavzu umuman tilga olinmagan. Masalan, *"ID-karta necha kunda
tayyor bo'ladi?"* savolining javobi: *"Hujjatlar to'liq qabul qilingandan so'ng, odatda
1 ish kuni ichida rasmiylashtirilib beriladi"*. Unda "ID-karta" so'zi yo'q.

Foydalanuvchi savoli bazadagi **savolga** ko'proq o'xshaydi (savol ↔ savol), javob matniga
emas. Shuning uchun Qdrant'ga savollar yoziladi, javob esa `answer_id` orqali olinadi.

### 2. Natija javob bo'yicha guruhlanadi

Har bir javobda 6 tadan savol bor. Guruhlashsiz eng yaxshi 3 ta natija ko'pincha bitta
javobning savollari bilan to'lib qoladi va "1- va 2-o'rin orasidagi farq"ni o'lchab
bo'lmaydi. Qdrant'ning `query_points_groups(group_by="answer_id")` funksiyasi har bir
javobdan eng yaxshi bitta savolni qaytaradi.

### 3. Qaror chegarasi va farqi

- **`SEARCH_THRESHOLD = 0.65`**: eng yaxshi ball shundan past bo'lsa → `not_found`.
- **`SEARCH_MARGIN = 0.06`**: 1- va 2-o'rin farqi shundan kichik bo'lsa → `ambiguous`.

Ikkala qiymat ham taxmin bilan emas, eval natijasida tanlangan
([Chegarani tanlash](#chegarani-tanlash)).

### 4. Matnni normallashtirish

`app/text.py`: kirill → lotin, apostroflarni bir xillashtirish (`ʻ ʼ ‘ ’` → `'`),
ortiqcha bo'sh joylarni olib tashlash. **Bir xil funksiya** indekslashda ham, qidiruvda
ham ishlatiladi.

| Savol                              | Bazadagi savolga o'xshashlik |
| ---------------------------------- | ---------------------------: |
| `ид карта неча кунда тайёр бўлади` |                        0.737 |
| normallashtirilgandan keyin        |                        0.956 |

### 5. Katta-kichik harfga chidamlilik

CAPS LOCK yoki aralash yozilgan savollar (`MAOSHIMDAN QANCHA SOLIQ...`, `iD-kArTa NeChA...`)
avval deyarli ishlamas edi. Endi qidiruv **ikki variant** bilan bajariladi: asl matn va
kichik harfli matn. Har bir javob uchun ikkisidan eng yaxshi ball olinadi
(`retrieve_robust`, `app/search.py`).

To'rt xil yondashuv o'lchab ko'rildi (foydali javoblar ulushi, chegara 0.65):

| Yondashuv                                   |     Oddiy |      CAPS |   Aralash |
| ------------------------------------------- | --------: | --------: | --------: |
| O'zgarishsiz                                |     84.1% |      9.1% |      4.5% |
| Faqat asosan CAPS matnni kichik harfga      |     84.1% |     72.7% |      4.5% |
| Har doim kichik harfga                      |     72.7% |     72.7% |     72.7% |
| **Ikki variant bilan qidirish (tanlangan)** | **86.4%** | **75.0%** | **72.7%** |

Har doim kichik harfga o'tkazish oddiy savollarni yomonlashtiradi: model "ID-karta",
"YaTT", "STIR" kabi qisqartmalardagi katta harflardan foydalanadi. Ikki variantli qidiruv
ikkalasining afzalligini oladi. Ikkala variant bitta chaqiruvda vektorga aylantiriladi,
shuning uchun javob vaqti deyarli oshmaydi.

### 6. To'liq oflayn ishlash

`HF_OFFLINE=true` bo'lsa, `HF_HUB_OFFLINE=1` o'rnatiladi: model faqat diskdan o'qiladi,
Hugging Face serverlariga hech qanday so'rov yuborilmaydi.

### 7. Model bir marta yuklanadi

`lru_cache` va FastAPI `lifespan` tufayli model server ishga tushganda bir marta yuklanadi.
`/ask` oddiy `def` bilan yozilgan: embedding CPU'ni band qiladi, shuning uchun FastAPI uni
alohida oqimda (threadpool) bajaradi va boshqa so'rovlar kutib qolmaydi.

---

## Ma'lumot sifati

Yuklashda avtomatik sifat hisoboti chiqariladi (`scripts/load_db.py`):

| Tekshiruv                                 | Natija                                            |
| ----------------------------------------- | ------------------------------------------------- |
| Javoblar / savollar                       | 505 / 3048                                        |
| Javobi yo'q savollar                      | 0                                                 |
| Savoli yo'q javoblar                      | 0                                                 |
| Takroriy savollar                         | 0                                                 |
| Lotin so'z ichidagi yashirin kirill harfi | 1 ta: javob #499, `egа` (normalizatsiya tuzatadi) |
| Javob boshiga savollar                    | 502 ta javobda 6 tadan, 3 tasida 12 tadan         |

**Kuzatuv:** savollar shablon asosida yaratilgan (*"... haqida ma'lumot bering"* 415 marta,
*"... bo'yicha ma'lumot kerak"* 349 marta). Shuning uchun faqat bazadagi savollar bilan
o'tkazilgan test natijani sun'iy ravishda yuqori ko'rsatadi (pastda).

---

## Sifatni tekshirish

```bash
python -m scripts.evaluate
```

To'liq hisobot: **[reports/eval_report.md](reports/eval_report.md)**. Eval ishlab
chiqarishdagi qidiruv bilan aynan bir xil funksiyadan (`retrieve_robust`) foydalanadi.

### Test to'plamlari

| To'plam      | Hajmi | Tavsif                                                             |
| ------------ | ----: | ------------------------------------------------------------------ |
| holdout      |   505 | Har javobdan 1 ta savol; qidiruvda o'zi chiqarib tashlanadi        |
| real         |    44 | Jonli uslubda qo'lda yozilgan, to'g'ri javobi belgilangan savollar |
| real CAPS    |    44 | `real` to'plami KATTA harflarda                                    |
| real aralash |    44 | `real` to'plamida harflar tasodifan katta yoki kichik              |
| ood          |    30 | Bazaga aloqasiz savollar (ob-havo, osh, futbol va yaqin mavzular)  |

`real` to'plamida odamlar haqiqatda ishlatadigan so'zlar bor: "prava", "propiska",
"svet puli", "zagran"; 3 ta savol kirillda. Fayllar: `data/eval/real_questions.csv`,
`data/eval/out_of_scope.csv`.

### Qidiruv sifati (qarorsiz)

To'g'ri javob 1-o'rinda (Top-1) yoki eng yaxshi 3 talikda (Top-3):

| To'plam      |  Top-1 |  Top-3 |
| ------------ | -----: | -----: |
| holdout      | 100.0% | 100.0% |
| **real**     |  65.9% |  86.4% |
| real CAPS    |  61.4% |  79.5% |
| real aralash |  61.4% |  79.5% |

Holdout'dagi 100% bazadagi savollar shablon bo'yicha yozilgani bilan izohlanadi.
**Haqiqiy ko'rsatkich — jonli savollardagi natija.**

### Joriy sozlamadagi natija (threshold 0.65, margin 0.06)

| To'plam      | To'g'ri | Aniqlashtirish |  Xato | O'tkazdi | Foydali jami |
| ------------ | ------: | -------------: | ----: | -------: | -----------: |
| holdout      |   96.4% |           3.6% |  0.0% |     0.0% |       100.0% |
| **real**     |   45.5% |          40.9% | 13.6% |     0.0% |    **86.4%** |
| real CAPS    |   43.2% |          31.8% | 22.7% |     2.3% |        75.0% |
| real aralash |   40.9% |          31.8% | 22.7% |     4.5% |        72.7% |

- **To'g'ri** — bitta javob berildi va u to'g'ri.
- **Aniqlashtirish** — bir nechta variant ko'rsatildi, to'g'risi ular orasida.
- **Xato** — javob berildi, lekin noto'g'ri.
- **O'tkazdi** — "topilmadi" deyildi, aslida javob bor edi.

Bazaga aloqasiz savollarga noto'g'ri javob: **3.3%** (30 tadan 1 tasi).

### Chegarani tanlash

24 ta kombinatsiya sinab ko'rildi (to'liq jadval hisobotda). Asosiy murosa:

| Sozlama         |   Foydali |  Xato | O'tkazdi | Begonaga javob |
| --------------- | --------: | ----: | -------: | -------------: |
| 0.70 / 0.06     |     70.5% | 13.6% |    15.9% |           0.0% |
| **0.65 / 0.06** | **86.4%** | 13.6% | **0.0%** |           3.3% |
| 0.60 / 0.06     |     86.4% | 13.6% |     0.0% |          30.0% |

- **0.65 vs 0.70:** o'tkazib yuborilgan savollar 15.9% dan 0% ga tushadi. Narxi —
  begona savolga bitta zararsiz javob ("Taksi chaqirib ber" → tez yordam chaqirish).
- **0.65 vs 0.60:** jonli savollarda natija bir xil, lekin 0.60 begona savollarning 30%
  iga javob qaytaradi.
- **Margin 0.06:** 0.03 da xatolar 13.6% dan 22.7% ga oshadi; 0.10 xatolarni
  kamaytirmaydi, faqat aniqlashtirishni ko'paytiradi.

Begona savollarning eng yuqori balli (0.673) va to'g'ri javobi 1-o'rinda turgan jonli
savollarning eng past ballari bir zonaga tushadi. Ya'ni bitta embedding balli bilan ularni
mukammal ajratib bo'lmaydi.

### Xatolar tahlili

Joriy sozlamadagi barcha xatolar:

| Savol                                                       | Nima topildi                | Sabab                                       |
| ----------------------------------------------------------- | --------------------------- | ------------------------------------------- |
| Oylik bermayapti, kimga **shikoyat** qilaman?               | Rad etilsa qayerga shikoyat | Bitta so'z butun ma'noni bosib ketdi        |
| Notariusda **ishonch qog'ozi** qanday yoziladi?             | Notariusda guvoh kerakmi    | "ishonch qog'ozi" = "ishonchnoma" bilinmadi |
| **My gov** ga qanday kiraman?                               | Boshqa javob                | Bazada "my.gov.uz" deb yozilgan             |
| Turmush qurish uchun **necha yosh** bo'lish kerak?          | Harbiy chaqiruv yoshi       | "Necha yosh" boshqa mavzuga tortdi          |
| Dadam vafot etdi, meros uchun notariusga nima olib boraman? | Merosga huquq guvohnomasi   | Mavzu to'g'ri, aniq savol boshqa            |
| Mashinamni boshqa odamga sotmoqchiman                       | Ishonchnoma bilan sotish    | Yaqin mavzu, aniq javob boshqa              |
| Taksi chaqirib ber *(begona savol)*                         | Tez yordam chaqirish        | "chaqir" so'zi                              |

---

## Cheklovlar va keyingi qadamlar

### Cheklovlar

- **Test to'plami kichik.** 44 ta savolda bitta savol natijani 2.3% ga o'zgartiradi.
  Chegara shu to'plamda tanlangani uchun natija biroz optimistik bo'lishi mumkin.
- **Ruscha savollar** ham lotinga o'giriladi ("kak poluchit pasport"). bge-m3 ruschani
  yaxshi tushunadi, shuning uchun ruscha matnni o'girmaslik yaxshiroq bo'lishi mumkin.
  O'lchanmagan.
- **Indekslash tekshiruvi** faqat savollar sonini solishtiradi. Matn o'zgarib, soni
  o'zgarmasa: `python -m scripts.index_qdrant --force`.

### Keyingi qadamlar

1. **Reranker** (`BAAI/bge-reranker-v2-m3`, lokal). Top-1 = 65.9%, Top-3 = 86.4%: 20%
   savolda to'g'ri javob topilgan, lekin 1-o'rinda emas. Cross-encoder savol va nomzodni
   birga o'qib, aynan shu holatlarni tuzatadi.
2. **Test to'plamini kengaytirish** (150–200 savol) va uni chegara tanlash (dev) hamda
   yakuniy baholash (test) qismlariga bo'lish.
3. **So'zlashuv lug'ati:** "prava" → "haydovchilik guvohnomasi", "my gov" → "my.gov.uz",
   "ishonch qog'ozi" → "ishonchnoma".
4. **Javob topilmagan savollarni saqlash:** bilim bazasini real talab asosida kengaytirish.
5. **Prod uchun:** bot webhook rejimida; indeksni to'xtovsiz yangilash (Qdrant alias).

---

## API

| Metod  | Manzil          | Tavsif                                               |
| ------ | --------------- | ---------------------------------------------------- |
| `POST` | `/ask`          | Savol → javob (`found` / `ambiguous` / `not_found`)  |
| `GET`  | `/answers/{id}` | Javob matni (botdagi "aniqlashtirish" tugmasi uchun) |
| `GET`  | `/health`       | Holat tekshiruvi                                     |

**So'rov:**

```bash
# Linux / macOS / Git Bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "Oyligimdan necha pul soliq ketadi?"}'
```

```powershell
# Windows PowerShell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ask -ContentType "application/json" `
  -Body '{"question": "Oyligimdan necha pul soliq ketadi?"}'
```

**Javob:**

```json
{
  "status": "found",
  "matches": [
    {
      "answer_id": 505,
      "score": 0.882,
      "matched_question": "Oyligimdan qancha daromad solig'i to'layman?",
      "answer": "Jismoniy shaxslarning odatdagi daromadlariga solinadigan daromad solig'i stavkasi 12 foizni tashkil etadi. ..."
    }
  ]
}
```

---

## Docker'siz ishga tushirish

```bash
docker compose up -d postgres qdrant     # faqat bazalar
python -m venv .venv
.venv\Scripts\activate                   # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.load_db                # CSV/Excel -> PostgreSQL
python -m scripts.index_qdrant           # savollar -> Qdrant
uvicorn app.api:app                      # API
python -m app.bot                        # bot (alohida terminalda)
python -m scripts.ask "savol"            # terminaldan sinash
```

Ma'lumot `data/` papkasidan o'qiladi: `answers.xlsx` / `questions.xlsx` bo'lsa ular,
bo'lmasa `.csv` fayllar.

Kod sifati: `ruff check app scripts` va `ruff format app scripts`.

---

## Loyiha tuzilmasi

```
app/
├── config.py        sozlamalar (.env)
├── db.py            PostgreSQL jadvallari
├── text.py          matnni normallashtirish
├── embedder.py      bge-m3: bir marta yuklash, oflayn rejim
├── search.py        retrieve / retrieve_robust → decide → javob matni
├── api.py           FastAPI
└── bot.py           Telegram bot
scripts/
├── load_db.py       CSV/Excel → PostgreSQL + sifat hisoboti
├── index_qdrant.py  savollar → Qdrant
├── evaluate.py      sifatni o'lchash → reports/eval_report.md
└── ask.py           terminaldan sinash
data/
├── answers.csv, questions.csv
└── eval/            test to'plamlari
reports/
└── eval_report.md   sifat hisoboti
```
