# Pelajaran dari bot Python untuk SDBot

Status: Draft
Tanggal: 2026-09-28
Sumber: kode `packages/` (branch `main` dan `feat/news-integration`), `specs/active/news-integration/`, `specs/archive/fixes/`, catatan analisis live dan backtest Juni–Juli 2026

PRD-EA sudah memuat hasil review delapan flow bot Python (bagian "Temuan review dan keputusan"). Dokumen ini menambah hal yang **belum** ada di PRD: bug yang pernah terjadi di live, data performa, dan pola arsitektur yang layak diambil. Setiap baris menyebut ke mana pelajaran itu dimasukkan.

## 1. Temuan performa strategi (dasar untuk Fase 3–5)

Data live 321 trade dan backtest ulang April–Juli 2026 di akun cent USC:

| Temuan | Bukti | Dampak untuk SDBot | Masuk ke |
|---|---|---|---|
| Skor konfluensi **tidak memprediksi profit** | korelasi skor vs PnL −0.02; bucket 80+ rugi, bucket 65–70 paling rugi (−$235 dari 88 trade) | Ambang 65 dan bobot PRD wajib dikalibrasi dari data, bukan dianggap benar. Setiap sinyal (lolos maupun ditolak) harus tercatat dengan skor per komponen sejak hari pertama | Skema `signals` + `signal_scores` (spec 03); UC kalibrasi di Fase 3 |
| Sebagian besar loser **langsung salah arah** | 25 dari 34 loss tidak pernah profit (MFE < 10 pip) | Masalah ada di arah/entry, bukan exit. MFE dan MAE per posisi wajib dicatat agar bisa dibedakan "entry salah" vs "exit buruk" | Kolom `mfe_r`, `mae_r` di `closures` (spec 03, 06) |
| **Breakeven "bocor"** | BE-stop rata-rata hanya menyimpan ~0.33R padahal MFE sempat 0.8–1.2R; 24 BE-scratch total +$57 | Payoff rusak di jarak antara BE dan trailing. Jenis penutupan harus dibedakan (SL asli, BE-stop, trailing-stop) agar kebocoran ini terukur | Alasan tutup `BE_STOP` dan `TRAIL_STOP` (spec 03, 06); tuning di Fase 6 |
| Tuning exit saja **tidak menyelamatkan** | sweep BE/trailing 3 kombinasi di 2 simbol: semua negatif | Jangan menambah parameter exit sebelum entry terbukti | Catatan roadmap Fase 5–6 |
| Layer trendline **menghitung garis melawan tren** | tanpa filter kemiringan, support menurun ikut memperkuat BUY; net −$102/30 hari | Komponen trendline wajib mengecek kemiringan searah sinyal | Spec Fase 5 (trendline) |
| Fibonacci **memilih level paling "bergengsi"**, bukan terdekat | 0.618 memberi skor penuh di ~83% setup | Skor Fibonacci harus berdasarkan level terdekat dan dikurangi sesuai jarak | Spec Fase 5 (Fibonacci) |
| Deteksi price action **salah urutan** | inside bar/doji dicek sebelum pola terarah → 241 dari 273 trade tercatat Inside Bar/Doji | Urutan detektor pola dari yang paling spesifik; netral paling akhir. Emas perlu perlakuan beda | Spec Fase 3 (trigger PA) |
| Gerbang "wajib ada pola candle" **memblokir ~45%** setup | ~45% candle tidak punya pola; alasan "arah salah" 0% | Trigger PA di LTF adalah gerbang wajib PRD. Frekuensinya harus diukur lewat alasan tolak | Alasan tolak `NO_PA_TRIGGER` (spec 03), analisis Fase 3 |
| Layer breakout **tidak pernah dipanggil** | bobot 0.12 tetapi fungsi tidak terhubung | Setiap komponen skor wajib punya uji yang membuktikan ia benar-benar menyumbang skor di pipeline | Aturan uji Fase 3/5 |
| RSI berfungsi sebagai **gerbang**, bukan skor | 6.773 penolakan vs 6 kontribusi | Di PRD, RSI hanya skor divergence (maks 5). Tetap pisahkan "gerbang" dan "skor" di telemetri | Fase 5 |

## 2. Bug live yang harus dicegah sejak desain

| Bug di bot Python | Pencegahan di SDBot | Masuk ke |
|---|---|---|
| Setelah partial close, volume posisi di DB tidak berkurang, sehingga close akhir, eksposur, dan PnL memakai volume penuh | Volume selalu dibaca dari posisi MT5 (terminal = sumber kebenaran). DB hanya log per deal | spec 06, tabel `deals` (spec 03) |
| Kunci hasil partial beda nama (`closed_volume` vs `close_volume`), sehingga sinkronisasi terlewat diam-diam | Struct bertipe di `Core/Types.mqh`, tidak ada dict/kunci teks | spec 02 |
| Eksposur mata uang **mengabaikan arah** (SELL dihitung terbalik), menyebabkan 5 posisi short-USD kena SL bersamaan | Fungsi eksposur murni dengan test case per arah dan pair JPY | Fase 4 (eksposur) |
| `entry_tags` selalu kosong, sehingga kualitas entry tidak bisa diatribusi | `trades.signal_id` wajib terisi untuk entry strategi, dan ada uji yang memastikannya | spec 03 (skema), Fase 3 |
| Data dry-run/backtest mencemari statistik live ("exclude $0 dry-run pollution") | File DB tester terpisah dan setiap baris membawa `session_id` | spec 03 |
| Ticket melebihi batas integer 32-bit (`ticket-bigint-fix`) | Semua ticket/ID MT5 disimpan `INTEGER` 64-bit, di-bind sebagai `long` | spec 03 |
| Posisi "yatim" di DB setelah restart (`close-orphaned-positions-on-load`) | Rekonsiliasi berbasis history deal + insert idempoten (`UNIQUE`), tanpa status OPEN yang bisa basi di DB | spec 03, 06 |
| Alert Critical bisa terblokir rate limit | Sudah di PRD (Critical tanpa limit) | Fase 2 |
| Telegram gagal kirim karena parse Markdown (`_`, `*` di nama simbol/layer) | HTML mode + escape `& < >` (juga di PRD) | Fase 2 |

## 3. Pola arsitektur yang diambil

| Pola bot Python | Di SDBot |
|---|---|
| `CloseReason` kanonik: server (SL/TP/SO) diutamakan, SL dibedakan jadi STOP_LOSS / BREAKEVEN_STOP / TRAILING_STOP dari status posisi | `MapCloseReason()` murni dengan invariant yang sama: trailing hanya aktif setelah BE, SL tidak pernah mundur (spec 06) |
| `RejectionStage` sebagai enum stabil yang dipakai worker dan API | `shared/schema/enums.md` + `CHECK` di skema + `schema.py check` mencocokkan keduanya (spec 03) |
| `trading_sessions` dengan `config_hash`, `is_backtest` | Tabel `sessions` dengan `mode`, `ea_version`, `input_hash`, `inputs_json` (spec 03) |
| MAE/MFE, holding time, slippage entry dan exit | Kolom `closures` (spec 03), dihitung dari bar M1 saat posisi tutup sehingga tetap benar walau EA restart (spec 06) |
| Validasi konfigurasi dengan invariant (trailing > BE) | `ValidateInputValues` (spec 02) |
| News: sumber di balik interface, **degrade aman + alert saat proteksi mati**, blackout per tingkat dampak, telemetri event terdekat, alasan tolak `NEWS_BLACKOUT`, replay tanpa lookahead untuk backtest | Spec Fase 4 news filter (catatan awal di [README](README.md#fase-berikutnya)) |
| Telegram: antrean, HTML mode, heartbeat tanpa bunyi, pesan start/stop, laporan harian, tanda mode (live/tester) | Spec Fase 2 notifier (catatan awal di README) |

## 4. Yang sengaja **tidak** diambil

| Pola bot Python | Alasan |
|---|---|
| Loop polling 55 detik dan cache analisis berbasis detik | PRD: analisis per bar baru, manajemen posisi per tick |
| Zona disimpan di DB dan dimuat ulang | PRD: zona dihitung ulang dari histori saat init (hindari kebocoran data backtest) |
| Ambang pip tetap per kelas aset | PRD: kelipatan R dan ATR |
| Scraping Investing.com untuk kalender | MT5 punya kalender bawaan (`CalendarValueHistory`); CSV hanya untuk tester |
| Bobot konfluensi 8 layer total 115% | PRD: total 100, struktur+MA digabung |
| Satu orchestrator besar (1.300+ baris) | Modul kecil satu tanggung jawab, `CSdbApp` hanya meneruskan event |
