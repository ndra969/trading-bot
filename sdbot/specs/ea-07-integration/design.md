# Design — 07 Integrasi dan penutup Fase 1

Status: Draft
Requirements: [requirements.md](requirements.md)

## 1. Overview

Spec ini menyambungkan hasil spec 01–06 menjadi paket Fase 1 yang bisa dirilis ke akun cent tanpa strategi: EA terpasang, memvalidasi akun, mencatat sesi dan snapshot, memantau risiko, dan siap menerima modul strategi di Fase 3.

## 2. Komponen

### 2.1 Metrik `OnTester`

```cpp
double TesterMetric(double totalR, int trades, double maxDdPct, int minTrades); // [murni]
// = (totalR / trades) / maxDdPct, atau 0 bila trades < minTrades atau maxDdPct <= 0
```

`CSdbApp::OnTester()` mengambil `totalR` dan `trades` dari `CClosureTracker` (spec 06) dan `maxDdPct` dari `TesterStatistics(STAT_EQUITY_DDREL_PERCENT)`.

### 2.2 Preset

```
ea/src/Presets/SDBot_DAY_EURUSDc.set   InpMagicNumber=2026091901
ea/src/Presets/SDBot_DAY_GBPUSDc.set   InpMagicNumber=2026091902
ea/src/Presets/SDBot_DAY_EURJPYc.set   InpMagicNumber=2026091903
ea/src/Presets/SDBot_DAY_GBPJPYc.set   InpMagicNumber=2026091904
```

Nomor magic mengikuti blok SDBot jika R2-1 disetujui (`…00` dicadangkan untuk harness). Uji preset: suite `TestPresets` membaca file `.set` dari folder `Presets/SDBot` (junction) dengan `FileOpen` dan memanggil `ValidateInputValues` (2.4). Input `InpPresetTag` (string, default kosong) diisi nama pair di preset agar EC-02 terdeteksi.

### 2.3 Query (`tools/queries/*.sql`)

| File | Isi |
|---|---|
| `summary_by_symbol_version.sql` | jumlah, win rate, profit factor, expectancy R per simbol × `ea_version` |
| `close_reasons.sql` | jumlah dan rata-rata R per `reason` |
| `be_leak.sql` | closure `BE_STOP` dengan `mfe_r ≥ 1`, rata-rata R yang tersimpan vs MFE |
| `losers_never_green.sql` | closure R < 0 dengan `mfe_r < 0.2` (entry salah arah) |
| `by_session_inputs.sql` | performa per `sessions.input_hash` |
| `balance_ops.sql` | operasi saldo per bulan |
| `alerts_by_severity.sql` | jumlah alert per severity dan status kirim |

Diuji di `sdbot/tools/tests/test_queries.py` terhadap `data_latest_sample.sqlite` (spec 03): setiap query jalan tanpa error dan mengembalikan kolom yang diharapkan (3.2). `seed_sample.sql` (spec 03) diperluas dengan closure berbagai alasan agar setiap query punya baris hasil.

### 2.4 Regresi dan SC-08

`run-ea-tests.ps1 -All` = `-Unit` lalu setiap `scenarios/SC-*.ini` berurutan; hasil dikumpulkan, exit 0 hanya jika semua PASS (4.1). SC-08: konfigurasi tester optimasi 2 pass (`Optimization=1` dengan satu input divariasikan 2 nilai) → runner mencatat `LastWriteTime` `sdbot_tester.sqlite` sebelum dan sesudah → harus sama, dan file hasil optimasi (XML report) berisi nilai metrik custom (4.2).

### 2.5 Dokumen

- `sdbot/docs/flows/`: `init.md`, `tick.md`, `timer.md`, `order-execution.md`, `risk-monitor.md`, `closure.md` (Mermaid), diambil dari design spec 02–06.
- `sdbot/CHANGELOG.md`: bagian EA dengan versi, daftar spec, ringkasan regresi (jumlah test, durasi).
- Versi EA: spec 01 `0.0`, naik MINOR setiap spec 02–06 selesai (`0.1` … `0.5`), Fase 1 selesai `0.6`. Versi `1.0` dicadangkan untuk rilis setelah validasi Fase 6.

## 3. Test case

| ID | Kasus | Harapan | Req |
|---|---|---|---|
| TC-IN-01 | `TesterMetric(30, 100, 10, 30)` | 0.03 | 1.1 |
| TC-IN-02 | `TesterMetric(5, 10, 10, 30)` | 0 (trade < 30) | 1.2 |
| TC-IN-03 | `TesterMetric(30, 100, 0, 30)` | 0 | 1.2 |
| TC-IN-04 | setiap preset dibaca dan divalidasi | lolos | 2.4 |
| TC-IN-05 | preset berisi kunci `Telegram` atau `Token` bernilai | gagal | 2.3 |
| TQ-01..07 | setiap query di §2.3 terhadap fixture | jalan, kolom sesuai | 3.2 |
| SC-08 | optimasi 2 pass | DB tester tidak berubah, metrik ada di report | 1.3, 4.2 |
| REG | `run-ea-tests.ps1 -All` | semua PASS, durasi dicatat | 4.1, 4.3 |

## 4. Traceability

| Requirement | Komponen | Uji |
|---|---|---|
| 1 | `TesterMetric`, `CSdbApp::OnTester` | TC-IN-01..03, SC-08 |
| 2 | preset, `TestPresets` | TC-IN-04..05 |
| 3 | `tools/queries`, `test_queries.py` | TQ-01..07 |
| 4 | `run-ea-tests.ps1 -All` | REG, SC-08 |
| 5 | checklist, flows, CHANGELOG, PRD/RULES | review dokumen |

## 5. Keputusan yang perlu disetujui

1. **Skema versi EA** `0.0` → `0.6` sepanjang Fase 1, `1.0` setelah validasi Fase 6.
2. **Minimal 30 trade** agar metrik optimasi dihitung.
3. **Preset dengan `InpAllowLiveTrading = false`** walau untuk akun cent, sehingga trader harus mengaktifkannya dengan sadar.
