"""Fixture bersama untuk uji schema.py: proyek SDBot tiruan di folder sementara."""

import shutil
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1]
SDBOT_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))


@pytest.fixture
def real_schema_dir() -> Path:
    return SDBOT_DIR / "shared" / "schema"


V1_LATER_COLUMNS = ("`alerts.status_reason`",)


@pytest.fixture
def project(tmp_path: Path, real_schema_dir: Path) -> Path:
    """Salinan sdbot/ minimal: shared/schema (enums, migrasi, seed) + folder tujuan generate."""
    root = tmp_path / "sdbot"
    schema = root / "shared" / "schema"
    (schema / "migrations" / "data").mkdir(parents=True)
    # Enum untuk kolom yang baru ada setelah 0001 (mis. alerts.status_reason, v3) tidak ikut.
    enums = (real_schema_dir / "enums.md").read_text(encoding="utf-8").splitlines(keepends=True)
    (schema / "enums.md").write_text(
        "".join(line for line in enums if not any(c in line for c in V1_LATER_COLUMNS)),
        encoding="utf-8",
    )
    shutil.copy(
        real_schema_dir / "migrations" / "data" / "0001_initial.sql",
        schema / "migrations" / "data" / "0001_initial.sql",
    )
    # Proyek tiruan hanya punya migrasi 0001 (uji membuat 0002 sendiri), jadi hanya blok seed v1 yang ikut.
    seed = (real_schema_dir / "migrations" / "data" / "seed_sample.sql").read_text(encoding="utf-8")
    cut = seed.find("-- @version 2")
    (schema / "migrations" / "data" / "seed_sample.sql").write_text(
        seed if cut < 0 else seed[:cut], encoding="utf-8"
    )
    (root / "ea" / "src" / "Include" / "SDBot" / "Storage").mkdir(parents=True)
    (root / "ea" / "src" / "Include" / "SDBot" / "Core").mkdir(parents=True)
    return root
