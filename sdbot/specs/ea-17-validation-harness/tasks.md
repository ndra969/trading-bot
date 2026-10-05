# Implementation plan — 17 Alat ukur in-sample / out-of-sample

Status: Done (2026-10-06)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD:
- pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`;
- suite MQL5 lewat `tools/run-ea-tests.ps1 -Unit`.

Setiap task: Red → Green → catat baris "Hasil". Commit sekali di akhir spec. Versi EA naik ke 1.19 di task 2 (skema v4). Backtest dijalankan dengan satu agen tester; run panjang di background.

- [x] 1. Periode dan kedalaman histori real ticks
  - Red: TS-60, TS-61, TS-70 terhadap stub `tools/periods.py` dan `tools/tick_history.py` → FAIL.
  - Green:
    - `tools/periods.py` (`Period`, `load_periods`, `classify`);
    - `tools/tick_history.py` (`months_between`, `short_history`, CLI MetaTrader5 ke terminal uji, menolak jalan saat `run.lock` ada, menutup terminal yang dibukanya);
    - `ea/tests/baseline/periods.ini`.
  - Verifikasi: RUN-01 `tick_history.py` 12 simbol; tanggal tick tertua dicatat di baris Hasil; `periods.ini` (awal IS, `ShortHistory`) disesuaikan dengan hasilnya.
  - _Requirements: 1.1, 1.4, 5.1–5.3_ · _Tests: TS-60, TS-61, TS-70, RUN-01_
  - Hasil (2026-10-05): Red = TS-60, 61, 70 FAIL (stub). Green: `tools/periods.py` (`Period`, `load_periods`, `classify`), `tools/tick_history.py`, `ea/tests/baseline/periods.ini`. Menyimpang dari design §3.7 (sudah diperbarui): `copy_ticks_*` MetaTrader5 menggantung bila diminta tick sejak 2015 dan tidak mencerminkan histori tester untuk logam, jadi kedalaman diukur lewat tester: runner `-ProbeHistory` (periode 2015 kosong → "found history data from A to B") dan `Get-TesterDataLines`; `tick_history.py` menjadi parser jurnal (`parse_probe`, `journal_problems`). `classify` mencocokkan tanggal saja, karena `sessions.tester_model` selalu NULL (EA tidak bisa membaca model) dan `tester_to` = tick terakhir (toleransi 4 hari). RUN-01: bar M1 tester sejak 2024-03-26 (BTC 2018-02-09, XAU 2014); **real ticks hanya sejak 2026-01-05** (XAUUSDc sejak 2026-08-14). Sebelum itu tester diam-diam memakai tick buatan ("real ticks begin from …, every tick generation used"). Dibahas dengan user, opsi A: IS 2024-04..2026-06 dan OOS 2026-07..2026-10 dengan OHLC M1, periode REAL 2026-01..2026-10 real ticks untuk cek realisme, `ShortHistory` = XAUUSDc. PC-25 dan requirements Req 1.2 diperbarui. pytest TS-60, 61, 70 lulus.

- [x] 2. Skema v4: `signal_scores.active`
  - Red: TS-71; TC Logger (DB baru dan DB v3: versi 4, skor `active = 1`) dan TC Migrations (1→4) → FAIL.
  - Green:
    - `schema.py new data "signal score active"` → `0004_signal_score_active.sql`; `seed_sample.sql` blok `@version 4` (satu skor bayangan);
    - `schema.py build` (data_db.sql, fixture, `Migrations.mqh`, lock);
    - `Storage/Logger.mqh` mengikat `active`; antrean entri skor membawa `active` (1 untuk ZONE, TREND, PA);
    - versi EA dan harness 1.19.
  - Verifikasi: `schema.py check` OK (data versi 4); unit ALL PASS; compile 0/0.
  - _Requirements: 4.1–4.4_ · _Tests: TS-71, TC Logger, TC Migrations_
  - Hasil (2026-10-05): Red = TS-71 FAIL (migrasi 0004 belum ada); TC-DB-01e dan TC-SG-24 (active=1) gagal sebelum migrasi. Green: `0004_signal_score_active.sql` (`active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))`), seed `@version 4` (FIB bayangan), `schema.py build` + `check` OK (data versi 4); `Logger.mqh` mengikat `?5 = active` (default 1 untuk ZONE/TREND/PA); versi EA dan harness 1.19. Test lama disesuaikan (insert dengan nama kolom, blok seed 1–4). Build 0/0, unit 599/599, pytest lulus.

- [x] 3. Metrik PF dan DD di laporan dasar
  - Red: TS-62..66 → FAIL.
  - Green: `baseline_report.py`:
    - `profit_factor`, `max_drawdown_pct`, `max_drawdown_r`, `prd_status`;
    - deposit dari `balance_ops` (fallback `--deposit`);
    - tabel per periode (`--periods`), kolom PF dan DD%, baris TOTAL;
    - pembanding per (periode, simbol); tanda simbol `--ticks` / `ShortHistory`;
    - cek kelengkapan skor hanya untuk `active = 1`.
  - Verifikasi: laporan atas sesi v1.18 (868–879, OHLC) dan real ticks 3 bulan (880–891) tercetak dengan PF/DD.
  - _Requirements: 2.1–2.7_ · _Tests: TS-62..66_
  - Hasil (2026-10-05): Red = TS-62..66 FAIL. Green: `baseline_report.py` (`profit_factor`, `fmt_pf`, `max_drawdown_pct`, `max_drawdown_r`, `Summary`, `prd_status`, `load_period_file`, `read_ticks`): tabel per periode (`== IS ==` / `== OOS ==` / `REAL` / `CUSTOM`), kolom PF dan DD%, baris TOTAL dengan PF gabungan dan DD total dalam R, pembanding per (periode, simbol), tanda `*` untuk simbol ShortHistory atau tick bermasalah (disaring `journal_problems`), status kriteria PRD sebagai informasi; kelengkapan skor hanya untuk `active = 1` (fallback DB v3). Deposit tester tidak tercatat di `balance_ops`, jadi dipakai `--deposit` 10000. Verifikasi: sesi 868–879 (v1.18 OHLC 12 bulan) PF per simbol 0,54–3,46; sesi 880–891 (real ticks 3 bulan) PF total 0,98.

- [x] 4. Laporan per nilai komponen
  - Red: TS-67..69 → FAIL.
  - Green: `tools/component_report.py` (`Group`, `group_trades`, `verdict`, render IS/OOS berdampingan, tanda sampel kecil, `--candidates`).
  - Verifikasi: laporan komponen atas sesi 868–879 menampilkan ZONE/TREND/PA per nilai (pemeriksaan isi: Fresh vs Tested sama dengan overview §2).
  - _Requirements: 3.1–3.5_ · _Tests: TS-67..69_
  - Hasil (2026-10-05): Red = TS-67..69 FAIL (modul kosong). Green: `tools/component_report.py` (`Group`, `group_trades`, `verdict`, `render`, `candidate_distribution`, `render_candidates`, CLI `--sessions A-B --periods --candidates --min-n`). Verifikasi atas sesi 868–879: ZONE 30 +0,065R (171) vs 15 −0,093R (77); TREND 0 +0,396R (25), 7 +0,038R (36), 15 −0,039R (187); PA 10 ditandai sampel kecil (15). Sama dengan overview §2. pytest 101/101.

- [x] 5. Runner `-Period` dan cek real ticks
  - Green:
    - `run-ea-tests.ps1 -Period IS|OOS|ALL` (prioritas opsi bebas > periode > `BL-*.ini`; batas waktu default 3600 detik);
    - opsi `-FromDate`, `-ToDate`, `-Model` (sudah ditambahkan 2026-10-05) didokumentasikan;
    - baris jurnal agen tentang tick buatan atau histori tick kosong ke `baseline-ticks.txt`; pola teks diambil dari jurnal nyata (Red: contoh baris asli di pytest bila pola diparse Python, atau run pendek simbol tanpa tick);
    - laporan dipanggil dengan `--periods` dan `--ticks`.
  - Verifikasi: run pendek `-Period OOS -Symbols EURUSDc` menghasilkan laporan berlabel OOS dengan PF/DD.
  - _Requirements: 1.1–1.6_ · _Tests: RUN-02 (sebagian)_
  - Hasil (2026-10-05): `run-ea-tests.ps1 -Period IS|OOS|ALL|REAL` (periods.ini dibaca runner; opsi bebas menang; id run `BL-<periode>-<simbol>`; batas waktu default 3600 detik), `-FromDate/-ToDate/-Model`, `-ProbeHistory`; `Get-TesterDataLines` membaca ekor 200.000 baris jurnal (baris tick ditulis di awal run lalu tertimbun log EA) dengan pola dari jurnal nyata ("real ticks begin", "every tick generation", "no history data", "found history data") ke `baseline-ticks.txt`; laporan dipanggil dengan `--periods` dan `--ticks`. Verifikasi: `-Baseline -Period OOS -Symbols EURUSDc` → laporan `== OOS ==` dengan PF 0,75 dan DD 1,0% (sesi 900); probe XAU Jan 2026 menandai "every tick generation used".

- [x] 6. Acuan Fase 5 dan dokumen
  - Run: `-Baseline -Period ALL` v1.19 12 simbol (background, satu agen); `component_report.py` atas sesi acuan.
  - Dokumen: README (alat `-Period`, `tick_history.py`, `component_report.py`), CHANGELOG 1.19 dengan hasil acuan (trade, PF, DD, R/trade per periode), README spec (sesi acuan), `shared/schema/README.md` bila perlu.
  - Regresi akhir: build 0/0, `-All` (background), pytest, `schema.py check`.
  - Tandai spec Done; commit `feat(sdbot): alat ukur IS/OOS dan skema v4 v1.19 (spec 17)`; git push.
  - Bila hasil acuan menunjukkan simbol tanpa real ticks atau durasi jauh di atas perkiraan, temuan dibahas dulu.
  - _Requirements: 1.5, 1.6, 6.1, 6.2_ · _Tests: RUN-02, RUN-03, semua_
  - Hasil (2026-10-05): `-Baseline -Period ALL` v1.19, 25 run, 1 jam 2 menit, sesi DB 901–924 (IS 901–912, OOS 913–924): IS 493 trade, PF 1,06, R/trade +0,029, DD maks simbol 6,9%, DD total 17,0R; OOS 52 trade, PF 1,07, +0,036R, DD 1,5%. Temuan run: kriteria jumlah trade PC-22 ikut menggagalkan OOS 3 bulan → kini hanya untuk periode panjang (TS-65b); format durasi kehilangan jam → hh:mm:ss. `component_report.py` atas 901–924: ZONE 30 +0,041R vs 15 +0,001R (IS); TREND 0 +0,001R (IS, 50 trade); semua status `SAMPEL KURANG` karena OOS hanya 52 trade (dibahas di spec 22). Dokumen: README (status, alat), CHANGELOG 1.19, README spec, PC-26. Regresi: build 0/0, unit 599/599, 26 skenario PASS (15:19), pytest 102/102, `schema.py check` OK (data v4).

## Validasi manual (di luar tasks)

- [ ] Sinkron PC-25 ke dokumen induk Claude Docs (bersama perubahan skema v4 di PRD-Backoffice, dicatat sebagai PC baru di task 2).
