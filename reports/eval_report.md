# Qidiruv sifati hisoboti

`python -m scripts.evaluate` tomonidan yaratilgan.

Joriy sozlama: **threshold 0.65**, **margin 0.06**.

## 1. Test to'plamlari

| To'plam      | Hajmi | Tavsif                                                  |
| ------------ | ----: | ------------------------------------------------------- |
| holdout      |   505 | har javobdan 1 ta savol, o'zi qidiruvdan chiqarilgan    |
| real         |    44 | jonli uslubdagi savollar (data/eval/real_questions.csv) |
| real CAPS    |    44 | real, KATTA harflarda                                   |
| real aralash |    44 | real, harflar tasodifan katta/kichik                    |
| ood          |    30 | bazaga aloqasiz savollar (data/eval/out_of_scope.csv)   |

## 2. Qidiruv (qarorsiz)

To'g'ri javob 1-o'rinda (Top-1) yoki eng yaxshi 3 talikda (Top-3).

| To'plam      |  Top-1 |  Top-3 |
| ------------ | -----: | -----: |
| holdout      | 100.0% | 100.0% |
| real         |  65.9% |  86.4% |
| real CAPS    |  61.4% |  79.5% |
| real aralash |  61.4% |  79.5% |

## 3. Joriy sozlamadagi natija

- **to'g'ri**: bitta javob berildi va u to'g'ri
- **aniqlashtirish**: bir nechta variant ko'rsatildi, to'g'risi ular orasida
- **xato**: javob berildi, lekin noto'g'ri
- **o'tkazdi**: "topilmadi" deyildi, aslida javob bor edi

| To'plam      | To'g'ri | Aniqlashtirish |  Xato | O'tkazdi | Foydali jami |
| ------------ | ------: | -------------: | ----: | -------: | -----------: |
| holdout      |   96.4% |           3.6% |  0.0% |     0.0% |       100.0% |
| real         |   45.5% |          40.9% | 13.6% |     0.0% |        86.4% |
| real CAPS    |   43.2% |          31.8% | 22.7% |     2.3% |        75.0% |
| real aralash |   40.9% |          31.8% | 22.7% |     4.5% |        72.7% |

Bazaga aloqasiz savollarga noto'g'ri javob: **3.3%** (1 / 30).

## 4. Chegara (threshold) va farq (margin) jadvali

REAL va HOLDOUT ustunlari: foiz. OOD: begona savollarga noto'g'ri javob.

| Threshold | Margin | REAL to'g'ri | REAL aniqlash | REAL xato | REAL o'tkazdi | HOLDOUT to'g'ri | OOD javob |          |
| --------: | -----: | -----------: | ------------: | --------: | ------------: | --------------: | --------: | -------- |
|      0.55 |   0.00 |        65.9% |          0.0% |     34.1% |          0.0% |          100.0% |     63.3% |          |
|      0.55 |   0.03 |        52.3% |         25.0% |     22.7% |          0.0% |           98.4% |     63.3% |          |
|      0.55 |   0.06 |        45.5% |         40.9% |     13.6% |          0.0% |           96.4% |     63.3% |          |
|      0.55 |   0.10 |        31.8% |         54.5% |     13.6% |          0.0% |           89.5% |     63.3% |          |
|      0.60 |   0.00 |        65.9% |          0.0% |     34.1% |          0.0% |          100.0% |     30.0% |          |
|      0.60 |   0.03 |        52.3% |         25.0% |     22.7% |          0.0% |           98.4% |     30.0% |          |
|      0.60 |   0.06 |        45.5% |         40.9% |     13.6% |          0.0% |           96.4% |     30.0% |          |
|      0.60 |   0.10 |        31.8% |         54.5% |     13.6% |          0.0% |           89.5% |     30.0% |          |
|      0.65 |   0.00 |        65.9% |          0.0% |     34.1% |          0.0% |          100.0% |      3.3% |          |
|      0.65 |   0.03 |        52.3% |         25.0% |     22.7% |          0.0% |           98.4% |      3.3% |          |
|      0.65 |   0.06 |        45.5% |         40.9% |     13.6% |          0.0% |           96.4% |      3.3% | <- joriy |
|      0.65 |   0.10 |        31.8% |         54.5% |     13.6% |          0.0% |           89.5% |      3.3% |          |
|      0.70 |   0.00 |        56.8% |          0.0% |     27.3% |         15.9% |          100.0% |      0.0% |          |
|      0.70 |   0.03 |        47.7% |         18.2% |     18.2% |         15.9% |           98.4% |      0.0% |          |
|      0.70 |   0.06 |        43.2% |         27.3% |     13.6% |         15.9% |           96.4% |      0.0% |          |
|      0.70 |   0.10 |        31.8% |         38.6% |     13.6% |         15.9% |           89.5% |      0.0% |          |
|      0.75 |   0.00 |        50.0% |          0.0% |     11.4% |         38.6% |          100.0% |      0.0% |          |
|      0.75 |   0.03 |        43.2% |         11.4% |      6.8% |         38.6% |           98.4% |      0.0% |          |
|      0.75 |   0.06 |        43.2% |         15.9% |      2.3% |         38.6% |           96.4% |      0.0% |          |
|      0.75 |   0.10 |        31.8% |         27.3% |      2.3% |         38.6% |           89.5% |      0.0% |          |
|      0.80 |   0.00 |        43.2% |          0.0% |      6.8% |         50.0% |          100.0% |      0.0% |          |
|      0.80 |   0.03 |        38.6% |          9.1% |      2.3% |         50.0% |           98.4% |      0.0% |          |
|      0.80 |   0.06 |        38.6% |         11.4% |      0.0% |         50.0% |           96.4% |      0.0% |          |
|      0.80 |   0.10 |        29.5% |         20.5% |      0.0% |         50.0% |           89.5% |      0.0% |          |

## 5. Xatolar (joriy sozlama, real va ood)

| Natija         | Savol                                                       | Kutilgan | Topildi (ball)                           |
| -------------- | ----------------------------------------------------------- | -------- | ---------------------------------------- |
| xato           | Turmush qurish uchun necha yosh bo'lish kerak?              | 8        | #145 (0.730), #289 (0.723), #128 (0.677) |
| xato           | Dadam vafot etdi, meros uchun notariusga nima olib boraman? | 44       | #43 (0.710), #306 (0.697), #209 (0.685)  |
| xato           | Notariusda ishonch qog'ozi qanday yoziladi?                 | 45       | #498 (0.734), #103 (0.728), #47 (0.719)  |
| xato           | Mashinamni boshqa odamga sotmoqchiman                       | 53       | #216 (0.715), #287 (0.685), #218 (0.668) |
| xato           | Oylik bermayapti, kimga shikoyat qilaman?                   | 126      | #490 (0.752), #467 (0.751), #119 (0.739) |
| xato           | My gov ga qanday kiraman?                                   | 72       | #76 (0.721), #483 (0.719), #119 (0.708)  |
| begonaga javob | Taksi chaqirib ber                                          | -        | #445 (0.673), #164 (0.649), #421 (0.640) |
