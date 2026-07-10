"""Small stdlib .env loader for Renaiss Collector Assistant scripts.

The project intentionally avoids third-party Python dependencies. This helper
loads KEY=VALUE pairs from `.env` so documentation that asks users to fill the
file works when scripts are launched directly with `python3 scripts/...`.
"""
from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Iterable


def _candidate_env_paths() -> list[Path]:
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    cwd = Path.cwd().resolve()
    repo_root = skill_dir.parent.parent if len(skill_dir.parents) >= 2 else skill_dir
    paths = [cwd / ".env", skill_dir / ".env", repo_root / ".env"]
    out: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _parse_line(line: str) -> tuple[str, str] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if s.startswith("export "):
        s = s[len("export "):].strip()
    if "=" not in s:
        return None
    key, value = s.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    # shlex handles simple single/double-quoted values and comments after values.
    try:
        parts = shlex.split(value, comments=True, posix=True)
        value = parts[0] if parts else ""
    except Exception:
        value = value.strip().strip('"').strip("'")
    return key, value


def load_dotenv_files(paths: Iterable[str | Path] | None = None, *, override: bool = False) -> list[str]:
    loaded: list[str] = []
    for raw_path in (list(paths) if paths is not None else _candidate_env_paths()):
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_line(line)
            if not parsed:
                continue
            key, value = parsed
            if override or key not in os.environ:
                os.environ[key] = value
        loaded.append(str(path))
    return loaded
