# Requirements — 15 Eksposur mata uang

Status: Done (2026-10-05)
Use case: UC-42, UC-46 ([overview](../fase-4-overview.md))
Asal: PRD-EA §Risk management (eksposur per mata uang: maks 2 posisi searah; pre-trade check berurutan), PC-09 (urutan pre-trade check), PC-21 (eksposur dengan arah; XAU/XAG/BTC mata uang sendiri); python-bot-lessons §2 (eksposur mengabaikan arah → SELL dihitung terbalik → 5 posisi short-USD kena SL bersamaan)
Butuh: spec 13

## Pendahuluan

Spec ini mengisi langkah `CURRENCY_EXPOSURE` di pre-trade check, yang sejak Fase 1 selalu lolos. Order ditolak bila setelah dibuka, suatu mata uang akan punya lebih dari N posisi SDBot searah di akun (default 2, PRD). Eksposur dihitung **dengan arah** per kaki mata uang: BUY EURUSD = long EUR + short USD. Bug bot Python yang mengabaikan arah tidak boleh terulang. Batas posisi per kategori (Fase 1) dan filter lain tidak berubah.

Selesai jika:
- suite ExposureRules ALL PASS, termasuk kasus SELL, pair JPY, dan XAU/BTC;
- uji integrasi dengan posisi nyata di tester membuktikan penolakan dan urutannya di pre-trade check;
- SC-16 membuktikan kandidat pipeline ditolak `CURRENCY_EXPOSURE` saat dua posisi SDBot searah sudah terbuka di simbol lain;
- regresi tetap PASS;
- EA naik ke `1.16`.

## Ukuran (dasar default)

Tester MT5 menguji satu simbol per run, jadi efek lintas simbol diukur dengan memutar ulang timeline gabungan 241 trade backtest dasar berfilter v1.15 (12 simbol, 2025-10..2026-10):

| Batas posisi searah per mata uang | Trade lolos | Total R lolos | Expectancy | Trade diblokir | R trade diblokir |
|---|---|---|---|---|---|
| Tanpa batas | 241 | +8,42 | +0,035 | 0 | — |
| 1 | 198 | +0,57 | +0,003 | 43 | +7,85 |
| **2 (PRD)** | **233** | **+9,26** | **+0,040** | **8** | **−0,85** |
| 3 | 240 | +9,42 | +0,039 | 1 | −1,00 |

Batas 2 memblokir sedikit trade (paling sering di NZDUSD) dan trade yang terblokir rugi bersih. Batas 1 membuang terlalu banyak trade bagus.

## Glosarium

- **Kaki mata uang:** satu posisi punya dua kaki, mata uang dasar (`SYMBOL_CURRENCY_BASE`) dan mata uang kuotasi (`SYMBOL_CURRENCY_PROFIT`). BUY = dasar long + kuotasi short; SELL = dasar short + kuotasi long.
- **Posisi searah per mata uang:** jumlah kaki dengan mata uang dan arah yang sama dari posisi SDBot terbuka (magic di blok SDBot, semua simbol) di akun.
- **XAU, XAG, BTC:** dihitung sebagai mata uang sendiri. BUY XAUUSD = long XAU + short USD.

## Requirements

### Requirement 1: Perhitungan eksposur

**User story:** Sebagai trader, saya ingin EA tidak menumpuk posisi searah pada satu mata uang, agar satu rilis berita tidak mengenai banyak posisi sekaligus.

#### Acceptance criteria

1.1. EA WAJIB menghitung kaki mata uang setiap posisi SDBot terbuka di akun dari mata uang dasar, mata uang kuotasi, dan arah posisi.
1.2. Posisi bukan SDBot (manual, EA lain) WAJIB tidak dihitung, sama dengan batas kategori dan total risiko.
1.3. Posisi dengan arah berlawanan pada mata uang yang sama WAJIB dihitung terpisah: long USD tidak mengurangi short USD dan sebaliknya.
1.4. Simbol yang mata uang dasar atau kuotasinya tidak terbaca (kosong) WAJIB tidak menambah eksposur dan dicatat WARN sekali.

### Requirement 2: Penolakan order

2.1. JIKA order baru akan membuat salah satu kakinya punya lebih dari `InpMaxSameDirectionPerCurrency` (default 2) posisi searah MAKA pre-trade check WAJIB menolak `CURRENCY_EXPOSURE`, dengan mata uang, arah, dan jumlah di detail (contoh `USD short 2/2`).
2.2. Langkah eksposur WAJIB berada di urutan PRD: setelah batas posisi per kategori dan sebelum margin.
2.3. `InpMaxSameDirectionPerCurrency` = 0 WAJIB mematikan langkah ini (selalu lolos); rentang 0–10.
2.4. Kandidat pipeline yang ditolak di langkah ini WAJIB tercatat di `signals` dengan `reject_stage` `CURRENCY_EXPOSURE` dan detailnya; zona tidak menjadi Used.

### Requirement 3: Input dan dokumen

3.1. Input `InpMaxSameDirectionPerCurrency` WAJIB divalidasi, masuk `inputs_json`, tabel input README, dan 12 preset (2).

### Requirement 4: Uji dan versi

4.1. Suite ExposureRules WAJIB menguji fungsi murni:
- kaki BUY dan SELL untuk EURUSD, USDJPY, EURJPY, XAUUSD, BTCUSD;
- hitungan dengan posisi campuran arah;
- batas tepat 2 lolos, posisi ke-3 ditolak, dan batas 0 mati;
- mata uang kosong.
4.2. Uji integrasi (tester, posisi nyata dengan magic SDBot lain di simbol lain) WAJIB membuktikan penolakan `CURRENCY_EXPOSURE` dan urutannya terhadap batas kategori dan margin.
4.3. SC-16 WAJIB menjalankan pipeline di tester dengan dua posisi SDBot short-USD yang dibuka harness di simbol lain, lalu membuktikan kandidat BUY USD-short ditolak `CURRENCY_EXPOSURE` dan kandidat arah lain tetap bisa dibuka.
4.4. EA dan harness WAJIB naik ke `1.16`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | 2 posisi BUY EURUSD dan BUY GBPUSD (short USD 2), lalu BUY AUDUSD | Ditolak `USD short 2/2` | 2.1 |
| EC-02 | 2 posisi short USD, lalu SELL EURUSD (long USD) | Lolos (arah lain) | 1.3 |
| EC-03 | BUY EURJPY + BUY USDJPY (short JPY 2), lalu BUY GBPJPY | Ditolak `JPY short 2/2` | 2.1 |
| EC-04 | BUY XAUUSD + BUY EURUSD (short USD 2), lalu BUY BTCUSD | Ditolak `USD short 2/2`; XAU dan BTC long masing-masing 1 | 1.1, 2.1 |
| EC-05 | Posisi manual short USD di akun | Tidak dihitung | 1.2 |
| EC-06 | Posisi lama tutup di antara dua kandidat | Hitungan dari posisi terbuka saat pre-trade check | 1.1 |
| EC-07 | Beberapa instance mengirim order hampir bersamaan | Bisa lolos bersamaan sebelum posisi tampil (risiko diterima, sama dengan batas kategori Fase 1) | 2.1 |
| EC-08 | Simbol dengan mata uang dasar/kuotasi kosong | Tidak menambah eksposur, WARN sekali | 1.4 |
| EC-09 | Batas kategori dan eksposur sama-sama terlewati | `CLASS_POSITION_LIMIT` (urutan) | 2.2 |

## Keputusan yang perlu disetujui

1. **Batas default 2 posisi searah per mata uang (PRD)**, dengan input `InpMaxSameDirectionPerCurrency` (0 = mati). Replay backtest: 8 dari 241 trade terblokir, dan trade itu rugi bersih.
2. **Hitungan atas semua posisi SDBot di akun** (blok magic), bukan per instance, karena risikonya ada di akun.
3. **Tanpa kunci antar-instance** untuk order yang hampir bersamaan (EC-07), sama dengan batas kategori Fase 1. Kunci Global Variable bisa ditambah nanti bila data live menunjukkan perlu.
4. **Tidak ada backtest dasar baru di spec ini.** Tester satu simbol tidak bisa mengukur eksposur lintas simbol; efeknya sudah diukur dengan replay di atas, sedangkan kebenaran perilaku dibuktikan oleh uji integrasi dan SC-16.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
