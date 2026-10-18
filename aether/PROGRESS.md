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
