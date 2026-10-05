# Requirements — 16 Filter berita

Status: Done (2026-10-05)
Use case: UC-43, UC-44, UC-45, UC-46 ([overview](../fase-4-overview.md))
Asal: PRD-EA §Pipeline analisis (pre-filter berita), §Parameter input EA (`NewsBlockMinutes`), PRD-EA (filter berita memakai kalender MT5; CSV historis di tester, script `ExportCalendar`); PC-21 (blackout per dampak, degrade aman + alert, pemetaan mata uang); python-bot-lessons §3 dan catatan Fase 4 di README (degrade aman tapi terlihat, tanpa lookahead, telemetri event terdekat)
Butuh: spec 14

## Pendahuluan

Spec ini menambahkan filter terakhir Fase 4: blackout di sekitar berita ekonomi berdampak, untuk mata uang simbol.
- **Live:** kalender ekonomi bawaan MT5 (`CalendarValueHistory`).
- **Strategy Tester:** fungsi kalender tidak tersedia, jadi kalender dibaca dari CSV yang dibuat script `ExportCalendar` di terminal live.

Bila kalender tidak bisa dibaca, entry **tidak** diblokir, tetapi operator diberi tahu sekali bahwa proteksi berita mati. Spec ini menutup Fase 4.

Selesai jika:
- suite NewsRules ALL PASS;
- SC-17 membuktikan kandidat di jendela blackout (dari CSV) ditolak `NEWS_BLACKOUT` dengan nama event dan menit;
- SC-17b membuktikan tester tanpa CSV tetap trading, dengan satu alert proteksi mati;
- backtest dasar 12 simbol dengan **semua** filter Fase 4 memenuhi kriteria PC-22;
- regresi tetap PASS;
- EA naik ke `1.17` (Fase 4 selesai).

## Glosarium

- **Event berdampak:** event kalender MT5 dengan `CALENDAR_IMPORTANCE_HIGH` (high) atau `CALENDAR_IMPORTANCE_MODERATE` (medium). `LOW`/`NONE` tidak diblokir.
- **Mata uang simbol:** mata uang dasar dan kuotasi simbol. Untuk XAU, XAG, dan BTC hanya kaki USD yang punya event (kalender MT5 tidak punya event untuk XAU/XAG/BTC).
- **Jendela blackout:** waktu event ± `InpNewsHighMinutes` (default 15, PC-24; PRD semula 30) untuk high dan ± `InpNewsMediumMinutes` (default 0 = tidak diblokir) untuk medium; batas inklusif.
- **Menit ke event:** waktu bar kandidat − waktu event, dalam menit (negatif = sebelum rilis).
- **CSV kalender:** `Common\Files\sdbot_calendar.csv`, satu baris per event: waktu server (epoch), mata uang, importance (`HIGH`/`MEDIUM`/`LOW`), ID event, nama event.

## Requirements

### Requirement 1: Blackout berita

**User story:** Sebagai trader, saya ingin EA tidak entry di sekitar berita berdampak untuk mata uang simbol, agar lonjakan harga saat rilis tidak menembus SL yang baru dipasang.

#### Acceptance criteria

1.1. JIKA ada event berdampak untuk salah satu mata uang simbol yang jendela blackout-nya mencakup waktu bar kandidat MAKA kandidat WAJIB ditolak `NEWS_BLACKOUT`, dengan nama event, mata uang, dampak, dan menit ke event di detail.
1.2. Bila beberapa event mencakup bar yang sama, detail WAJIB menyebut event dengan dampak tertinggi, lalu yang terdekat.
1.3. Input `InpNewsFilter` (default true) WAJIB bisa mematikan filter. `InpNewsHighMinutes` (15; 0–240) dan `InpNewsMediumMinutes` (0; 0–240) WAJIB mengatur jendela; 0 = dampak itu tidak diblokir.
1.4. Urutan tahap kandidat WAJIB: pre-filter risiko → `NEWS_BLACKOUT` → `OUTSIDE_SESSION` → `SPREAD_TOO_WIDE` → `POSITION_OPEN` → … (PC-21).
1.5. Filter berita WAJIB hanya memengaruhi entry baru; manajemen posisi tidak berubah.

### Requirement 2: Sumber kalender

2.1. Di live, EA WAJIB membaca event berdampak untuk mata uang simbol dari `CalendarValueHistory`, untuk jendela waktu yang cukup menampung blackout terpanjang, dan menyegarkannya paling sering tiap 15 menit (tidak tiap tick).
2.2. Di Strategy Tester, EA WAJIB membaca CSV kalender sekali saat init dan hanya memakai event untuk mata uang simbol.
2.3. Waktu event WAJIB dalam waktu server, sama dengan waktu bar.
2.4. Tanpa lookahead: EA WAJIB hanya memakai jadwal event (waktu, mata uang, dampak, nama), bukan nilai `actual`, sehingga backtest tidak membaca hasil rilis sebelum waktunya.

### Requirement 3: Degrade aman tapi terlihat

**User story:** Sebagai trader, saya ingin tahu bila proteksi berita mati, tanpa EA berhenti trading karenanya.

#### Acceptance criteria

3.1. JIKA kalender tidak bisa dibaca (fungsi kalender gagal di live, atau CSV tidak ada / kosong / rusak di tester) MAKA EA WAJIB tidak memblokir entry karena berita, dan mengirim **satu** alert `NEWS_FILTER_OFF` (severity High) per sesi EA dengan alasannya.
3.2. KETIKA kalender kembali terbaca di live MAKA EA WAJIB memakai filter lagi dan mencatat INFO sekali.
3.3. Konteks setiap kandidat WAJIB memuat status filter berita (`ON`, `OFF`, `DISABLED`).

### Requirement 4: Telemetri

4.1. Konteks kandidat yang lolos WAJIB memuat event berdampak terdekat untuk mata uang simbol dalam 24 jam ke depan (nama, mata uang, dampak, menit ke event), atau kosong bila tidak ada.
4.2. Alert type `NEWS_FILTER_OFF` WAJIB masuk `enums.md`.

### Requirement 5: Script ExportCalendar

5.1. Script `Scripts/SDBot/ExportCalendar.mq5` WAJIB menulis CSV kalender (format glosarium) untuk rentang tanggal input (default 2025-01-01 s.d. hari ini) dan mata uang 12 simbol (USD, EUR, GBP, JPY, CHF, AUD, CAD, NZD), dengan dampak low ke atas, urut waktu.
5.2. Script WAJIB melaporkan jumlah event per mata uang dan dampak, dan gagal dengan pesan jelas bila kalender belum tersinkron.
5.3. Alat uji WAJIB bisa menjalankan `ExportCalendar` dari baris perintah di terminal uji (tanpa membuka chart), agar backtest dasar memakai CSV terbaru.

### Requirement 6: Uji, backtest dasar, versi

6.1. Suite NewsRules WAJIB menguji fungsi murni:
- jendela high dan medium, termasuk batas tepat 30/10 menit sebelum dan sesudah;
- dampak low tidak diblokir;
- pemetaan mata uang (EURUSD, USDJPY, EURJPY, XAUUSD, BTCUSD);
- pilihan event saat beberapa event tumpang tindih;
- parse baris CSV, termasuk baris rusak;
- event terdekat 24 jam.
6.2. SC-17 (fixture CSV di repo dengan event buatan di waktu yang diketahui) WAJIB membuktikan kandidat di jendela ditolak `NEWS_BLACKOUT` dan kandidat di luar jendela tidak.
6.3. SC-17b (tester tanpa CSV) WAJIB membuktikan pipeline tetap membuka posisi, satu alert `NEWS_FILTER_OFF`, dan konteks `news` = `OFF`.
6.4. Backtest dasar 12 simbol dengan semua filter Fase 4 dan CSV hasil `ExportCalendar` WAJIB memenuhi kriteria PC-22 (≥ 200 trade, ≥ 10 per simbol, tanpa log ERROR/CRITICAL, telemetri lengkap). Laporan dibandingkan dengan backtest v1.15.
6.5. EA dan harness WAJIB naik ke `1.17`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Bar tepat 30 menit sebelum event high | Diblokir (batas inklusif) | 1.1 |
| EC-02 | Event medium 11 menit setelah bar | Tidak diblokir | 1.3 |
| EC-03 | NFP (USD high) saat kandidat XAUUSD | Diblokir lewat kaki USD | 1.1 |
| EC-04 | Event EUR high dan USD medium tumpang tindih untuk EURUSD | Detail menyebut event EUR high | 1.2 |
| EC-05 | Terminal live baru start, kalender belum sinkron | Filter OFF + satu alert; aktif lagi otomatis saat terbaca | 3.1, 3.2 |
| EC-06 | CSV tidak ada di tester | Trading jalan, satu alert, konteks `OFF` | 3.1, 6.3 |
| EC-07 | Baris CSV rusak (kolom kurang, waktu bukan angka) | Baris dilewati, WARN dengan jumlah baris rusak | 2.2 |
| EC-08 | Event dijadwal ulang setelah CSV diekspor | Backtest memakai jadwal saat ekspor (batasan diterima, ekspor ulang memperbarui) | 2.2 |
| EC-09 | `InpNewsHighMinutes` 0 dan medium 0 | Tidak ada blackout, status `ON` tetap tercatat | 1.3 |
| EC-10 | Kandidat STOPPED sekaligus di jendela berita | `STOPPED` (urutan) | 1.4 |

## Keputusan yang perlu disetujui

1. **Input:** `InpNewsFilter` (true), `InpNewsHighMinutes` (15), `InpNewsMediumMinutes` (0); diubah dari 30/10 pada 2026-10-05 setelah backtest dasar task 5 (PC-24). Input lama PRD `NewsBlockMinutes` diganti dua input ini.
2. **Kalender live disegarkan tiap 15 menit** ke cache memori, bukan dibaca tiap kandidat, agar `OnTick` tetap ringan.
3. **XAU, XAG, BTC hanya memakai event USD.**
4. **Alert `NEWS_FILTER_OFF` severity High, sekali per sesi EA**, bukan Critical: trading tetap aman dengan SL, hanya proteksi tambahannya yang mati.
5. **CSV kalender tidak di-commit** (data, dibuat ulang dengan `ExportCalendar`). Hanya fixture kecil untuk SC-17 yang masuk repo. Runner mendapat perintah `-ExportCalendar` yang menjalankan script di terminal uji lewat konfigurasi startup.
6. **Efek filter diukur di backtest dasar akhir spec**, bukan di requirements, karena data kalender baru tersedia setelah `ExportCalendar` dibuat. Bila kriteria PC-22 gagal, temuan dibahas dulu.

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
