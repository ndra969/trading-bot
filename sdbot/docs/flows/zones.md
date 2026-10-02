# Zona Supply & Demand (spec 11)

```mermaid
flowchart TB
    T([CZoneBook.OnTick]) --> N{bar H1 tertutup baru atau penanda Used berubah?}
    N -->|tidak| Z([selesai])
    N -->|ya| C[CopyRates shift 1, ZonesNeeded = 156 bar]
    C -->|kurang| DK[peta kosong, WARN throttled]
    C --> CL[hapus GV Used zona dengan swing sebelum bar ke-(terakhir - 100)]
    CL --> B[BuildZones: ATR(14) Wilder, FindSwings kekuatan 2]
    B --> K[calon per swing: demand = low .. max(open,close); supply = high .. min(open,close)]
    K --> W{lebar 0,3-2,0 ATR dan gerak keluar >= 1,5 ATR dalam 10 bar?}
    W -->|tidak| X[dibuang]
    W -->|ya| A[aktif sejak max(konfirmasi swing, gerak keluar tercapai)]
    A --> S[status: Invalid (close lewat batas jauh) > sentuhan 0/1/>=2 = Fresh/Tested/Lemah > Kedaluwarsa > 100 bar]
    S --> U[Used dari GV magic_ZU_epoch_D/S]
```

Pipeline (spec 13) bertanya `TouchedZone` (zona valid searah yang disentuh bar, Fresh lalu terbaru), `OppositeZone` (batas dekat zona lawan terdekat untuk TP), dan `MarkUsed` setelah entry. Peta adalah fungsi murni dari 156 bar terakhir dan daftar Used, sehingga jalan terus, restart, dan pembangunan dari histori pasti sama (SC-13/SC-13x).
