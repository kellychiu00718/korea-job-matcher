from pathlib import Path

_SQL_DIR = Path(__file__).parent
_SUBDIRS = ["queries", "views", "schema"]
_cache: dict[str, str] = {}


def load_sql(name: str) -> str:
    if name in _cache:
        return _cache[name]

    for subdir in _SUBDIRS:
        path = _SQL_DIR / subdir / f"{name}.sql"
        if path.exists():
            sql = path.read_text(encoding="utf-8").strip()
            _cache[name] = sql
            return sql

    raise FileNotFoundError(f"SQL file not found: {name}.sql (searched {_SUBDIRS})")


def load_all_in(subdir: str) -> list[tuple[str, str]]:
    folder = _SQL_DIR / subdir
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.sql"))
    results = []
    for f in files:
        sql = f.read_text(encoding="utf-8").strip()
        _cache[f.stem] = sql
        results.append((f.stem, sql))
    return results
