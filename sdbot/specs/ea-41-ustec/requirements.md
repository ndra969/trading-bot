# Requirements — USTEC sebagai simbol ke-13 (H15)

Status: Done (2026-10-19)
Use case: UC-83 ([fase-5c-overview.md](../fase-5c-overview.md))
Asal: permintaan user 2026-10-19 ("ustec aja kalau mau, gbpaud saya gamau, fokus yang usd kalau ga jpy"); spec 35 (USTEC lolos IS sendiri: 14 trade, +0,354R, PF 1,98, dengan konfigurasi 1.32); PRD-EA §Simbol, §Risk (kategori dan batas posisi); PC-28 (aturan uji)
Butuh: spec 35 (preset dan baseline kandidat USTECc), spec 37 (konfigurasi 1.35+). Acuan = EA 1.37, 12 simbol live

## Pendahuluan

Di spec 35 USTEC (Nasdaq 100) adalah satu dari dua kandidat yang positif di IS. H8 ditolak karena kurang dari 3 simbol lolos, sehingga OOS dan REAL USTEC belum pernah dijalankan. Hasil IS itu dibuat dengan konfigurasi 1.32 (BE 1R, partial 1,5R). Live sekarang memakai BE 1,5R tanpa partial.

Spec ini menguji hipotesis H15: USTEC dengan konfigurasi live tetap positif di IS, OOS, dan REAL, sehingga layak menjadi chart ke-13.

Perkiraan dampak: sekitar 0,5 trade per bulan (14 trade dalam 27 bulan IS). Sampelnya kecil, jadi aturan lolos di bawah memakai ambang yang realistis untuk jumlah trade sekecil ini, dan keputusan akhirnya tetap menunggu persetujuan user.

Di luar lingkup:
- simbol lain (GBPAUD ditolak user; US30 dan US500 negatif di spec 35);
- perubahan kode EA (preset USTECc dan kategori aset sudah ada sejak spec 35).

Bukti selesai:
- backtest USTECc IS, OOS, dan REAL dengan konfigurasi 1.37;
- keputusan H15.

## Requirements

### Requirement 1: Pengukuran dengan konfigurasi live
#### Acceptance criteria
1. Backtest `-Baseline -BaselineSet kandidat -Symbols USTECc` untuk IS, OOS, dan REAL dengan preset USTECc dan default 1.37 (BE 1,5R tanpa partial, zona lawan wajib, R:R ≥ 2).
2. Laporan per periode WAJIB memuat:
   - trade, trade per bulan, win rate, R per trade, total R, PF, DD;
   - alasan tutup dan tahap tolak.
3. Laporan WAJIB mencatat kandidat yang ditolak `LOT_BELOW_MIN` atau risiko per trade, karena akun live hanya ±1.780 USC sedangkan tester memakai deposit baseline.
4. Backtest IS WAJIB diulang sekali dengan `-Deposit 1777.78` dan risk 1%, meniru akun live, untuk memastikan lot USTEC bisa dihitung di saldo kecil.

### Requirement 2: Aturan lolos (ditulis sebelum hasil)
#### Acceptance criteria
1. IS:
   - ≥ 10 trade;
   - R per trade ≥ +0,10;
   - PF ≥ 1,20.
2. OOS dan REAL masing-masing: total R ≥ 0 dan tidak ada DD lebih dari 5R. Sampel OOS/REAL diperkirakan 1–5 trade, jadi R per trade per periode tidak dipakai sebagai syarat.
3. OOS + REAL digabung: R per trade ≥ +0,05.
4. Uji saldo kecil (1.4): ≥ 80% kandidat yang lolos sampai tahap lot di IS dapat dibuka. Tidak boleh ada penolakan sistematis `LOT_BELOW_MIN`.
5. Lolos semua: USTECc dicatat sebagai kandidat chart ke-13 dengan magic dan preset spec 35. Pemasangan live menunggu persetujuan user dan PC untuk PRD §Simbol.
6. Gagal salah satu: USTEC tidak dipakai; hasil dicatat.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Jam pasar indeks berbeda dengan forex (sesi cash New York) | Filter sesi EA berlaku apa adanya; dicatat | 1.1 |
| EC-02 | Real ticks USTECc lebih pendek dari periode REAL | Dicatat (ShortHistory) di laporan | 1.1 |
| EC-03 | Lot minimum terlalu besar untuk risk 1% di 1.780 USC | Terlihat di uji 1.4; aturan 2.4 | 1.3, 1.4, 2.4 |
| EC-04 | Gap pembukaan indeks | Simulator tester apa adanya | 1.1 |
| EC-05 | USTEC berkorelasi dengan sentimen USD dan risk | Batas posisi kategori dan risiko terbuka 3% EA tetap berlaku | 1.1 |

## Keputusan (2026-10-19)

1. Ambang OOS/REAL longgar (Req 2.2–2.3) karena sampel kecil.
