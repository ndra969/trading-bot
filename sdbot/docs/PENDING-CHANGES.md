# Perubahan PRD/RULES yang belum masuk ke dokumen induk

Dokumen induk ada di claude.ai (Claude Docs). Salinan di folder ini tidak diedit langsung. Setiap keputusan yang sudah disetujui dan mengubah isi PRD atau RULES dicatat di sini, lalu diterapkan ke dokumen induk dan diekspor ulang ke repo lewat skill `sdbot-docs-sync`.

## Open

### PC-01: Skema data baru menggantikan tabel PRD
- Status: Open
- Tanggal disetujui: 2026-09-29
- Dokumen: PRD-EA §Data dan database; PRD-Backoffice §Arsitektur integrasi, §Database dan kontrak data
- Sumber: spec `ea-03-storage-migrations` design §2–§3, keputusan §9.1
- Perubahan:
    - Tabel `sdbot.sqlite` menjadi: `sessions`, `accounts`, `signals` + `signal_scores`, `trades` (kunci `login + position_id`), `deals`, `position_events`, `closures` (alasan `TP`/`SL`/`BE_STOP`/`TRAIL_STOP`/`MANUAL`/`STOP_OUT`/`EA_CLOSE`/`ROLLOVER`/`OTHER`, plus `mfe_r`, `mae_r`, `holding_sec`, flag BE/partial/trailing), `balance_ops`, `alerts` (+ `attempts`, `sent_at`), view `v_trade_results`, dan `schema_migrations` menggantikan `schema_version`.
    - Semua waktu UTC epoch detik; `accounts.server_utc_offset_sec` menyimpan selisih waktu server.
    - Backtest menulis ke file terpisah `sdbot_tester.sqlite`; optimasi tidak menulis DB. Backoffice hanya membaca `sdbot.sqlite`.
    - Tabel ringkas di PRD-EA diganti tabel versi baru (nama tabel + isi utama); DDL lengkap dirujuk ke `shared/schema/data_db.sql`.

### PC-02: Blok magic SDBot
- Status: Open
- Tanggal disetujui: 2026-09-29
- Dokumen: PRD-EA §Parameter input EA, §Risk management, §Instalasi 5; RULES §Aturan wajib keamanan trading
- Sumber: spec `ea-05-risk` keputusan R2-1, spec `ea-02-core-account` kriteria 1.6
- Perubahan:
    - `MagicNumber` default `2026091901`, wajib di rentang `2026091901`–`2026091999`, satu nomor per pair (EURUSDc …01, GBPUSDc …02, EURJPYc …03, GBPJPYc …04); `2026091900` dicadangkan untuk harness uji.
    - Risk management: saat emergency stop, setiap instance menutup **semua posisi SDBot** (magic di blok) di simbol mana pun; total risiko terbuka 3% dihitung atas semua posisi SDBot di akun.
    - RULES: "setiap loop posisi memfilter magic serta simbol" tetap berlaku, dengan pengecualian tertulis untuk emergency close dan perhitungan risiko terbuka akun.

### PC-03: Skema versi EA
- Status: Open
- Tanggal disetujui: 2026-09-29 (dipaksa compiler, temuan spike spec 01)
- Dokumen: RULES §Git, versi, dan rahasia
- Sumber: spec `ea-01-tooling` design §8
- Perubahan: format `MAJOR.MINOR` dengan MAJOR ≥ 1, karena MetaEditor memberi warning 68 untuk versi `0.x` dan aturan compile adalah 0 warning. Fase 1 memakai `1.00`–`1.06` (naik `0.01` per spec), `2.00` setelah validasi Fase 6.

### PC-04: Migrasi skema lewat skrip
- Status: Open
- Tanggal disetujui: 2026-09-29
- Dokumen: RULES §Struktur folder repo, §Kontrak lintas bagian, §Definition of done
- Sumber: spec `ea-03-storage-migrations` Req 4–6
- Perubahan:
    - `shared/schema/` berisi `migrations/data/NNNN_*.sql`, `migrations.lock.json`, `enums.md`, snapshot `data_db.sql` (hasil generate), `fixtures/`.
    - Perubahan skema: `python sdbot/tools/schema.py new data "<deskripsi>"` → tulis SQL → `schema.py build` (menghasilkan `Storage/Migrations.mqh`, `Core/SchemaEnums.mqh`, snapshot, fixture) → commit (pre-commit menjalankan `schema.py check`). EA menerapkan migrasi sendiri saat start. Migrasi hanya maju; migrasi rilis tidak boleh diedit.
    - Kalimat lama "ubah `shared/schema/*.sql`, naikkan `schema_version`" diganti alur di atas.

### PC-05: Alat build dan uji
- Status: Open
- Tanggal disetujui: 2026-09-29
- Dokumen: RULES §Struktur folder repo, §Menghubungkan repo ke MT5, §Testing
- Sumber: spec `ea-01-tooling` (approved)
- Perubahan:
    - `tools/` bertambah `build-ea.ps1`, `run-ea-tests.ps1`, `lib/Mt5Paths.psm1`, `mt5-paths.example.json` (`mt5-paths.local.json` tidak di-commit).
    - `link-mt5.ps1` juga membuat junction `Experts/SDBotTests`, `Include/SDBotTests`, `Scripts/SDBotTests` ke `ea/tests/`.
    - Unit test ditulis sebagai suite `.mqh` di `ea/tests/Include/SDBotTests/Suites/`, dijalankan otomatis oleh `run-ea-tests.ps1` di Strategy Tester terminal uji (terpisah dari terminal live), atau manual lewat script `RunUnitTests`.

### PC-06: Telegram memakai bot yang sama dengan bot Python
- Status: Open
- Tanggal disetujui: 2026-09-29
- Dokumen: PRD-EA §Notifikasi, §Instalasi dan pemasangan 4
- Sumber: permintaan user 2026-09-29; catatan Fase 2 di `sdbot/specs/README.md`
- Perubahan:
    - §Instalasi 4 "Siapkan bot Telegram": tidak membuat bot baru lewat @BotFather; token dan chat ID diambil dari `.env` bot Python (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) dan diisi ke input EA lewat preset pribadi `*.local.set`.
    - §Notifikasi: format pesan mengikuti bot Python (emoji per level, HTML, start/stop, heartbeat tanpa bunyi, laporan harian) dengan penanda `SDBot` + pair + tipe akun di setiap pesan; batas kirim Telegram dibagi dengan bot Python.

### PC-07: Lapisan App, komentar order, dan aturan eksekusi
- Status: Open
- Tanggal disetujui: 2026-09-29
- Dokumen: RULES §Struktur folder repo (tabel lapisan), §Aturan wajib keamanan trading; PRD-EA §Eksekusi order
- Sumber: spec `ea-04-execution-harness` design §9
- Perubahan:
    - Lapisan baru `Include/SDBot/App/` (paling atas, hanya orkestrasi: `CSdbApp`, `CTeeSink`); `SDBot.mq5` hanya meneruskan event ke `CSdbApp`.
    - Komentar order `SDB|<SL awal>|<ID permintaan 4 karakter>` untuk deteksi order ganda setelah retcode ambigu.
    - `OrderCheck` wajib sebelum setiap `OrderSend`; deviasi maksimum 10 point (konstanta); modify dan close ikut diulang maksimal 3 kali seperti open.
    - Alasan tolak baru di `reject_stage`: `INVALID_STOPS`, `INVALID_VOLUME`.

### PC-08: run_key memisahkan run backtest (skema v2)
- Status: Open
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Data dan database; PRD-Backoffice §Database dan kontrak data
- Sumber: spec `ea-04-execution-harness` task 7 (temuan SC-00: baris `trades` run kedua dan seterusnya hilang di `sdbot_tester.sqlite`), keputusan user 2026-09-30
- Perubahan:
    - Migrasi `0002_run_key`: kolom `run_key INTEGER NOT NULL DEFAULT 0` di `sessions`, `trades`, `deals`, `closures`, `balance_ops`, `position_events`. Kunci unik menjadi `(login, run_key, position_id)` untuk `trades`/`closures` dan `(login, run_key, deal_ticket)` untuk `deals`/`balance_ops`. View `v_trade_results` menggabungkan dengan `run_key` dan menampilkannya.
    - `run_key` = 0 di live (posisi tetap unik per login lintas restart EA). Di Strategy Tester = ID sesi pertama run; disimpan di Global Variable tester `SDB_<login>_RUN_KEY` agar restart di tengah run memakai run yang sama.
    - Alasan: di tester, position ID dan deal ticket mulai dari angka kecil yang sama di setiap run dengan login yang sama, sehingga `ON CONFLICT DO NOTHING` membuang semua baris run berikutnya tanpa error.
    - Backoffice dan query analisis wajib memakai `login + run_key + position_id` sebagai kunci posisi.

### PC-09: Detail risk management yang tidak diatur PRD
- Status: Open
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Risk management
- Sumber: spec `ea-05-risk` requirements, keputusan 1–3
- Perubahan:
    - Pre-trade check urutannya: boleh trading → STOPPED → pause harian → risiko per trade → total risiko terbuka → eksposur mata uang → margin. Langkah "risiko per trade" menolak order yang risikonya (volume, entry, SL) melebihi risiko efektif per trade, dengan alasan tolak baru `RISK_PER_TRADE` (`enums.md`).
    - Close all saat STOPPED: percobaan saat pasar tutup (tiap 60 detik) tidak dihitung gagal; Critical `CLOSE_ALL_FAILED` hanya setelah 3 gagal berturut-turut saat pasar buka, lalu paling sering tiap 15 menit.
    - Posisi SDBot tanpa SL dihitung berisiko 1% balance di total risiko terbuka, dengan log WARN.
    - Operasi saldo yang sudah ada saat status bersama belum ada (akun baru, GV dihapus, awal run tester) dianggap sudah diproses.
    - Ambang kembali normal dari lot × 0.5 = min(8%, `InpDDReducePct` × 0.8), agar histeresis tetap ada bila batas REDUCE disetel di bawah 8% (temuan SC-03; default PRD tetap 8%). Disetujui 2026-09-30.

### PC-10: Simbol mengikuti bot Python, preset per simbol, batas posisi per kategori
- Status: Open
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Temuan review dan keputusan (pair), §Risk management, §Parameter input EA, §Instalasi; RULES §Struktur folder (Presets)
- Sumber: permintaan user 2026-09-30; `config/active_symbols.yaml` bot Python; spec `ea-05-risk` kriteria 2.8
- Perubahan:
    - Simbol SDBot = simbol aktif bot Python, versi cent Exness (akhiran `c`): forex major EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD; forex cross EURJPY, GBPJPY; komoditas XAUUSD, XAGUSD; crypto BTCUSD. Menggantikan keputusan 4 pair (EURUSD, GBPUSD, EURJPY, GBPJPY). Ketersediaan NZDUSDc di akun perlu dicek.
    - Magic per simbol (blok PC-02): 01 EURUSD, 02 GBPUSD, 03 EURJPY, 04 GBPJPY (tetap), 05 USDJPY, 06 USDCHF, 07 AUDUSD, 08 USDCAD, 09 NZDUSD, 10 XAUUSD, 11 XAGUSD, 12 BTCUSD.
    - Setting berbeda per kategori lewat preset `.set` per simbol (`SDBot_DAY_<SIMBOL>c.set`) dengan input EA yang sama. Nilai awal per kategori diambil dari config bot Python saat spec pemiliknya dibuat (preset di spec 07, filter sesi/spread di Fase 4). BE/partial/trailing tetap berbasis R dan ATR sesuai PRD.
    - Risk management: batas posisi SDBot per kategori aset di akun (forex major 5, forex cross 3, komoditas 1, crypto 1; input `InpMaxPos*`), langkah pre-trade check setelah total risiko terbuka, alasan tolak `CLASS_POSITION_LIMIT`. Kategori ditentukan dari mata uang base/quote simbol.

### PC-11: Detail manajemen posisi dan closure
- Status: Open
- Tanggal disetujui: 2026-09-30
- Dokumen: PRD-EA §Position management, §Notifikasi
- Sumber: spec `ea-06-position` requirements, keputusan 1–4
- Perubahan:
    - Posisi milik instance ditentukan dari deal pembukanya (magic + simbol), bukan dari deal penutup; closure dari close all lintas instance tercatat oleh pemilik dengan alasan `EA_CLOSE`.
    - Titik BE = harga buka ± (spread + komisi pulang-pergi dalam point + `InpBreakevenBufferPoints`).
    - Modifikasi/partial gagal: dicoba ulang tiap 30 detik maksimal 3 kali per aksi, lalu satu event `MODIFY_FAILED` + satu alert Medium, berhenti sampai kondisi posisi berubah.
    - SL yang dihapus manual dipasang kembali (SL awal bila valid, atau SL valid terdekat) + alert High; gagal 3x → Critical.
    - Alasan tutup dibedakan `SL` / `BE_STOP` / `TRAIL_STOP` dari level pemicu SL; MFE/MAE dari bar M1 saat posisi tutup.

## Done

(belum ada)
