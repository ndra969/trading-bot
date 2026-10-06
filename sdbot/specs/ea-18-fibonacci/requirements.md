# Requirements — Skor Fibonacci (mode bayangan)

Status: Done (2026-10-06)
Use case: UC-53 ([fase-5-overview.md](../fase-5-overview.md))
Asal: PRD-EA §Skor konfluensi (Fibonacci maks 15), PC-25 (mode OFF / SHADOW / ACTIVE, aturan aktivasi); python-bot-lessons §1 (Fibonacci memilih level paling "bergengsi": 0.618 memberi skor penuh di ~83% setup)
Butuh: spec 17 (skema v4 `signal_scores.active`, `component_report.py`, periode IS/OOS)

## Pendahuluan

Spec ini menambah komponen skor Fibonacci: posisi zona kandidat di retracement gerak impuls MTF yang membentuk zona itu.

- Komponen berjalan dalam mode bayangan secara default: nilainya dicatat untuk setiap kandidat, tetapi tidak mengubah skor gerbang, entry, atau jumlah trade.
- Spec ini tidak mengaktifkan Fibonacci. Aktivasi diputuskan di spec 22 dari data IS/OOS.
- Di luar lingkup: Fibonacci extension untuk TP, dan level selain 0.382 / 0.5 / 0.618 / 0.786.

Bukti selesai:
- suite `FibRules` ALL PASS, termasuk kasus bug bot Python;
- skenario SC-18 PASS;
- backtest IS + OOS dengan entry yang identik dengan acuan v1.19, plus laporan komponen FIB tercatat.

## Glosarium

- **Leg impuls:** gerak MTF yang membentuk zona. Demand: dari low swing zona (batas jauh) ke high tertinggi bar MTF tertutup sesudahnya, sampai sebelum bar kandidat. Supply: cerminnya.
- **Rasio retracement:** posisi harga di leg, 0 = ujung impuls (high untuk demand), 1 = awal leg (low swing zona).
- **Level Fibonacci:** 0.382, 0.5, 0.618, 0.786.
- **Mode komponen:** OFF (tidak dihitung), SHADOW (dihitung dan dicatat `active = 0`, tidak ikut skor gerbang), ACTIVE (ikut skor gerbang dan maksimum skor).

## Requirements

### Requirement 1: Leg impuls tanpa lookahead
**User story:** Sebagai developer, saya ingin leg Fibonacci dihitung hanya dari bar MTF yang sudah tertutup sebelum kandidat, agar skor di backtest sama dengan yang akan terjadi di live.

#### Acceptance criteria
1. KETIKA kandidat dinilai MAKA EA WAJIB membentuk leg impuls dari batas jauh zona kandidat ke ekstrem bar MTF tertutup sesudah candle swing zona, sampai bar MTF tertutup terakhir sebelum waktu bar kandidat.
2. EA WAJIB tidak memakai bar MTF yang belum tertutup, maupun bar sesudah bar kandidat.
3. JIKA panjang leg < `ZoneMinLegAtr` × ATR zona (1,5 ATR) MAKA skor Fibonacci WAJIB 0, dengan alasan "leg pendek".
4. Untuk bar kandidat yang sama, nilai Fibonacci WAJIB sama, baik dihitung bar per bar maupun setelah restart.

### Requirement 2: Skor dari level terdekat
**User story:** Sebagai trader, saya ingin skor Fibonacci menilai level yang benar-benar terdekat dengan zona, agar skor penuh tidak diberikan hampir ke semua setup seperti di bot Python.

#### Acceptance criteria
1. EA WAJIB menghitung rasio retracement batas dekat zona (titik sentuh harga) pada leg impuls.
2. EA WAJIB memilih level Fibonacci yang **terdekat** dengan rasio itu, bukan level dengan skor tertinggi.
3. Nilai dasar WAJIB mengikuti PRD: level 0.5 atau 0.618 = 15, level 0.382 atau 0.786 = 8.
4. Skor WAJIB berkurang sesuai jarak rasio ke level terdekat. Di luar toleransi, skornya 0.
5. JIKA rasio < 0,236 atau > 1,0 (zona di luar leg) MAKA skor WAJIB 0.
6. EA WAJIB mencatat rasio, level terdekat, dan jaraknya di konteks sinyal, agar distribusinya bisa diperiksa.

### Requirement 3: Mode komponen
**User story:** Sebagai developer, saya ingin Fibonacci dicatat tanpa mengubah entry, agar efeknya bisa diukur pada kandidat yang sama sebelum diaktifkan.

#### Acceptance criteria
1. Input `InpScoreFibMode` WAJIB menerima OFF, SHADOW, atau ACTIVE, dengan default SHADOW.
2. SELAMA mode SHADOW, EA WAJIB mencatat skor FIB di `signal_scores` dengan `active = 0`. Skor gerbang, maksimum skor (55), entry, dan `signals.score_total` WAJIB sama dengan mode OFF.
3. SELAMA mode ACTIVE, skor FIB WAJIB masuk skor gerbang dan maksimum skor bertambah 15 (menjadi 70). Ambang tetap `MinConfluenceScore` persen dari maksimum aktif.
4. SELAMA mode OFF, EA WAJIB tidak menghitung dan tidak mencatat FIB.
5. Komponen FIB WAJIB dicatat untuk setiap kandidat yang dicatat dengan ZONE/TREND/PA, termasuk yang ditolak di tahap mana pun.

### Requirement 4: Pengukuran IS/OOS
**User story:** Sebagai developer, saya ingin hasil Fibonacci bayangan diukur di IS dan OOS, agar spec 22 punya data aktivasi.

#### Acceptance criteria
1. Backtest dasar `-Period ALL` dengan versi spec ini WAJIB menghasilkan trade yang identik dengan acuan v1.19 (sesi 901–924): jumlah trade dan R total per simbol sama.
2. `component_report.py` atas sesi baru WAJIB menampilkan FIB (bayangan) per nilai skor di IS dan OOS, dan hasilnya dicatat di spec dan CHANGELOG.
3. Distribusi nilai FIB atas semua kandidat (`--candidates`) WAJIB dicatat. Bila > 60% kandidat ACCEPTED mendapat skor penuh, temuan itu WAJIB dibahas (tanda pola bug bot Python).

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Zona baru aktif, belum ada bar sesudah gerak keluar yang melewati ujung leg | Leg = gerak keluar zona yang sudah ada (≥ 1,5 ATR menurut aturan zona) | 1.1 |
| EC-02 | Harga membuat high baru sesudah zona, lalu kembali ke zona | Leg ujungnya high baru itu (ekstrem terbaru), rasio dihitung ulang | 1.1 |
| EC-03 | Batas dekat zona tepat di tengah dua level (misalnya 0.559) | Pemilihan deterministik dengan aturan tie yang terdokumentasi | 2.2 |
| EC-04 | Zona lebar menutupi 0.382–0.618 | Tetap satu titik ukur (batas dekat), satu level terdekat | 2.1, 2.2 |
| EC-05 | Pair JPY (3 digit), XAU, BTC dengan harga besar | Rasio tidak bergantung skala harga; toleransi dalam rasio, bukan pip | 2.4 |
| EC-06 | Restart EA di tengah hari | Nilai FIB untuk bar yang sama tidak berubah (bar MTF dari histori) | 1.4 |
| EC-07 | Histori MTF kurang (awal backtest) | FIB 0 dengan alasan data kurang; kandidat tetap dinilai komponen lain | 1.1 |
| EC-08 | Mode diubah antar sesi | `inputs_json` mencatat mode, sehingga laporan bisa membedakan sesi | 3.1 |
| EC-09 | Rasio > 1 (zona ditembus wick tapi belum invalid) | Skor 0 | 2.5 |

## Pertanyaan terbuka

- Titik ukur: batas dekat zona (usulan; tempat harga menyentuh) atau tengah zona?
- Bentuk pengurangan jarak: linear dari nilai dasar ke 0 pada jarak 0,05 rasio (usulan), atau bertingkat (penuh ≤ 0,02, setengah ≤ 0,05)?
