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


@pytest.fixture
def project(tmp_path: Path, real_schema_dir: Path) -> Path:
    """Salinan sdbot/ minimal: shared/schema (enums, migrasi, seed) + folder tujuan generate."""
    root = tmp_path / "sdbot"
    schema = root / "shared" / "schema"
    (schema / "migrations" / "data").mkdir(parents=True)
    shutil.copy(real_schema_dir / "enums.md", schema / "enums.md")
    for name in ("0001_initial.sql", "seed_sample.sql"):
        shutil.copy(
            real_schema_dir / "migrations" / "data" / name, schema / "migrations" / "data" / name
        )
    (root / "ea" / "src" / "Include" / "SDBot" / "Storage").mkdir(parents=True)
    (root / "ea" / "src" / "Include" / "SDBot" / "Core").mkdir(parents=True)
    return root
