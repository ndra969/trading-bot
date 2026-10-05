# Filter berita (spec 16)

```mermaid
flowchart TB
    I([CSdbApp.Init: cfg.signalsOn]) --> NI[CNewsFilter.Init: mata uang dasar + kuotasi simbol]
    NI --> EN{InpNewsFilter?}
    EN -->|false| DIS[status DISABLED]
    EN -->|true| MODE{Strategy Tester?}
    MODE -->|ya| CSV[baca Common\Files\InpNewsCsvFile sekali]
    CSV -->|tidak ada / tanpa event valid| OFF
    CSV -->|ok| ON[status ON]
    MODE -->|tidak: live| LIVE[CSignalEngine.CollectFacts -> Refresh tiap 15 menit]
    LIVE --> CAL[CalendarValueHistory -1..+2 hari per mata uang kalender + CalendarEventById]
    CAL -->|gagal| OFF[status OFF: entry tidak diblokir berita; coba lagi 60 detik]
    CAL -->|ok| ON
    OFF --> AL[alert High NEWS_FILTER_OFF, satu kali per sesi]
    ON --> BL{Blocked bar: event mata uang simbol, jendela inklusif HIGH ±InpNewsHighMinutes, MEDIUM ±InpNewsMediumMinutes}
    BL -->|ya| REJ[NEWS_BLACKOUT, detail 'nama CCY DAMPAK menit', dampak tertinggi lalu terdekat]
    BL -->|tidak| NEXT[konteks news_next: event >= medium terdekat 24 jam]
```

Mata uang tanpa event kalender (XAU, XAG, BTC) hanya terlindungi lewat kaki USD. Hanya jadwal event yang dipakai, tidak pernah nilai actual, sehingga backtest tanpa lookahead. LOW tidak pernah memblokir.

## Kalender untuk tester

Kalender MT5 tidak tersedia di Strategy Tester. Script `Scripts/SDBot/ExportCalendar.mq5` di terminal yang login menulis `Common\Files\sdbot_calendar.csv` (baris `epoch_server,ccy,impact,event_id,nama`, urut waktu) untuk USD, EUR, GBP, JPY, CHF, AUD, CAD, NZD, dan ringkasan di `sdbot_calendar_status.txt`. Kalender yang belum sinkron (err 5401) ditunggu sampai 120 detik.

```powershell
sdbot\tools\run-ea-tests.ps1 -ExportCalendar             # terminal uji, tutup sendiri setelah selesai
sdbot\tools\run-ea-tests.ps1 -ExportCalendar -Baseline   # ekspor lalu backtest dasar
```
