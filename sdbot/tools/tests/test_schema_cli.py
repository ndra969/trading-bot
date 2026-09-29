"""Uji perintah schema.py: new, build, check, release, status (spec 03 task 3)."""

import hashlib
import json
import sqlite3
from pathlib import Path

import schema

MIGRATIONS_MQH = Path("ea/src/Include/SDBot/Storage/Migrations.mqh")
ENUMS_MQH = Path("ea/src/Include/SDBot/Core/SchemaEnums.mqh")
SNAPSHOT = Path("shared/schema/data_db.sql")
LOCK = Path("shared/schema/migrations/data/migrations.lock.json")
MIG_DIR = Path("shared/schema/migrations/data")
FIX_EMPTY = Path("shared/schema/fixtures/data_latest_empty.sqlite")
FIX_SAMPLE = Path("shared/schema/fixtures/data_latest_sample.sqlite")
TEXT_OUTPUTS = [MIGRATIONS_MQH, ENUMS_MQH, SNAPSHOT, LOCK]


def run(root: Path, *args: str) -> int:
    return schema.main(["--root", str(root), *args])


def digests(root: Path) -> dict:
    return {
        str(p): hashlib.sha256((root / p).read_bytes()).hexdigest()
        for p in TEXT_OUTPUTS
        if (root / p).exists()
    }


def test_ts01_new_creates_next_numbered_file(project: Path):
    assert run(project, "new", "data", "Tambah kolom X!") == 0
    created = project / MIG_DIR / "0002_tambah_kolom_x.sql"
    assert created.exists()
    assert "0002" in created.read_text(encoding="utf-8")


def test_ts02_build_is_deterministic_and_check_passes(project: Path):
    assert run(project, "build") == 0
    first = digests(project)
    assert len(first) == len(TEXT_OUTPUTS)
    assert (project / FIX_EMPTY).exists() and (project / FIX_SAMPLE).exists()
    assert run(project, "build") == 0
    assert digests(project) == first
    assert run(project, "check") == 0
    for p in TEXT_OUTPUTS:
        text = (project / p).read_text(encoding="utf-8")
        assert text.endswith("\n") and not text.endswith("\n\n"), f"{p} harus berakhir satu newline"
        assert not any(
            line != line.rstrip() for line in text.splitlines()
        ), f"{p} ada spasi di akhir"


def test_ts03_bad_sql_changes_nothing(project: Path):
    assert run(project, "build") == 0
    before = digests(project)
    (project / MIG_DIR / "0002_bad.sql").write_text("CREATE TABLE (;", encoding="utf-8")
    assert run(project, "build") == 1
    assert digests(project) == before


def test_ts04_editing_released_migration_fails_check(project: Path, capsys):
    assert run(project, "build") == 0
    assert run(project, "release") == 0
    path = project / MIG_DIR / "0001_initial.sql"
    path.write_text(path.read_text(encoding="utf-8") + "\n-- diedit\n", encoding="utf-8")
    assert run(project, "check") == 1
    assert "0001" in capsys.readouterr().out
    assert run(project, "build") == 1


def test_ts05_editing_unreleased_migration_then_build_passes(project: Path):
    assert run(project, "build") == 0
    path = project / MIG_DIR / "0001_initial.sql"
    path.write_text(path.read_text(encoding="utf-8") + "\n-- diedit\n", encoding="utf-8")
    assert run(project, "check") == 1
    assert run(project, "build") == 0
    assert run(project, "check") == 0


def test_ts06_hand_edited_generated_file_fails_check(project: Path, capsys):
    assert run(project, "build") == 0
    mqh = project / MIGRATIONS_MQH
    mqh.write_text(mqh.read_text(encoding="utf-8") + "\n// diedit tangan\n", encoding="utf-8")
    assert run(project, "check") == 1
    assert "Migrations.mqh" in capsys.readouterr().out


def test_check_fails_when_new_migration_not_built(project: Path):
    assert run(project, "build") == 0
    (project / MIG_DIR / "0002_x.sql").write_text("CREATE TABLE x (a INTEGER);", encoding="utf-8")
    assert run(project, "check") == 1


def test_ts10_migration_failing_only_with_sample_data_is_caught(project: Path, capsys):
    # Kosong: lolos. Dengan data contoh (dua deal EURUSDc): unique index gagal.
    (project / MIG_DIR / "0002_unique_symbol.sql").write_text(
        "CREATE UNIQUE INDEX ux_deals_symbol ON deals (symbol);", encoding="utf-8"
    )
    assert run(project, "build") == 1
    assert "0002" in capsys.readouterr().out


def test_ts11_check_constraint_must_match_enums(project: Path, capsys):
    enums = project / "shared/schema/enums.md"
    text = enums.read_text(encoding="utf-8").replace(
        "| `direction` | `BUY`, `SELL` |", "| `direction` | `BUY`, `SELL`, `HOLD` |"
    )
    enums.write_text(text, encoding="utf-8")
    assert run(project, "build") == 1
    out = capsys.readouterr().out
    assert "direction" in out and "signals.direction" in out


def test_check_without_enum_is_reported(project: Path, capsys):
    (project / MIG_DIR / "0002_state.sql").write_text(
        "CREATE TABLE extra (state TEXT NOT NULL CHECK (state IN ('A','B')));", encoding="utf-8"
    )
    assert run(project, "build") == 1
    assert "extra.state" in capsys.readouterr().out


def test_ts12_mql_string_literals_are_escaped(project: Path):
    (project / MIG_DIR / "0002_esc.sql").write_text(
        "CREATE TABLE esc (a TEXT DEFAULT 'x\"y\\z');", encoding="utf-8"
    )
    assert run(project, "build") == 0
    mqh = (project / MIGRATIONS_MQH).read_text(encoding="utf-8")
    assert "'x\\\"y\\\\z'" in mqh
    assert "#define SDB_SCHEMA_LATEST 2" in mqh
    assert mqh.startswith("// GENERATED oleh sdbot/tools/schema.py")


def test_ts13_release_marks_all_migrations(project: Path):
    assert run(project, "build") == 0
    assert run(project, "release") == 0
    lock = json.loads((project / LOCK).read_text(encoding="utf-8"))
    assert lock["1"]["released"] is True
    assert run(project, "check") == 0


def test_schema_enums_mqh_has_constants_and_validator(project: Path):
    assert run(project, "build") == 0
    text = (project / ENUMS_MQH).read_text(encoding="utf-8")
    assert '#define SDB_CLOSE_REASON_TP "TP"' in text
    assert '#define SDB_ALERT_TYPE_CONN_DOWN "CONN_DOWN"' in text
    assert "bool SdbEnumIsValid(const string enumName, const string value)" in text


def test_fixtures_contain_schema_and_sample(project: Path):
    assert run(project, "build") == 0
    empty = sqlite3.connect(project / FIX_EMPTY)
    sample = sqlite3.connect(project / FIX_SAMPLE)
    assert empty.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 0
    assert sample.execute("SELECT COUNT(*) FROM closures").fetchone()[0] == 4
    assert sample.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 1
    empty.close()
    sample.close()


def test_status_reports_version(project: Path, capsys):
    assert run(project, "build") == 0
    assert run(project, "status", str(project / FIX_SAMPLE)) == 0
    assert "versi 1" in capsys.readouterr().out
