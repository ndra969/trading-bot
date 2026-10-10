# Implementation plan — 28 Laporan live

Status: Done (2026-10-10)
Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

TDD: pytest lewat `uv run pytest -c sdbot/tools/pytest.ini sdbot/tools/tests`. Tidak ada build, tester, atau perubahan EA. Commit menunggu spec 27 di sesi lain selesai (overview Fase 6).

Setiap task: Red → Green → catat baris "Hasil".

- [x] 1. Scope, hasil trade, dan CLI
  - Red: fixture DB + TS-120, TS-121, TS-122, TS-127 di `tools/tests/test_live_report.py` → FAIL.
  - Green: `default_db`, `resolve_scope`, `trade_stats`, `render` (bagian Periode, Hasil, Alasan tutup, Posisi terbuka), `main` (`--db --from --to --version --out`) sampai PASS.
  - _Requirements: 1.1–1.4, 2.1–2.4_ · _Tests: TS-120–94, TS-127_
  - Hasil (2026-10-09): Red error koleksi (modul belum ada); Green TS-120–94, TS-127 PASS. Satu perbaikan uji: `capsys` dibersihkan sebelum membandingkan keluaran `--out`.

- [x] 2. Eksekusi, kandidat, alert, dan sesi
  - Red: TS-123–98 → FAIL.
  - Green: `exec_stats`, `candidate_counts`, `alert_stats`, `session_health` dan bagiannya di `render` sampai PASS; ruff dan black bersih.
  - _Requirements: 3.1–3.3, 4.1–4.4_ · _Tests: TS-123–98_
  - Hasil (2026-10-09): Red 4 FAIL (fungsi belum ada); Green TS-123–98 PASS; pytest seluruh tools 131 passed; ruff/black bersih.

- [x] 3. Verifikasi pada DB live dan dokumen
  - Jalankan pada `Common\Files\sdbot.sqlite` periode sejak 2026-10-09 (semua versi dan `--version 1.25`); cocokkan hitungan kandidat dan alert dengan query langsung; catat ringkasan di baris "Hasil".
  - README tools (baris `live_report.py`), README spec (baris Fase 6), CHANGELOG (bagian tools).
  - Tandai spec Done. Commit `feat(sdbot/tools): live_report (spec 28)` dan push **sesudah spec 27 di-commit**; sampai itu perubahan dibiarkan di working tree.
  - _Requirements: semua_ · _Tests: semua_
  - Verifikasi DB live (2026-10-09 15:38 UTC): `--from 2026-10-09 --version 1.25` → 12 sesi aktif (magic sesuai simbol), 0 trade, 56 kandidat (NO_VALID_ZONE 54 dari BTCUSDc/XAGUSDc, NO_PA_TRIGGER 2), 20 alert INFO SENT; cocok dengan query langsung. Tanpa filter: 50 sesi sejak 2026-10-08 10:45, 182 kandidat, 7 alert CRITICAL `ACCOUNT_REJECTED` (2026-10-08, preset belum dimuat) tampil di daftar HIGH/CRITICAL. Celah 00:00–07:39 pada `--version 1.25` adalah periode sesi 1.24 (perilaku filter yang benar).
  - Dokumen (2026-10-10, sesudah spec 27 di-commit bb1bdb7): README tools, README spec (bagian Fase 6), CHANGELOG (bagian Tools). Nomor uji digeser ke TS-120..127 karena TS-91..112 sudah dipakai spec 27 dan 31.
