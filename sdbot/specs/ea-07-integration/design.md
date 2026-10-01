# Design — 07 Integrasi dan penutup Fase 1

Status: Done (2026-10-01)
Requirements: [requirements.md](requirements.md)

## 1. Overview

Spec ini menyambungkan hasil spec 01–06 menjadi paket Fase 1 yang bisa dipasang di akun cent tanpa strategi: EA terpasang dengan preset per simbol, memvalidasi akun, mencatat sesi dan snapshot, memantau risiko, mengelola posisi (bila ada), dan siap menerima modul strategi di Fase 3. Tambahan kode kecil: metrik `OnTester`, penanda preset, dan dukungan optimasi di runner. Sisanya file data (preset, query), dokumen, dan sinkronisasi PRD.

## 2. Komponen

### 2.1 Metrik `OnTester`

```cpp
// App/TesterMetric.mqh [murni]
double TesterMetric(double totalR, int trades, double maxDdPct, int minTrades);
// = (totalR / trades) / maxDdPct; 0 bila trades < minTrades atau maxDdPct <= 0 (Req 1.1, 1.2)
```

- `CClosureTracker` menjumlahkan `rResult` dan menghitung closure dengan R diketahui di memori (`TotalR()`, `TradesWithR()`); closure dengan R kosong tidak dihitung (EC-06).
- `CSdbApp::OnTester()` = `TesterMetric(tracker.TotalR(), tracker.TradesWithR(), TesterStatistics(STAT_EQUITY_DDREL_PERCENT), SDB_TESTER_MIN_TRADES)`. Harness memanggil `CSdbApp::OnTester()` yang sama (1.4); restart harness memulai hitungan baru (harness skenario restart tidak dipakai untuk optimasi).
- Optimasi tidak menulis DB karena `SdbDbTargetForRuntime()` = `NONE` (spec 03); SC-09 membuktikannya (1.3, EC-08).

### 2.2 Penanda preset (EC-02)

Input baru `InpPresetTag` (grup Umum, string, default kosong) di `Inputs.mqh`, `CurrentInputsJson`, `SdbAppConfig.presetTag`, dan tabel input README. `CSdbApp::OnInit`: tag tidak kosong dan ≠ `_Symbol` → WARN sekali "preset <tag> dimuat di chart <simbol>" (2.6). Pemeriksaan murni `PresetMatchesSymbol(tag, symbol)` di `Core/Utils.mqh` (kosong → cocok).

### 2.3 Preset (`ea/src/Presets/`)

```
SDBot_DAY_EURUSDc.set  …01  forex major      SDBot_DAY_EURJPYc.set  …03  forex cross
SDBot_DAY_GBPUSDc.set  …02  forex major      SDBot_DAY_GBPJPYc.set  …04  forex cross
SDBot_DAY_USDJPYc.set  …05  forex major      SDBot_DAY_XAUUSDc.set  …10  komoditas
SDBot_DAY_USDCHFc.set  …06  forex major      SDBot_DAY_XAGUSDc.set  …11  komoditas
SDBot_DAY_AUDUSDc.set  …07  forex major      SDBot_DAY_BTCUSDc.set  …12  crypto
SDBot_DAY_USDCADc.set  …08  forex major
SDBot_DAY_NZDUSDc.set  …09  forex major
```

Isi: semua input Fase 1 dengan default PRD (`InpRiskPerTradePct=0.5`, dst.), `InpSymbolSuffix=c`, `InpAllowLiveTrading=false`, `InpMagicNumber` sesuai tabel, `InpPresetTag=<SIMBOL>c`. Komentar `;` di atas: kategori, cara mengaktifkan akun cent (`InpAllowLiveTrading=true`), larangan mengisi token di file yang di-commit, dan nilai referensi bot Python untuk kategori itu (spread maks, sesi, jarak SL default) yang belum punya input (keputusan PC-12 no. 1). File hanya berisi ASCII agar dialog Load MT5 membacanya apa pun encoding-nya. File dibangkitkan dari satu tabel oleh `tools/gen-presets.py` (12 file identik kecuali magic, tag, dan komentar), dan pytest memastikan file di repo sama dengan hasil generator.

Uji:
- pytest `tools/tests/test_presets.py` (TP-01..05): 12 file ada; magic unik dan sesuai PC-10; `InpAllowLiveTrading=false`, `InpSymbolSuffix=c`; tidak ada kunci rahasia (`Token`, `ChatID`, `MetaQuotes`) bernilai; file = hasil generator.
- MQL5 suite `TestPresets` (TC-IN-04): runner menyalin `ea/src/Presets/*.set` ke `Common\Files\sdbot_presets\` sebelum unit run (sandbox MQL5 tidak bisa membaca folder `Presets`); suite membaca setiap file, mengisi `InputValues` dari pasangan kunci=nilai, dan memanggil `ValidateInputValues` (2.5). Tidak ada file → FAIL, bukan lewat diam-diam.

### 2.4 Query (`tools/queries/*.sql`)

| File | Isi |
|---|---|
| `summary_by_symbol_version.sql` | jumlah, win rate, profit factor, expectancy R per simbol × `ea_version` |
| `close_reasons.sql` | jumlah dan rata-rata R per `reason` |
| `be_leak.sql` | closure `BE_STOP` dengan `mfe_r ≥ 1`: R tersimpan vs MFE |
| `losers_never_green.sql` | closure R < 0 dengan `mfe_r < 0.2` (entry salah arah) |
| `by_session_inputs.sql` | performa per `sessions.input_hash` |
| `by_run.sql` | ringkasan per `run_key` (satu backtest = satu baris) |
| `balance_ops.sql` | operasi saldo per bulan |
| `alerts_by_severity.sql` | jumlah alert per severity dan status kirim |

Join posisi selalu `login + run_key + position_id` (3.2), lewat `v_trade_results` bila cukup. Diuji di `tools/tests/test_queries.py` (TQ-01..08) terhadap `data_latest_sample.sqlite`: jalan tanpa error, kolom sesuai, ≥ 1 baris (3.3). `seed_sample.sql` mendapat blok `-- @version 2` berisi satu sesi tester (`run_key` = id sesi) dengan trade, closure `BE_STOP` ber-MFE ≥ 1, closure SL ber-MFE < 0.2, dan operasi saldo, agar setiap query punya baris. `test_seed_blocks_are_split_per_version` diperbarui ke `{1, 2}`.

### 2.5 Runner: optimasi dan salinan preset

- Unit run: sebelum tester dijalankan, runner menyalin preset ke `Common\Files\sdbot_presets\` (lalu menghapusnya sesudah run).
- Skenario optimasi: `.ini` dengan `Optimization=1` dan `OptimizationCriterion=6` (custom max), `.set` dengan rentang input (`HarnessSlPoints=200||200||100||300||Y` → 2 pass). Runner mendeteksi mode ini lalu: mencatat ukuran dan `LastWriteTime` `sdbot_tester.sqlite` sebelum run; menjalankan tester dengan `Report=<tmp>\opt-<runId>`; sesudahnya memastikan file DB tidak berubah, laporan XML ada, berisi ≥ 2 pass, dan kolom hasil custom terisi angka (4.2). Hasil ditulis dalam format yang sama dengan skenario lain (PASS/FAIL per pemeriksaan) sehingga ringkasan `-All` seragam.
- `-All` mencatat durasi total di ringkasan (4.3).

### 2.6 Dokumen

- `ea/tests/manual-checklist.md`: semua MC dari spec 01–06 + daftar "skenario uji fungsi wajib" PRD, kolom tanggal/hasil/catatan; item Fase 3 diberi tanda (5.1).
- `sdbot/docs/flows/`: `init.md`, `tick.md`, `timer.md`, `order-execution.md`, `risk-monitor.md`, `closure.md` (Mermaid), mengikuti kode v1.06 (5.2).
- `sdbot/CHANGELOG.md`: bagian EA 1.00–1.06 per spec, ringkasan regresi (jumlah test, skenario, durasi) (5.3).
- Sinkron PRD/RULES: skill `sdbot-docs-sync` menerapkan PC-01..PC-12 ke dokumen induk di claude.ai lalu mengekspor salinan repo; entri pindah ke "Done" (5.4). Dijalankan setelah semua task kode hijau.
- Versi EA `1.06`, harness `1.06` (5.5).

## 3. Data models

- `SdbAppConfig.presetTag`; input `InpPresetTag` (README, JSON input: TC-SU-04c 21 → 22).
- Konstanta: `SDB_TESTER_MIN_TRADES` 30.
- Tidak ada perubahan skema DB (hanya data contoh `seed_sample.sql`).

## 4. Test case

| ID | Kasus | Harapan | Req |
|---|---|---|---|
| TC-IN-01 | `TesterMetric(30, 100, 10, 30)` | 0.03 | 1.1 |
| TC-IN-02 | `TesterMetric(5, 10, 10, 30)` | 0 (trade < 30) | 1.2, EC-01 |
| TC-IN-03 | `TesterMetric(30, 100, 0, 30)`; `TesterMetric(-20, 40, 5, 30)` | 0; −0.1 | 1.1, 1.2 |
| TC-IN-04 | setiap preset di `Common\Files\sdbot_presets` dibaca dan divalidasi | 12 file, semua lolos | 2.5 |
| TC-IN-05 | `PresetMatchesSymbol("EURUSDc", "EURUSDc")`; `("EURUSDc", "GBPUSDc")`; `("", "GBPUSDc")` | true; false; true | 2.6, EC-02 |
| TC-IN-06 | `CClosureTracker`: closure R 2.0, closure R NULL, closure R −1.0 | `TotalR` 1.0, `TradesWithR` 2 | 1.1, EC-06 |
| TP-01..05 | pytest preset (§2.3) | lolos | 2.1–2.5, EC-07 |
| TQ-01..08 | setiap query terhadap fixture | jalan, kolom sesuai, ≥ 1 baris | 3.1–3.3 |
| SC-09 | optimasi 2 pass harness (entry tiap 20 bar, 1 minggu) | DB tester tidak berubah; laporan berisi 2 pass dengan hasil custom terisi | 1.3, 4.2, EC-08 |
| REG | `run-ea-tests.ps1 -All` | semua PASS, durasi < 30 menit dicatat | 4.1, 4.3 |

## 5. Traceability

| Requirement | Komponen | Uji |
|---|---|---|
| 1 | `TesterMetric`, `CClosureTracker` (R di memori), `CSdbApp::OnTester` | TC-IN-01..03, 06, SC-09 |
| 2 | preset, `gen-presets.py`, `TestPresets`, `InpPresetTag` | TC-IN-04..05, TP-01..05 |
| 3 | `tools/queries`, `seed_sample.sql` v2, `test_queries.py` | TQ-01..08 |
| 4 | `run-ea-tests.ps1` (optimasi, salinan preset, durasi) | REG, SC-09 |
| 5 | checklist, flows, CHANGELOG, `sdbot-docs-sync`, versi 1.06 | review dokumen |

## 6. Keputusan (no. 2–5 disetujui 2026-10-01)

1. **[Disetujui 2026-10-01, PC-12]** Keputusan requirements 1–5.
2. **Preset dibangkitkan generator** (`tools/gen-presets.py`) dari satu tabel, agar 12 file tidak menyimpang satu sama lain; pytest memastikan file di repo sama dengan hasil generator.
3. **Validasi preset dengan `ValidateInputValues` asli lewat salinan ke `Common\Files`**, bukan menulis ulang aturan validasi di Python (satu sumber aturan).
4. **SC-09 diperiksa oleh runner** (DB dan laporan XML), bukan oleh harness, karena pass optimasi berjalan di agen tester yang menulis ke sandbox-nya sendiri.
5. **Sinkron PRD lewat skill `sdbot-docs-sync`** di akhir spec, setelah semua task kode hijau, karena isinya bergantung pada hasil akhir spec ini.
