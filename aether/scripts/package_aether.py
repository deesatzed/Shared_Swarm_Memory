#!/usr/bin/env python3
"""Build Aether exports from an explicit file list that excludes credentials."""

from __future__ import annotations

import argparse
import pprint
import zipfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILES = (
    "aether_core.py", "aether_core2.py", "aether_swarm.py", "aether_cli.py",
    "aether_cli2.py", "openrouter_adapter.py", "model_config.py", "pyproject.toml",
    "uv.lock", "README.md", "PROGRESS.md", "DECISIONS.md", ".env.example",
    "scripts/check_models.py", "scripts/package_aether.py", "tests/test_model_refresh.py",
    "receipts/model-check-2026-10-18.json",
)


def generator(files: dict[str, str], *, archive: bool) -> str:
    source = '''#!/usr/bin/env python3
"""Generated from the Aether workspace; credential files are excluded."""
from __future__ import annotations
import argparse
import zipfile
from pathlib import Path

FILES = __FILES__

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path.cwd())
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in FILES.items():
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    __ARCHIVE__
    print(f"Wrote {len(FILES)} Aether files to {args.output}")

if __name__ == "__main__":
    main()
'''
    archive_code = '''with zipfile.ZipFile(args.output / "aether-ultimate.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, content in FILES.items():
            bundle.writestr(name, content)'''
    # Insert file contents last so placeholders inside the packaged generator
    # source remain literal text rather than being replaced inside Python strings.
    return source.replace("__ARCHIVE__", archive_code if archive else "pass").replace("__FILES__", pprint.pformat(files, sort_dicts=False))


def package(output: Path) -> None:
    files = {name: (SOURCE_ROOT / name).read_text(encoding="utf-8") for name in PACKAGE_FILES}
    for name, content in files.items():
        if name.endswith(".py"):
            compile(content, name, "exec")
    output.mkdir(parents=True, exist_ok=True)
    for name, archive in [("aether_setup.py", False), ("bundle_aether.py", True)]:
        content = generator(files, archive=archive)
        compile(content, name, "exec")
        (output / name).write_text(content, encoding="utf-8")
    with zipfile.ZipFile(output / "aether-ultimate.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
    for base in [output, output / "aether-ultimate"]:
        for name, content in files.items():
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    print(f"Updated Aether exports: {len(files)} files, two generators, and archive at {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    package(parser.parse_args().output)
