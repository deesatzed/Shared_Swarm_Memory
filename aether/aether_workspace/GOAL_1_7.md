# Aether Steps 1–7 Implementation Plan

> **For Codex:** Use the `executing-plans` skill when instructed to execute this
> plan. Use `test-driven-development` for behavior changes and
> `verification-before-completion` before marking a step complete.

**Goal:** Deliver one reliable, evidence-backed Aether workflow, then add a
controlled improvement loop supported by repeatable evaluation.

**Architecture:** Aether orchestrates role-specific harnesses around the approved
text and typed-decision clients. The main `swarm_memory` SQLite record remains
the authority for accepted facts; retrieval and reconstruction must preserve its
current-binding and evidence rules. Improvement operates on versioned harness
changes with recorded adoption evidence and rollback.

**Tech stack:** Python 3.12+, Pydantic, HTTPX, SQLite, unittest for Aether, pytest
for `swarm_memory`, OpenRouter text/System One/embedding endpoints.

**Created:** 2026-10-18. **Status:** Planned; steps 1–7 have not been executed.
Creating this document does not start implementation, commit, push, or live runs.

---

## Workspace, authority, and baseline

- Repository root: `/Volumes/WS4TB/Swarm_Mem_Share`.
- Canonical Aether source: `aether/aether_workspace/` under the repository root.
- All relative implementation paths below are relative to canonical Aether source
  unless prefixed with `../../`, which addresses the repository root.
- Read this file with `DECISIONS.md`, `PROGRESS.md`,
  `../../MODEL_CONFIGURATION.md`, and
  `../../docs/plans/2026-10-17-swarm-decision-memory-design.md`.
- Read `GOAL.md`, `STANDARDS.md`, `IMPLEMENT.md`, and `TASK_QUEUE.md` if they are
  added. Resolve conflicts using the latest explicit user instruction and record
  material changes in `DECISIONS.md`.
- Last verified baseline before this plan: 14 Aether regression tests and 54 main
  memory-library tests passed. Re-run them when execution starts; these counts
  are historical evidence, not a guarantee about the next checkout.
- All seven approved models passed generic connection checks. Receipt:
  `receipts/model-check-2026-10-18.json`. That proves access and response shape,
  not task accuracy, calibrated confidence, or production readiness.
- The model refresh remains uncommitted. The parent repository also contains
  unrelated untracked `hmss/` and `memasys.md`; preserve them.
- HMSS is a separate reference implementation. Its code, defaults, and measured
  offline examples do not define this project's implementation or evidence.

## Approved model contract

| Purpose | Default | Alternatives | Endpoint |
| --- | --- | --- | --- |
| Text | `deepseek/deepseek-v4.1-flash-1017` | `nvidia/nemotron-3.5-super-vl`, `google/gemini-4-argon` | `/api/v1/chat/completions` |
| Decisions | `liquid/d1-ultra` | `typesafe/jev-1.14` | `/api/v1/systemone` |
| Embeddings | `google/gemini-embedding-2` | `liquid/lfm-2.5-embedding-350m:free` | `/api/v1/embeddings` |

`model_config.py` defines selection. List order supplies the default and allowed
alternatives. Keep text, typed decisions, and embeddings in their own API groups.
Record the requested model and actual serving model for evaluation.

Read only `OPENROUTER_API_KEY` from an explicitly selected credential file, such
as `/Volumes/WS4TB/merged.env`. Never source that file, import its other settings,
print its secrets, or include credentials in commits, logs, or distributions.

Embedding alternatives never fall back automatically. The connection checks
observed 3072 dimensions for Gemini and 1024 for Liquid. Persist the exact model
and dimensions with an index; switching models requires a separate index or a
complete, explicit re-embedding migration.

## Execution rules

1. Execute steps in dependency order. Finish each step's acceptance checks before
   marking it complete. Independent read-only discovery may proceed while a
   later product decision is pending.
2. Before a behavior change, write a focused failing regression test, observe
   its failure, implement the smallest correction, and run the relevant suite.
3. Record actual commands, exit codes, evidence paths, limitations, and the next
   action in `PROGRESS.md`. Record material decisions in `DECISIONS.md`.
4. Make safe implementation assumptions explicit and continue. Ask only when
   blocked, when a product decision materially changes scope, or when an action
   needs authority that the session has not supplied.
5. Keep source, generated copies, generators, and archives consistent using
   `scripts/package_aether.py`. Inspect its explicit file list before packaging.
   Preserve user files and unrelated work; never use broad staging or resets.
6. The previous authorization covered seven small model connection checks.
   Before additional live evaluation, establish the approved input set, outbound
   data scope, spending ceiling, and request limits. Approval of this document
   alone does not authorize those calls or sensitive-data upload.
7. Stop for missing credentials/accounts, destructive actions, production
   deployment, sensitive-data risk, legal/compliance uncertainty, repeated failure
   after mitigation, or a material scope decision. Follow the standing AGENTS.md
   instructions; avoid repeatedly patching the same unexplained failure.

## Step tracker

| Step | Deliverable | Dependency | Status | Evidence |
| --- | --- | --- | --- | --- |
| 1 | Scoped Git checkpoint | Execution instruction | Not started | Pending |
| 2 | Correctness fixes and regression tests | 1 | Not started | Pending |
| 3 | Approved first workflow and acceptance criteria | 2 | Not started | Pending |
| 4 | Typed decisions integrated into that workflow | 3 | Not started | Pending |
| 5 | Current-fact memory retrieval integrated | 4 | Not started | Pending |
| 6 | Repeatable end-to-end evaluation | 4, 5 | Not started | Pending |
| 7 | Controlled improvement loop and rollback | 6 | Not started | Pending |

## Step 1 — Checkpoint the model refresh in Git

**Purpose:** Preserve a reviewable baseline before runtime changes.

**Inspect:** The repository diff, `../../MODEL_CONFIGURATION.md`, the canonical
Aether files, generated exports, and the model-check receipt.

- [ ] Record the current branch, HEAD, tracked diff, and untracked inventory.
- [ ] Re-run the baseline verification commands below.
- [ ] Review an explicit staging manifest covering only the authorized model
      refresh, its tests/docs/distributions, and this goal document.
- [ ] Exclude `.env`, `merged.env`, `.venv/`, local indexes, unrelated HMSS files,
      and unrelated user work. Check generated artifacts for credentials.
- [ ] Create the scoped commit when execution authority includes that action.
      Preserve the current checkout's dirty work; do not switch or reset blindly.
- [ ] Record the resulting commit ID and verification evidence in `PROGRESS.md`.

**Acceptance:** The approved baseline can be identified by commit, its staged
content was reviewed, and no secret or unrelated file entered the commit. A push
is a separate action requiring session authorization.

## Step 2 — Fix Aether's correctness bugs

**Modify:** `aether_core.py`, `aether_swarm.py`.
**Create tests:** `tests/test_runtime_correctness.py`,
`tests/test_swarm_correctness.py`. Use new files so the model-access tests retain
their specific purpose.

For each item, write and observe the failing test before implementation:

- [ ] Reproduce a missed required action on the worker-only shortcut. A skipped
      verifier must be distinguishable from a passed verifier; failure cannot
      yield approval. Apply the same explicit status semantics to full runs.
- [ ] Reproduce an all-quarantined candidate set. Return an explicit no-adoption
      result rather than selecting a quarantined candidate. Preserve quarantine
      reasons in the decision record.
- [ ] Reproduce an action token or essential handoff evidence occurring after the
      first 160 characters. Keep full responses for behavior and handoffs;
      reserve `response_preview` for display. Decide and document what full text
      may be persisted so fixing truncation does not silently expand logging.
- [ ] Reproduce `TraceAnalyzer.analyze([])`. Return a defined empty report with
      no divide-by-zero error and no implied successful verification.
- [ ] Test positive paths, invalid/missing actions, explicit verification failure,
      skipped verification, and candidate sets containing both valid and
      quarantined entries.
- [ ] Keep generated copies aligned; document any schema migration.

**Acceptance:** All four original failures have regression evidence, no skipped
or failed check is reported as approval, rejected candidates cannot be adopted,
and the Aether and main memory suites pass.

## Step 3 — Define the first real user workflow

**Create:** `docs/FIRST_WORKFLOW.md`, `docs/EVALUATION_PROTOCOL.md`.
**Modify:** `DECISIONS.md`, `PROGRESS.md`; change a domain pack only after its
purpose and data contract are settled.

- [ ] Identify the actual user, recurring problem, current workaround, and the
      decision the workflow should help them make.
- [ ] Specify inputs, source ownership, allowed data, outputs, action boundaries,
      success criteria, and the person or mechanism that assesses correctness.
- [ ] Select representative development cases and a separate held-out case set.
      Record provenance and split rules before tuning against results.
- [ ] Set acceptance targets for correctness, missed escalations, unsupported
      claims, latency, and cost. Identify which are strict requirements and
      which are measurements to explore.
- [ ] For a live run, record the authorized outbound input subset, maximum spend,
      maximum requests, and stop conditions before making calls.

**Candidate, not selected:** The current SRE pack could become read-only incident
triage over authorized alerts and runbooks, producing a recommendation plus
evidence. Its existing metrics are simulated; they do not establish a real use
case, source connection, or permission to act on infrastructure.

**Acceptance:** A concrete workflow and its evaluation criteria are approved and
recorded. If the workflow choice materially changes scope, resolve it with the
user. Continue independent correctness/documentation work while it is pending.

## Step 4 — Integrate typed decision models

**Modify:** `openrouter_adapter.py`, `aether_swarm.py`, and the selected workflow
entry point. Add `aether_decisions.py` if a separate schema/validation boundary
keeps model output handling out of orchestration.
**Create tests:** `tests/test_decision_integration.py`.

- [ ] Define the specific routing or verification questions required by step 3,
      their permitted answers, probability interpretation, and abstention rules.
- [ ] Build the smallest case containing the relevant request, candidate actions,
      source references, and constraints. Do not send the complete memory store.
- [ ] Call D1 Ultra through `/systemone`, with Jev as the approved alternative.
      Preserve typed answers and probabilities; never parse a generated sentence
      as a substitute for a System One result.
- [ ] Validate every required answer, allowed choice, and finite probability in
      range. Missing, malformed, inconsistent, or failed responses defer the
      decision and cannot cause approval.
- [ ] Keep the main memory package's numeric risk bars, class-raising rules, and
      independent-evidence requirements in deterministic code. Record how model
      outputs map to that contract before connecting live binding.
- [ ] Record model identity, fallback, request outcome, usage, and safe source
      references without logging credentials or unapproved payloads.
- [ ] Test valid responses, abstention, malformed probabilities, missing answers,
      provider failure, fallback identity, and unsuccessful verification.

**Acceptance:** The chosen workflow consumes typed decisions with explicit
failure behavior. Model confidence alone cannot bypass an evidence or approval
gate. Local contract tests pass; authorized live evidence is recorded separately.

## Step 5 — Integrate shared-memory retrieval

**Modify:** `../../swarm_memory/index.py`, `../../swarm_memory/service.py`,
`../../swarm_memory/store.py` as required, and the selected Aether integration
boundary. Preserve the tested interfaces where possible.
**Create tests:** `../../tests/test_index_integration.py`,
`tests/test_memory_integration.py`.

- [ ] Verify the chosen Hy-Memory SDK version and real API before installing or
      implementing against it. Record the dependency and supported interface.
- [ ] Implement index writes and search using one selected embedding model.
      Record model ID, vector dimensions, schema version, and source decision ID.
- [ ] Preserve SQLite-first binding, dirty-index tracking, and a bounded,
      idempotent recovery path for failed index writes.
- [ ] Feed search hits through the current-binding filter before returning them.
      Preserve the existing limit of 5, 2000-character budget, 500-character
      per-item cap, whole-item skipping, and explicit used/ignored reports.
- [ ] Define the interface between accepted facts and Aether scaffold cues in
      `DECISIONS.md`. References must retain decision IDs and provenance;
      generated reconstructions cannot establish their own factual authority.
- [ ] Test rejected/open facts staying out of the index, superseded facts being
      dropped, duplicate writes, index failures, recovery, model/dimension
      mismatch, and prompt-budget limits.
- [ ] Verify the round trip: evidence-backed bind → index → search → current
      binding check → bounded workflow context.

**Acceptance:** Authorized facts complete the real retrieval round trip, stale
facts cannot re-enter as current facts, index failure does not erase the SQLite
record, and model switches cannot mix embedding spaces. Test-double evidence
remains distinct from live index evidence. Keep one writer.

## Step 6 — Evaluate the full workflow

**Create:** `scripts/evaluate_workflow.py`, `docs/EVALUATION_RESULTS.md`, and
versioned, nonsecret receipts under `receipts/evaluation/`.
**Use:** The frozen protocol and held-out cases from step 3.

- [ ] Run the same cases against the existing baseline and integrated workflow,
      recording code version, harness version, model IDs, index model, and inputs.
- [ ] Measure task correctness, missed required escalations, unsupported claims,
      stale-fact leakage, memory usefulness, actual API usage/cost, and latency.
- [ ] Separate deterministic tests, test-double simulations, live observations,
      and reviewer judgments. Keep estimates distinguishable from API usage.
- [ ] Exercise API failures, invalid decisions, empty memory, stale memory, and
      index failure. Measure safe failure behavior as well as successful runs.
- [ ] Compare results with the predeclared acceptance criteria. Report failures
      and uncertainty; do not tune against the held-out set and retain its label.
- [ ] Stop at the authorized spend/request limits. Missing authority blocks live
      runs, not local test and evaluation-harness implementation.

**Acceptance:** A reproducible report identifies which requirements passed or
failed with linked receipts. Failed mandatory criteria must be resolved before
step 7 can adopt changes; narrow connection checks cannot satisfy this gate.

## Step 7 — Add the controlled improvement loop

**Modify:** `aether_core.py`, `openrouter_adapter.py`, and the workflow entry point.
**Create:** `improvement_library.py`, `tests/test_improvement_loop.py`, and
`docs/IMPROVEMENT_POLICY.md`.

- [ ] Define a versioned improvement record: parent harness, proposed diff,
      rationale, evidence references, probe protocol, scores, disposition,
      adopted version if any, and rollback target.
- [ ] Implement the missing Improvement Library and bounded candidate proposals.
      Proposed edits remain data until evaluated; do not execute arbitrary
      generated code or expand the authorized tool/data boundary.
- [ ] Apply each candidate to an isolated harness and memory snapshot. Support
      declared prompt additions, thresholds, guardrails, nodes, and edges without
      changing the active baseline during probing.
- [ ] Reuse step 6's protocol to compare candidates against the baseline under a
      declared iteration, request, and spending budget. Use separate development
      and confirmation cases; no improvements may redefine their own evaluator.
- [ ] Rank viable candidates with explicit criteria and evidence. Reject every
      quarantined candidate and return no adoption when none qualifies.
- [ ] Adopt only when mandatory gates pass and session authority permits the
      change. Record rejected candidates and reasons as well as accepted ones.
- [ ] Version the adopted harness and test restoration of the previous version,
      including compatible memory/index references and a complete audit record.
- [ ] Run the finished loop on the approved workflow and record whether an
      improvement was demonstrated, rejected, or remained unverified.

**Acceptance:** One bounded propose → probe → score → adopt-or-reject cycle is
reproducible, evidence-linked, and reversible. Rejection is a valid result.
Claims of improvement require confirmation evidence; implementing the loop alone
does not demonstrate improved task performance or justify production deployment.

## Verification commands

Run from `/Volumes/WS4TB/Swarm_Mem_Share/aether/aether_workspace`:

```sh
# Aether local regression suite; initially 14 tests.
.venv/bin/python -B -m unittest discover -s tests -v

# Main memory policy/store suite; initially 54 tests.
PYTHONPATH=../.. ../../.venv/bin/python -B -m pytest ../../tests -q -p no:cacheprovider

# Entry point and repository whitespace check.
.venv/bin/python -B aether_cli.py --help
git -C ../.. diff --check
git -C ../.. status --short
```

Capture the actual count after new tests are added. A passing unit suite does not
substitute for steps 5–6's live integration and workflow evidence.

Use `scripts/package_aether.py --output <approved-output-directory>` to rebuild
exports when source changes. Its regression test compiles emitted code; also
verify that exported files match canonical source and exclude credentials.
Writing parent exports or Git metadata may require filesystem-sandbox approval.

## Completion and handoff

This goal is complete only when all seven steps have their acceptance evidence,
the approved workflow meets mandatory criteria, rollback is demonstrated,
canonical/exported code agrees, and the scoped commits and remaining limitations
are recorded. If a required gate fails, retain the truthful incomplete status.

For each execution session, append to `PROGRESS.md`:

```text
Step/task:
Change and purpose:
Verification command, result, and exit code:
Evidence/receipt path:
Code/harness/model/index versions:
Decision or explicit assumption:
Remaining limitation or blocker:
Next concrete action:
```

Maintain the tracker above as work proceeds. Do not mark later steps complete
because their interfaces, placeholders, connection probes, or plans exist.
