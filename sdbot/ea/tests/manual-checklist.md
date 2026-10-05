# Checklist manual SDBot EA

Uji yang tidak bisa dijalankan otomatis oleh `tools/run-ea-tests.ps1` (spec 07 Req 5.1). Isi kolom Tanggal, Hasil (OK / GAGAL), dan Catatan saat dicek. Item bertanda **Fase 3** baru bisa dicek setelah EA membuka posisi dari sinyal di akun cent.

Versi EA saat checklist dibuat: 1.06 (Fase 1 selesai). Terminal live: akun cent Exness (USC, hedging). Terminal uji: instalasi "Broker A".

## Fase 1: bisa dicek sekarang

| ID | Asal | Langkah | Harapan | Tanggal | Hasil | Catatan |
|---|---|---|---|---|---|---|
| MC-T-01 | spec 01 | Pasang `SDBot.mq5` di satu chart Broker A | Log INFO init muncul, tidak ada aktivitas lain | | | |
| MC-T-02 | spec 01 | Seret script `SDBotTests\RunUnitTests` ke chart Broker A | Suite murni lulus seperti runner; suite tester-only dilewati dengan INFO; TC-ENV-07 versi live lulus (selisih waktu server kelipatan 15 menit) | | | |
| MC-01 | spec 02 | `InpAllowLiveTrading = false` di akun cent | Gagal init, CRITICAL | | | |
| MC-02 | spec 02 | Muat `SDBot_DAY_EURUSDc.set` di chart EURUSDc, `InpAllowLiveTrading = true` | Init sukses, snapshot akun di log, tidak ada WARN preset | | | |
| MC-03 | spec 02 | Tutup MT5 dengan EA terpasang, buka lagi | Validasi tertunda lalu lolos | | | |
| MC-04 | spec 02 | Matikan Algo Trading 1 menit | Satu WARN, satu INFO saat hidup lagi | | | |
| MC-05 | spec 02 | Cabut jaringan 6 menit | WARN, alert Medium `CONN_DOWN` di menit ke-5, Info saat pulih | | | |
| MC-06 | spec 02 | Setel GV uji (flush), lalu matikan paksa `terminal64.exe` dari Task Manager; buka lagi | GV tetap ada | | | |
| MC-DB-01 | spec 03 | DB Browser menahan kunci `sdbot.sqlite` 6 menit saat EA live | WARN, alert High di menit ke-5, Info setelah dilepas, tidak ada event hilang | | | |
| MC-DB-02 | spec 03 | Jalankan backtest saat EA live berjalan | Dua file terpisah (`sdbot.sqlite`, `sdbot_tester.sqlite`), tidak ada error kunci | | | |
| MC-EX-01 | spec 04 | EA di chart EURUSDc akun cent selama 1 jam | Tidak ada order; sesi LIVE tercatat; `accounts.updated_at` diperbarui tiap menit | | | |
| MC-EX-02 | spec 04 | Pasang `SDBotHarness` di chart live terminal uji | Gagal init dengan CRITICAL | | | |
| MC-RK-01 | spec 05 | Dua chart (EURUSDc, GBPUSDc) di akun cent; setel GV `SDB_<login>_STOPPED` = 1 lewat F3 | Kedua instance mencatat STOPPED | | | |
| MC-RK-02 | spec 05 | STOPPED aktif; `InpResetEmergencyStop = true`, init ulang tanpa mengembalikannya | Reset sekali + `EMERGENCY_RESET`; init berikutnya WARN tanpa reset | | | |
| MC-IN-01 | spec 07 | Muat setiap preset lewat Inputs → Load di satu chart | File terbaca, nilai sesuai; preset simbol lain di chart ini → WARN `InpPresetTag` | | | |
| MC-IN-02 | spec 07 | Cek simbol NZDUSDc tersedia di akun cent | Ada di Market Watch; bila tidak, catat di kolom Catatan | | | |
| PRD-08 | PRD uji fungsi wajib | Akun real dengan `AllowLiveTrading = false` | EA menolak jalan (= MC-01) | | | |
| MC-TG-01 | spec 09 | `uv run python sdbot/tools/make_local_presets.py`, muat `SDBot_DAY_EURUSDc.local.set` di chart EURUSDc akun cent | 12 file `.local.set` dibuat, tidak muncul di `git status`; token terisi di tab Inputs | | | |
| MC-TG-02 | spec 09 | Pasang EA v1.08 dengan `.local.set` | Pesan start masuk chat bot Python tanpa bunyi, HTML tampil benar (penanda `SDBot` · EURUSDc · CENT · v1.08) | | | |
| MC-TG-03 | spec 09 | Hapus `https://api.telegram.org` dari daftar WebRequest, init ulang EA | 1 log CRITICAL "Telegram nonaktif" + 1 push HP; tidak diulang tiap detik | | | |
| MC-TG-04 | spec 09 | Ubah satu karakter token di Inputs | Sama dengan MC-TG-03 (HTTP 401/404) | | | |
| MC-TG-05 | spec 09 | Dua chart (EURUSDc, GBPUSDc) 2 jam | 1 heartbeat per jam (tanpa bunyi), "Instance hidup 2" | | | |
| MC-TG-06 | spec 09 | Lepas chart pemimpin | Heartbeat berikutnya tetap datang dari chart lain | | | |
| MC-TG-07 | spec 09 | Laporan harian pertama setelah pergantian hari server | Angka (P&L, posisi tutup, per simbol) cocok dengan history MT5 | | | |
| MC-TG-08 | spec 09 | Telegram nonaktif (MC-TG-03), lalu picu Critical (GV `SDB_<login>_STOPPED` = 1 lewat F3) | Push Critical sampai di HP; baris `alerts` `FAILED` + `PUSH_SENT` | | | |
| MC-NT-01 | spec 08 | EA v1.07 di chart EURUSDc akun cent 1 jam | Pesan notifier di log Experts berformat spec 08 design §4.4 (penanda `SDBot` · simbol · `CENT` · versi), baris `alerts` berstatus `SENT` dengan `notify_key` | | | |

## Fase 3: setelah ada entry dari sinyal

| ID | Asal | Langkah | Harapan | Tanggal | Hasil | Catatan |
|---|---|---|---|---|---|---|
| MC-PS-01 | spec 06 | Tutup posisi SDBot manual dari HP | Closure `MANUAL` | | | |
| MC-PS-02 | spec 06 | Hapus SL posisi SDBot manual | SL dipasang kembali dalam 1 detik + alert High `SL_RESTORED` | | | |
| MC-PS-03 | spec 06 | Cek `ORDER_SL` order pembuka di Exness | Tidak 0 | | | |
| MC-PS-04 | spec 06 | Tutup MT5 saat ada posisi, posisi kena TP saat MT5 mati, buka lagi | Closure `TP` tercatat saat init | | | |
| MC-SG-01 | spec 13 | EA v1.12 di akun cent EURUSDc (risiko minimum) sampai sinyal pertama | Baris `signals` ACCEPTED dengan 3 skor, posisi punya SL/TP dari zona, pesan Telegram masuk | | | |
| MC-SG-02 | spec 13 | Restart EA di tengah bar M15 setelah kandidat | Tidak ada baris `signals` atau order ganda | | | |
| MC-FL-01 | spec 14 | EA v1.15+ di akun cent EURUSDc, amati log di luar 08:00–22:00 UTC | Kandidat ditolak `OUTSIDE_SESSION`; jam UTC di detail cocok dengan jam dunia | | | |
| MC-EXP-01 | spec 15 | Akun cent dengan dua posisi SDBot searah USD terbuka | Kandidat ketiga searah USD tercatat `CURRENCY_EXPOSURE` dengan detail mata uang | | | |
| MC-NW-01 | spec 16 | EA v1.17 di akun cent menjelang berita USD high | Log menunjukkan kandidat `NEWS_BLACKOUT` dengan nama event; `news_next` terisi di sinyal lain | | | |
| MC-NW-02 | spec 16 | Start terminal sebelum kalender MT5 sinkron | Satu alert `NEWS_FILTER_OFF`, lalu log INFO saat filter aktif kembali | | | |
| PRD-01 | PRD uji fungsi wajib | Restart EA saat ada posisi terbuka | Status BE dan partial tetap benar (otomatis: SC-04) | | | |
| PRD-02 | PRD uji fungsi wajib | Koneksi putus saat ada sinyal | Entry tertahan, alert terkirim | | | |
| PRD-03 | PRD uji fungsi wajib | Rugi harian 3% tercapai | Entry pause sampai hari server berikutnya (otomatis: SC-02) | | | |
| PRD-04 | PRD uji fungsi wajib | Drawdown 15% | Semua posisi ditutup, STOPPED tetap setelah restart (otomatis: SC-03, SC-03r) | | | |
| PRD-05 | PRD uji fungsi wajib | Lot hitungan di bawah lot minimum | Sinyal ditolak (otomatis: SC-05) | | | |
| PRD-06 | PRD uji fungsi wajib | Posisi ditutup manual | Tercatat dengan alasan yang benar (= MC-PS-01) | | | |
| PRD-07 | PRD uji fungsi wajib (Fase 2) | Telegram gagal | Alert Critical terkirim lewat push HP | | | |
