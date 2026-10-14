# Design — Zona M30 (H9)

Status: Done (2026-10-14)
Requirements: [requirements.md](requirements.md) (Approved 2026-10-13)

## 1. Overview

- **Input timeframe.** Tiga input baru `InpHtfTimeframe`, `InpMtfTimeframe`, `InpLtfTimeframe` (ENUM_TIMEFRAMES, default `PERIOD_CURRENT`). Fungsi murni baru `ResolveTimeframes(style, inH, inM, inL, &htf, &mtf, &ltf)` di `Core/Utils.mqh`:
  - semua `PERIOD_CURRENT` → `StyleTimeframes(style)` (perilaku sekarang);
  - semua diisi → pakai input.

  Dua pemanggil `StyleTimeframes` di `CSdbApp` (`InitPositions` untuk ATR trailing LTF, `InitAnalysis` untuk struktur, zona, dan trigger) diganti `ResolveTimeframes`. Komponen lain menerima timeframe dari App, jadi tidak berubah.
- **Validasi.** `ValidateInputValues`: sebagian diisi → gagal; `PeriodSeconds(htf) > PeriodSeconds(mtf) > PeriodSeconds(ltf)` wajib.
- **Telemetri.** `inputs_json` 60 kunci; `zone_ref` otomatis memakai teks MTF (`M30-<waktu>-D`) lewat `ZoneTfText` yang ada. `signals.style` tetap gaya (skema tetap v5).
- **Pengukuran.** V1 `-SetInput InpHtfTimeframe=16385,InpMtfTimeframe=30,InpLtfTimeframe=15` (H1/M30/M15); V2 `InpHtfTimeframe=16388,...` (H4/M30/M15). Aturan pilih §4.

## 2. Komponen

| Komponen | Perubahan | Murni | Kriteria |
|---|---|---|---|
| `Core/Utils.mqh` | `ResolveTimeframes` | ya | 1.2, 1.4 |
| `Core/InputRules.mqh` | `InputValues.htfTf/mtfTf/ltfTf`; validasi sebagian dan urutan | ya | 1.3 |
| `Core/Inputs.mqh` | 3 input + `inputs_json` kunci 58–60 (`EnumToString`) | — | 1.1, 1.5 |
| `App/SdbApp.mqh` | dua pemanggil → `ResolveTimeframes(cfg.style, cfg.inputs.htfTf, ...)` | — | 1.2 |
| `tools/gen_presets.py` + preset | `InpHtfTimeframe=0`, `InpMtfTimeframe=0`, `InpLtfTimeframe=0` | — | 1.4 |
| Uji `TestCodec` (60), `TestPresets` (kunci), `test_presets` (TS-125) | — | — | 1.5 |
| `ea/tests/scenarios/SC-36_*` | harness pipeline EURUSDc H1/M30/M15 | — | 1.2, 1.5 |
| README, `docs/flows/` | baris input | — | 1.1 |
| Versi | 1.33; 1.34 bila default berubah | — | 3.3 |

## 3. Error handling

Input tidak sah (sebagian diisi, urutan salah) → `INIT_PARAMETERS_INCORRECT` dengan pesan validasi. Histori M30 kurang → perilaku `MarkNotReady`/peta zona kosong yang ada.

## 4. Aturan pilih (ditulis sebelum IS)

Acuan 1.31: IS 121 trade (4,5/bulan), +0,164R, +19,8R; OOS 21 trade, +8,84R; REAL 55 trade, +12,32R.

1. Varian lolos IS bila:
   - ≥ 182 trade;
   - R per trade ≥ +0,05 dan PF ≥ 1,10;
   - total R ≥ +19,8R;
   - ≥ 8 trade per simbol.
2. Dari yang lolos: total R tertinggi; selisih < 2R → R per trade lebih tinggi.
3. Konfirmasi sekali: DITERIMA bila di OOS dan REAL:
   - total R ≥ acuan;
   - R per trade ≥ +0,05;
   - trade ≥ 1,5× acuan (OOS ≥ 32, REAL ≥ 83).

## 5. Test case

| ID | Kasus | Harapan | Kriteria |
|---|---|---|---|
| TC-CU-19 | `ResolveTimeframes`: semua CURRENT + DAY → H4/H1/M15; H1/M30/M15 → H1/M30/M15 | sesuai | 1.2, 1.4 |
| TC-IR-05 | Validasi: semua 0 lolos; H1/M30/M15 lolos; hanya MTF → gagal; M30/H1/M15 → gagal; H1/M30/M30 → gagal | pesan menyebut input | 1.3, EC-01, EC-02 |
| TC-SU-04c, TestPresets, TS-125 | 60 kunci; preset berisi 3 input = 0 | sesuai | 1.5, 1.4 |
| SC-36 | **Given** harness pipeline EURUSDc 2026.04.01–2026.09.26, H1/M30/M15. **Then** ≥ 1 kandidat dengan `zone_ref LIKE 'M30-%'`, ≥ 1 ACCEPTED, `inputs_json` memuat ketiga input | sesuai | 1.2, 1.5 |
| REG | `-All` default | PASS, perilaku identik | 1.4 |
| RUN-01 | IS V1, V2 | aturan §4 | 2 |
| RUN-02 | Varian terpilih OOS + REAL | aturan §4.3 | 3 |

## 6. Keputusan yang perlu disetujui

1. **Input timeframe mengganti pasangan gaya** (semua atau tidak sama sekali), bukan gaya baru. Mencoba kombinasi berikutnya tidak perlu perubahan skema.
2. **Validasi urutan HTF > MTF > LTF** lewat `PeriodSeconds`.
3. **Aturan pilih §4**, termasuk syarat total R dan frekuensi di OOS/REAL.
4. **Versi 1.33** (1.34 bila diterima).
