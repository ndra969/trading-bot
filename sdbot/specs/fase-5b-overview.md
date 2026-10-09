# Fase 5b — Perbaikan strategi inti: overview

Status: Done (2026-10-09)
Sumber: diagnosis sesudah Fase 5 (spec 22, PC-27; sesi DB 1157–1180 untuk IS/OOS v1.23 dan 1260–1271 untuk REAL v1.24); PRD-EA §Aturan zona, §Position management, §Parameter input; PC-21 (sesi UTC); PRD §Pengujian (tahap 2–3); permintaan user 2026-10-07: hasil backtest jelek berarti strategi dan spec diperbaiki

Fase 5 menunjukkan bahwa komponen konfirmasi tidak memperbaiki hasil. Strategi dasarnya sendiri belum profitable dengan real ticks: Jan–Okt 2026, 167 trade, −0,045R per trade, PF 0,91. Fase 5b menguji tiga perbaikan pada strategi inti, satu per satu, dengan disiplin yang sama dengan Fase 5:
- dikembangkan dan disetel hanya di in-sample (IS);
- dikonfirmasi sekali di out-of-sample (OOS) dan di periode real ticks (REAL);
- yang lolos dipakai, yang tidak ditolak dan dicatat.

Fase 6 (live akun cent) dimulai sesudah Fase 5b.

## 1. Tujuan dan batas

Fase 5b selesai jika:
- ketiga hipotesis punya keputusan (diterima atau ditolak) dengan data IS, OOS, dan REAL;
- konfigurasi akhir tidak lebih buruk dari acuan v1.24 di OOS dan REAL;
- PRD diperbarui lewat PC untuk hipotesis yang diterima.

Di luar Fase 5b:
- komponen konfirmasi baru;
- filter arah (BUY lebih baik dari SELL di data ini, tetapi kemungkinan karena rezim pasar periode ini, bukan sifat strategi);
- perubahan bobot skor tren (terbalik di OOS dan REAL, tetapi tidak di IS: tidak konsisten);
- mode entry Adaptive/Limit dan filter candle klimaks, yang ditinjau sesudah H2 karena keduanya juga menyangkut titik entry dan risiko awal.

## 2. Diagnosis (R per trade, jumlah trade dalam kurung)

| Faktor | IS | OOS | REAL | Konsisten? |
|---|---|---|---|---|
| Zona Fresh | +0,041 (340) | +0,157 (37) | +0,030 (116) | ya, positif |
| Zona Tested | +0,001 (153) | −0,264 (15) | −0,216 (51) | ya, sumber rugi |
| Sesi overlap 13–17 UTC | +0,120 (213) | +0,232 (22) | +0,108 (69) | ya, positif |
| Sesi London di luar overlap | −0,062 (195) | +0,008 (22) | −0,059 (65) | lemah |
| Sesi New York di luar overlap | +0,009 (85) | −0,428 (8) | −0,338 (33) | rugi di OOS/REAL |
| Loser yang sempat ≥ +0,5R (MFE) | 83 dari 241 SL | 6 dari 25 | 31 dari 87 | ya, sekitar sepertiga |
| Alasan tutup BE_STOP | +0,275 (53) | +0,402 (8) | +0,304 (17) | — |

## 3. Hipotesis dan pembagian spec

| # | Spec | Hipotesis | Perubahan | Butuh kode | Versi |
|---|---|---|---|---|---|
| 23 | `ea-23-fresh-zones` | H1: hanya zona Fresh yang dipakai untuk entry | input `InpAllowTestedZones` (default sesuai keputusan) | ya (gerbang zona + input) | 1.25 |
| 24 | `ea-24-breakeven-tuning` | H2: breakeven lebih awal memotong loser yang sempat untung | `InpBreakevenR` 0,5 / 0,75 / 1,0 diuji di IS (input sudah ada) | tidak (preset + default bila diterima) | 1.26 |
| 25 | `ea-25-session-window` | H3: jendela entry dipersempit ke jam yang positif | opsi jendela sesi (misalnya overlap saja, atau London + overlap tanpa NY sesudah 17:00 UTC) | ya (opsi sesi + input) | 1.27 |

Hipotesis diuji **berurutan dan kumulatif**: H2 diukur dengan H1 bila H1 diterima, H3 dengan H1 + H2 yang diterima. Urutannya dari yang paling konsisten di data dan paling murah (H1, H2) ke yang paling memotong jumlah trade (H3).

## 4. Aturan uji (sama untuk setiap spec)

1. **Pengembangan di IS saja.** Varian parameter dipilih dengan aturan yang ditulis di design sebelum OOS dijalankan.
2. **Konfirmasi:** varian terpilih harus lebih baik dari acuan saat ini (konfigurasi yang berlaku sebelum spec itu) dalam R per trade di IS, dan tidak lebih buruk di OOS **dan** REAL. Profit factor dan drawdown dilaporkan.
3. **Jumlah trade:** filter kualitas memang mengurangi trade. Kriteria PC-22 (≥ 200 per 12 bulan, ≥ 10 per simbol) dilonggarkan menjadi ≥ 150 per 12 bulan dan ≥ 6 per simbol untuk Fase 5b (keputusan 3).
4. **Ditolak = tidak diterapkan**: default dan preset tidak berubah, temuan dicatat di CHANGELOG dan spec.

## 5. Use case

Nomor melanjutkan Fase 5 (UC-50..57).

| ID | Use case | Aktor | Spec |
|---|---|---|---|
| UC-60 | Entry hanya dari zona yang belum pernah disentuh | EA | 23 |
| UC-61 | Mengamankan posisi lebih cepat saat sudah bergerak sesuai arah | EA | 24 |
| UC-62 | Membatasi entry ke jam dengan hasil terbaik | EA, Trader | 25 |
| UC-63 | Menilai setiap perbaikan dengan IS/OOS/REAL dan mencatat keputusan | Developer | 23–25 |

## 6. Keputusan yang perlu diambil

Usulan saya dalam kurung.

1. **Tiga spec berurutan dan kumulatif** (H1 → H2 → H3). Alternatif: satu spec dengan semua perubahan sekaligus; lebih cepat, tetapi efek tiap perubahan tidak bisa dipisahkan.
2. **Mengubah aturan PRD bila hipotesis diterima.** H1 mengubah aturan zona (PRD: Fresh 30, Tested 15). H2 mengubah `BreakevenR` (PRD 1.0). H3 mengubah default sesi (PC-21). Semuanya dicatat sebagai PC dan disetujui di requirements tiap spec.
3. **Kriteria jumlah trade Fase 5b: ≥ 150 per 12 bulan dan ≥ 6 per simbol** (IS 26 bulan: ≥ 325 total, ≥ 13 per simbol). Dengan H1 saja, IS sekitar 340 trade. Alternatif: tetap PC-22; H1 hampir pasti gagal hanya karena jumlah, bukan kualitas.
4. **Filter arah dan bobot tren tidak disentuh** (alasan di §1).
5. **Mode entry Adaptive/Limit dan filter klimaks ditinjau sesudah spec 24.** Keduanya bisa jadi spec 26 bila data entry masih menunjukkan masalah.

## 7. Hasil Fase 5b (selesai 2026-10-09)

| Spec | Hipotesis | IS (R/trade) | OOS | REAL | Keputusan |
|---|---|---|---|---|---|
| 23 | H1 zona Fresh saja | +0,046 vs +0,029 | +0,156 vs +0,036 | +0,030 vs −0,045 | **Diterima** (1.25, PC-29) |
| 24 | H2 breakeven 0,5 / 0,75R | +0,023 / +0,021 vs +0,046 | — | — | Ditolak di IS (trailing ikut aktif lebih awal) |
| 25 | H3 jam akhir entry 19 UTC | +0,066 vs +0,046 | +0,125 vs +0,156 | +0,064 vs +0,030 | Ditolak (OOS lebih buruk; input tetap ada, 1.26) |
| 26 | H4 trailing ATR × 4 (lanjutan) | +0,064 vs +0,046 | +0,116 vs +0,156 | +0,019 vs +0,030 | Ditolak (OOS dan REAL lebih buruk) |

Konfigurasi akhir: zona Fresh saja, breakeven 1R, sesi London + New York sampai 22 UTC. Dibanding acuan v1.24, real ticks berubah dari −0,045R (PF 0,91) menjadi +0,030R (PF 1,06); PF masih di bawah target PRD tahap 2 (1,3).

Kandidat sesudah Fase 5b: pemicu trailing yang terpisah dari BE (temuan spec 24; trailing lebih longgar saja ditolak di spec 26), mode entry Limit/Adaptive dan filter candle klimaks (keputusan 5), serta jam akhir entry yang diuji ulang bila data OOS bertambah.
