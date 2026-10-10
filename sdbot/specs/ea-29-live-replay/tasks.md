# Implementation plan — 29 Replay tester periode live

Status: Done (2026-10-10)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Tidak ada perubahan EA. Tester hanya dipakai di task 4, sesudah spec 27 di sesi lain selesai memakainya. Commit bersama spec 28, sesudah spec 27 di-commit.

Setiap task: Red → Green → catat baris "Hasil".

- [x] 1. Input replay dari sesi live
  - Red: TS-128, TS-129 di `tools/tests/test_live_compare.py` → FAIL.
  - Green: `enum_values`, `replay_inputs`, `ReplayInputError`, subperintah `inputs` sampai PASS.
  - _Requirements: 1.1, 1.2_ · _Tests: TS-128, TS-129_
  - Hasil (2026-10-09): Red error koleksi; Green TS-128, TS-129 PASS. Tambahan `--version` (design §3 catatan versi): DB live EURUSDc 2026-10-09 tanpa filter ditolak (hash 1.24 sampai 07:39 UTC, lalu 1.25); dengan `--version 1.25` → 50 kunci (53 dikurangi 3 yang dibuang).

- [x] 2. Perbandingan kandidat, trade, dan ambang
  - Red: TS-130–105 → FAIL.
  - Green: `live_windows`, `pair_candidates`, `pair_trades`, `assess`, `render`, subperintah `compare` sampai PASS; ruff dan black bersih.
  - _Requirements: 2.1–2.3, 3.1–3.2, 4.1–4.3_ · _Tests: TS-130–105_
  - Hasil (2026-10-09): Red 4 FAIL; Green TS-130–105 PASS; pytest tools 137 passed; ruff/black bersih. Deviasi design: selisih harga buka dalam R (tabel `trades` tanpa ukuran point), dicatat di design §3.1.

- [x] 3. Skrip replay
  - `tools/run-live-replay.ps1` (`-From -To -Symbols -ExportCalendar -DryRun`, cek terminal tester hidup, ringkasan `replay=A-B`).
  - Verifikasi RUN-01: `-DryRun` untuk periode live v1.25 (2026-10-09 ..) mencetak 12 perintah dengan `-SetInput` lengkap; cocokkan beberapa nilai dengan `inputs_json`.
  - _Requirements: 1.1–1.5_ · _Tests: RUN-01_
  - Hasil (2026-10-09): `run-live-replay.ps1` (`-From -To -Symbols -Version -ExportCalendar -DryRun`). RUN-01 `-DryRun -Version 1.25` periode 2026-10-09: 12 perintah, masing-masing 50 kunci; nilai EURUSDc cocok dengan `inputs_json` sesi 49 (magic 2026091901, `InpScoreFibMode` SHADOW → 1, `InpLogLevel` INFO → 1, `InpMaxSpreadPoints` 24). Dua perbaikan saat verifikasi: `${testerDb}` (PowerShell membaca `$testerDb?mode` sebagai nama variabel) dan runner dipanggil di proses yang sama agar array `-SetInput` utuh.

- [x] 4. Replay pertama, penyesuaian v1.28, dan dokumen
  - Penyesuaian sesudah spec 27 (v1.28, 2026-10-10): `LEGACY_INPUTS` (TS-134) agar replay EA 1.28 meniru perilaku versi live; nomor uji TS-128..134.
  - Bila tester bebas: replay periode live v1.25 (2026-10-09, sesi sejak 07:39 UTC), lalu `compare`; catat laporan dan penjelasan setiap ketidakcocokan (RUN-02). Ketidakcocokan yang tidak terjelaskan dicatat sebagai calon bug untuk spec perbaikan.
  - README tools (`live_compare.py`, `run-live-replay.ps1`), README spec, CHANGELOG.
  - Tandai spec Done; commit `feat(sdbot/tools): replay live dan live_compare (spec 29)`; push.
  - Validasi berkala berikutnya memakai periode live versi yang sedang jalan (1.28 sesudah live diganti), minimal beberapa hari trading penuh.
  - _Requirements: semua_ · _Tests: TS-134, RUN-02_
  - Hasil (2026-10-10): RUN-02 replay 2026-10-09 `--version 1.25` dengan EA 1.28 + `LEGACY_INPUTS` (53 input), kalender diekspor (18.970 event), sesi tester 1780–1791. `compare`: kandidat live 58, replay 58, tahap sama 58 (cocok 100% di kedua sisi, tanpa perbedaan dikenal atau tidak dikenal); 0 trade di kedua sisi → ambang trade SAMPEL KURANG. Peringatan versi 1.25 vs 1.28 hanya untuk input yang diisi nilai lama.
  - Perbaikan saat replay: splatting hashtable ke runner (splatting array mengirim `-Baseline` sebagai argumen posisi); keberhasilan dinilai dari sesi tester baru, karena kode 1 runner berasal dari kriteria jumlah trade `baseline-report` yang tidak berlaku untuk replay satu hari; label peringatan membedakan input nilai lama dari default versi replay.
  - pytest tools 138 passed; ruff/black bersih.
