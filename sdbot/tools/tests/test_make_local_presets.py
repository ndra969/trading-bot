"""Preset pribadi *.local.set dari .env bot Python (spec 09 Req 1.3-1.7): TS-40..45.

Setiap uji memakai repo git tiruan di folder sementara; .env sungguhan tidak pernah dibaca.
"""

import subprocess
from pathlib import Path

import make_local_presets as mlp
import pytest

TOKEN = "123456:ABC-def_GHI"
CHAT = "-1001234567890"
PRESET = (
    "; SDBot preset EURUSDc\n"
    "InpMagicNumber=2026091901\n"
    "InpTelegramToken=\n"
    "InpTelegramChatID=\n"
    "InpHeartbeatMinutes=60\n"
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("*.local.set\n.env\n", encoding="ascii")
    presets = tmp_path / "Presets"
    presets.mkdir()
    for sym in ("EURUSD", "GBPUSD"):
        (presets / f"SDBot_DAY_{sym}c.set").write_text(PRESET, encoding="ascii", newline="\n")
    (tmp_path / ".env").write_text(
        f"# komentar\nexport TELEGRAM_BOT_TOKEN = \"{TOKEN}\"\nTELEGRAM_CHAT_ID='{CHAT}'\nLAIN=x\n",
        encoding="utf-8",
    )
    return tmp_path


def _run(repo: Path, *extra: str) -> int:
    return mlp.main(["--env", str(repo / ".env"), "--presets", str(repo / "Presets"), *extra])


def test_ts40_parse_env_handles_export_quotes_spaces_comments():
    values = mlp.parse_env(
        "# c\n\nexport TELEGRAM_BOT_TOKEN = \"a:b\"\nTELEGRAM_CHAT_ID='-1'\nX=1 \n"
    )
    assert values["TELEGRAM_BOT_TOKEN"] == "a:b"
    assert values["TELEGRAM_CHAT_ID"] == "-1"
    assert values["X"] == "1"


def test_ts41_missing_env_or_empty_value_writes_nothing(repo: Path):
    (repo / ".env").unlink()
    assert _run(repo) == 1
    (repo / ".env").write_text('TELEGRAM_BOT_TOKEN=""\nTELEGRAM_CHAT_ID=1\n', encoding="utf-8")
    assert _run(repo) == 1
    assert not list((repo / "Presets").glob("*.local.set"))


def test_ts42_one_local_preset_per_repo_preset(repo: Path):
    assert _run(repo) == 0
    local = repo / "Presets" / "SDBot_DAY_EURUSDc.local.set"
    text = local.read_text(encoding="ascii")
    assert f"InpTelegramToken={TOKEN}\n" in text
    assert f"InpTelegramChatID={CHAT}\n" in text
    assert "InpMagicNumber=2026091901\n" in text and "InpHeartbeatMinutes=60\n" in text
    names = sorted(p.name for p in (repo / "Presets").glob("*.local.set"))
    assert names == ["SDBot_DAY_EURUSDc.local.set", "SDBot_DAY_GBPUSDc.local.set"]
    assert _run(repo) == 0  # .local.set yang ada tidak dibaca sebagai preset sumber
    assert not list((repo / "Presets").glob("*.local.local.set"))


def test_ts43_edited_local_preset_kept_unless_force(repo: Path):
    assert _run(repo) == 0
    local = repo / "Presets" / "SDBot_DAY_EURUSDc.local.set"
    local.write_text(local.read_text(encoding="ascii") + "InpLogLevel=0\n", encoding="ascii")
    assert _run(repo) == 0
    assert "InpLogLevel=0" in local.read_text(encoding="ascii")
    assert _run(repo, "--force") == 0
    assert "InpLogLevel=0" not in local.read_text(encoding="ascii")


def test_ts44_not_ignored_by_git_fails_and_removes_file(repo: Path):
    (repo / ".gitignore").write_text(".env\n", encoding="ascii")
    assert _run(repo) == 1
    assert not list((repo / "Presets").glob("*.local.set"))


def test_ts45_output_never_contains_token(repo: Path, capsys: pytest.CaptureFixture[str]):
    assert _run(repo) == 0
    out = capsys.readouterr()
    assert TOKEN not in out.out + out.err
    assert "123456" not in out.out + out.err
