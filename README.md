# Semantik savol-javob tizimi

Foydalanuvchi savolni o'z so'zlari bilan yozadi, tizim esa 505 ta tayyor javobdan
ma'no jihatidan eng mosini topadi. Mos javob bo'lmasa, buni ochiq aytadi.
Hammasi lokal ishlaydi: tashqi API'larga murojaat qilinmaydi.

**Stek:** bge-m3 (embedding) · Qdrant (vektor baza) · PostgreSQL · FastAPI · aiogram (Telegram bot) · Docker

---

## Tezkor ishga tushirish

Talablar: Docker Desktop (yoki Docker + Compose v2), ~6 GB bo'sh joy.

```bash
cp .env.example .env        # Windows: copy .env.example .env
# .env ichida: BOT_TOKEN=<@BotFather bergan token>
docker compose up -d --build
```

Birinchi ishga tushirishda bge-m3 modeli (~2.2 GB) yuklab olinadi va 3048 ta savol
indekslanadi (~5 daqiqa, CPU). Shundan keyin `.env` da `HF_OFFLINE=true` qilish mumkin:
tizim internetsiz ishlaydi.

- API hujjati: http://localhost:8000/docs
- Qdrant paneli: http://localhost:6333/dashboard
- Telegram: botingizga savol yozing

```bash
docker compose ps            # holat
docker compose logs -f api   # loglar
```

---

## Arxitektura

```
TAYYORLASH (init xizmati, bir marta)
  data/*.csv | *.xlsx ──► PostgreSQL (asl savol va javoblar)
                              │
                              ▼
                       normalize ──► bge-m3 ──► Qdrant (3048 vektor, payload: answer_id)

JAVOB BERISH (har savolda)
  Telegram bot ──► API POST /ask
                      │
                      ▼
                normalize ──► bge-m3 ──► Qdrant (javob bo'yicha guruhlangan top-3)
                      │
                      ▼
                qaror: found / ambiguous / not_found
                      │
                      ▼
                PostgreSQL'dan javob matni
```

| Xizmat | Vazifasi |
|---|---|
| `postgres` | Haqiqat manbai: savollar va javoblarning asl matni |
| `qdrant` | Savollar vektorlari va ular bo'yicha qidiruv |
| `init` | CSV/Excel → PostgreSQL → Qdrant. Indeks bo'lsa, qayta qurmaydi |
| `api` | FastAPI: `/ask`, `/answers/{id}`, `/health` |
| `bot` | Telegram bot. API orqali ishlaydi, modelni o'zi yuklamaydi |

---

## Texnik qarorlar

**Javoblar emas, savollar indekslanadi.** Ko'p javob matnlarida mavzu umuman
tilga olinmagan. Masalan, "ID-karta necha kunda tayyor bo'ladi?" savolining javobi:
*"Hujjatlar to'liq qabul qilingandan so'ng, odatda 1 ish kuni ichida..."*: unda
"ID-karta" so'zi yo'q. Foydalanuvchi savoli bazadagi savolga (savol↔savol) ko'proq
o'xshaydi, javob matniga emas.

**Natija javob bo'yicha guruhlanadi** (`query_points_groups`, `group_by="answer_id"`).
Har bir javobda 6 tadan savol bor. Guruhlashsiz top-3 ko'pincha bitta javobning
savollari bilan to'lib qoladi va 1- hamda 2-o'rin orasidagi farqni o'lchab bo'lmaydi.

**Uch xil qaror:**
- `found`: eng yaxshi ball ≥ `SEARCH_THRESHOLD` va keyingi javob undan ≥ `SEARCH_MARGIN` past;
- `ambiguous`: bir nechta javobning bali bir-biriga juda yaqin. Bot "qaysi biri?" deb tugmalar chiqaradi;
- `not_found`: eng yaxshi ball chegaradan past.

Chegara va farq eval asosida tanlangan: **0.65 / 0.06** (pastroqqa qarang).

**Matnni normallashtirish** (`app/text.py`): kirill → lotin, apostroflarni bir xillashtirish
(`ʻ ʼ ‘ ’` → `'`), bo'sh joylar. Bir xil funksiya indekslashda ham, qidiruvda ham ishlatiladi.
Ta'siri: kirillcha "ид карта неча кунда тайёр бўлади" savolining bazadagi savolga
o'xshashligi **0.737 → 0.956**.

**To'liq oflayn.** `HF_OFFLINE=true` bo'lsa, `HF_HUB_OFFLINE=1` o'rnatiladi: model
faqat diskdan o'qiladi, Hugging Face serverlariga so'rov yuborilmaydi.

**Model bir marta yuklanadi** (`lru_cache`, FastAPI `lifespan`). `/ask` oddiy `def`
bilan yozilgan: embedding CPU'ni band qiladi, shuning uchun FastAPI uni threadpool'da
bajaradi va event loop bloklanmaydi.

---

## Ma'lumot sifati

Yuklashda avtomatik sifat hisoboti chiqariladi (`scripts/load_db.py`):

| Tekshiruv | Natija |
|---|---|
| Javoblar / savollar | 505 / 3048 |
| Javobi yo'q savollar, savoli yo'q javoblar | 0 / 0 |
| Takroriy savollar | 0 |
| Lotin so'z ichidagi yashirin kirill harfi | 1 ta: javob #499, `"egа"` (normalizatsiya tuzatadi) |
| Javob boshiga savollar | 502 ta javobda 6 tadan, 3 tasida 12 tadan |

Kuzatuv: savollar shablon asosida yaratilgan ("... haqida ma'lumot bering" 415 marta,
"... bo'yicha ma'lumot kerak" 349 marta). Shu sababli faqat bazadagi savollar bilan
o'tkazilgan test natijani sun'iy ravishda yuqori ko'rsatadi (pastroqqa qarang).

---

## Sifatni tekshirish

```bash
python -m scripts.evaluate
```
Natija: [`reports/eval_results.txt`](reports/eval_results.txt)

### Test to'plamlari

| To'plam | Hajmi | Nima |
|---|---|---|
| holdout | 505 | Har bir javobdan 1 ta savol. Qidiruvda o'zi chiqarib tashlanadi (leave-one-out, Qdrant filtri) |
| real | 44 | Jonli uslubda qo'lda yozilgan savollar, to'g'ri javobi belgilangan: "prava", "propiska", "svet puli", 3 tasi kirillda ([`data/eval/real_questions.csv`](data/eval/real_questions.csv)) |
| ood | 30 | Bazaga aloqasiz savollar: ob-havo, osh, futbol, shuningdek "Bosh og'rig'iga qaysi dori yaxshi?" kabi yaqin mavzular ([`data/eval/out_of_scope.csv`](data/eval/out_of_scope.csv)) |

### Qidiruv (qarorsiz)

| | Top-1 | Top-3 |
|---|---|---|
| holdout | 100.0% | 100.0% |
| **real** | **70.5%** | **86.4%** |

Holdout'dagi 100% bazadagi savollar shablon bo'yicha yozilgani bilan izohlanadi.
**Haqiqiy ko'rsatkich jonli savollardagi natija.**

### Qaror (threshold 0.65, margin 0.06)

| real | |
|---|---|
| ✅ To'g'ri javob | 45.5% |
| 🟡 Aniqlashtirish (to'g'risi variantlar ichida) | 38.6% |
| ❌ Xato javob | 13.6% |
| ❌ O'tkazib yuborildi | 2.3% |
| **Foydali jami** | **84.1%** |

| holdout: to'g'ri | ood: noto'g'ri javob berildi |
|---|---|
| 96.8% (qolgani — aniqlashtirish) | 3.3% (30 tadan 1 tasi) |

### Chegarani tanlash

24 ta kombinatsiya sinab ko'rildi (`reports/eval_results.txt`). Asosiy murosa:

| Sozlama | Foydali | Xato | O'tkazib yuborildi | OOD'ga javob |
|---|---|---|---|---|
| 0.70 / 0.06 | 68.2% | 11.4% | 20.5% | 0% |
| **0.65 / 0.06** | **84.1%** | 13.6% | **2.3%** | 3.3% |
| 0.60 / 0.06 | 86.4% | 13.6% | 0% | 30.0% |

0.65 tanlandi: o'tkazib yuborilgan savollar 20.5% dan 2.3% ga tushadi, buning narxi
esa begona savolga bitta zararsiz javob ("Taksi chaqirib ber" → tez yordam chaqirish).
Begona savollarning eng yuqori bali (0.655) va to'g'ri topilgan jonli savollarning
eng past ballari (0.63–0.69) bir zonaga tushadi. Ya'ni bitta embedding bali bilan
ularni mukammal ajratib bo'lmaydi.

### Xatolar tahlili

| Savol | Nima bo'ldi | Sabab |
|---|---|---|
| Oylik bermayapti, kimga **shikoyat** qilaman? | "rad etilsa qayerga shikoyat" | Bitta so'z butun ma'noni bosib ketdi |
| Notariusda **ishonch qog'ozi** qanday yoziladi? | notariusda guvoh kerakmi | Model "ishonch qog'ozi" = "ishonchnoma" ekanini bilmaydi |
| **My gov** ga qanday kiraman? | boshqa javob | Bazada "my.gov.uz" deb yozilgan |
| Turmush qurish uchun necha yosh? | "hokim nikoh yoshini kamaytirishi" | Mavzu bir xil, savol boshqa |
| Propiska qanday qilinadi? | to'g'ri javob 1-o'rinda, lekin ball 0.630 | So'zlashuv so'zi, chegaradan past |

### Cheklovlar

- Test to'plami kichik: 44 ta savolda bitta savol natijani 2.3% ga o'zgartiradi.
  Chegara shu to'plamda tanlangani uchun natija biroz optimistik bo'lishi mumkin.
- Ruscha savollar ham lotinga o'giriladi ("kak poluchit pasport"). bge-m3 ruschani
  yaxshi tushunadi, shuning uchun ruscha matnni o'girmaslik yaxshiroq bo'lishi mumkin.
  O'lchanmagan.
- `init` faqat savollar sonini solishtiradi. Matn o'zgarib, soni o'zgarmasa:
  `python -m scripts.index_qdrant --force`.

### Keyingi qadamlar

1. **Reranker** (`BAAI/bge-reranker-v2-m3`, lokal). Top-1 = 70.5%, Top-3 = 86.4%:
   savollarning 16% ida to'g'ri javob topilgan, lekin 1-o'rinda emas. Cross-encoder
   savol va nomzodni birga o'qib, aynan shu holatlarni tuzatadi.
2. Test to'plamini 150–200 savolgacha kengaytirish, chegara tanlash uchun alohida
   (dev) va yakuniy baholash uchun alohida (test) qismga bo'lish.
3. So'zlashuv so'zlari lug'ati: "prava" → "haydovchilik guvohnomasi",
   "my gov" → "my.gov.uz", "propiska" va hokazo.
4. Javob topilmagan savollarni bazaga yozish: bilim bazasini real talab asosida kengaytirish.
5. Prod uchun: bot webhook rejimida; indeksni to'xtovsiz yangilash (Qdrant alias).

---

## API

| Metod | Manzil | Tavsif |
|---|---|---|
| `POST` | `/ask` | `{"question": "..."}` → `{"status", "matches": [{answer_id, score, matched_question, answer}]}` |
| `GET` | `/answers/{id}` | Javob matni (bot "aniqlashtirish" tugmasi uchun) |
| `GET` | `/health` | Holat tekshiruvi |

```bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "Oyligimdan necha pul soliq ketadi?"}'
```

---

## Lokal ishga tushirish (Docker'siz)

```bash
docker compose up -d postgres qdrant
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.load_db          # CSV/Excel -> PostgreSQL
python -m scripts.index_qdrant     # savollar -> Qdrant
uvicorn app.api:app                # API
python -m app.bot                  # bot (alohida terminalda)
python -m scripts.ask "savol"      # terminaldan sinash
```

Ma'lumot `data/` papkasidan o'qiladi: `answers.xlsx` / `questions.xlsx` bo'lsa ular,
bo'lmasa `.csv` fayllar.

---

## Loyiha tuzilmasi

```
app/
  config.py      sozlamalar (.env)
  db.py          PostgreSQL jadvallari
  text.py        normalizatsiya
  embedder.py    bge-m3 (bir marta yuklash, oflayn rejim)
  search.py      retrieve -> decide -> javob matni
  api.py         FastAPI
  bot.py         Telegram bot
scripts/
  load_db.py       CSV/Excel -> PostgreSQL + sifat hisoboti
  index_qdrant.py  savollar -> Qdrant
  evaluate.py      sifatni o'lchash
  ask.py           terminaldan sinash
data/
  answers.csv, questions.csv
  eval/            test to'plamlari
reports/
  eval_results.txt
```
