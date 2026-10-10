# Requirements — Replay tester periode live (spec 29)

Status: Done (2026-10-10)
Use case: UC-71, UC-72 ([fase-6-overview.md](../fase-6-overview.md))
Asal: PRD-EA §Pengujian dan kriteria penerimaan tahap 4 ("entry/exit cocok dengan backtest"), §Data dan database; overview Fase 6 keputusan 4 dan 5 (kecocokan kandidat dan trade, sekitar 2 minggu live)
Butuh: spec 28 (`live_report.py`: scope sesi dan celah sesi); tester tidak dipakai sesi lain saat replay dijalankan (batas CPU, satu agen)

## Pendahuluan

Spec ini membuktikan bahwa EA live mengambil keputusan yang sama dengan EA di Strategy Tester pada data yang sama. Isinya dua bagian:
- **Replay:** menjalankan tester untuk periode live per simbol, dengan real ticks dan input yang sama dengan sesi live.
- **Perbandingan:** alat `tools/live_compare.py` memasangkan kandidat dan trade live dengan hasil replay, lalu melaporkan kecocokan dan selisihnya.

Kandidat lebih banyak daripada trade (live mencatat sekitar 100+ kandidat per hari). Karena itu perbandingan kandidat bisa menemukan perbedaan perilaku dalam hitungan hari.

Di luar lingkup:
- perbaikan bug yang ditemukan replay (menjadi spec perbaikan tersendiri dengan versi baru);
- penilaian profit (tahap 3, laporan bulanan spec 28);
- keputusan penerimaan (spec 30).

Bukti selesai:
- pytest ALL PASS;
- satu replay ujung ke ujung untuk periode live v1.25 tercatat beserta laporan kecocokannya;
- setiap ketidakcocokan diberi penjelasan (perbedaan data atau lingkungan yang diketahui, atau calon bug).

## Glosarium

- **Periode replay**: rentang UTC yang dipilih; per simbol hanya bagian yang tertutup sesi live aktif (celah sesi dari spec 28 dikeluarkan dari perbandingan).
- **Pasangan kandidat**: kandidat live dan replay dengan simbol, waktu bar, dan arah yang sama.
- **Pasangan trade**: trade live dan replay dengan simbol dan arah sama, waktu buka berselisih ≤ 1 bar LTF (15 menit).

## Requirements

### Requirement 1: Menjalankan replay
**User story:** Sebagai developer, saya ingin replay tester memakai input yang persis sama dengan sesi live, agar perbedaan yang muncul bukan karena setelan.

#### Acceptance criteria
1. Untuk setiap simbol, replay WAJIB memakai input dari `inputs_json` sesi live yang aktif di periode itu, kecuali `InpAllowLiveTrading`, Telegram, dan `InpRiskPerTradePct`. Risk boleh berbeda karena perbandingan dalam R.
2. JIKA dalam satu periode satu simbol punya beberapa sesi dengan `input_hash` berbeda, MAKA alat WAJIB menolak periode itu dan menyebut batas waktu tiap hash. Periode dipecah oleh pengguna.
3. Replay WAJIB memakai model real ticks (Model 4) dan periode yang sama dengan live (dibulatkan ke hari penuh, dengan warm-up yang sama dengan backtest dasar).
4. Filter berita di replay WAJIB memakai CSV kalender yang diekspor untuk periode itu (`-ExportCalendar`). Bila CSV tidak mencakup periode, laporan WAJIB menandai perbandingan `NEWS_BLACKOUT` sebagai tidak bisa dinilai.
5. Replay WAJIB menulis ke `sdbot_tester.sqlite` seperti backtest lain, dan rentang sesinya WAJIB dicatat agar bisa dipakai `live_compare.py`.

### Requirement 2: Perbandingan kandidat
**User story:** Sebagai developer, saya ingin setiap kandidat live dibandingkan dengan replay, agar perbedaan perilaku cepat terlihat walaupun trade masih sedikit.

#### Acceptance criteria
1. `live_compare.py` WAJIB memasangkan kandidat live dan replay per simbol, waktu bar, dan arah, hanya di bagian periode yang tertutup sesi live aktif.
2. Untuk setiap pasangan, alat WAJIB membandingkan tahap tolak (atau ACCEPTED) dan skor total, lalu melaporkan:
   - persentase pasangan dengan tahap sama;
   - persentase kandidat live yang punya pasangan, dan sebaliknya;
   - daftar pasangan yang berbeda, dengan tahap dan detail kedua sisi.
3. Ketidakcocokan WAJIB dikelompokkan menurut tahap. Perbedaan yang dikenal (spread live vs tester untuk `SPREAD_TOO_WIDE`, kalender berita untuk `NEWS_BLACKOUT`) WAJIB ditampilkan terpisah dari perbedaan yang tidak dijelaskan.

### Requirement 3: Perbandingan trade
**User story:** Sebagai trader, saya ingin trade live dibandingkan dengan trade replay, agar entry dan exit live terbukti sesuai backtest (PRD tahap 4).

#### Acceptance criteria
1. Alat WAJIB memasangkan trade live dan replay, lalu melaporkan:
   - persentase trade live yang berpasangan, dan sebaliknya;
   - persentase pasangan dengan alasan tutup sama;
   - selisih R rata-rata dan maksimum;
   - selisih harga buka (point) rata-rata.
2. Trade yang tidak berpasangan WAJIB didaftar dengan alasan yang diketahui bila ada (misalnya kandidat pasangannya ditolak di sisi lain pada tahap tertentu).

### Requirement 4: Ambang dan keluaran
**User story:** Sebagai trader, saya ingin tahu dengan jelas apakah kecocokan memenuhi ambang tahap 4.

#### Acceptance criteria
1. Laporan WAJIB menilai ambang:
   - ≥ 95% kandidat live berpasangan dengan tahap sama (dan sebaliknya), dihitung tanpa perbedaan yang dikenal;
   - ≥ 90% trade live berpasangan;
   - ≥ 90% pasangan trade dengan alasan tutup sama;
   - selisih R rata-rata ≤ 0,1R.
2. Setiap ambang WAJIB ditulis LOLOS / TIDAK / SAMPEL KURANG (trade berpasangan < 10).
3. Alat WAJIB hanya membaca kedua DB (read-only). Keluaran teks, ditambah `--out FILE` seperti spec 28.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | PC mati beberapa jam (celah sesi live) | Bagian itu dikeluarkan dari perbandingan; replay tetap jalan menerus | 2.1 |
| EC-02 | Posisi live sudah terbuka sebelum periode replay | Trade itu dikecualikan (replay tidak punya posisi awal); dicatat terpisah | 3.1 |
| EC-03 | Restart EA di tengah periode (versi sama) | Satu periode; kandidat di bar restart tidak ganda (penanda bar) | 2.1 |
| EC-04 | Spread live berbeda dari spread tick tester | Ketidakcocokan `SPREAD_TOO_WIDE` dihitung sebagai perbedaan dikenal | 2.3 |
| EC-05 | Kalender berita MT5 live berbeda dari CSV ekspor | Ketidakcocokan `NEWS_BLACKOUT` sebagai perbedaan dikenal; bila CSV tidak ada, tahap itu tidak dinilai | 1.4, 2.3 |
| EC-06 | Slippage live membuat harga buka berbeda | Selisih harga buka dan R dilaporkan; pasangan tetap sah | 3.1 |
| EC-07 | Zona sudah Used di live dari sesi sebelumnya (Global Variable) | Bisa membuat kandidat replay lolos tetapi live ditolak `ZONE_USED`; ditampilkan sebagai perbedaan yang perlu dicek | 2.2 |
| EC-08 | Input berubah di tengah periode (misalnya ganti versi) | Ditolak, minta periode dipecah | 1.2 |
| EC-09 | Real ticks tester belum tersedia untuk hari terakhir | Periode dipotong ke hari penuh terakhir yang tersedia | 1.3 |

## Keputusan

1. Ambang kandidat ≥ 95% dihitung tanpa perbedaan yang dikenal (spread, kalender berita).
2. Replay lewat skrip tipis `tools/run-live-replay.ps1` yang menyiapkan `-SetInput` dari `inputs_json` sesi live; perbandingan oleh `tools/live_compare.py` yang terpisah.
