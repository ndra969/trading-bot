# SDBot

Expert Advisor MQL5 untuk MetaTrader 5 (zona Supply & Demand + skor konfluensi) beserta backoffice lokal. Proyek terpisah dari bot Python di repo yang sama.

- Kebutuhan produk: [docs/PRD-EA.md](docs/PRD-EA.md), [docs/PRD-Backoffice.md](docs/PRD-Backoffice.md)
- Aturan kode dan struktur: [docs/RULES.md](docs/RULES.md)
- Rencana kerja per spec: [specs/README.md](specs/README.md)

Status: Fase 1 (fondasi) sedang dibangun. Belum ada logika trading.

## Konfigurasi dan tuning

PRD mengganti konfigurasi YAML bot Python dengan **input EA** yang disimpan sebagai file `.set`. Setiap jenis konfigurasi punya satu tempat:

| Apa | File | Diubah oleh | Kapan berlaku |
|---|---|---|---|
| **Input EA** (semua angka yang bisa di-tuning: risiko, BE, partial, trailing, skor, filter) | `ea/src/Include/SDBot/Core/Inputs.mqh`: satu-satunya tempat deklarasi `input`, dengan default dari PRD | Developer (default); trader lewat tab Inputs MT5 atau file `.set` | Saat EA dipasang atau input diubah (EA re-init) |
| Batas aman input | `ea/src/Include/SDBot/Core/InputRules.mqh` | Developer | EA menolak jalan jika input di luar batas |
| **Preset per pair** | `ea/src/Presets/SDBot_DAY_<PAIR>c.set` (EURUSDc, GBPUSDc, EURJPYc, GBPJPYc) | Hasil tuning, di-commit | Dimuat di tab Inputs: Load |
| Preset pribadi (rahasia) | `*.local.set`, misalnya `SDBot_DAY_EURUSDc.local.set` | Trader, **tidak di-commit** | Berisi token dan chat ID Telegram (sama dengan `.env` bot Python) |
| Konstanta tetap dari PRD | `ea/src/Include/SDBot/Core/Constants.mqh` (retry 3x, cooldown 30 detik, DD info 5%, pulih 8%, margin 300%/200%, dll.) | Developer, lewat perubahan kode + compile | Versi EA berikutnya |
| Setting dari panel backoffice (Fase B5) | tabel `settings` di `sdbot_control.sqlite` | Admin lewat panel | Siklus timer berikutnya; **hanya boleh lebih ketat** dari input MT5 |
| Status runtime (bukan konfigurasi) | Global Variables `SDB_<login>_*` di terminal (puncak equity, STOPPED, pause harian, …) | EA sendiri | Jangan diedit; buka STOPPED hanya lewat `InpResetEmergencyStop` |
| Path mesin untuk alat build/uji | `tools/mt5-paths.local.json` (contoh: `tools/mt5-paths.example.json`) | Developer, **tidak di-commit** | Dibaca setiap kali skrip `tools/` jalan |

Kolom "Dibuat di" pada tabel input di bawah menunjukkan spec yang menambahkannya. Sebelum spec itu selesai, file dan input tersebut belum ada.

### Daftar input

| Grup | Input | Default | Batas | Dibuat di |
|---|---|---|---|---|
| Umum | `InpMagicNumber` | 2026091901 | 2026091901–2026091999, satu nomor per pair | spec 02 |
| Umum | `InpTradingStyle` | Day trading (H4/H1/M15) | — | spec 02 |
| Umum | `InpSymbolSuffix` | kosong (`c` di preset akun cent) | — | spec 02 |
| Umum | `InpAllowLiveTrading` | false | — | spec 02 |
| Umum | `InpLogLevel` | INFO | — | spec 02 |
| Risiko | `InpRiskPerTradePct` | 0.5 | 0 < x ≤ 1.0 | spec 02 (dipakai spec 05) |
| Risiko | `InpMaxOpenRiskPct` | 3.0 | risk per trade ≤ x ≤ 10 | spec 02 (dipakai spec 05) |
| Risiko | `InpDailyLossPct` | 3.0 | 0 < x ≤ 10 | spec 02 (dipakai spec 05) |
| Risiko | `InpDDReducePct` / `InpDDStopPct` | 10 / 15 | 0 < reduce < stop ≤ 50 | spec 02 (dipakai spec 05) |
| Risiko | `InpResetEmergencyStop` | false | reset hanya saat berubah false → true | spec 02 (dipakai spec 05) |
| Posisi | `InpBreakevenR` / `InpBreakevenBufferPoints` | 1.0 / 2 | BE R < partial R | spec 02 (dipakai spec 06) |
| Posisi | `InpPartialR` / `InpPartialPct` | 1.5 / 50 | 0 < pct < 100 | spec 02 (dipakai spec 06) |
| Posisi | `InpTrailATRPeriod` / `InpTrailATRMult` | 14 / 2.0 (ATR di M15) | period 2–200, mult 0–10 | spec 02 (dipakai spec 06) |
| Entry | `InpEntryMode` | Market (opsi Limit) | — | Fase 3 |
| Entry | `InpMinConfluenceScore` / `InpMinRR` / `InpMaxZoneAgeBars` | 65 / 2.0 / 100 | — | Fase 3 |
| Filter | `InpMaxSpreadPoints` | per simbol (disetel dari data spread) | — | Fase 4 |
| Filter | `InpNewsBlockMinutes` / `InpTradingSessions` | 30 / London + New York | — | Fase 4 |
| Notifikasi | `InpTelegramToken` / `InpTelegramChatID` | kosong (isi di `*.local.set`) | — | Fase 2 |
| Notifikasi | `InpHeartbeatMinutes` | 60 | — | Fase 2 |
| Backoffice | `InpEnableBackoffice` / `InpControlPollSeconds` | true / 2 | — | Fase B5 |

### Alur tuning

1. Ubah nilai input di Strategy Tester (tab Inputs), atau jalankan **optimasi** dengan rentang nilai. Metrik optimasi SDBot adalah expectancy per trade dalam R ÷ max drawdown (`OnTester`).
2. Bandingkan hasil backtest di `sdbot_tester.sqlite`: setiap run tercatat di tabel `sessions` bersama `input_hash` dan nilai input lengkap (`inputs_json`), jadi hasil bisa dikelompokkan per setelan. Query siap pakai ada di `tools/queries/` (spec 07).
3. Nilai yang terbukti lebih baik (backtest + forward test sesuai PRD) disimpan ke preset `ea/src/Presets/SDBot_DAY_<PAIR>c.set` dan di-commit.
4. Jika yang berubah adalah **default** di `Inputs.mqh` atau konstanta di `Constants.mqh`, perubahannya juga dicatat di `docs/PENDING-CHANGES.md` agar PRD ikut diperbarui (skill `sdbot-docs-sync`).
5. Di akun live, perubahan setting yang sifatnya mengetatkan (misalnya menurunkan risiko) bisa lewat panel backoffice tanpa membuka MT5 (Fase B5).

## Alat pengembangan

Semua skrip di `tools/`, dijalankan dari PowerShell (`powershell -ExecutionPolicy Bypass -File …`):

| Skrip | Fungsi |
|---|---|
| `link-mt5.ps1 -DataDir <folder data MT5>` | Hubungkan `ea/src` dan `ea/tests` ke MT5 lewat junction |
| `build-ea.ps1` | Compile EA dan entry point uji; gagal bila ada error atau warning |
| `run-ea-tests.ps1 [-Unit] [-Scenario SC-xx] [-All]` | Compile lalu jalankan unit test/skenario di Strategy Tester terminal uji; exit 0 = semua lulus |

Terminal uji di mesin ini adalah instalasi "Broker A". Terminal "Broker B" dipakai bot Python dan tidak disentuh alat-alat ini.
