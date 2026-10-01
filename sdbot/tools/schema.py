"""Alat migrasi skema SQLite SDBot (spec 03).

Migrasi ditulis tangan di sdbot/shared/schema/migrations/<db>/NNNN_<slug>.sql, lalu dibangun
menjadi file yang dibawa EA (Storage/Migrations.mqh), konstanta enum (Core/SchemaEnums.mqh),
snapshot skema, dan fixture. Hanya pustaka standar Python.

Pemakaian: lihat `python sdbot/tools/schema.py --help` atau sdbot/shared/schema/README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
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


# ---------------------------------------------------------------- proyek dan enum

GENERATED_NOTE = "GENERATED oleh sdbot/tools/schema.py — jangan diedit"
SCHEMA_MIGRATIONS_DDL = (
    "CREATE TABLE IF NOT EXISTS schema_migrations (\n"
    "  version     INTEGER PRIMARY KEY,\n"
    "  name        TEXT    NOT NULL,\n"
    "  checksum    TEXT    NOT NULL,\n"
    "  applied_at  INTEGER NOT NULL,\n"
    "  applied_by  TEXT    NOT NULL\n"
    ")"
)
ENUM_ROW = re.compile(r"^\|\s*`([a-z_]+)`\s*\|(.*?)\|\s*(ya|tidak)\s*\|(.*?)\|\s*$")
TEXT_CHECK = re.compile(
    r"(\w+)\s+TEXT\b[^,]*?CHECK\s*\(\s*(\w+)\s+IN\s*\(([^)]*)\)\s*\)", re.IGNORECASE
)


@dataclass
class EnumDef:
    name: str
    values: list[str]
    has_check: bool
    columns: list[str]


class Project:
    """Lokasi file sumber dan hasil generate relatif ke folder sdbot/."""

    def __init__(self, root: Path, db: str = "data") -> None:
        self.root = Path(root)
        self.db = db
        self.schema_dir = self.root / "shared" / "schema"
        self.mig_dir = self.schema_dir / "migrations" / db
        self.lock = self.mig_dir / "migrations.lock.json"
        self.seed = self.mig_dir / "seed_sample.sql"
        self.enums = self.schema_dir / "enums.md"
        include = self.root / "ea" / "src" / "Include" / "SDBot"
        self.migrations_mqh = include / "Storage" / "Migrations.mqh"
        self.enums_mqh = include / "Core" / "SchemaEnums.mqh"
        self.snapshot = self.schema_dir / f"{db}_db.sql"
        self.fixture_empty = self.schema_dir / "fixtures" / f"{db}_latest_empty.sqlite"
        self.fixture_sample = self.schema_dir / "fixtures" / f"{db}_latest_sample.sqlite"


def load_enums(path: Path) -> list[EnumDef]:
    enums = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = ENUM_ROW.match(line.strip())
        if not m:
            continue
        values = re.findall(r"`([^`]+)`", m.group(2))
        bad = [v for v in values if not re.fullmatch(r"[A-Z][A-Z0-9_]*", v)]
        if bad:
            raise SchemaError(f"enum {m.group(1)}: nilai tidak valid {bad} (huruf besar dan _)")
        columns = re.findall(r"`([a-z_]+\.[a-z_]+)`", m.group(4))
        enums.append(EnumDef(m.group(1), values, m.group(3) == "ya", columns))
    if not enums:
        raise SchemaError(f"tidak ada tabel enum di {path}")
    return enums


def schema_checks(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """{'tabel.kolom': [nilai CHECK]} untuk setiap kolom TEXT dengan CHECK (kolom IN (...))."""
    found = {}
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
    )
    for table, sql in rows:
        for m in TEXT_CHECK.finditer(sql):
            if m.group(1) == m.group(2):
                found[f"{table}.{m.group(1)}"] = re.findall(r"'([^']*)'", m.group(3))
    return found


def verify_enums(conn: sqlite3.Connection, enums: list[EnumDef]) -> list[str]:
    errors = []
    checks = schema_checks(conn)
    claimed = set()
    for e in enums:
        for col in e.columns:
            claimed.add(col)
            table, column = col.split(".")
            names = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            if column not in names:
                errors.append(f"enum {e.name}: kolom {col} tidak ada di skema")
            elif e.has_check and sorted(checks.get(col, [])) != sorted(e.values):
                errors.append(
                    f"enum {e.name}: CHECK {col} {checks.get(col)} != enums.md {e.values}"
                )
            elif not e.has_check and col in checks:
                errors.append(f"enum {e.name}: {col} punya CHECK padahal enums.md bilang 'tidak'")
    for col in sorted(set(checks) - claimed):
        errors.append(f"CHECK di {col} tidak terdaftar di enums.md")
    return errors


# ---------------------------------------------------------------- validasi dan lock


def verify_migrations(migrations: list[Migration], seed: dict[int, str]) -> sqlite3.Connection:
    """Terapkan ke DB kosong, lalu uji setiap versi N >= 2 di atas DB N-1 berisi data contoh."""
    for n in range(2, len(migrations) + 1):
        conn = sqlite3.connect(":memory:", isolation_level=None)
        apply_migrations(conn, migrations[: n - 1])
        for v in sorted(seed):
            if v <= n - 1:
                conn.executescript(seed[v])
        try:
            apply_migrations(conn, [migrations[n - 1]])
        except SchemaError as exc:
            raise SchemaError(f"{exc} (dengan data contoh versi <= {n - 1:04d})") from exc
        finally:
            conn.close()
    conn = sqlite3.connect(":memory:", isolation_level=None)
    apply_migrations(conn, migrations)
    return conn


def updated_lock(migrations: list[Migration], lock_path: Path) -> dict:
    old = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
    files = {str(m.version) for m in migrations}
    missing = sorted(set(old) - files, key=int)
    if missing:
        raise SchemaError(
            f"migrasi di lock tidak punya file: {', '.join(v.zfill(4) for v in missing)}"
        )
    lock = {}
    for m in migrations:
        prev = old.get(str(m.version), {})
        if prev.get("released") and prev.get("sha256") != m.sha256:
            raise SchemaError(
                f"migrasi {m.version:04d}_{m.name} sudah rilis dan isinya berubah; buat migrasi baru"
            )
        lock[str(m.version)] = {
            "name": m.name,
            "sha256": m.sha256,
            "released": bool(prev.get("released", False)),
        }
    return lock


def lock_text(lock: dict) -> str:
    ordered = dict(sorted(lock.items(), key=lambda kv: int(kv[0])))
    return json.dumps(ordered, indent=2) + "\n"


# ---------------------------------------------------------------- generator


def mql_string(text: str) -> str:
    """Literal string MQL5: escape backslash, kutip, dan tab."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")
    return '"' + escaped + '"'


def mql_statement(stmt: str, indent: str) -> str:
    """Satu pernyataan SQL sebagai literal MQL5 per baris, disambung dengan +."""
    lines = stmt.replace("\r\n", "\n").split("\n")
    parts = []
    for i, line in enumerate(lines):
        literal = mql_string(line)
        if i < len(lines) - 1:
            literal = literal[:-1] + '\\n"'
        parts.append(literal)
    return (" +\n" + indent).join(parts)


def _switch_strings(values: list[str]) -> list[str]:
    body = ["      switch(i)", "        {"]
    body += [f'         case {i}: return "{v}";' for i, v in enumerate(values)]
    return body + ["        }", '      return "";']


def render_migrations_mqh(migrations: list[Migration], db: str) -> str:
    n = len(migrations)
    out = [
        f"// {GENERATED_NOTE}. Sumber: shared/schema/migrations/{db}/",
        "#ifndef SDB_STORAGE_MIGRATIONS_MQH",
        "#define SDB_STORAGE_MIGRATIONS_MQH",
        "",
        "#include <SDBot/Storage/MigrationSource.mqh>",
        "",
        f"#define SDB_SCHEMA_LATEST {n}",
        "",
        "class CSdbDataMigrations : public ISdbMigrationSource",
        "  {",
        "public:",
        f"   int    Count()              {{ return {n}; }}",
        "   int    Version(const int i) { return i + 1; }",
        "   string Name(const int i)",
        "     {",
        *_switch_strings([m.name for m in migrations]),
        "     }",
        "   string Checksum(const int i)",
        "     {",
        *_switch_strings([m.sha256 for m in migrations]),
        "     }",
        "   int    Statements(const int i, string &out[])",
        "     {",
        "      ArrayFree(out);",
        "      switch(i)",
        "        {",
    ]
    for i, m in enumerate(migrations):
        out.append(f"         case {i}:")
        out.append(f"            ArrayResize(out, {len(m.statements)});")
        for j, stmt in enumerate(m.statements):
            prefix = f"            out[{j}] = "
            out.append(prefix + mql_statement(stmt, " " * len(prefix)) + ";")
        out.append(f"            return {len(m.statements)};")
    out += ["        }", "      return 0;", "     }", "  };", ""]
    out += ["#endif // SDB_STORAGE_MIGRATIONS_MQH", ""]
    return "\n".join(out)


def render_enums_mqh(enums: list[EnumDef]) -> str:
    out = [
        f"// {GENERATED_NOTE}. Sumber: shared/schema/enums.md",
        "#ifndef SDB_CORE_SCHEMAENUMS_MQH",
        "#define SDB_CORE_SCHEMAENUMS_MQH",
        "",
    ]
    for e in enums:
        out.append(f"// {e.name}: {', '.join(e.columns)}")
        out += [f'#define SDB_{e.name.upper()}_{v} "{v}"' for v in e.values]
        out.append("")
    out += [
        "// true bila value adalah nilai sah enum enumName (nama seperti di enums.md).",
        "bool SdbEnumIsValid(const string enumName, const string value)",
        "  {",
    ]
    for e in enums:
        cond = " || ".join(f'value == "{v}"' for v in e.values)
        out.append(f'   if(enumName == "{e.name}")')
        out.append(f"      return {cond};")
    out += ["   return false;", "  }", "", "#endif // SDB_CORE_SCHEMAENUMS_MQH", ""]
    return "\n".join(out)


def render_snapshot(conn: sqlite3.Connection, db: str) -> str:
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
        "ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 WHEN 'view' THEN 2 ELSE 3 END,"
        " name"
    ).fetchall()
    head = [
        f"-- {GENERATED_NOTE}.",
        f"-- Snapshot skema {db} terbaru dari shared/schema/migrations/{db}/, untuk dibaca.",
        "-- Tabel schema_migrations dibuat oleh runner migrasi (EA/API):",
        "",
        SCHEMA_MIGRATIONS_DDL + ";",
        "",
    ]
    body = "\n\n".join(r[0] + ";" for r in rows)
    # Tepat satu newline di akhir: hook end-of-file-fixer tidak akan mengubah file ini.
    return "\n".join(head) + "\n" + body + "\n"


def write_fixture(path: Path, migrations: list[Migration], seed: dict[int, str] | None) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.execute(SCHEMA_MIGRATIONS_DDL)
        apply_migrations(conn, migrations)
        for m in migrations:
            conn.execute(
                "INSERT INTO schema_migrations VALUES (?, ?, ?, 0, 'schema.py')",
                (m.version, m.name, m.sha256),
            )
        # Blok data contoh untuk migrasi yang belum ada (misalnya proyek tiruan di uji) dilewati.
        latest = migrations[-1].version if migrations else 0
        for v in sorted(seed or {}):
            if v <= latest:
                conn.executescript(seed[v])
    finally:
        conn.close()


def fixture_dump(path: Path) -> str:
    conn = sqlite3.connect(path)
    try:
        return "\n".join(conn.iterdump())
    finally:
        conn.close()


# ---------------------------------------------------------------- build / check


def generate(project: Project) -> tuple[dict[Path, str], list[Migration], dict[int, str]]:
    """Semua file teks hasil generate, tanpa menulis apa pun. Lempar SchemaError bila gagal."""
    migrations = load_migrations(project.mig_dir)
    if not migrations:
        raise SchemaError(f"tidak ada migrasi di {project.mig_dir}")
    seed = load_seed(project.seed) if project.seed.exists() else {}
    enums = load_enums(project.enums)
    conn = verify_migrations(migrations, seed)
    try:
        errors = verify_enums(conn, enums)
        if errors:
            raise SchemaError("\n".join(errors))
        files = {
            project.migrations_mqh: render_migrations_mqh(migrations, project.db),
            project.enums_mqh: render_enums_mqh(enums),
            project.snapshot: render_snapshot(conn, project.db),
            project.lock: lock_text(updated_lock(migrations, project.lock)),
        }
    finally:
        conn.close()
    return files, migrations, seed


def cmd_build(project: Project) -> int:
    files, migrations, seed = generate(project)
    # Staging di dalam proyek: os.replace atomik dan tidak bisa lintas drive (TEMP di C:, repo di D:).
    with tempfile.TemporaryDirectory(dir=project.root, prefix=".schema-build-") as tmp:
        staged = []
        for i, (dest, text) in enumerate(files.items()):
            src = Path(tmp) / f"{i}.txt"
            src.write_bytes(text.encode("utf-8"))
            staged.append((src, dest))
        fx_empty, fx_sample = Path(tmp) / "empty.sqlite", Path(tmp) / "sample.sqlite"
        write_fixture(fx_empty, migrations, None)
        write_fixture(fx_sample, migrations, seed)
        staged += [(fx_empty, project.fixture_empty), (fx_sample, project.fixture_sample)]
        # Semua sudah berhasil dibuat; baru sekarang file tujuan diganti.
        for src, dest in staged:
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dest)
    print(f"[schema] build OK: {project.db} versi {len(migrations)}, {len(staged)} file")
    return 0


def cmd_check(project: Project) -> int:
    files, migrations, seed = generate(project)
    errors = []
    for dest, text in files.items():
        current = None
        if dest.exists():
            current = dest.read_text(encoding="utf-8").replace("\r\n", "\n")
        if current != text:
            rel = dest.relative_to(project.root)
            errors.append(f"{rel} tidak sama dengan hasil build (jalankan build)")
    with tempfile.TemporaryDirectory() as tmp:
        for dest, data in ((project.fixture_empty, None), (project.fixture_sample, seed)):
            fresh = Path(tmp) / dest.name
            write_fixture(fresh, migrations, data)
            if not dest.exists() or fixture_dump(dest) != fixture_dump(fresh):
                errors.append(f"{dest.relative_to(project.root)} tidak sama dengan hasil build")
    if errors:
        raise SchemaError("\n".join(errors))
    print(f"[schema] check OK: {project.db} versi {len(migrations)}")
    return 0


def cmd_new(project: Project, description: str) -> int:
    migrations = load_migrations(project.mig_dir)
    slug = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_") or "migrasi"
    number = len(migrations) + 1
    path = project.mig_dir / f"{number:04d}_{slug}.sql"
    path.write_text(
        f"-- {number:04d}: {description}\n"
        "-- SQL maju saja. Dilarang: BEGIN/COMMIT/ROLLBACK/PRAGMA/ATTACH/VACUUM/CREATE TRIGGER.\n"
        "-- Kolom NOT NULL baru di tabel berisi data wajib punya DEFAULT.\n\n",
        encoding="utf-8",
    )
    print(f"[schema] dibuat: {path.relative_to(project.root)}")
    return 0


def cmd_release(project: Project) -> int:
    lock = updated_lock(load_migrations(project.mig_dir), project.lock)
    for entry in lock.values():
        entry["released"] = True
    project.lock.write_text(lock_text(lock), encoding="utf-8")
    print(f"[schema] {len(lock)} migrasi ditandai rilis")
    return 0


def cmd_status(db_file: Path) -> int:
    conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT version, name, applied_by FROM schema_migrations ORDER BY version"
        ).fetchall()
    except sqlite3.Error:
        print(f"[schema] {db_file}: tidak ada tabel schema_migrations")
        return 1
    finally:
        conn.close()
    version = rows[-1][0] if rows else 0
    print(f"[schema] {db_file}: versi {version}")
    for v, name, by in rows:
        print(f"  {v:04d} {name} ({by})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="schema.py", description="Migrasi skema SQLite SDBot")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new", help="buat file migrasi bernomor berikutnya")
    p_new.add_argument("db")
    p_new.add_argument("description")
    for name in ("build", "check", "release"):
        sub.add_parser(name).add_argument("--db", default="data")
    sub.add_parser("status").add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "new":
            return cmd_new(Project(args.root, args.db), args.description)
        if args.cmd == "status":
            return cmd_status(args.file)
        project = Project(args.root, args.db)
        commands = {"build": cmd_build, "check": cmd_check, "release": cmd_release}
        return commands[args.cmd](project)
    except SchemaError as exc:
        print(f"[schema] GAGAL:\n{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
