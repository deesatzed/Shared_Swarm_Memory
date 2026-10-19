# Swarm memory comparison: design

Date: 2026-10-19
Status: APPROVED by the user on 2026-10-19, section by section, in a brainstorming session.
Branch: `feat/swarm-comparison`, made from `main` at `9318598`. Run file: [GOAL_RUN_EXP.md](../../GOAL_RUN_EXP.md).

## Plain version

We will test whether our shared memory app is worth having. Five AI agents with different roles work through the same real project history three times:

1. Each agent sees every earlier message.
2. Agents share a search box over earlier messages.
3. Agents use our memory app.

We count tokens and cost, correct answers, and how often an agent relies on an out-of-date value. The memory app gets only the additions needed to stop out-of-date or wrong exact values. Everything else waits until the results show it is needed.

## Why: the outcome metrics

| Metric | Meaning | Target |
|---|---|---|
| M1 (must pass) | No stale or wrong exact value is ever acted on | Zero |
| M2 | Answers at least as good as the other two swarms, using less context | Measured, no target set |

These metrics came first. Every mechanism below closes one way M1 can fail:

| How M1 fails | What closes it |
|---|---|
| a. The agent never saw the fact | Push current values to role cards; key registry |
| b. The agent copied it wrong | Read-back check at use |
| c. The binding went stale | Source capture plus re-check |
| d. A false bind | Evidence agents cannot author, plus the gate |
| e. Search returned an old value | Drop non-current hits (already built) |
| f. A reconstructed value | Rule: exact values are never reconstructed, and reconstructed text is never evidence |
| g. One fact under two names | Key registry |

## What each source idea contributed

| Source | Taken into this design | Left out for now |
|---|---|---|
| `swarm_memory` decision record | Risk bars, dissent, duplicate guard, current-binding filter, recall budget, use-based ranking | Self-reported confidence as the bind signal; two-agent evidence rule (replaced, below) |
| Multi-store / scaffold idea | Read classes: exact values are pushed, derived status is re-checked | Scaffold files, expiring notes |
| `memasys.md` | Rules-first reading: no model in the read path | Reconstructive scaffold |
| HMSS | Nothing new. Use-based ranking already exists. | All of it |
| Memorilla | Its comparison method: no memory, search, full context | Compressed memory vectors (needs a Linux GPU and open model weights) |

## Locked choices

| Choice | Result |
|---|---|
| Workloads | Software-build swarm and clinical swarm are both in scope. This measurement uses non-clinical tasks only (user, 2026-10-19). |
| Clinical data | Public clinical reference data first. Local patient data later, through a local-only route. Not part of this measurement. |
| Agent model | `deepseek/deepseek-v4.1-flash-1017` on `/api/v1/chat/completions`, provider fallback off |
| Routine decisions | `liquid/d1-ultra` on `/api/v1/systemone` |
| High and critical approval | `google/gemini-4-argon` on `/api/v1/chat/completions` |
| Search embeddings | `google/gemini-embedding-2` on `/api/v1/embeddings` (3,072 dimensions in the 2026-10-18 receipt) |
| Credentials | Only `OPENROUTER_API_KEY`, read from `/Volumes/WS4TB/merged.env`. The file is never sourced or printed. |
| Evidence for high and critical keys | A harness capture whose content contains the value. This replaces "two experiences from two agents" (user, 2026-10-19). |

All four model IDs passed a connection check on 2026-10-18 (`aether/aether_workspace/receipts/model-check-2026-10-18.json` on branch `aether-goal-1-7`). `liquid/d1-ultra` and `google/gemini-embedding-2` are not in the `/api/v1/models` list. They are served from their own endpoints.

## Section 1: the measurement harness

**Tasks** are real, non-clinical, and taken from this repo's git history where facts changed. These facts were checked with `git show` on 2026-10-19:

| Task | Document states replayed, in order | Changing facts (expected now / stale) |
|---|---|---|
| A, handoff | `HANDOFF_2026-10-17.md` at `6136de0`, `379afbc`, `9318598` | Tests passing: `54` / `40`. Remote: `deesatzed/Shared_Swarm_Memory` / `no git remote`. |
| B, design | `docs/plans/2026-10-17-swarm-decision-memory-design.md` at `1138186`, `3dbc1a4`, `ad5c20a` | Decision model: `liquid/d1-ultra` / `lfm-2.5-24b-a2b`. Evidence rule for high keys: `two different agents` / no stale string. |

String counts per state were checked on 2026-10-19:
- `40 passed` and `no git remote` appear at `6136de0` and `379afbc`, and not at `9318598`.
- `54 passed` and `deesatzed/Shared_Swarm_Memory` appear only at `9318598`.
- `two different agents` first appears at `3dbc1a4`, and `d1-ultra` first appears at `ad5c20a`.

Each task also asks control questions whose answers never changed. For example, `0.92` (the high risk bar) appears in all six states. Known hard case: at `ad5c20a` the design file names `liquid/d1-ultra` on line 3 and still lists `liquid/lfm-2.5-24b-a2b` on line 19. Re-check alone will not catch this. `ad5c20a` exists only on branch `aether-goal-1-7`, which the harness reads with `git show`.

**Question format:** `experiments/flat_briefing/questions.json` style: `{"id", "question", "expect": [...], "stale": [...], "answer_at"}`.

**Three swarms.** Each has the same five roles (planner, coder, tester, reviewer, release), the same model, the same role prompts and the same answer format. Only the shared context differs:

| Swarm | Context besides the role prompt |
|---|---|
| Full context | All earlier document states and all earlier messages |
| Search only | The top 5 matches from a shared embedding store of earlier states and messages, packed to 2,000 characters |
| Our memory | The role card, plus a recall of at most 2,000 characters |

**Measures per run:**
- tokens and cost, from the usage each response reports, including every call the memory app makes
- correct answers: each answer is given as a JSON value field, and it is correct when it contains every expected string as whole words, case and spacing ignored
- stale-value actions: a relied-on value or an answer value that contains a listed stale string as whole words

Scoring reads only the value fields. An agent's prose can mention an old value ("was 40, now 54") without counting as a stale action.

**Repeats:** 3 per task per swarm for the full run. The harness stops at the user's spending limit.

**Output:** a results file plus a plain summary table.

## Section 2: what the memory app adds

The base is the existing `swarm_memory` package and its 54 tests. Only additions that close an M1 failure path are built.

1. **Key registry.** `keys.json` declares each key once: type, unit, risk floor, sensitivity, shelf life, and the roles that use it. An undeclared key cannot bind; it stays a note. The registry floor replaces the prefix guesses in `risk.py` for registered keys.
2. **Captures.** Only the harness records captures. A capture is a file at a commit (path, commit, hash, content) or a command run (command, exit code, output hash). Agents cite capture ids. Agents have no way to write one.
3. **Decision models.**
   - `liquid/d1-ultra` receives one packed case: the key, the candidate values, the cited capture text and the current binding. It returns a choice among the candidates or "none", with a probability.
   - That probability replaces the proposer's self-reported confidence. Code applies the bar.
   - In this version d1-ultra is not asked for a risk class. The registry floor and the existing code rules set the class.
   - For high and critical keys, `google/gemini-4-argon` must also approve.
4. **Capture rule.** For high and critical keys, a cited capture must contain the value, or the fact stays open as `no_capture`. A conclusion an agent reasoned its way to, with no capture behind it, cannot become a high or critical fact.
5. **Push.** Each role card lists the current values for that role's keys, with decision ids.
6. **Read-back.** Every agent output ends with a block listing the values it relies on. Code checks the block against the current bindings. A mismatch is blocked and counted.
7. **Re-check.** When a newer document state arrives, each binding's capture is checked against it. If the value no longer appears there, the binding moves to "needs re-check" and comes off the role cards.

**Kept as is:** the current-binding filter on recall, the 2,000-character recall budget, the 500-character cap per item, use-based ranking, dissent, the duplicate guard.

**Recall index:** recall uses the same embedding store as the search-only swarm, behind the existing index port in `swarm_memory/index.py`. Hy-Memory stays uninstalled.

**Left out until the results show a gap:** scaffold files, expiring working notes, a graph store, Memorilla, any model in the read path.

## Section 3: how one task runs

**In all three swarms:**
- A task is a list of document states. Each state is also a capture.
- There is one round per state. The harness shows the new state in full, then each of the five agents takes one turn in a fixed order.
- Every turn ends with the same structured block of relied-on values (key, value, and decision id when there is one).
- After the last state, every agent answers the task's questions. The question prompt carries only the role prompt and that swarm's context, with no new document state. That makes the answers a test of memory.

**Memory swarm only:**
1. **Before the round,** re-check every binding against the new state.
2. **After each turn,** handle each proposed fact:
   - The key must be in the registry.
   - For a high or critical key, the cited capture must contain the value.
   - d1-ultra picks a value and gives a probability, and code applies the bar.
   - For a high or critical key, gemini-4-argon must also approve.
3. **After each turn,** read-back. A mismatch gives the agent one retry with the current value shown, and the mismatch is counted.

**Scoring:**
- Tokens and cost cover every call: agents, embeddings, both decision models and retries.
- The memory swarm is reported twice, before and after read-back, so the effect of read-back is visible.

## Section 4: failure handling

The rule is to fail closed and record it. A failure never binds a fact and never becomes an estimated number.

**Model calls:**
- **Transient errors** (HTTP 429, 5xx, timeouts) are retried up to 3 times, waiting as long as the provider asks. HTTP 400, 401, 402, 403 and 404 are not retried. Once the retries are spent, the run is marked failed with the error text.
- **No fallback** to another model, and no cached or simulated response.
- **d1-ultra failures:** an error, a missing choice, or a probability that is missing or outside 0–1 leaves the proposal open as `decision_model_unavailable`.
- **gemini-4-argon failures:** an error, an answer that is not the agreed JSON, or a refusal leaves a high or critical proposal open as `not_approved`.
- **Bad relied-on block:** if it is missing or can't be parsed, the agent gets one re-prompt, and the tokens are counted. A second failure is counted as a format failure and the run continues.

**Spending:**
- The limit is read from `SWARM_EXP_SPEND_LIMIT_USD`. If it is not set, the harness makes no paid call.
- The running total comes from the `usage.cost` each response reports. The harness checks the total before every call and stops once the limit is reached.
- The last call can go past the limit, because a call's cost is known only after it returns.
- A run cut short is marked incomplete. A response with no usage numbers is flagged, never estimated.

**Comparability:** the comparison table counts a task and repeat only when all three swarms finished it.

**Crash and resume:** every call is appended to a JSON lines log as soon as it returns. The log records the request id, requested and served model, tokens, cost and output. A restart skips finished runs and resumes from the last complete round.

**Keys:**
- The key is never written to logs, results or errors.
- Request headers are not logged.
- Error text is redacted for `sk-` strings before it is saved.

## Section 5: testing

**Unit tests** follow the existing pytest style. Each is written first and fails before its code exists. The 54 current tests keep passing, except the tests for the two-agent rule. The capture rule replaces that rule, so those tests are rewritten, and the commit lists them.

New tests cover:
- the registry
- the capture rule
- decision-answer handling
- read-back
- re-check
- parsing of the relied-on block
- scoring
- the spending stop
- resume
- redaction

The decision logic takes model answers as input data, so these tests need no model calls and no fake responses.

**Answer key check:**
- A test runs `git show` to confirm each expected string appears in the state that should contain it.
- It confirms each stale string appears in an earlier state, and each control answer in every state.

**Live checks:**
- Marked `live` and run only on request, after the spending limit is set.
- One real call to each of the four models confirms the request and response shape. This includes the field name of d1-ultra's probability, which the 2026-10-18 receipt does not show.
- Nothing is recorded for replay.

**Trial run:** task A, 1 repeat, all three swarms. The run then stops for the user to review the results table, the spend and any failures. The full run starts only when the user says so.

**Done means:**
- All unit tests pass, with exact counts reported.
- The trial run finishes in all three swarms.
- The results file and summary table exist.

## Open items needing the user

- Set `SWARM_EXP_SPEND_LIMIT_USD`. It blocks every paid call.
- Rotate the five API keys exposed in the 2026-10-17 session.
- Delete `/Volumes/WS4TB/Swarm_Mem_Share/merged.env`. It is byte-identical to `/Volumes/WS4TB/merged.env`, outside the repo (checked with `cmp` on 2026-10-19).
- Decide whether to commit the `.gitignore` line that excludes `merged.env` (uncommitted on `aether-goal-1-7`).
- Decide whether to delete `feat/swarm-decision-memory`.
- Any push of `feat/swarm-comparison` needs a new instruction.
