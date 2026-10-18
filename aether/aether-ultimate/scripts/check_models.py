#!/usr/bin/env python3
"""Explicit, bounded live connection checks; never uploads project or user data."""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model_config import DECISION_MODELS, EMBEDDING_MODELS, TEXT_MODELS, resolve_openrouter_key
from openrouter_adapter import OpenRouterConfig, OpenRouterFrozenLLM, OpenRouterRequestError


def check_models(credentials_file: Path | None, group: str = "all") -> dict:
    key = resolve_openrouter_key(credentials_file)
    if not key:
        raise ValueError("OPENROUTER_API_KEY is missing")
    groups = {"embeddings": EMBEDDING_MODELS, "decisions": DECISION_MODELS, "text": TEXT_MODELS}
    checks = []
    for kind, models in groups.items():
        if group not in {"all", kind}:
            continue
        for model in models:
            started = time.perf_counter()
            row = {"group": kind, "requested_model": model}
            config = OpenRouterConfig(
                api_key=key, default_model=model if kind == "text" else TEXT_MODELS[0],
                fallback_models=[], max_retries=1, max_tokens=128, timeout_seconds=30,
            )
            try:
                with OpenRouterFrozenLLM(config) as client:
                    if kind == "embeddings":
                        data = client.embed(["Aether connection check: the color is green."], model=model)
                        vector = data["data"][0]["embedding"]
                        row["dimensions"] = len(vector)
                        row["validated"] = bool(vector) and all(isinstance(x, (float, int)) and math.isfinite(x) for x in vector)
                    elif kind == "decisions":
                        data = client.decide("The color is green.", {
                            "color": {"type": "choice", "instructions": "Which color is explicitly named in the state?",
                                      "criteria": {"green": "The color is green", "red": "The color is red", "blue": "The color is blue"}},
                        }, model=model)
                        answer = data["answers"]["color"]
                        row["choice"] = answer.get("choice")
                        row["validated"] = row["choice"] == "green"
                    else:
                        content = client.generate("Reply with exactly AETHER_OK and nothing else.", "Connection check.")
                        row["validated"] = content.strip() == "AETHER_OK"
                        row["completion_characters"] = len(content)
                    row["served_model"] = client.last_model
                    row["usage"] = {k: v for k, v in client.last_usage.items() if k in {
                        "prompt_tokens", "completion_tokens", "input_tokens", "output_tokens", "total_tokens", "cost",
                    }}
                    row["status"] = "passed" if row["validated"] else "validation_failed"
            except OpenRouterRequestError as exc:
                row.update(status="request_failed", http_status=exc.status_code)
            except (RuntimeError, KeyError, TypeError, ValueError, IndexError) as exc:
                row.update(status="validation_failed", error_type=type(exc).__name__)
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
            checks.append(row)
            print(json.dumps(row), flush=True)
            if row.get("http_status") in {401, 402, 403}:
                return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "stopped_for_auth_or_quota": True}
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--group", choices=["all", "embeddings", "decisions", "text"], default="all")
    parser.add_argument("--output", type=Path, required=True, help="Destination for nonsecret verification metadata")
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    receipt = check_models(args.credentials_file, args.group)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0 if receipt["checks"] and all(r["status"] == "passed" for r in receipt["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
