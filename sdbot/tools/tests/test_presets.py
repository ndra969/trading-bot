"""Preset SDBot per simbol (spec 07 Req 2, PC-10, PC-12): TP-01..05."""

import re
from pathlib import Path

import gen_presets

PRESETS = Path(__file__).resolve().parents[2] / "ea" / "src" / "Presets"

EXPECTED_MAGIC = {
    "EURUSD": 2026091901,
    "GBPUSD": 2026091902,
    "EURJPY": 2026091903,
    "GBPJPY": 2026091904,
    "USDJPY": 2026091905,
    "USDCHF": 2026091906,
    "AUDUSD": 2026091907,
    "USDCAD": 2026091908,
    "NZDUSD": 2026091909,
    "XAUUSD": 2026091910,
    "XAGUSD": 2026091911,
    "BTCUSD": 2026091912,
}
SECRET_KEY = re.compile(r"token|chatid|metaquotes|password|secret", re.IGNORECASE)


def _read(symbol: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PRESETS / f"SDBot_DAY_{symbol}c.set").read_text(encoding="ascii").splitlines():
        line = line.strip()
        if line and not line.startswith(";") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def test_tp01_one_preset_per_python_bot_symbol():
    names = sorted(
        p.name for p in PRESETS.glob("SDBot_DAY_*.set") if not p.name.endswith(".local.set")
    )
    assert names == sorted(f"SDBot_DAY_{s}c.set" for s in EXPECTED_MAGIC)


def test_tp02_magic_matches_pc10_and_is_unique():
    magics = {s: int(_read(s)["InpMagicNumber"]) for s in EXPECTED_MAGIC}
    assert magics == EXPECTED_MAGIC
    assert len(set(magics.values())) == len(magics)


def test_tp03_safe_defaults_suffix_and_tag():
    for symbol in EXPECTED_MAGIC:
        v = _read(symbol)
        assert v["InpAllowLiveTrading"] == "false", symbol
        assert v["InpSymbolSuffix"] == "c", symbol
        assert v["InpPresetTag"] == f"{symbol}c", symbol
        assert v["InpRiskPerTradePct"] == "0.5", symbol


def test_tp04_ascii_and_no_secret_values():
    # *.local.set (salinan pribadi berisi token, diabaikan git) bukan preset repo.
    for path in (p for p in PRESETS.glob("SDBot_DAY_*.set") if not p.name.endswith(".local.set")):
        raw = path.read_bytes()
        assert all(b < 128 for b in raw), f"{path.name} bukan ASCII"
        for line in raw.decode("ascii").splitlines():
            if line.strip().startswith(";") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            assert not (
                SECRET_KEY.search(key) and value.strip()
            ), f"{path.name}: {key} berisi nilai"


def test_tp05_files_equal_generator_output():
    for symbol in EXPECTED_MAGIC:
        expected = gen_presets.render(symbol)
        actual = (PRESETS / f"SDBot_DAY_{symbol}c.set").read_text(encoding="ascii")
        assert actual == expected, f"{symbol}: jalankan `uv run python sdbot/tools/gen_presets.py`"


def test_ts47_analysis_inputs_have_defaults():
    """Spec 10 Req 7.3: input analisis dengan default PRD/katalog di semua preset."""
    for symbol in EXPECTED_MAGIC:
        v = _read(symbol)
        assert v.get("InpSwingStrength") == "2", symbol
        assert v.get("InpStructureLookback") == "100", symbol
        assert v.get("InpEmaPeriod") == "50", symbol
        assert v.get("InpEmaSlopeBars") == "3", symbol


def test_ts48_zone_inputs_have_defaults():
    """Spec 11 Req 5.2: input zona dengan default dari ukuran histori di semua preset."""
    for symbol in EXPECTED_MAGIC:
        v = _read(symbol)
        assert v.get("InpZoneMinWidthAtr") == "0.3", symbol
        assert v.get("InpZoneMaxWidthAtr") == "2.0", symbol
        assert v.get("InpZoneMinLegAtr") == "1.5", symbol
        assert v.get("InpZoneLegBars") == "10", symbol
        assert v.get("InpMaxZoneAgeBars") == "100", symbol


def test_ts46_telegram_inputs_present_and_empty():
    """Spec 09 Req 1.8: input Telegram ada di preset repo, token dan chat ID kosong."""
    for symbol in EXPECTED_MAGIC:
        v = _read(symbol)
        assert v.get("InpTelegramToken") == "", symbol
        assert v.get("InpTelegramChatID") == "", symbol
        assert v.get("InpHeartbeatMinutes") == "60", symbol


def test_ts51_signal_inputs_have_defaults():
    """Spec 13 Req 7.2: input sinyal dan SL dengan default PC-19 di semua preset."""
    for symbol in EXPECTED_MAGIC:
        v = _read(symbol)
        assert v.get("InpMinConfluenceScore") == "65", symbol
        assert v.get("InpMinRR") == "2.0", symbol
        assert v.get("InpSlBufferAtr") == "0.1", symbol
        assert v.get("InpMinSlAtr") == "0.3", symbol
        assert v.get("InpMaxSlAtr") == "3.0", symbol


PC22_SPREAD = {
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


def test_ts54_session_spread_inputs():
    """Spec 14 Req 4.1: sesi London + NY, offset tester 0, spread per simbol PC-22."""
    for symbol, spread in PC22_SPREAD.items():
        v = _read(symbol)
        assert v.get("InpSessionTokyo") == "false", symbol
        assert v.get("InpSessionLondon") == "true", symbol
        assert v.get("InpSessionNewYork") == "true", symbol
        assert v.get("InpTesterUtcOffsetHours") == "0", symbol
        assert v.get("InpMaxSpreadPoints") == str(spread), symbol


def test_ts56_exposure_input():
    """Spec 15 Req 3.1: batas posisi searah per mata uang = 2 di semua preset (PC-23)."""
    for symbol in EXPECTED_MAGIC:
        assert _read(symbol).get("InpMaxSameDirectionPerCurrency") == "2", symbol
