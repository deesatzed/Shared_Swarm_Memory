"""User-selected models, grouped by their OpenRouter API contract."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

TEXT_MODELS = (
    "deepseek/deepseek-v4.1-flash-1017",
    "nvidia/nemotron-3.5-super-vl",
    "google/gemini-4-argon",
)
DECISION_MODELS = ("liquid/d1-ultra", "typesafe/jev-1.14")
EMBEDDING_MODELS = (
    "google/gemini-embedding-2",
    "liquid/lfm-2.5-embedding-350m:free",
)
API_ROOT = "https://openrouter.ai/api/v1"


def selected_models(variable: str, choices: tuple[str, ...]) -> list[str]:
    """Put an explicit model selection first, retaining only its API group."""
    selected = os.environ.get(variable) or choices[0]
    if selected not in choices:
        raise ValueError(f"{variable} must select an approved model for its API group")
    return [selected, *(model for model in choices if model != selected)]


def resolve_openrouter_key(credentials_file: str | Path | None = None) -> str:
    """Read only OPENROUTER_API_KEY; never execute or import a whole env file.

    An explicit file (argument or AETHER_CREDENTIALS_FILE) takes precedence over
    the environment. No host-specific credential path is opened implicitly.
    """
    selected = credentials_file or os.environ.get("AETHER_CREDENTIALS_FILE")
    if selected is None:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()
    key = ""
    for line in Path(selected).expanduser().read_text(encoding="utf-8").splitlines():
        name, separator, value = line.strip().removeprefix("export ").partition("=")
        if not separator or name.strip() != "OPENROUTER_API_KEY":
            continue
        try:
            words = shlex.split(value, comments=True, posix=True)
        except ValueError:
            raise ValueError("Malformed OPENROUTER_API_KEY entry in credential file") from None
        if len(words) != 1:
            raise ValueError("Credential file must contain one nonempty OPENROUTER_API_KEY")
        key = words[0].strip()
    if not key:
        raise ValueError("Credential file has no nonempty OPENROUTER_API_KEY")
    return key
