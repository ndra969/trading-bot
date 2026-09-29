"""Alat migrasi skema SQLite SDBot (spec 03).

Migrasi ditulis tangan di sdbot/shared/schema/migrations/<db>/NNNN_<slug>.sql, lalu dibangun
menjadi file yang dibawa EA (Storage/Migrations.mqh), konstanta enum (Core/SchemaEnums.mqh),
snapshot skema, dan fixture. Hanya pustaka standar Python.

Pemakaian: lihat `python sdbot/tools/schema.py --help` atau sdbot/shared/schema/README.md.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

MIGRATION_NAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
SEED_MARKER = re.compile(r"^--\s*@version\s+(\d+)\s*$", re.MULTILINE)
# Pernyataan yang dikelola runner (transaksi, pragma) atau tidak didukung pemisah sederhana (trigger).
FORBIDDEN_FIRST_WORDS = {
    "BEGIN",
    "COMMIT",
    "END",
    "ROLLBACK",
    "PRAGMA",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "SAVEPOINT",
    "RELEASE",
}
TRIGGER = re.compile(r"^CREATE\s+(TEMP\s+|TEMPORARY\s+)?TRIGGER\b", re.IGNORECASE)


class SchemaError(Exception):
    """Kesalahan pada migrasi, enum, atau file hasil generate."""


@dataclass
class Migration:
    version: int
    name: str
    path: Path
    sql: str
    sha256: str
    statements: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- pemisah pernyataan


def split_statements(sql: str) -> list[str]:
    """Pisah SQL di ';' yang berada di luar string, identifier berkutip, dan komentar."""
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if ch in ("'", '"'):
            end = _quoted_end(sql, i, ch)
            buf.append(sql[i:end])
            i = end
        elif ch == "-" and nxt == "-":
            end = sql.find("\n", i)
            end = n if end < 0 else end
            buf.append(sql[i:end])
            i = end
        elif ch == "/" and nxt == "*":
            end = sql.find("*/", i + 2)
            end = n if end < 0 else end + 2
            buf.append(sql[i:end])
            i = end
        elif ch == ";":
            _flush(buf, statements)
            i += 1
        else:
            buf.append(ch)
            i += 1
    _flush(buf, statements)
    return statements


def _quoted_end(sql: str, start: int, quote: str) -> int:
    """Indeks setelah penutup kutip; kutip ganda ('' atau "") adalah escape."""
    i = start + 1
    while i < len(sql):
        if sql[i] == quote:
            if i + 1 < len(sql) and sql[i + 1] == quote:
                i += 2
                continue
            return i + 1
        i += 1
    return len(sql)


LEADING_COMMENT = re.compile(r"^\s*(--[^\n]*(\n|$)|/\*.*?\*/)", re.DOTALL)


def _flush(buf: list[str], out: list[str]) -> None:
    text = "".join(buf)
    buf.clear()
    # Komentar sebelum pernyataan (misalnya sisa komentar setelah ';' sebelumnya) dibuang.
    while True:
        m = LEADING_COMMENT.match(text)
        if not m:
            break
        text = text[m.end() :]
    text = text.strip()
    if text:
        out.append(text)


def _strip_comments(stmt: str) -> str:
    stmt = re.sub(r"/\*.*?\*/", " ", stmt, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", stmt)


def forbidden_statements(statements: list[str]) -> list[str]:
    """Pesan untuk setiap pernyataan yang tidak boleh ada di migrasi."""
    errors = []
    for stmt in statements:
        body = _strip_comments(stmt).strip()
        first = body.split(None, 1)[0].upper() if body else ""
        if first in FORBIDDEN_FIRST_WORDS:
            errors.append(
                f"pernyataan {first} dilarang di migrasi (runner yang mengatur transaksi/pragma): {body[:60]}"
            )
        elif TRIGGER.match(body):
            errors.append(f"CREATE TRIGGER dilarang di migrasi: {body[:60]}")
    return errors


# ---------------------------------------------------------------- migrasi dan seed


def sha256_normalized(text: str) -> str:
    """Checksum dengan akhir baris LF, agar checkout CRLF di Windows tidak mengubah checksum."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def load_migrations(mig_dir: Path) -> list[Migration]:
    """Baca migrasi berurutan 0001..N; tolak nama salah, nomor ganda, dan nomor yang lompat."""
    found: dict[int, list[Path]] = {}
    for path in sorted(Path(mig_dir).glob("*.sql")):
        if path.name == "seed_sample.sql":
            continue
        m = MIGRATION_NAME.match(path.name)
        if not m:
            raise SchemaError(f"nama file migrasi tidak valid: {path.name} (format NNNN_slug.sql)")
        found.setdefault(int(m.group(1)), []).append(path)
    migrations = []
    for expected, version in enumerate(sorted(found), start=1):
        paths = found[version]
        if version != expected:
            raise SchemaError(
                f"nomor migrasi lompat: diharapkan {expected:04d}, ditemukan {version:04d}"
            )
        if len(paths) > 1:
            raise SchemaError(
                f"nomor migrasi {version:04d} ganda: {', '.join(p.name for p in paths)}"
            )
        path = paths[0]
        sql = path.read_text(encoding="utf-8")
        name = MIGRATION_NAME.match(path.name).group(2)
        migrations.append(
            Migration(version, name, path, sql, sha256_normalized(sql), split_statements(sql))
        )
    return migrations


def apply_migrations(conn: sqlite3.Connection, migrations: list[Migration]) -> None:
    """Terapkan migrasi berurutan, masing-masing dalam satu transaksi (seperti runner EA)."""
    for mig in migrations:
        errors = forbidden_statements(mig.statements)
        if errors:
            raise SchemaError(f"{mig.path.name}: " + "; ".join(errors))
        try:
            conn.execute("BEGIN")
            for stmt in mig.statements:
                conn.execute(stmt)
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            conn.execute("ROLLBACK")
            raise SchemaError(f"{mig.path.name} gagal diterapkan: {exc}") from exc


def load_seed(path: Path) -> dict[int, str]:
    """Blok data contoh per versi: {versi: sql} dari penanda '-- @version N'."""
    text = Path(path).read_text(encoding="utf-8")
    marks = list(SEED_MARKER.finditer(text))
    blocks = {}
    for idx, m in enumerate(marks):
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(text)
        blocks[int(m.group(1))] = text[m.end() : end].strip()
    return blocks
