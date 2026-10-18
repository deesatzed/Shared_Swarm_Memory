# Model refresh decisions — 2026-10-18

- The user's seven exact IDs replace the previous Aether model defaults.
- Use the list order as default and alternatives within each API category.
- Text uses `/api/v1/chat/completions`, typed decisions use `/api/v1/systemone`,
  and embeddings use `/api/v1/embeddings`.
- Decision outputs retain model probabilities. The main memory package's risk
  bars and evidence gates are not replaced by this client update.
- Embedding models never fall back automatically. A switch requires an independent
  index or re-embedding all indexed content.
- Read only `OPENROUTER_API_KEY` from a selected credentials file. Do not source
  `/Volumes/WS4TB/merged.env`, import its other settings, or copy secrets into repo
  files or distributions.
- The user authorized one small connection check per named model. These seven
  checks succeeded; they do not authorize uploading sensitive data or establish
  semantic quality, calibration, or production readiness.
- Aether's current workspace is the source for generated copies and archives.
  HMSS stays a separate reference implementation.

## Runtime correctness decisions — 2026-10-18

- A runtime trace retains the complete model response only in memory while the
  dispatch is active. `response_preview` remains the display and persistent-log
  field. Persistent JSONL traces deliberately exclude `response_text` so this
  correction does not expand on-disk prompt/output retention.
- Verification has explicit `passed`, `failed`, and `not_run` states. A fast
  path has status `not_run`; it may return a proposed action but cannot claim
  verifier approval. A full path is approved only when the verifier status is
  `passed` against a supplied hard trigger.
- Candidates below either deterministic safety or evidence threshold remain in
  the decision record with their quarantine reasons. If every candidate is
  quarantined, the decision returns no selected candidate and no adoption.
- An empty trace set is incomplete evidence, represented by a zero-valued
  report with `NO_TRACES`; it is not a successful verification outcome.
