# Shared swarm memory: decision models first

Date: 2026-10-17

This is the design for shared memory in this workspace. It records decisions already made in the design session. It does not claim the code exists yet.

## Plain version

Agents share a small set of current facts. A fact becomes current only when a decision record says so. The record names the risk of being wrong, the confidence of the agent, the value that lost, and the evidence used. Search can find an older sentence. The record drops that sentence when it is no longer the current fact. Tool output stays out of this store.

## Locked choices

| Choice | Result |
|---|---|
| Conflict on a fact | Stays open until a decision instance binds one value. The other value stays as dissent. |
| Who may bind | Any agent, when the decision instance clears the risk bar. |
| Decision runner | `liquid/lfm-2.5-24b-a2b` (`DECISION_MODEL` in `.env`). Catalog name: LiquidAI LFM2.5-24B-A2B. Context length 128,000. Text in, text out. |
| Worker model | `deepseek/deepseek-v4.1-flash-1017` (`MODEL1`). Catalog name: DeepSeek V4.1 Flash 1017. Context length 1,048,576. Text and image in, text out. |
| Risk bars | low 0.60, standard 0.80, high 0.92, critical 0.97 |
| Record | SQLite |
| Search index | Hy-Memory, and only for a sentence that is the current binding |
| Traces | context-mode. This package does not store them as facts. |
| Second cognitive store | Agno memory stays unused. `add_memories_to_context` stays off if Agno is the runtime. |

`.env` holds the OpenRouter key. This design does not copy the key. The workspace root is not a git repository. `.gitignore` ignores `.env`.

## Models and what each one sees

Workers propose candidates with `MODEL1`. They do not set the bar.

`liquid/lfm-2.5-24b-a2b` sees one packed case: the fact key, the candidates, the evidence ids, the current binding if one exists, and the criteria. It returns a risk class, a confidence from 0 to 1, a chosen value, and a one-line reason. It does not see the whole store. It does not output the numeric bar.

The packed case has to stay small. The decision model’s context length is 128,000 tokens. The worker’s context is larger. That difference is why the decision runner receives a case and the worker does not dump memory into the decision call.

## Decision models

These are versioned rules. Code executes the knockouts. The language model names a class and a confidence.

### `risk_scaled_bar` version 1

| Class | Bar | How a fact reaches it |
|---|---|---|
| low | 0.60 | The key is declared low, and no raise rule fires |
| standard | 0.80 | Default |
| high | 0.92 | Prefix `clinical.`, `genome.`, `identity.`, or `auth.`; more than one role will act on it; any replacement of a bound value |
| critical | 0.97 | Declared critical, or the action is patient-facing, deletion, or publication |

Order of classification:

1. The declared floor on the key is the lowest class allowed.
2. Code raises the class when a prefix, a multi-role flag, or an existing binding matches. A raise is mandatory.
3. The decision model may raise one more step and must give a one-line reason. A request to jump two steps becomes one step. A request to lower the class is ignored.
4. Code looks up the bar and compares it with the recorded confidence.

### `agent_confidence_bind` version 1

A contested fact becomes current only when all of these are true:

- Confidence is a number and is greater than or equal to the bar.
- Both candidates are cited.
- The losing value is stored as dissent.
- If a value is already bound, the new instance cites at least one evidence id the earlier instance did not use.

Below the bar, the conflict stays open. Any agent may emit the instance.

### `uncontested_claim` version 1

A first write has no rival. It uses the same risk bar. Being first does not lower the class.

### `preference_recency` version 1

A preference may be replaced by a newer preference from the same shared user. The fact-conflict bar does not apply. The old preference stays as history.

### `storage_split` version 1

SQLite is the record of models, instances, candidates, bindings, dissent, role cards, and the recall log. Hy-Memory receives one sentence after a bind, and that sentence carries the decision id. Open conflicts are not indexed as settled facts.

## Write path

A write has a class: fact, experience, preference, or trace.

- A trace is refused by this package. context-mode keeps tool output.
- An experience is appended in SQLite. It can be cited later. It does not bind a fact.
- A fact with no fact key is stored as an experience.
- A fact with a key loads the current binding and builds one decision case.
- On a bind, SQLite commits the instance and the binding first. Hy-Memory is written second. If the index write fails, the binding remains and `index_dirty` is set.
- On an open conflict, SQLite records the open instance. Hy-Memory receives nothing.

## Read path

The role card is the text placed at the start of a turn for that role. It lists current bindings and open conflicts for keys that role acts on. The card stops at 2,000 characters. Bindings come before open conflicts.

`Recall` searches the Hy-Memory index with a limit of 5. Each hit must carry a decision id. SQLite keeps the hit only when that id is still the current binding for its fact key. The tool returns the decision before the sentence and stops at 2,000 characters. The call is appended to the recall log.

## Failure behavior

| Event | Result |
|---|---|
| Confidence missing or not a number | Instance stays open. No index write. |
| Decision-model output is missing a required field, or the call fails | Instance stays open. No index write. |
| Model names a lower class than the floor | Code keeps the floor and the code raises. |
| Model names a class more than one step above the code result | Code raises one step. |
| Same evidence as the current binding | The flip is rejected. The current binding stays. |
| SQLite commit fails | No index write. |
| Index write fails after a SQLite commit | Binding stays. `index_dirty` is 1. |
| Recall hit has no decision id, or the id is not the current binding | The hit is dropped. |

`evolve()` and Agno `optimize_memories()` are not part of this bind path. A summary must not choose the winner of an open conflict.

## Components

| Piece | Path | Job |
|---|---|---|
| Risk table | `swarm_memory/risk.py` | Floors, raises, bars |
| Bind rules | `swarm_memory/decide.py` | Open, bind, or reject |
| Record | `swarm_memory/store.py` | SQLite |
| Role card | `swarm_memory/card.py` | Bounded text for one role |
| Recall filter | `swarm_memory/recall.py` | Drop stale hits, apply the character budget |
| Index port | `swarm_memory/index.py` | Write a bound sentence. Production adapter is Hy-Memory. |
| Service | `swarm_memory/service.py` | `remember` and `recall` in the order above |

The existing `swarm_shared_memory.py` demo writes straight to Hy-Memory. It stays as a demo until a later task points `SwarmAgent` at the service. Until then, the demo is not the decision path.

## Tests

Tests call the risk table, the bind rules, SQLite, the role card, and the recall filter with explicit inputs. They do not call OpenRouter. They do not stand in for Hy-Memory as a memory store. A test may pass a list of index hits into the recall filter. That list is input data for the filter.

A live Hy-Memory write is a separate step. It waits on an embedding model id.

## Open items

- Hy-Memory is not installed in `.venv`.
- On 2026-10-17 the OpenRouter `/api/v1/models` catalog returned 470 models. None had an embedding id. `openai/text-embedding-3-small`, the id in `swarm_shared_memory.py`, was not in that catalog. The index adapter must not use an unverified embedding id.
- context-mode is built and is the trace store. This design does not call it yet.
- No usefulness downranking yet. The recall log is the place that later work will read.
- The workspace root has no git repository. Do not commit `.env`.
