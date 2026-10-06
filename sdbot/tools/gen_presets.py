"""Bangkitkan preset SDBot per simbol (spec 07 Req 2, PC-10, PC-12).

Satu tabel -> 12 file `ea/src/Presets/SDBot_DAY_<SIMBOL>c.set`, identik kecuali magic, tag, dan
komentar kategori. File hanya ASCII agar dialog Inputs -> Load MT5 membacanya apa pun encoding-nya.
Nilai referensi bot Python (spread, sesi, SL default) disalin dari `config/active_symbols.yaml`
dan hanya menjadi komentar sampai inputnya ada di Fase 3-4.

Pemakaian: uv run python sdbot/tools/gen_presets.py
"""

from __future__ import annotations

from pathlib import Path

PRESETS_DIR = Path(__file__).resolve().parents[1] / "ea" / "src" / "Presets"

# simbol: (magic PC-10, kategori, referensi bot Python: spread maks, sesi, SL default)
SYMBOLS: dict[str, tuple[int, str, str]] = {
    "EURUSD": (
        2026091901,
        "forex major",
        "spread maks 3 pip; sesi London + New York; SL default 30 pip",
    ),
    "GBPUSD": (
        2026091902,
        "forex major",
        "spread maks 4 pip; sesi London + New York; SL default 40 pip",
    ),
    "EURJPY": (
        2026091903,
        "forex cross",
        "spread maks 5 pip; sesi London + New York; SL default 20 pip",
    ),
    "GBPJPY": (
        2026091904,
        "forex cross",
        "spread maks 6 pip; sesi Tokyo + London; SL default 25 pip",
    ),
    "USDJPY": (
        2026091905,
        "forex major",
        "spread maks 3 pip; sesi Tokyo + London + New York; SL default 40 pip",
    ),
    "USDCHF": (
        2026091906,
        "forex major",
        "spread maks 4 pip; sesi London + New York; SL default 30 pip",
    ),
    "AUDUSD": (
        2026091907,
        "forex major",
        "spread maks 4 pip; sesi Sydney + Tokyo + New York; SL default 15 pip",
    ),
    "USDCAD": (
        2026091908,
        "forex major",
        "spread maks 4 pip; sesi London + New York; SL default 15 pip",
    ),
    "NZDUSD": (
        2026091909,
        "forex major",
        "spread maks 4 pip; sesi Tokyo + London + New York; SL default tidak diatur",
    ),
    "XAUUSD": (
        2026091910,
        "komoditas",
        "spread maks 50 pip (0.1); sesi London + New York; SL default 350 pip",
    ),
    "XAGUSD": (
        2026091911,
        "komoditas",
        "spread maks 10 pip (0.01); sesi London + New York; SL default 50 pip",
    ),
    "BTCUSD": (2026091912, "crypto", "spread maks 1000 pip (1.0); sesi 24/7; SL default 1500 pip"),
}

# Input dengan default PRD (Core/Inputs.mqh). Enum ditulis sebagai angka seperti file .set MT5.
COMMON_INPUTS: list[tuple[str, str]] = [
    ("InpTradingStyle", "1"),  # SDB_STYLE_DAY
    ("InpSymbolSuffix", "c"),
    ("InpAllowLiveTrading", "false"),
    ("InpLogLevel", "1"),  # SDB_LOG_INFO
    ("InpRiskPerTradePct", "0.5"),
    ("InpMaxOpenRiskPct", "3.0"),
    ("InpMaxPosForexMajor", "5"),
    ("InpMaxPosForexCross", "3"),
    ("InpMaxPosCommodity", "1"),
    ("InpMaxPosCrypto", "1"),
    ("InpMaxSameDirectionPerCurrency", "2"),  # spec 15, PC-23
    ("InpDailyLossPct", "3.0"),
    ("InpDDReducePct", "10.0"),
    ("InpDDStopPct", "15.0"),
    ("InpResetEmergencyStop", "false"),
    ("InpBreakevenR", "1.0"),
    ("InpBreakevenBufferPoints", "2"),
    ("InpPartialR", "1.5"),
    ("InpPartialPct", "50.0"),
    ("InpTrailATRPeriod", "14"),
    ("InpTrailATRMult", "2.0"),
    # Analisis struktur (spec 10, PC-16)
    ("InpSwingStrength", "2"),
    ("InpStructureLookback", "100"),
    ("InpEmaPeriod", "50"),
    ("InpEmaSlopeBars", "3"),
    # Zona S&D (spec 11, PC-17): default dari ukuran histori H1 12 simbol
    ("InpZoneMinWidthAtr", "0.3"),
    ("InpZoneMaxWidthAtr", "2.0"),
    ("InpZoneMinLegAtr", "1.5"),
    ("InpZoneLegBars", "10"),
    ("InpMaxZoneAgeBars", "100"),
    # Sinyal dan entry (spec 13, PC-19): skor = persen dari maksimum komponen aktif; SL relatif ATR(14) H1
    ("InpMinConfluenceScore", "65"),
    ("InpMinRR", "2.0"),
    ("InpSlBufferAtr", "0.1"),
    ("InpMinSlAtr", "0.3"),
    ("InpMaxSlAtr", "3.0"),
    # Filter sesi (spec 14, PC-21/22): London + New York UTC; selisih server-UTC tester 0 (Exness GMT+0)
    ("InpSessionTokyo", "false"),
    ("InpSessionLondon", "true"),
    ("InpSessionNewYork", "true"),
    ("InpTesterUtcOffsetHours", "0"),
    # Filter berita (spec 16, PC-24): high +-30, medium +-10 menit; CSV kalender untuk tester
    ("InpNewsFilter", "true"),
    ("InpNewsHighMinutes", "15"),
    ("InpNewsMediumMinutes", "0"),
    ("InpNewsCsvFile", "sdbot_calendar.csv"),
    ("InpScoreFibMode", "1"),  # SDB_COMPONENT_SHADOW (spec 18)
    # Notifikasi (spec 09): token dan chat ID sengaja kosong; diisi make_local_presets.py di *.local.set.
    ("InpTelegramToken", ""),
    ("InpTelegramChatID", ""),
    ("InpHeartbeatMinutes", "60"),
]


# Spread maksimum (point) = 3 x median spread live akun cent, tick 7 hari s.d. 2026-10-03 (spec 14, PC-22).
MAX_SPREAD_POINTS: dict[str, int] = {
    "EURUSD": 24,
    "GBPUSD": 30,
    "USDJPY": 30,
    "USDCHF": 39,
    "AUDUSD": 27,
    "USDCAD": 48,
    "NZDUSD": 42,
    "EURJPY": 48,
    "GBPJPY": 66,
    "XAUUSD": 720,
    "XAGUSD": 90,
    "BTCUSD": 3000,
}


def render(symbol: str) -> str:
    magic, category, reference = SYMBOLS[symbol]
    lines = [
        f"; SDBot preset {symbol}c - kategori {category} (PC-10). Dibangkitkan tools/gen_presets.py, jangan diedit tangan.",
        "; Akun cent Exness: ubah InpAllowLiveTrading=true dengan sadar sebelum dipasang (default aman: false).",
        "; Jangan isi token/chat ID Telegram di file ini; pakai salinan pribadi *.local.set yang tidak di-commit.",
        f"; Referensi bot Python (belum ada inputnya, Fase 3-4): {reference}.",
        f"InpMagicNumber={magic}",
        f"InpPresetTag={symbol}c",
    ]
    lines += [f"{key}={value}" for key, value in COMMON_INPUTS]
    lines.append(f"InpMaxSpreadPoints={MAX_SPREAD_POINTS[symbol]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    for symbol in SYMBOLS:
        path = PRESETS_DIR / f"SDBot_DAY_{symbol}c.set"
        path.write_text(render(symbol), encoding="ascii", newline="\n")
        print(f"[gen_presets] {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
