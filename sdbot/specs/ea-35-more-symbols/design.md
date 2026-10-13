# Design — Simbol tambahan (H8)

Status: Done (2026-10-13)
Requirements: [requirements.md](requirements.md) (Approved 2026-10-13)

## 1. Overview

- **Tanpa perubahan logika EA.** Kategori aset yang ada sudah aman untuk kandidat:
  - indeks dan energi (base = profit = USD) masuk `SDB_CLASS_OTHER`, dibatasi `SDB_MAX_POS_OTHER_CLASS` = 1 posisi di seluruh akun, dan tidak punya kaki eksposur mata uang (`LegsOf` = 0);
  - ETHUSD masuk kripto bersama BTCUSD (`InpMaxPosCrypto`);
  - cross forex masuk mayor/cross sesuai aturan yang ada.

  Kategori indeks/energi terpisah dengan input sendiri hanya dibuat bila H8 diterima dan batas 1 posisi terbukti menahan entry di live (spec lanjutan).
- **Preset kandidat.** `gen_presets.py` mendapat 17 simbol dengan magic 2026091913–2026091929, kategori, dan spread maksimum 3× median spread M1 7 hari akun cent (aturan PC-22 yang sama; diukur 2026-10-13). Preset ditulis ke `ea/src/Presets/` seperti preset aktif. Preset kandidat tidak dipakai live sampai diterima.
- **Baseline kandidat terpisah.** File `BL-<SIMBOL>.ini` kandidat disimpan di `ea/tests/baseline/kandidat/` agar `-Baseline` biasa tetap 12 simbol (acuan tidak bergeser). Runner mendapat `-BaselineSet kandidat` untuk memakai folder itu, juga untuk `-ProbeHistory`.
- **Pengukuran.**
  1. `-ProbeHistory -BaselineSet kandidat` (histori);
  2. IS semua kandidat;
  3. seleksi §5;
  4. OOS + REAL kelompok terpilih;
  5. backtest 12 bulan `-Deposit 1801.37` kelompok terpilih untuk lot minimum.

## 2. Komponen

| Komponen | Perubahan | Kriteria |
|---|---|---|
| `tools/gen_presets.py` | `SYMBOLS` + 17 kandidat (magic 13–29, kategori), `MAX_SPREAD_POINTS` (tabel §3) | 1.1 |
| `ea/src/Presets/` | 17 preset baru (hasil generate) | 1.1 |
| `tools/tests/test_presets.py` | `EXPECTED_MAGIC` 29 simbol; magic unik | 1.1 |
| `ea/tests/Include/SDBotTests/Suites/TestPresets.mqh` | `TPR_EXPECTED` 29 | 1.1 |
| `ea/tests/baseline/kandidat/BL-<SIMBOL>.ini` | 17 file (M15, OHLC M1, 12 bulan) | 1.4, 2.1 |
| `tools/run-ea-tests.ps1` | `-BaselineSet` ('' = folder utama, 'kandidat' = subfolder) untuk `-Baseline` dan `-ProbeHistory` | 1.4, 2.1 |
| `tools/periods.py` / `tick_history.py` | tidak berubah (dipakai apa adanya) | 1.4 |
| README (tabel simbol, tools), `make_local_presets.py` | baris simbol; preset lokal dibuat bila diterima | 3.3 |
| Versi | tidak naik (tidak ada perubahan kode EA); preset dan alat saja | — |

## 3. Spread maksimum kandidat (3 × median M1 7 hari, point)

| Simbol | Maks | Simbol | Maks | Simbol | Maks |
|---|---|---|---|---|---|
| US30 | 39 | CADJPY | 33 | EURNZD | 66 |
| USTEC | 336 | AUDJPY | 33 | GBPNZD | 72 |
| US500 | 120 | CHFJPY | 63 | AUDCHF | 27 |
| USOIL | 60 | NZDJPY | 42 | GBPAUD | 63 |
| UKOIL | 39 | EURCAD | 45 | GBPCAD | 54 |
| ETHUSD | 300 | EURAUD | 51 | | |

## 4. Error handling

- Kandidat dengan histori tester tidak menutup IS (`-ProbeHistory`): dikeluarkan dari seleksi dan dicatat (Req 1.4).
- Run tester gagal: diulang sekali; bila tetap gagal, kandidat dicatat tidak teruji.
- Lot minimum: kandidat dengan > 50% sinyal ACCEPTED tertolak `LOT_BELOW_MIN` di run `-Deposit` dicatat sebagai tidak cocok untuk saldo live, walau lolos seleksi (Req 1.5).

## 5. Aturan seleksi dan keputusan (ditulis sebelum IS)

1. Kandidat lolos IS bila:
   - ≥ 8 trade;
   - R per trade ≥ +0,05;
   - PF ≥ 1,10.
2. Kelompok terpilih = semua yang lolos. Bila < 3 simbol, H8 ditolak.
3. OOS dan REAL kelompok terpilih (sekali). DITERIMA bila:
   - di OOS dan REAL, total R kelompok > 0;
   - R per trade kelompok ≥ +0,05;
   - R per trade portofolio (12 aktif acuan + kelompok) ≥ R per trade acuan − 0,03 (OOS ≥ +0,391, REAL ≥ +0,194).
4. Batas posisi per kategori tidak aktif di backtest (setiap simbol diuji sendiri). Dampaknya di live (OTHER = 1 posisi) dicatat sebagai risiko, bukan syarat.

## 6. Test case

| ID | Kasus | Harapan | Kriteria |
|---|---|---|---|
| TS-115 | `gen_presets`: 29 preset, magic unik 2026091901–2026091929, spread maks sesuai tabel §3 | sesuai | 1.1 |
| TestPresets | 29 preset lolos validasi input EA | ALL PASS | 1.1 |
| TC-RK (ada) | `AssetClassOf("USD","USD")` = OTHER, `("ETH","USD")` = CRYPTO, `("CAD","JPY")` = CROSS; `LegsOf` base = quote → 0 | sesuai (uji yang ada + kasus baru bila belum ada) | 1.2, EC-01 |
| RUN-00 | `-ProbeHistory -BaselineSet kandidat` | histori per kandidat tercatat | 1.4 |
| RUN-01 | `-Baseline -Period IS -BaselineSet kandidat` | laporan per kandidat; seleksi §5 | 2.1–2.4 |
| RUN-02 | Kelompok terpilih `-Period OOS`, `REAL` | aturan §5.3 | 3.1, 3.2 |
| RUN-03 | Kelompok terpilih 12 bulan `-Deposit 1801.37` risk 0,5% | lot minimum per simbol | 1.5 |
| REG | `-All` | PASS (preset baru tidak mengubah skenario) | — |

## 7. Traceability

| Req | Komponen | Uji |
|---|---|---|
| 1.1 | gen_presets, preset, uji preset | TS-115, TestPresets |
| 1.2, 1.3 | kategori aset yang ada | TC-RK |
| 1.4 | runner `-BaselineSet`, ProbeHistory | RUN-00 |
| 1.5 | runner `-Deposit` | RUN-03 |
| 2.1–2.4 | runner, laporan, aturan §5 | RUN-01 |
| 3.1–3.5 | runner, preset, dokumen | RUN-02 |

## 8. Keputusan yang perlu disetujui

1. **Tanpa kode EA baru.** Indeks dan energi memakai kategori OTHER (1 posisi sekaligus, tanpa eksposur mata uang). Kategori khusus hanya bila terbukti perlu.
2. **Baseline kandidat di subfolder `kandidat/`** + `-BaselineSet`, agar baseline 12 simbol tetap sama.
3. **Spread maksimum 3 × median** (tabel §3), aturan yang sama dengan preset aktif.
4. **Aturan seleksi §5**, termasuk syarat portofolio.
5. **Versi EA tidak naik** (hanya preset dan alat).
