//+------------------------------------------------------------------+
//| Types.mqh — enum dan struct yang dipakai antar-modul SDBot.
//| Modul berkomunikasi lewat struct ini, bukan variabel global (RULES).
//+------------------------------------------------------------------+
#ifndef SDB_CORE_TYPES_MQH
#define SDB_CORE_TYPES_MQH

enum ENUM_SDB_LOG_LEVEL
  {
   SDB_LOG_DEBUG = 0,
   SDB_LOG_INFO = 1,
   SDB_LOG_WARN = 2,
   SDB_LOG_ERROR = 3,
   SDB_LOG_CRITICAL = 4
  };

enum ENUM_SDB_SEVERITY
  {
   SDB_SEV_INFO = 0,
   SDB_SEV_MEDIUM = 1,
   SDB_SEV_HIGH = 2,
   SDB_SEV_CRITICAL = 3
  };

// Mode komponen skor konfirmasi Fase 5 (PC-25): OFF tidak dihitung, SHADOW dicatat active=0, ACTIVE ikut skor gerbang.
enum ENUM_SDB_COMPONENT_MODE
  {
   SDB_COMPONENT_OFF = 0,
   SDB_COMPONENT_SHADOW = 1,
   SDB_COMPONENT_ACTIVE = 2
  };

enum ENUM_SDB_TRADING_STYLE
  {
   SDB_STYLE_SCALPING = 0,
   SDB_STYLE_DAY = 1,
   SDB_STYLE_SWING = 2,
   SDB_STYLE_POSITION = 3
  };

enum ENUM_SDB_ACCOUNT_TYPE
  {
   SDB_ACC_DEMO = 0,
   SDB_ACC_REAL = 1,
   SDB_ACC_CENT = 2
  };

enum ENUM_SDB_VALIDATION
  {
   SDB_VAL_PASSED = 0,
   SDB_VAL_PENDING = 1,
   SDB_VAL_REJECTED = 2
  };

enum ENUM_SDB_CONN_ACTION
  {
   SDB_CONN_NONE = 0,
   SDB_CONN_LOG_DOWN = 1,
   SDB_CONN_ALERT_MEDIUM = 2,
   SDB_CONN_ALERT_RECOVERED = 3
  };

// File database yang dibuka CLogger (spec 03 Req 1).
enum ENUM_SDB_DB_TARGET
  {
   SDB_DB_NONE = 0,        // optimasi: tidak membuka file apa pun
   SDB_DB_LIVE = 1,        // sdbot.sqlite
   SDB_DB_TESTER = 2,      // sdbot_tester.sqlite
   SDB_DB_UNITTEST = 3     // sdbot_unittest.sqlite
  };

// Eksekusi (spec 04 design §4.1, §5).
enum ENUM_SDB_RETCODE_CLASS
  {
   SDB_RC_SUCCESS = 0,
   SDB_RC_NO_CHANGES = 1,
   SDB_RC_TRANSIENT = 2,       // requote, harga berubah: aman diulang
   SDB_RC_AMBIGUOUS = 3,       // tanpa jawaban pasti: cari dulu berdasarkan ID permintaan
   SDB_RC_POSITION_GONE = 4,
   SDB_RC_PERMANENT = 5,
   SDB_RC_MARKET_CLOSED = 6    // sesi simbol tutup (jeda harian, akhir pekan): tunda, bukan gagal
  };

enum ENUM_SDB_NEXT_STEP
  {
   SDB_STEP_SUCCEED = 0,
   SDB_STEP_RETRY = 1,
   SDB_STEP_GONE = 2,
   SDB_STEP_GIVE_UP = 3,
   SDB_STEP_DEFER = 4          // coba lagi di tick berikutnya, tanpa retry beruntun dan tanpa ERROR
  };

enum ENUM_SDB_EXEC
  {
   SDB_EXEC_OK = 0,
   SDB_EXEC_SKIPPED = 1,       // ditolak aturan sebelum ke broker (misalnya SL tidak lebih baik)
   SDB_EXEC_GONE = 2,          // posisi sudah tidak ada
   SDB_EXEC_FAILED = 3
  };

// Hasil satu percobaan close all per posisi (spec 05 Req 5; perbaikan v1.14).
enum ENUM_SDB_CLOSE_TRY
  {
   SDB_CLOSE_TRY_CLOSED = 0,
   SDB_CLOSE_TRY_DEFERRED = 1,   // pasar tutup: dicoba lagi, bukan gagal
   SDB_CLOSE_TRY_FAILED = 2
  };

enum ENUM_SDB_APP_MODE
  {
   SDB_APP_LIVE = 0,           // SDBot.mq5 (live dan backtest)
   SDB_APP_HARNESS = 1,        // SDBotHarness.mq5
   SDB_APP_UNITTEST = 2        // suite TestApp
  };

// Risk management (spec 05 design §4.1, §5).
enum ENUM_SDB_DD_LEVEL
  {
   SDB_DD_NORMAL = 0,
   SDB_DD_INFO = 1,
   SDB_DD_REDUCE = 2,          // lot x 0.5
   SDB_DD_STOP = 3             // STOPPED; hanya reset manual yang mengembalikannya
  };

enum ENUM_SDB_LOT_FLAG
  {
   SDB_LOT_OK = 0,
   SDB_LOT_BELOW_MIN = 1,
   SDB_LOT_CAPPED_MAX = 2,
   SDB_LOT_INVALID = 3         // nilai uang per lot <= 0
  };

// Kategori aset untuk batas posisi per kategori (spec 05 Req 2.8, PC-10).
enum ENUM_SDB_ASSET_CLASS
  {
   SDB_CLASS_FOREX_MAJOR = 0,  // pasangan dengan USD
   SDB_CLASS_FOREX_CROSS = 1,  // dua mata uang fiat tanpa USD
   SDB_CLASS_COMMODITY = 2,    // XAU, XAG, ...
   SDB_CLASS_CRYPTO = 3,
   SDB_CLASS_OTHER = 4         // tidak dikenali (indeks, dll.)
  };

// Manajemen posisi (spec 06 design §4.3, §5).
enum ENUM_SDB_SL_SOURCE
  {
   SDB_SL_SRC_NONE = 0,        // tidak diketahui: BE dan partial dilewati (Req 1.3)
   SDB_SL_SRC_COMMENT = 1,     // komentar SDB|<SL>|<ID>
   SDB_SL_SRC_ORDER = 2,       // ORDER_SL order pembuka di history
   SDB_SL_SRC_DB = 3           // tabel trades lewat event sink
  };

enum ENUM_SDB_POS_ACTION
  {
   SDB_ACT_BE = 0,
   SDB_ACT_TRAIL = 1,
   SDB_ACT_PARTIAL = 2,
   SDB_ACT_RESTORE = 3,
   SDB_ACT_COUNT = 4
  };

// Nilai mahal per posisi yang tidak berubah selama posisi terbuka, plus penghitung retry per aksi.
struct PositionCacheEntry
  {
   ulong             positionId;
   bool              owned;
   bool              isBuy;
   double            entry;
   datetime          entryTime;
   double            initialSl;
   ENUM_SDB_SL_SOURCE slSource;
   double            initialVolume;
   double            riskMoney;       // SDB_NULL_DOUBLE bila SL awal tidak diketahui
   double            commission;      // komisi pulang-pergi (uang, positif) untuk titik BE
   string            symbol;
   double            beSl;            // titik BE yang dipasang; 0 = belum
   bool              beDone;
   bool              partialDone;
   bool              trailDone;
   bool              slUnknownLogged;
   bool              partialSkippedLogged;
   datetime          lastTrailEventBar;
   int               fails[SDB_ACT_COUNT];
   datetime          lastFail[SDB_ACT_COUNT];
   double            failKeySl[SDB_ACT_COUNT];   // SL saat gagal; berubah -> penghitung di-reset (Req 5.3)
   double            failKeyVol[SDB_ACT_COUNT];
   bool              failAlerted[SDB_ACT_COUNT];
  };

// Hasil satu putaran close all (Req 5.8). closedMarket = dilewati karena pasar simbolnya tutup.
struct CloseAllResult
  {
   int               total;
   int               closed;
   int               failed;
   int               closedMarket;
  };

// Permintaan market order ke CExecutor. SL dan TP harga absolut.
struct OrderRequest
  {
   bool              isBuy;
   double            sl;
   double            tp;
   double            volume;
   long              signalId;        // SDB_NULL_LONG sebelum Fase 3
  };

// Hasil OpenMarket (Req 3.4). rejectStage "" = berhasil, selain itu kode reject_stage.
struct OrderResult
  {
   bool              ok;
   string            rejectStage;
   string            detail;
   uint              retcode;
   string            requestId;
   long              positionId;
   long              dealTicket;
   double            priceRequested;
   double            priceFilled;
   double            volumeFilled;
   long              slippagePts;     // SDB_NULL_LONG bila harga isi tidak diketahui
   long              spreadPts;
   double            riskMoney;       // SDB_NULL_DOUBLE bila tidak bisa dihitung
   int               attempts;
  };

// Nilai penanda NULL untuk kolom yang boleh kosong: DatabaseBind MQL5 tidak bisa mengikat NULL,
// jadi Logger mengubah penanda ini menjadi NULL (NULLIF) saat menulis.
#define SDB_NULL_DOUBLE DBL_MAX
#define SDB_NULL_LONG   LONG_MIN

// Semua waktu di struct event adalah waktu server MT5; Logger mengubahnya ke UTC saat menulis.

// Snapshot akun untuk tabel accounts.
struct AccountSnapshot
  {
   long                     login;
   string                   server;
   string                   company;
   ENUM_SDB_ACCOUNT_TYPE    type;
   ENUM_ACCOUNT_MARGIN_MODE marginMode;
   string                   currency;
   long                     leverage;
   double                   balance;
   double                   equity;
   double                   peakEquity;   // puncak dari status risiko (spec 05); sebelum itu = equity
   datetime                 time;
  };

// Satu baris tabel sessions (spec 03 Req 8). inputsJson wajib kanonik (CurrentInputsJson),
// input_hash dihitung CLogger dari teks itu. testerFrom/testerTo 0 dan testerModel "" = NULL.
struct SessionInfo
  {
   long              login;
   long              runKey;          // SDB_RUN_KEY_LIVE, SDB_RUN_KEY_NEW, atau run_key run tester yang sedang jalan
   long              magic;
   string            symbol;
   string            mode;            // SDB_SESSION_MODE_*
   string            eaVersion;
   string            inputsJson;
   datetime          startedAt;
   datetime          testerFrom;
   datetime          testerTo;
   string            testerModel;
  };

// Alert untuk tabel alerts; dikirim Notifier (spec 08). type = kode stabil dari enums.md.
struct AlertEvent
  {
   string            type;
   ENUM_SDB_SEVERITY severity;
   string            message;
   string            symbol;
   long              magic;
   datetime          time;
   string            key;             // notify_key (spec 08): diisi CTeeSink bila kosong
  };

// Hasil kirim notifikasi untuk baris alerts dengan notify_key yang sama (spec 08 Req 5).
struct AlertStatus
  {
   string            key;
   string            status;          // SDB_ALERT_STATUS_*
   int               attempts;
   datetime          sentAt;          // 0 = NULL (waktu server)
   string            reason;          // SDB_ALERT_STATUS_REASON_*, "" = NULL
  };

//--- Notifier (spec 08 design §4.1)
enum ENUM_SDB_NT_LEVEL
  {
   SDB_NT_INFO = 0,
   SDB_NT_SUCCESS = 1,
   SDB_NT_MEDIUM = 2,
   SDB_NT_HIGH = 3,
   SDB_NT_CRITICAL = 4
  };

enum ENUM_SDB_NT_SCOPE
  {
   SDB_NT_SCOPE_INSTANCE = 0,
   SDB_NT_SCOPE_ACCOUNT = 1
  };

enum ENUM_SDB_SEND_CODE
  {
   SDB_SEND_OK = 0,
   SDB_SEND_TEMP = 1,         // gagal sementara: coba lagi siklus berikutnya
   SDB_SEND_LIMITED = 2,      // dibatasi: tunggu retryAfterSec
   SDB_SEND_PERMANENT = 3     // tidak akan berhasil bila diulang
  };

enum ENUM_SDB_NT_NEXT
  {
   SDB_NT_DONE_SENT = 0,
   SDB_NT_RETRY = 1,
   SDB_NT_WAIT = 2,
   SDB_NT_DONE_FAILED = 3
  };

// Hasil klasifikasi respons Telegram (spec 09 design §4.3).
enum ENUM_SDB_TG_OUTCOME
  {
   SDB_TG_OK = 0,
   SDB_TG_TEMP = 1,
   SDB_TG_LIMITED = 2,
   SDB_TG_PARSE_ERROR = 3,    // HTML ditolak: kirim ulang sekali sebagai teks polos
   SDB_TG_PERMANENT = 4,
   SDB_TG_CONFIG = 5          // URL belum diizinkan, token/chat salah: Telegram nonaktif sesi ini
  };

//--- Analisis struktur (spec 10 design §4.1). Array bar selalu urut waktu naik (indeks 0 tertua).
enum ENUM_SDB_DIR
  {
   SDB_DIR_BEAR = -1,
   SDB_DIR_NONE = 0,
   SDB_DIR_BULL = 1
  };

struct SdbSwing
  {
   int               index;           // indeks di array bar
   datetime          time;
   double            price;
   bool              isHigh;
  };

struct SdbStructure
  {
   ENUM_SDB_DIR      dir;             // arah BOS terakhir dalam jendela lookback
   datetime          bosTime;         // 0 = belum ada BOS
   double            bosLevel;
   double            lastHigh;        // swing high terkonfirmasi terakhir (0 = tidak ada)
   datetime          lastHighTime;
   double            lastLow;
   datetime          lastLowTime;
   int               swings;
  };

struct SdbStructureParams
  {
   int               strength;
   int               lookback;
   int               emaPeriod;
   int               slopeBars;
  };

struct SdbTfAnalysis
  {
   bool              ready;
   string            reason;          // "" = siap; "data kurang"
   datetime          barTime;         // bar tertutup terbaru yang dianalisis
   SdbStructure      st;
   double            ema;
   ENUM_SDB_DIR      emaDir;
  };

struct SdbBias
  {
   ENUM_SDB_DIR      dir;
   string            reason;          // OK, STRUCTURE, EMA, CONFLICT, DATA
   datetime          htfBarTime;
  };

//--- Zona Supply & Demand (spec 11 design §4.1)
enum ENUM_SDB_ZONE_STATUS
  {
   SDB_ZONE_FRESH = 0,
   SDB_ZONE_TESTED = 1,
   SDB_ZONE_WEAK = 2,          // >= 2 sentuhan: tidak dipakai (PRD)
   SDB_ZONE_INVALID = 3,       // close melewati batas jauh (final)
   SDB_ZONE_EXPIRED = 4        // usia > MaxZoneAgeBars (final)
  };

struct SdbZoneParams
  {
   double            minWidthAtr;
   double            maxWidthAtr;
   double            minLegAtr;
   int               legBars;
   int               maxAge;
   int               strength;
  };

struct SdbZone
  {
   string            id;
   bool              demand;
   datetime          swingTime;
   int               swingIdx;
   double            distal;          // batas jauh: low (demand) / high (supply) candle swing
   double            proximal;        // batas dekat: sisi badan yang menghadap harga
   double            atr;             // ATR MTF di bar swing
   double            widthAtr;
   double            legAtr;
   int               activeIdx;
   datetime          activeTime;
   int               touches;
   ENUM_SDB_ZONE_STATUS status;
   bool              used;
  };

// Trigger price action LTF (spec 12): kode = SDB_PA_PATTERN_*.
struct SdbPattern
  {
   string            code;
   ENUM_SDB_DIR      dir;
   int               score;           // PRD: engulfing kuat 10, pin bar 7, terarah lain 3, tanpa pola 0
   datetime          barTime;
  };

// Sinyal dan entry (spec 13 design §3.1): parameter dari input, fakta satu kandidat, hasil penilaian.
struct SdbSignalParams
  {
   double            minScorePct;     // InpMinConfluenceScore: persen dari maksimum aktif
   double            minRR;
   double            slBufferAtr;
   double            minSlAtr;
   double            maxSlAtr;
   int               maxSpreadPoints; // 0 = filter spread mati (spec 14)
   bool              allowTestedZones; // spec 23: false = zona Tested ditolak NO_VALID_ZONE
  };

// Hasil skor Fibonacci satu kandidat (spec 18, Strategies/FibRules.mqh).
struct SdbFibResult
  {
   int               score;           // 0..SDB_SCORE_MAX_FIB
   double            ratio;           // rasio retracement batas dekat; -1 = tidak dihitung
   double            level;           // level terdekat; 0 = tidak ada
   double            dist;            // |ratio - level|
   double            legStart;        // batas jauh zona
   double            legEnd;          // ekstrem impuls
   string            reason;          // "" = dihitung
  };

// Hasil skor trendline satu kandidat (spec 19, Strategies/TrendlineRules.mqh).
struct SdbTrendlineResult
  {
   int               score;           // 0, 7, 15
   int               touches;         // 0 = tidak ada garis
   double            slopeAtr;        // ATR per bar MTF (+ naik, - turun)
   double            distAtr;         // jarak proyeksi ke zona dalam ATR (0 = di dalam zona)
   datetime          t1;              // titik pembentuk pertama
   datetime          t2;              // titik pembentuk kedua
   string            reason;          // "" = ada garis
  };

// Hasil skor breakout & retest satu kandidat (spec 20, Strategies/BreakoutRules.mqh).
struct SdbBreakoutResult
  {
   int               score;           // 0 atau 10
   double            level;           // 0 = tidak ada
   int               ageBars;         // bar MTF sejak breakout sampai bar kandidat
   double            distAtr;         // jarak level ke zona dalam ATR
   datetime          tBreak;          // waktu bar breakout
   string            reason;          // "" = ada
  };

// Hasil skor RSI divergence satu kandidat (spec 21, Strategies/RsiRules.mqh).
struct SdbRsiResult
  {
   int               score;           // 0 atau 5
   bool              have;            // ada dua swing sinyal
   double            rsiDiff;         // poin RSI, + = searah divergence
   double            priceDiffAtr;    // |harga swing 2 - swing 1| / ATR
   int               ageBars;         // n - indeks swing kedua
   string            reason;          // "" = ada dua swing
  };

struct SdbSignalFacts
  {
   ENUM_SDB_DIR      dir;             // arah bias HTF = arah kandidat
   SdbZone           zone;            // zona valid searah yang disentuh bar
   string            preStage;        // "" = lolos pre-filter risiko, selain itu SDB_REJECT_STAGE_*
   string            preDetail;
   bool              positionOpen;    // instance (magic + simbol) masih punya posisi
   SdbPattern        pattern;         // pola bar LTF untuk arah kandidat
   int               trendScore;      // TrendScore MTF
   double            bid;
   double            ask;
   double            point;
   int               digits;
   int               stopsLevel;      // point
   double            atrMtf;          // ATR(14) MTF bar tertutup terakhir
   bool              haveOpposite;
   double            oppositeProximal;
   string            session;         // sesi UTC bar (spec 14): TOKYO, LONDON, OVERLAP, NEWYORK, OFF
   bool              sessionAllowed;
   bool              sessionInWindow; // spec 25: sesi diizinkan tanpa memperhitungkan jam akhir
   int               sessionEndHour;  // spec 25: InpSessionEndHourUtc
   long              spreadPoints;    // ask - bid saat penilaian (point)
   bool              newsBlocked;     // filter berita (spec 16)
   string            newsDetail;      // event yang memblokir
   string            newsStatus;      // ON, OFF, DISABLED
   string            newsNext;        // event berdampak terdekat 24 jam; "" = tidak ada
   ENUM_SDB_COMPONENT_MODE fibMode;   // spec 18
   SdbFibResult      fib;
   ENUM_SDB_COMPONENT_MODE tlMode;    // spec 19
   SdbTrendlineResult tl;
   ENUM_SDB_COMPONENT_MODE boMode;    // spec 20
   SdbBreakoutResult bo;
   ENUM_SDB_COMPONENT_MODE rsiMode;   // spec 21
   SdbRsiResult      rsi;
  };

struct SdbStops
  {
   double            entry;
   double            sl;
   double            tp;
   double            risk;            // R: jarak entry ke SL
   double            rr;
   string            tpSource;        // SDB_TP_SOURCE_*
  };

struct SdbDecision
  {
   string            stage;           // "" = lolos sampai tahap SL/TP; lot dan eksekusi dinilai engine
   string            detail;
   int               zoneScore;
   int               trendScore;
   int               paScore;
   int               fibScore;        // spec 18: dicatat di semua mode != OFF, ikut total hanya ACTIVE
   int               tlScore;         // spec 19: sama dengan fibScore
   int               boScore;         // spec 20
   int               rsiScore;        // spec 21 (hanya skor, tidak pernah tahap tolak)
   int               total;
   int               maxActive;
   double            pct;
   SdbStops          stops;
   bool              stopsKnown;
  };

// Satu kandidat sinyal (tabel signals + 3 baris signal_scores). id dari SignalIdOf, bukan DB.
struct SignalRecord
  {
   long              id;
   long              magic;
   string            symbol;
   datetime          time;            // waktu buka bar LTF (server)
   string            direction;       // SDB_DIRECTION_*
   string            style;           // SDB_TRADING_STYLE_*
   string            zoneRef;
   double            scoreTotal;
   long              spreadPoints;
   string            status;          // SDB_SIGNAL_STATUS_*
   string            rejectStage;     // "" untuk ACCEPTED
   string            rejectDetail;
   string            contextJson;
   int               scoreZone;
   int               scoreTrend;
   int               scorePa;
   int               scoreFib;        // spec 18
   ENUM_SDB_COMPONENT_MODE fibMode;
   int               scoreTrendline;  // spec 19
   ENUM_SDB_COMPONENT_MODE trendlineMode;
   int               scoreBreakout;   // spec 20
   ENUM_SDB_COMPONENT_MODE breakoutMode;
   int               scoreRsi;        // spec 21
   ENUM_SDB_COMPONENT_MODE rsiMode;
  };

// Laporan harian (spec 09 design §4.1-4.2).
#define SDB_DS_KIND_IN      0
#define SDB_DS_KIND_OUT     1
#define SDB_DS_KIND_BALANCE 2
#define SDB_DS_MAX_SYMBOLS  16

struct SdbDealRow
  {
   long              ticket;
   long              positionId;
   string            symbol;
   int               kind;            // SDB_DS_KIND_*
   long              time;            // waktu server
   double            net;             // profit + komisi + swap + fee (deal trading)
   double            amount;          // jumlah operasi saldo (BALANCE/CREDIT)
  };

struct SdbDayStats
  {
   long              dayStart;
   double            net;
   int               closed;
   int               wins;
   double            balanceOps;
   bool              hasBalanceOps;
   int               symbolCount;
   string            symbols[SDB_DS_MAX_SYMBOLS];
   double            symbolNet[SDB_DS_MAX_SYMBOLS];
   double            balanceNow;      // diisi pengumpul saat laporan dibuat
  };

// Data heartbeat dari App (spec 09 design §4.1); instance hidup dan pesan ditahan diisi notifier.
struct SdbHeartbeat
  {
   double            balance;
   double            equity;
   double            ddPct;
   string            riskStatus;      // normal, lot x 0.5, pause harian, STOPPED
   int               sdbotPositions;
   int               instancesAlive;
   int               heldLastHour;
  };

struct SdbStartInfo
  {
   long              magic;
   string            presetTag;
   string            validation;
   bool              hasPrevious;
   bool              previousAbnormal;
   datetime          previousEndedAt;
   string            previousReason;
  };

struct SdbNtContext
  {
   long              login;           // penanda AKUN <login> untuk heartbeat dan laporan harian
   string            symbol;
   string            accountTag;      // CENT, REAL, DEMO, TESTER
   string            eaVersion;
   string            currency;
   int               digits;
  };

struct SdbOutMessage
  {
   string            key;
   string            type;
   string            text;            // HTML Telegram, sudah dipotong ke batas
   bool              silent;
   ENUM_SDB_SEVERITY severity;
  };

struct SdbSendResult
  {
   ENUM_SDB_SEND_CODE code;
   int               retryAfterSec;   // LIMITED: tunggu; TEMP: jeda sebelum kiriman berikutnya (spec 09 Req 2.6)
   string            error;
   bool              disable;         // error konfigurasi: transport nonaktif sesi ini (spec 09 Req 2.3)
   string            note;            // alasan status saat SENT/FAILED, mis. PLAIN_TEXT, TELEGRAM_OFF
  };

struct SdbNtItem
  {
   SdbOutMessage     msg;
   long              queuedAt;        // waktu notifier saat masuk antrean (bukan AlertEvent.time)
   int               attempts;
   long              notBefore;       // 0 = siap
  };

// Struct event berikut mengikuti kolom tabel di shared/schema/data_db.sql. Kolom teks enum
// diisi dengan konstanta Core/SchemaEnums.mqh. Kolom yang boleh NULL memakai SDB_NULL_*.

struct TradeRecord          // tabel trades (spec 04 mengisi dari Executor, spec 06 dari rekonsiliasi)
  {
   long              positionId;
   long              magic;
   string            symbol;
   string            direction;       // SDB_DIRECTION_*
   string            source;          // SDB_TRADE_SOURCE_*
   double            volumeInitial;
   double            priceRequested;  // SDB_NULL_DOUBLE untuk RECONCILED
   double            priceOpen;
   long              slippagePoints;  // SDB_NULL_LONG untuk RECONCILED
   long              spreadPoints;    // SDB_NULL_LONG untuk RECONCILED
   double            slInitial;
   double            tpInitial;
   double            riskMoney;       // SDB_NULL_DOUBLE bila tidak diketahui
   double            riskPct;         // SDB_NULL_DOUBLE bila tidak diketahui
   long              signalId;        // SDB_NULL_LONG sebelum Fase 3
   string            eaVersion;
   datetime          openedAt;
  };

struct DealRecord           // tabel deals
  {
   long              dealTicket;
   long              positionId;
   long              magic;
   string            symbol;
   datetime          time;
   string            entry;           // SDB_DEAL_ENTRY_*
   string            dealType;        // SDB_DEAL_TYPE_*
   double            volume;
   double            price;
   string            reason;          // SDB_DEAL_REASON_*
   double            profit;
   double            commission;
   double            swap;
   double            fee;
  };

struct PositionEvent        // tabel position_events
  {
   long              positionId;
   datetime          time;
   string            type;            // SDB_POSITION_EVENT_*
   double            slOld;           // SDB_NULL_DOUBLE bila tidak relevan
   double            slNew;           // SDB_NULL_DOUBLE bila tidak relevan
   double            volume;
   double            price;
   long              spreadPoints;
   string            detail;          // "" = NULL
  };

struct ClosureRecord        // tabel closures
  {
   long              positionId;
   long              magic;
   string            symbol;
   datetime          closedAt;
   string            reason;          // SDB_CLOSE_REASON_*
   double            levelPrice;      // SDB_NULL_DOUBLE untuk close manual
   double            priceClose;
   long              slippagePoints;  // SDB_NULL_LONG bila tidak ada level
   double            volumeTotal;
   double            profit;
   double            commission;
   double            swap;
   double            fee;
   double            netProfit;
   double            rResult;         // SDB_NULL_DOUBLE bila risiko awal tidak diketahui
   double            mfeR;            // SDB_NULL_DOUBLE bila bar M1 tidak tersedia
   double            maeR;
   long              holdingSec;
   bool              beActivated;
   bool              partialDone;
   bool              trailActivated;
  };

struct BalanceOpRecord      // tabel balance_ops (spec 05)
  {
   long              dealTicket;
   datetime          time;
   string            opType;          // SDB_BALANCE_OP_TYPE_*
   double            amount;
   string            comment;
  };

#endif // SDB_CORE_TYPES_MQH
