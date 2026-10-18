#!/usr/bin/env python3
"""Synchronize this reviewed model refresh into the enclosing Aether repository."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from package_aether import PACKAGE_FILES, SOURCE_ROOT, package


def replacements(root: Path) -> dict[Path, str]:
    receipt = json.loads((SOURCE_ROOT / "receipts/model-check-2026-10-18.json").read_text())
    if len(receipt["checks"]) != 7 or not all(r["status"] == "passed" for r in receipt["checks"]):
        raise RuntimeError("The seven-model verification receipt is incomplete")
    settings = {
        "MODEL1": "deepseek/deepseek-v4.1-flash-1017",
        "TEXT_FALLBACK_MODELS": "nvidia/nemotron-3.5-super-vl,google/gemini-4-argon",
        "DECISION_MODEL": "liquid/d1-ultra",
        "DECISION_FALLBACK_MODEL": "typesafe/jev-1.14",
        "EMBED_MODEL": "google/gemini-embedding-2",
        "EMBED_ALTERNATIVE_MODEL": "liquid/lfm-2.5-embedding-350m:free",
        "AETHER_CREDENTIALS_FILE": "/Volumes/WS4TB/merged.env",
    }
    updates = {}
    env = root / ".env"
    if env.is_file():
        text = env.read_text(encoding="utf-8")
        before_secrets = [line for line in text.splitlines() if "OPENROUTER_API_KEY" in line]
        for name, value in settings.items():
            pattern = rf"(?m)^(?:export\s+)?{name}=.*$"
            if re.search(pattern, text):
                text = re.sub(pattern, f"{name}={value}", text)
            else:
                text = text.rstrip("\n") + f"\n{name}={value}\n"
        if [line for line in text.splitlines() if "OPENROUTER_API_KEY" in line] != before_secrets:
            raise RuntimeError("Credential preservation check failed")
        updates[env] = text

    note = (
        "Model selection updated 2026-10-18 by explicit user instruction. "
        "See [MODEL_CONFIGURATION.md](MODEL_CONFIGURATION.md) for the current "
        "seven-model configuration and live connection receipts. Earlier model "
        "IDs and catalog-availability notes below are historical.\n\n"
    )
    for name in ["README.md", "HANDOFF_LATEST.md"]:
        path = root / name
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if note not in text:
                header, _, body = text.partition("\n")
                updates[path] = header + "\n\n" + note + body.lstrip("\n")

    design = root / "docs/plans/2026-10-17-swarm-decision-memory-design.md"
    if design.is_file():
        text = design.read_text(encoding="utf-8")
        note_design = (
            "2026-10-18 model update: the user selected `liquid/d1-ultra` and "
            "`typesafe/jev-1.14` for typed decisions, the three current text models, "
            "and two embedding models documented in "
            "[MODEL_CONFIGURATION.md](../../MODEL_CONFIGURATION.md). This "
            "supersedes earlier model IDs and generative decision-output assumptions "
            "below. System One returns typed probabilities; live binding remains "
            "unconnected and risk bars/evidence rules are unchanged.\n\n"
        )
        if note_design not in text:
            header, _, body = text.partition("\n")
            updates[design] = header + "\n\n" + note_design + body.lstrip("\n")

    demo = root / "swarm_shared_memory.py"
    if demo.is_file():
        text = demo.read_text(encoding="utf-8")
        for name, value in {
            "LLM_MODEL": '"deepseek/deepseek-v4.1-flash-1017"',
            "EMBED_MODEL": '"google/gemini-embedding-2"',
            "EMBED_DIMS": "3072",
        }.items():
            text, count = re.subn(rf"(?m)^{name} = .*$", f"{name} = {value}", text)
            if count != 1:
                raise RuntimeError(f"Unexpected legacy demo setting: {name}")
        compile(text, str(demo), "exec")
        updates[demo] = text

    config_doc = (SOURCE_ROOT / "README.md").read_text(encoding="utf-8")
    config_doc += (
        "\n## Verification and repository boundary\n\n"
        "All seven exact model IDs passed generic connection checks on 2026-10-18 "
        "using only the OpenRouter key read from `/Volumes/WS4TB/merged.env`. "
        "Reported total request cost: USD 0.000241562. "
        "The receipt is `aether/aether_workspace/receipts/model-check-2026-10-18.json`.\n\n"
        "The main `swarm_memory` package still evaluates deterministic rules. "
        "Its live decision binding, Hy-Memory index, and trace-store integration "
        "are not implemented by this refresh. The older Hy-Memory demo has updated "
        "text/embedding constants but has not been run. Existing vectors must not "
        "be reused with the new embedding model. HMSS remains a separate historical "
        "reference; its defaults are not the active Aether configuration.\n"
    )
    updates[root / "MODEL_CONFIGURATION.md"] = config_doc
    return updates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = SOURCE_ROOT.parent.parent
    if not (root / "swarm_memory/service.py").is_file():
        raise RuntimeError("Unexpected repository layout")
    updates = replacements(root)
    for path in updates:
        print(f"{'Update' if args.apply else 'Planned update'}: {path.relative_to(root)}")
    print(f"Aether exports: {len(PACKAGE_FILES)} allowlisted files, standalone copy, generators, ZIP")
    if not args.apply:
        return
    # Rebuild exports before updating the small parent configuration documents.
    package(root / "aether")
    for path, content in updates.items():
        path.write_text(content, encoding="utf-8")
    print("Synced model configuration; existing credential line preserved; no secrets copied")


if __name__ == "__main__":
    main()
