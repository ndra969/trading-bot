# Requirements — 12 Trigger price action

Status: Done (2026-10-03)
Use case: UC-34 ([overview](../fase-3-overview.md))
Asal: PRD-EA §Pipeline analisis (trigger PA di LTF sebagai gerbang wajib), §Skor konfluensi (kekuatan PA: engulfing kuat 10, pin bar 7, lainnya 3); python-bot-lessons §1 (urutan detektor salah: pola netral dicek sebelum pola terarah sehingga 241 dari 273 trade tercatat Inside Bar/Doji; ~45% candle tanpa pola; setiap komponen skor wajib terbukti terpanggil); PC-15 (relatif ATR); spec 10–11 (bar tertutup, ATR Wilder)
Butuh: spec 10

## Pendahuluan

Spec ini membangun detektor pola candle di LTF (M15 untuk day trading) pada bar tertutup: daftar pola terarah dengan urutan dari yang paling spesifik ke yang paling umum, arah pola, nama pola, dan komponen skor kekuatan PA. Pola netral (inside bar, doji, harami) tidak pernah menjadi trigger. Pemeriksaan "bar menyentuh zona searah bias" dan keputusan sinyal ada di spec 13.

Selesai jika suite PatternRules ALL PASS (termasuk kasus yang di bot Python salah diklasifikasi), regresi tetap PASS, dan EA naik ke `1.11`.

## Ukuran dari histori (dasar default)

M15, 2026-04-01 s.d. 2026-10-01, 12 simbol, definisi usulan di glosarium. Persen = bar yang punya pola itu (pola pertama sesuai urutan, arah bullish atau bearish):

| Pola | Forex | XAU / XAG | BTC |
|---|---|---|---|
| Bintang pagi / sore | 2,5–3,0% | 2,6–2,7% | 2,7% |
| Engulfing kuat | 2,9–5,2% | 2,8–3,1% | 2,5% |
| Pin bar | 7,1–7,5% | 6,6–6,9% | 6,6% |
| Engulfing biasa | 11,4–13,2% | 9,1–10,5% | 9,2% |
| Tweezer | 9,7–11,6% | 11,0–12,5% | 11,3% |
| Outside bar terarah | 3,1–4,3% | 4,6% | 4,7% |
| **Ada pola terarah** | **40–42%** | **38–39%** | **37%** |

Satu set definisi relatif ATR berlaku untuk semua simbol; logam dan BTC sedikit lebih jarang tetapi tidak perlu aturan khusus.

## Glosarium

Semua ukuran dari bar tertutup LTF; ATR = ATR(14) Wilder LTF di bar itu; "badan" = |close − open|; "rentang" = high − low. Definisi untuk arah bullish; bearish adalah cerminnya.

- **Bintang pagi**: bar i−2 bearish dengan badan > 0,5 ATR, bar i−1 badannya < 0,3 × badan bar i−2, bar i bullish dan close di atas titik tengah badan bar i−2.
- **Engulfing kuat**: bar i−1 bearish, bar i bullish, badan bar i menelan badan bar i−1 dan lebih besar, badan ≥ 60% rentang dan ≥ 0,8 ATR, dan close di atas high bar i−1.
- **Pin bar (hammer)**: badan ≤ 35% rentang, sumbu bawah ≥ 2 × badan, ≥ 60% rentang, dan > 2 × sumbu atas, rentang ≥ 0,8 ATR.
- **Engulfing biasa**: syarat badan engulfing tanpa syarat kekuatan.
- **Tweezer bottom**: bar i−1 bearish, bar i bullish, low keduanya berselisih ≤ 0,1 ATR.
- **Outside bar terarah**: high dan low bar i melewati bar i−1, bar i bullish dan close di atas close bar i−1.
- **Pola netral**: inside bar, doji, harami, dan bar tanpa pola: bukan trigger.

## Requirements

### Requirement 1: Deteksi pola terarah

**User story:** Sebagai trader, saya ingin trigger hanya dari pola yang menunjukkan arah, agar entry tidak lahir dari candle ragu-ragu.

#### Acceptance criteria

1.1. EA WAJIB memeriksa bar LTF tertutup terakhir terhadap pola terarah sesuai glosarium dalam urutan tetap: bintang pagi/sore, engulfing kuat, pin bar, engulfing biasa, tweezer, outside bar terarah; hasil = pola pertama yang cocok.
1.2. EA WAJIB menilai pola untuk arah yang diminta (bullish untuk sinyal BUY, bearish untuk SELL) dan tidak pernah mengembalikan pola arah berlawanan.
1.3. Pola netral (inside bar, doji, harami) WAJIB tidak pernah menjadi trigger, dan tidak boleh mendahului pemeriksaan pola terarah.
1.4. Ukuran pola WAJIB relatif terhadap ATR LTF dan rentang bar, bukan pip, sehingga satu definisi berlaku untuk forex, logam, dan crypto.
1.5. JIKA bar tidak punya rentang (high = low) atau histori LTF kurang MAKA EA WAJIB mengembalikan "tidak ada pola" tanpa error.

### Requirement 2: Skor kekuatan PA

**User story:** Sebagai developer, saya ingin komponen PA bernilai sesuai PRD dan terbukti terpanggil.

#### Acceptance criteria

2.1. Skor kekuatan PA WAJIB 10 untuk engulfing kuat, 7 untuk pin bar, 3 untuk pola terarah lain, 0 tanpa pola (PRD).
2.2. Hasil deteksi WAJIB membawa nama pola (kode stabil), arah, dan skor, untuk dicatat di `signal_scores` dan konteks sinyal (spec 13).

### Requirement 3: Trigger di LTF

**User story:** Sebagai developer pipeline, saya ingin trigger dihitung sekali per bar LTF dari salinan bar yang sama dengan analisis lain.

#### Acceptance criteria

3.1. EA WAJIB menyalin bar LTF tertutup hanya saat bar LTF baru, dan menyediakan hasil deteksi untuk kedua arah bagi pipeline.
3.2. Hasil deteksi sebuah bar WAJIB hanya bergantung pada bar sampai bar itu (tanpa repaint).

### Requirement 4: Uji dan versi

4.1. Suite PatternRules WAJIB berisi, untuk setiap pola, kasus cocok, kasus tepat di batas, dan kasus hampir cocok; kasus urutan (bar yang memenuhi engulfing kuat sekaligus outside bar, pin bar yang juga tweezer, bintang yang bar terakhirnya engulfing); dan kasus bot Python (inside bar / doji tidak menang atas pola terarah).
4.2. EA dan harness WAJIB naik ke `1.11`.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Bar engulfing kuat yang juga outside bar | Engulfing kuat (10) | 1.1 |
| EC-02 | Pin bar yang juga membentuk tweezer | Pin bar (7) | 1.1 |
| EC-03 | Bar ketiga bintang pagi juga engulfing | Bintang pagi (3) | 1.1 |
| EC-04 | Bar inside bar bullish kecil | Tidak ada pola | 1.3 |
| EC-05 | Doji dengan sumbu bawah panjang (dragonfly) | Pin bar bila badan ≤ 35% dan syarat sumbu terpenuhi; selain itu tidak ada | 1.1, 1.3 |
| EC-06 | Bar high = low (data rusak atau pasar beku) | Tidak ada pola | 1.5 |
| EC-07 | Pola bullish saat meminta arah bearish | Tidak ada pola | 1.2 |
| EC-08 | Badan tepat 60% rentang / 0,8 ATR | Lolos (batas inklusif) | 1.1 |
| EC-09 | Engulfing dengan open bar i persis di close bar i−1 | Engulfing (menelan termasuk sama) | glosarium |
| EC-10 | XAUUSDc dan BTCUSDc | Definisi sama, relatif ATR | 1.4 |

## Keputusan yang perlu disetujui

1. **Enam pola terarah dengan urutan di atas**; bintang (3 bar) diperiksa pertama karena paling spesifik, walau skornya hanya 3 menurut PRD. Pola bot Python lain (order block, liquidity sweep, double top/bottom, pullback) tidak diambil di Fase 3: lebih dekat ke struktur dan zona yang sudah ditangani spec 10–11, dan bisa ditambah di Fase 5 bila data mendukung.
2. **Ambang dari ukuran histori**: engulfing kuat (badan ≥ 60% rentang, ≥ 0,8 ATR, close melewati high/low sebelumnya), pin bar (badan ≤ 35%, sumbu ≥ 2 × badan dan ≥ 60% rentang dan > 2 × sumbu lain, rentang ≥ 0,8 ATR), tweezer 0,1 ATR, bintang (badan pertama > 0,5 ATR, tengah < 0,3 × badan pertama). Sebagai **konstanta**, bukan input, sampai data Fase 3 menunjukkan perlu dioptimasi; kalibrasi skor di Fase 5–6.
3. **Tidak ada aturan khusus emas** (catatan bot Python): definisi relatif ATR sudah memberi frekuensi serupa untuk XAU/XAG.
4. **Kode pola stabil** untuk telemetri: `STAR`, `ENGULF_STRONG`, `PIN`, `ENGULF`, `TWEEZER`, `OUTSIDE`, `NONE` (masuk `enums.md` sebagai enum baru `pa_pattern`, tanpa CHECK).

## Pertanyaan terbuka

- Tidak ada selain keputusan di atas.
