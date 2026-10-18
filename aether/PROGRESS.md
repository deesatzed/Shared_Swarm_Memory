# Aether model refresh

2026-10-18: User authorized the seven exact model IDs below and testing the
OpenRouter credential in `/Volumes/WS4TB/merged.env`. This supersedes the older
model selection and no-live-call restriction for these small connection checks.

- Text: `deepseek/deepseek-v4.1-flash-1017`,
  `nvidia/nemotron-3.5-super-vl`, `google/gemini-4-argon`.
- Decisions: `liquid/d1-ultra`, `typesafe/jev-1.14`.
- Embeddings: `google/gemini-embedding-2`,
  `liquid/lfm-2.5-embedding-350m:free`.

Assumption: list order supplies the default, followed by allowed alternatives.
Embedding alternatives are explicitly selected, never automatically mixed in an
existing index. The model refresh covers the Aether workspace and its generated
deliverables, plus the main repo's model-selection notes; HMSS is a reference
implementation with a separate architecture.

Scope: update model selection and API request types; read only the OpenRouter key
from the selected credential file without executing it or copying its secrets.
Run generic connection probes, preserving exact model identity and recording only
nonsecret metadata. This does not implement the unfinished improvement loop or
connect the main memory service to live inference.

Baseline: 54 main memory tests pass. Aether's newer CLI fails importing the unused
`ImprovementLibrary`. Nine new model-refresh regression tests fail before changes.
The main memory rules and their independent-evidence gates remain authoritative.

Implemented: grouped model selection, correct text/System One/embedding request
paths, key-only credential-file loading, safe API errors, and explicit embedding
selection. Removed the unused missing `ImprovementLibrary` import so the CLI can
load the configured text client. The standard CLI now forwards to that runner.

Live verification: all seven named models passed one generic request each using
the OpenRouter key read from `/Volumes/WS4TB/merged.env`; no key values or other
file contents were printed or copied. Receipt:
`receipts/model-check-2026-10-18.json`. Native vector dimensions were 3072 for
Gemini and 1024 for Liquid. Reported total cost was USD 0.000241562. Exact serving
IDs (including dated decision aliases) and usage are recorded in the receipt.

Fourteen focused regression tests pass, including API separation, decision
fallback, embedding-space isolation, credential-file behavior, startup, and
generated-source compilation. A file-list packager excludes credential files and
rebuilds the two generators, the standalone copy, and the ZIP from current code.

Remaining limitations from the audit: no automatic Propose-Probe-Compose loop;
the fast-path verifier flag and all-quarantined candidate selection are still
unfixed; SRE tools remain simulated; the main Hy-Memory adapter and live decision
binding remain unconnected. Model access does not establish decision quality.

## GOAL_1_7 execution — 2026-10-18

Step/task: 1 — scoped model-refresh checkpoint preparation.

Change and purpose: Created the local branch `aether-goal-1-7` so planned
runtime changes do not begin on `main`. Reviewed the intended manifest: the
model-refresh notes, `swarm_shared_memory.py` constants, `MODEL_CONFIGURATION.md`,
and the explicit Aether source/generated distribution. `hmss/`, `memasys.md`,
credential files, virtual environments, local indexes, and Finder metadata are
excluded.

Verification command, result, and exit code: `.venv/bin/python -B -m unittest
discover -s tests -v` — 14 passed, exit 0; `PYTHONPATH=../..
../../.venv/bin/python -B -m pytest ../../tests -q -p no:cacheprovider` — 54
passed, exit 0; `.venv/bin/python -B aether_cli.py --help` — exit 0; `git -C
../.. diff --check` — exit 0.

Evidence/receipt path: `receipts/model-check-2026-10-18.json`; baseline command
output from this execution session.

Code/harness/model/index versions: branch `aether-goal-1-7`, parent HEAD
`9318598` before the checkpoint; approved models are recorded in
`MODEL_CONFIGURATION.md`.

Decision or explicit assumption: The active `GOAL_1_7.md` authorizes its scoped
checkpoint but does not authorize a remote push. The existing ignored `.env` is
not inspected, staged, or copied.

Remaining limitation or blocker: The first real workflow has not been selected;
that material product choice will be requested before live evaluation. It does
not block the deterministic correctness work.

Next concrete action: Stage the reviewed manifest, inspect staged content for
credentials and unrelated files, create the local checkpoint commit, then write
the focused Step 2 failing regression tests.

Step/task: 1 and 2 — checkpoint and deterministic runtime correctness.

Change and purpose: Created local checkpoint `ad5c20a`
(`feat(aether): add model-aware runtime baseline`) on `aether-goal-1-7` without
pushing. Fixed four runtime failures: full response text now drives handoffs and
action extraction without being persisted to JSONL traces; verifier status is
explicit and skipped verification cannot approve; all-quarantined decisions
return no adoption with reasons; empty trace analysis is explicit incomplete
evidence. Added eight focused regressions in `tests/test_runtime_correctness.py`
and `tests/test_swarm_correctness.py`.

Verification command, result, and exit code: the new focused suite first failed
with two failures and three errors against the old behavior, then passed 8 tests,
exit 0. `.venv/bin/python -B -m unittest discover -s tests -v` — 22 passed,
exit 0. `PYTHONPATH=../.. ../../.venv/bin/python -B -m pytest ../../tests -q
-p no:cacheprovider` — 54 passed, exit 0.

Evidence/receipt path: source tests above; no external request or live model
evaluation was performed.

Code/harness/model/index versions: `ad5c20a` is the checkpoint parent and
`f07b94f` records Step 2 after export review. The package manifest contains 19
canonical files and all three exported locations matched source byte-for-byte.

Decision or explicit assumption: Complete response text is needed transiently
for behavior and handoffs, but persistent trace logs retain only previews. A
missing expected hard trigger means verification was not run and cannot approve.

Remaining limitation or blocker: The required first user workflow is not yet
selected. Live evaluation remains unauthorized until its data boundary, request
limit, and spend ceiling are approved.

Next concrete action: rebuild and inspect the distribution, then define the
workflow and evaluation protocol once the user selects the material use case.
