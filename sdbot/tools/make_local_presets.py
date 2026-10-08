"""Buat preset pribadi SDBot_DAY_<SIMBOL>c.local.set dari .env bot Python (spec 09 Req 1.4-1.7, PC-14).

SDBot memakai bot dan chat Telegram yang sama dengan bot Python (PC-06). Skrip ini menyalin setiap
preset repo dan mengisi InpTelegramToken / InpTelegramChatID dari TELEGRAM_BOT_TOKEN /
TELEGRAM_CHAT_ID, supaya token tidak disalin tangan dan tidak pernah masuk preset yang di-commit.

- .local.set yang sudah ada dan berbeda (misalnya disunting di MT5) tidak ditimpa tanpa --force.
- Setiap file hasil wajib diabaikan git (git check-ignore); bila tidak, file dihapus dan skrip gagal.
- Token tidak pernah dicetak.

--live mengisi InpAllowLiveTrading=true dan --risk mengganti InpRiskPerTradePct (0 < x <= 1) hanya di preset pribadi,
untuk menjalankan EA di akun cent (pengumpulan data, 2026-10-08). Preset repo tetap aman (false, 0.5).

Pemakaian: uv run python sdbot/tools/make_local_presets.py [--env PATH] [--presets DIR] [--force] [--live] [--risk 0.1]
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

SDBOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV = SDBOT.parent / ".env"
DEFAULT_PRESETS = SDBOT / "ea" / "src" / "Presets"
TOKEN_KEY = "TELEGRAM_BOT_TOKEN"
CHAT_KEY = "TELEGRAM_CHAT_ID"
LOCAL_SUFFIX = ".local.set"


def parse_env(text: str) -> dict[str, str]:
    """KEY=VALUE per baris; abaikan kosong dan '#', terima 'export ', buang spasi dan kutip pembungkus."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1].strip()
        values[key.strip()] = value
    return values


def render_local(
    preset_text: str, token: str, chat_id: str, live: bool = False, risk: float | None = None
) -> str:
    out = []
    for line in preset_text.splitlines():
        if line.startswith("InpTelegramToken="):
            line = f"InpTelegramToken={token}"
        elif line.startswith("InpTelegramChatID="):
            line = f"InpTelegramChatID={chat_id}"
        elif live and line.startswith("InpAllowLiveTrading="):
            line = "InpAllowLiveTrading=true"
        elif risk is not None and line.startswith("InpRiskPerTradePct="):
            line = f"InpRiskPerTradePct={risk:g}"
        out.append(line)
    return "\n".join(out) + "\n"


def is_git_ignored(path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", path.name],
        cwd=path.parent,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _masked_chat(chat_id: str) -> str:
    return "***" + chat_id[-4:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV, help="file .env bot Python")
    parser.add_argument("--presets", type=Path, default=DEFAULT_PRESETS, help="folder preset repo")
    parser.add_argument("--force", action="store_true", help="timpa .local.set yang berbeda")
    parser.add_argument("--live", action="store_true", help="InpAllowLiveTrading=true (akun cent)")
    parser.add_argument(
        "--risk", type=float, help="InpRiskPerTradePct untuk preset pribadi, 0 < x <= 1"
    )
    args = parser.parse_args(argv)
    if args.risk is not None and not 0.0 < args.risk <= 1.0:
        print(f"[make_local_presets] --risk {args.risk} di luar 0 < x <= 1")
        return 1

    if not args.env.is_file():
        print(f"[make_local_presets] .env tidak ditemukan: {args.env}")
        return 1
    values = parse_env(args.env.read_text(encoding="utf-8"))
    token, chat_id = values.get(TOKEN_KEY, ""), values.get(CHAT_KEY, "")
    if not token or not chat_id:
        print(f"[make_local_presets] {TOKEN_KEY} dan {CHAT_KEY} wajib terisi di {args.env}")
        return 1

    sources = sorted(
        p for p in args.presets.glob("SDBot_DAY_*.set") if not p.name.endswith(LOCAL_SUFFIX)
    )
    if not sources:
        print(f"[make_local_presets] tidak ada preset di {args.presets}")
        return 1

    status = 0
    for src in sources:
        target = src.with_name(src.name[: -len(".set")] + LOCAL_SUFFIX)
        content = render_local(
            src.read_text(encoding="ascii"), token, chat_id, args.live, args.risk
        )
        if target.exists() and target.read_text(encoding="ascii") != content and not args.force:
            print(f"[make_local_presets] dilewati (sudah disunting, pakai --force): {target.name}")
            continue
        target.write_text(content, encoding="ascii", newline="\n")
        if not is_git_ignored(target):
            target.unlink()
            print(f"[make_local_presets] {target.name} TIDAK diabaikan git; file dihapus")
            status = 1
            continue
        print(f"[make_local_presets] {target.name} (chat {_masked_chat(chat_id)})")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
