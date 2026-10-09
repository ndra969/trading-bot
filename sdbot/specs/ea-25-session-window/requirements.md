# Requirements — Jendela entry dipersempit (H3)

Status: Done (2026-10-09)
Use case: UC-62, UC-63 ([fase-5b-overview.md](../fase-5b-overview.md))
Asal: PRD-EA §Pipeline (urutan tahap tolak, `OUTSIDE_SESSION`), §Parameter input (`SessionTokyo` / `SessionLondon` / `SessionNewYork`); PC-21 (sesi UTC); PC-28 (aturan uji Fase 5b); PC-29 (acuan v1.25)
Butuh: spec 23 (v1.25, acuan); spec 24 ditolak, jadi acuan tetap v1.25

## Pendahuluan

Spec ini menguji hipotesis H3: entry yang dibatasi ke jam dengan hasil terbaik memperbaiki hasil.

Data v1.25 per jam entry (UTC, R per trade dan jumlah trade):

| Jendela | IS | OOS | REAL |
|---|---|---|---|
| London 08–13 | −0,018 (130) | +0,014 (16) | +0,059 (43) |
| Overlap 13–17 | +0,141 (149) | +0,447 (16) | +0,202 (50) |
| NY sesudah overlap 17–22 | −0,064 (61) | −0,318 (5) | −0,463 (22) |

Jam NY sesudah 17:00 UTC rugi di ketiga periode. Sebaliknya, overlap positif di ketiga periode.

Filter sesi yang ada hanya bisa menyalakan atau mematikan sesi utuh. Masalahnya, New York (13–22) ikut mencakup overlap. Mematikan NY tetap menyisakan overlap (karena London menyala), tapi sekaligus tidak bisa memotong jam 17–22 saja. Spec ini menambah satu input jam akhir entry, lalu mengukurnya.

Di luar lingkup:
- jam mulai entry (London 08–13 tidak konsisten: negatif di IS, positif di OOS/REAL);
- sesi Tokyo;
- jendela per simbol;
- penutupan posisi di jam tertentu. Posisi yang sudah terbuka tetap dikelola seperti biasa.

Bukti selesai:
- suite unit ALL PASS;
- skenario SC-23 PASS;
- backtest IS untuk tiap varian tercatat;
- varian terpilih diuji di OOS dan REAL;
- keputusan H3 diterima atau ditolak beserta datanya.

## Glosarium

- **Jam akhir entry**: jam UTC. Kandidat dengan waktu bar pada atau sesudah jam ini ditolak `OUTSIDE_SESSION`.
- **Acuan**: v1.25 (jam akhir efektif 22, zona Fresh saja). Sesinya: IS 1396–1407, OOS 1408–1419, REAL 1420–1431.

## Requirements

### Requirement 1: Input jam akhir entry
**User story:** Sebagai trader, saya ingin membatasi jam terakhir entry, agar EA tidak membuka posisi di jam yang secara data merugikan.

#### Acceptance criteria
1. Input `InpSessionEndHourUtc` (bilangan bulat) WAJIB mengatur jam UTC terakhir entry. Rentang yang sah 9–22; default 22, yaitu perilaku sekarang.
2. SELAMA filter sesi aktif, kandidat yang waktu bar UTC-nya ≥ `InpSessionEndHourUtc`:00 WAJIB ditolak `OUTSIDE_SESSION`. Detailnya menyebut jam akhir.
3. Input ini WAJIB hanya memotong akhir jendela. Sesi yang mati (misalnya Tokyo false) tetap mati, dan jam 22–24 tetap di luar sesi.
4. SELAMA filter sesi mati (ketiga input sesi false), input ini WAJIB tidak berlaku. Ini sama dengan aturan filter sesi mati yang ada.
5. JIKA nilai di luar rentang 9–22, MAKA EA WAJIB gagal init dengan pesan validasi, seperti input lain.
6. Posisi yang sudah terbuka WAJIB tetap dikelola (BE, partial, trailing) di luar jendela entry.
7. `inputs_json` WAJIB memuat input ini (54 kunci), agar run dengan nilai berbeda bisa dibedakan.

### Requirement 2: Pengukuran IS
**User story:** Sebagai developer, saya ingin varian jam akhir diukur dengan aturan yang sama, agar pilihan tidak bergantung pada OOS.

#### Acceptance criteria
1. Backtest `-Period IS` WAJIB dijalankan untuk `InpSessionEndHourUtc` 17 dan 19, dengan konfigurasi lain sama dengan acuan.
2. Setiap varian WAJIB dilaporkan dengan:
   - trade, R per trade, PF, dan DD;
   - jumlah trade per simbol;
   - sebaran alasan tutup (`exit_report.py`).
3. Varian terpilih WAJIB ditentukan hanya dari IS, dengan aturan yang ditulis di design sebelum OOS dijalankan. Syaratnya R per trade IS lebih tinggi dari acuan dan memenuhi kriteria jumlah trade khusus H3 (PC-30): IS ≥ 260 trade (≥ 120 per 12 bulan) dan ≥ 13 trade per simbol.
4. JIKA tidak ada varian yang lolos, MAKA H3 WAJIB ditolak tanpa OOS dan REAL.

### Requirement 3: Konfirmasi dan keputusan
**User story:** Sebagai trader, saya ingin aturan yang jelas kapan jendela entry diubah.

#### Acceptance criteria
1. Varian terpilih WAJIB dijalankan sekali di OOS dan sekali di REAL, lalu dibandingkan dengan acuan.
2. H3 DITERIMA bila R per trade OOS dan REAL ≥ acuan masing-masing.
3. Bila DITERIMA:
   - default `InpSessionEndHourUtc` dan preset 12 simbol berubah;
   - versi EA naik ke 1.27;
   - PC baru untuk PRD §Parameter input (dan §Pipeline bila perlu).
4. Bila DITOLAK: default tetap 22 dan preset tidak berubah. Input tetap ada (versi 1.26) untuk eksperimen.
5. Semua hasil WAJIB dicatat di spec dan CHANGELOG.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | Bar M15 jam 16:45 UTC dengan jam akhir 17 | Diterima: waktu bar 16:45 < 17:00. Order bisa terisi 17:00 sesudah bar tutup | 1.2 |
| EC-02 | Bar 17:00 UTC dengan jam akhir 17 | Ditolak `OUTSIDE_SESSION` | 1.2 |
| EC-03 | Server tidak di UTC (live) | Jam dihitung dari waktu server dikurangi selisih server-UTC, sama dengan filter sesi yang ada | 1.2 |
| EC-04 | Tester (`InpTesterUtcOffsetHours`) | Memakai offset tester yang ada | 1.2 |
| EC-05 | Jam akhir 22 | Perilaku identik dengan v1.25 (regresi) | 1.1 |
| EC-06 | Filter sesi mati dan jam akhir 17 | Tidak ada penolakan sesi | 1.4 |
| EC-07 | Posisi terbuka sebelum jam akhir dan masih jalan sesudahnya | BE, partial, dan trailing tetap berjalan | 1.6 |
| EC-08 | Jumlah trade IS turun di bawah kriteria | Varian tidak lolos, dicatat | 2.3, 2.4 |
| EC-09 | Berita sedang blackout dan jam di luar jendela | Tahap `NEWS_BLACKOUT` (urutan PRD: berita sebelum sesi) | 1.2 |

## Keputusan

1. **Kriteria jumlah trade H3 (opsi B, 2026-10-09, PC-30):** ≥ 120 trade per 12 bulan (IS ≥ 260) dan ≥ 13 per simbol. Kriteria Fase 5b (≥ 325) membuat setiap pemotongan jam pasti ditolak karena jumlah: dengan jam akhir 17, IS sekitar 279 trade, setiap simbol ≥ 14. Keputusan akhir tetap ditentukan OOS dan REAL.
2. Grid jam akhir 17 dan 19.
