# Implementation plan — 39 Filter candle impuls sesudah berita (H13)

Status: Done (2026-10-15)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: suite MQL5 `-Unit`, skenario `-Scenario`, pytest. Setiap task: Red → Green → "Hasil". Commit sekali di akhir spec, lalu push. Satu proses terminal uji, CPU ≤ 50% core.

- [x] 1. Aturan murni impuls dan berita terbaru
  - Red: TC-NW-12, 12b, 12c, 13, 14 di `TestNewsRules.mqh` → FAIL (fungsi belum ada).
  - Green: konstanta `SDB_IMPULSE_*` dan default/batas di `Constants.mqh`; `SdbNewsParams.impulseMult/impulseMinutes`; `ImpulseRatio`, `FindRecentHigh`, `ImpulseDecision` di `NewsRules.mqh`.
  - Verifikasi: unit ALL PASS, compile 0/0.
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 2.2_ · _Tests: TC-NW-12..14_
  - Hasil (2026-10-15): Red build gagal (fungsi/field belum ada); Green compile 0/0, NewsRules pass=16, unit pass=695 fail=0.

- [x] 2. Input, validasi, preset
  - Red: TC-IR-06, TC-SU-04d (62 kunci), kunci baru di `TestPresets.mqh`, TS-136 di `test_presets.py` → FAIL.
  - Green: `InpNewsImpulseMult`, `InpNewsImpulseMinutes` (Inputs.mqh + `inputs_json`); `InputValues` + default + validasi (InputRules.mqh); `gen_presets.py` + regenerasi preset; tabel input README.
  - Verifikasi: unit ALL PASS, pytest PASS.
  - _Requirements: 2.1_ · _Tests: TC-IR-06, TC-SU-04d, TestPresets, TS-136_
  - Hasil (2026-10-15): Red build gagal (field belum ada) + TS-136 FAIL; Green compile 0/0, unit PASS (Codec 17, CoreUtils 41), pytest PASS; 29 preset dengan dua input baru; README. Deviasi: TC-SU-04d sudah dipakai (token), kunci baru diuji di TC-SU-04e.

- [x] 3. Pipeline sinyal dan telemetri
  - Red: TC-SG-44 (urutan keputusan), TC-SG-45 (`impulse` di `context_json`) → FAIL.
  - Green: `SdbSignalFacts.impulseRatio/newsImpulseBlocked/newsImpulseDetail`; `CNewsFilter.ImpulseBlocked`; `CSignalEngine.Facts` menghitung rasio dari `CopyHigh/CopyLow` LTF 14 bar; keputusan di `SignalRules` sesudah blackout ±15 menit; kunci `impulse`; `CSdbApp` meneruskan input ke `SdbNewsParams`.
  - Verifikasi: unit ALL PASS, compile 0/0; skenario SC-17 (berita) tetap PASS.
  - _Requirements: 1.1, 1.4, 2.2, 2.3, 2.4_ · _Tests: TC-SG-44, TC-SG-45, SC-17_
  - Hasil (2026-10-15): compile 0/0; unit pass=699 fail=0 (SignalRules 48, NewsRules 16); SC-17 PASS. TC-SG-21/22/22b memperbarui JSON kanonik dengan `"impulse":null`. Catatan: Red TC-SG-44/45 tidak dijalankan terpisah (uji dan kode ditulis dalam satu langkah; uji gagal compile tanpa field baru).

- [x] 4. Skenario SC-39, versi, regresi
  - Red: file `SC-39_news_impulse.ini/.set` lebih dulu → FAIL (skenario tak dikenal).
  - Green: `CheckSc39` + dispatch; versi 1.37 (EA + harness).
  - Verifikasi: SC-39 PASS; `-All` background PASS.
  - _Requirements: 1.1, 2.3_ · _Tests: SC-39, REG_
  - Hasil (2026-10-15): Red SC-39 FAIL (skenario tak dikenal); Green SC-39 PASS (6 penolakan impuls, semua 12:30–14:00, rasio ≥ 2; 337 dari 337 kandidat membawa `impulse`); versi 1.37; `-All` 38 run PASS.

- [x] 5. Pengukuran IS/OOS/REAL dan keputusan
  - Run: `-Baseline -Period` IS, OOS, REAL dengan default; `trade_diff` vs 1.35 (2307–2318, 2376–2387, 2388–2399); hitung kandidat ditolak detail `impuls`.
  - Laporan Req 3.2; aturan biaya Req 3.3 (trade hilang ≤ 5%, total R turun ≤ 2R per periode).
  - Lolos biaya: laporkan ke user dan tunggu keputusan aktif/tidak. Tidak lolos: default `InpNewsImpulseMult` = 0 (preset ikut, uji preset Red dulu).
  - _Requirements: 3.1–3.4_ · _Tests: RUN-01..03_
  - Hasil (2026-10-15), default 5× / 90 menit vs acuan 1.35:

    | Periode | Sesi | Trade | R/trade | Total R | Hilang | Ditolak impuls |
    |---|---|---|---|---|---|---|
    | IS | 2537–2548 | 121 → 121 | +0,205 → +0,206 | sama | 0 | 14 kandidat |
    | OOS | 2549–2560 | 21 → 19 | +0,524 → +0,485 | 11,0 → 9,2 (−1,8R) | 2 (**9,5%**, +0,907R) | 2 |
    | REAL | 2561–2572 | 55 → 53 | +0,297 → +0,275 | 16,4 → 14,6 (−1,8R) | 2 (3,6%, +0,903R) | 9 |

  - Trade hilang: XAGUSDc dan XAUUSDc BUY 2026-09-04 13:00 sesudah Unemployment Rate USD (rasio 5,37 / 6,04), keduanya untung. Tidak ada trade baru.
  - Syarat biaya Req 3.3 gagal di OOS (9,5% > 5%). Sesuai Req 3.4: default `InpNewsImpulseMult` = 0 (mati), preset ikut (Red TS-136 FAIL, lalu Green); input dan telemetri `impulse` tetap.

- [x] 6. Dokumen dan penutupan
  - PC (bila aktif: §Filter berita, §Parameter input; bila mati: input eksperimen); CHANGELOG; README spec; `fase-5c-overview.md` §8.
  - Tandai Done; commit `feat(sdbot/ea): filter impuls sesudah berita (H13) v1.37 (spec 39)`; push.
  - _Requirements: 3.4, 3.5_
  - Hasil (2026-10-15): PC-38 (input eksperimen); CHANGELOG 1.37; README spec; `fase-5c-overview.md` §8; regresi `-All` dengan default mati.

Validasi manual (di luar tasks): sesudah deploy, pantau `impulse` di `context_json` kandidat live dan penolakan detail `impuls` pada rilis HIGH berikutnya (misalnya NFP).
