#!/usr/bin/env python3
"""Sync requirements.txt with dependencies declared in pyproject.toml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    print("Python 3.11+ required (tomllib missing).", file=sys.stderr)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQUIREMENTS = ROOT / "requirements.txt"


def load_dependencies(include_extras: bool) -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text())
    deps: list[str] = list(data["project"].get("dependencies", []))
    if include_extras:
        for extra in sorted(data["project"].get("optional-dependencies", {})):
            deps.extend(data["project"]["optional-dependencies"][extra])
    return deps


def sync(include_extras: bool) -> None:
    deps = load_dependencies(include_extras)
    header = [
        "# Generated from pyproject.toml via scripts/sync_requirements.py",
        "# Do not edit manually; re-run the script after modifying dependencies.",
        "",
    ]
    REQUIREMENTS.write_text("\n".join(header + deps) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-extras",
        action="store_true",
        help="Include optional dependencies (e.g., dev extras).",
    )
    args = parser.parse_args()
    sync(include_extras=args.with_extras)


if __name__ == "__main__":
    main()
