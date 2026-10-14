# Design — Manajemen posisi lebih ringan: TP ke zona lawan (H10)

Status: Done (2026-10-14)
Requirements: [requirements.md](requirements.md) (Approved 2026-10-13)

## 1. Overview

Tanpa perubahan kode EA. Varian dijalankan lewat `-SetInput` pada runner yang ada:

| Varian | `-SetInput` |
|---|---|
| V1 murni | `InpBreakevenR=9`, `InpPartialR=10` |
| V2 tanpa partial | `InpPartialR=10` (BE tetap 1,0) |
| V3 BE 1,5R tanpa partial | `InpBreakevenR=1.5`, `InpPartialR=10` |

Validasi input yang ada (`0 < BE < partial ≤ 10`) menerima ketiga varian. Trailing di EA hanya aktif sesudah BE terpasang, jadi V1 juga tanpa trailing.

Laporan memakai alat yang ada:
- `baseline_report.py` (trade, R, PF, DD per simbol);
- `exit_report.py` (alasan tutup, trade per bulan, lama posisi);
- `trade_diff.py` terhadap acuan (trade hilang akibat posisi lebih lama).

Tambahan: hitungan trade dengan R:R rencana > 9 (BE/partial masih terpicu) lewat query `context_json.rr` pada sesi varian.

## 2. Aturan pilih (ditulis sebelum IS)

Acuan 1.31: IS 121 trade, +0,164R, DD 6,55R; OOS +0,421R; REAL +0,224R.

1. Varian lolos IS bila:
   - R per trade > +0,164;
   - DD ≤ 9,8R;
   - trade ≥ 109.
2. Dari yang lolos: R per trade tertinggi; selisih < 0,02R → urutan V2, V3, V1 (perubahan terkecil dulu).
3. Konfirmasi sekali: DITERIMA bila R per trade OOS ≥ +0,421 dan REAL ≥ +0,224.
4. Bila diterima, default diubah lewat konstanta dan preset (uji preset Red dulu); input "mati" eksplisit (0 = tanpa BE/partial) menjadi spec lanjutan bila varian V1 terpilih.

## 3. Test case

| ID | Kasus | Harapan | Kriteria |
|---|---|---|---|
| RUN-01 | IS V1, V2, V3 | laporan + aturan §2 | 1.1–1.5 |
| RUN-02 | Varian terpilih OOS + REAL | aturan §2.3 | 2.1, 2.2 |
| TS (bila diterima) | preset berisi default baru | Red lalu Green | 2.3 |
| REG (bila diterima) | `-All` | PASS | 2.3 |

## 4. Keputusan yang perlu disetujui

1. **Varian lewat input yang ada** (nilai besar = mati), tanpa kode baru, agar pengujian cepat.
2. **Aturan pilih §2**.
