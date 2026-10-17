# Swarm decision memory implementation plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Agents bind a shared fact only through a decision record whose risk bar, dissent, and evidence checks are enforced in code, with SQLite as the record.

**Architecture:** `swarm_memory` classifies a write, applies `risk_scaled_bar` and `agent_confidence_bind`, and commits the result to SQLite before any search index write. Recall drops index hits that are not the current binding. Hy-Memory is the production index and is not called until an embedding model id is verified.

**Tech Stack:** Python 3.14, SQLite, pytest. Decision runner `liquid/lfm-2.5-24b-a2b`. Worker `deepseek/deepseek-v4.1-flash-1017`. Design: `docs/plans/2026-10-17-swarm-decision-memory-design.md`.

---

## Preconditions

- Work from `/Volumes/WS4TB/Swarm_Mem_Share`.
- `.gitignore` already ignores `.env`, `.venv/`, and `*.sqlite`. Confirm with `git status` before every commit. `.env` must not appear.
- The workspace root was not a git repository when this plan was written. Before the first commit: `git init`, then `git status`. If `.env` is listed, stop.
- Tests use the venv: `/Volumes/WS4TB/Swarm_Mem_Share/.venv/bin/python -m pytest`.
- Do not install a substitute embedding model. Do not call OpenRouter from tests.

## Task 1: Risk bar

**Files:**
- Create: `swarm_memory/__init__.py`
- Create: `swarm_memory/risk.py`
- Test: `tests/test_risk.py`

**Step 1: Write the failing test**

```python
from swarm_memory.risk import classify


def test_clinical_key_floors_at_high():
    result = classify(fact_key="genome.caller", declared_floor=None, action=None, multi_role=False, has_prior=False, model_class=None)
    assert result.final_class == "high"
    assert result.bar == 0.92


def test_model_cannot_lower_a_clinical_key():
    result = classify(fact_key="clinical.marker", declared_floor=None, action=None, multi_role=False, has_prior=False, model_class="low")
    assert result.final_class == "high"
    assert result.bar == 0.92


def test_model_raise_is_one_step():
    result = classify(fact_key="stack.web", declared_floor=None, action=None, multi_role=False, has_prior=False, model_class="critical")
    assert result.final_class == "high"
    assert result.bar == 0.92


def test_prior_binding_raises_to_high():
    result = classify(fact_key="style.quote", declared_floor="low", action=None, multi_role=False, has_prior=True, model_class=None)
    assert result.final_class == "high"


def test_publish_action_is_critical():
    result = classify(fact_key="note", declared_floor=None, action="publish", multi_role=False, has_prior=False, model_class=None)
    assert result.final_class == "critical"
    assert result.bar == 0.97


def test_declared_low_stays_low_without_a_raise():
    result = classify(fact_key="style.quote", declared_floor="low", action=None, multi_role=False, has_prior=False, model_class=None)
    assert result.final_class == "low"
    assert result.bar == 0.60
```

**Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_risk.py -v`

Expected: FAIL, `swarm_memory` is not a package.

**Step 3: Implement the table**

`swarm_memory/__init__.py` is empty.

`swarm_memory/risk.py`:

```python
from dataclasses import dataclass

ORDER = ("low", "standard", "high", "critical")
BARS = {"low": 0.60, "standard": 0.80, "high": 0.92, "critical": 0.97}
HIGH_PREFIXES = ("clinical.", "genome.", "identity.", "auth.")
CRITICAL_ACTIONS = frozenset({"patient_facing", "delete", "publish"})


@dataclass(frozen=True)
class RiskResult:
    final_class: str
    bar: float
    floor: str


def _rank(name: str) -> int:
    return ORDER.index(name)


def _one_step_up(name: str) -> str:
    return ORDER[min(_rank(name) + 1, len(ORDER) - 1)]


def _floor(fact_key: str, declared_floor: str | None, action: str | None) -> str:
    if declared_floor == "critical" or action in CRITICAL_ACTIONS:
        return "critical"
    if declared_floor == "high" or fact_key.startswith(HIGH_PREFIXES):
        return "high"
    if declared_floor == "low":
        return "low"
    return "standard"


def classify(fact_key: str, declared_floor: str | None, action: str | None, multi_role: bool, has_prior: bool, model_class: str | None) -> RiskResult:
    floor = _floor(fact_key, declared_floor, action)
    current = floor
    if multi_role or has_prior:
        if _rank(current) < _rank("high"):
            current = "high"
    if model_class in ORDER and _rank(model_class) > _rank(current):
        current = _one_step_up(current)
    return RiskResult(final_class=current, bar=BARS[current], floor=floor)
```

**Step 4: Run the test and confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_risk.py -v`

Expected: 6 passed.

**Step 5: Commit**

```bash
git add .gitignore swarm_memory/__init__.py swarm_memory/risk.py tests/test_risk.py docs/plans/2026-10-17-swarm-decision-memory-design.md docs/plans/2026-10-17-swarm-decision-memory.md
git status
git commit -m "feat: add risk-scaled decision bar"
```

`git status` must not list `.env`.

## Task 2: Bind rules

**Files:**
- Create: `swarm_memory/decide.py`
- Test: `tests/test_decide.py`

**Step 1: Write the failing test**

```python
from swarm_memory.decide import Proposal, evaluate


def _proposal(**kwargs):
    base = dict(
        fact_key="stack.web",
        value="fastapi",
        agent_id="coder",
        evidence_ids=("e1",),
        write_class="fact",
        confidence=0.90,
        declared_floor=None,
        action=None,
        multi_role=False,
        model_class=None,
        rival_value=None,
        prior_decision_id=None,
        prior_value=None,
        prior_evidence_ids=(),
    )
    base.update(kwargs)
    return Proposal(**base)


def test_first_clinical_write_below_bar_stays_open():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.90))
    assert result.status == "open"
    assert result.bar == 0.92


def test_first_clinical_write_at_bar_binds():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.92))
    assert result.status == "bound"
    assert result.value == "fastapi"


def test_missing_confidence_stays_open():
    result = evaluate(_proposal(confidence=None))
    assert result.status == "open"
    assert result.reason == "missing_confidence"


def test_missing_fact_key_is_an_experience():
    result = evaluate(_proposal(fact_key=None, write_class="fact"))
    assert result.status == "stored_experience"


def test_trace_is_refused():
    result = evaluate(_proposal(write_class="trace"))
    assert result.status == "ignored_trace"


def test_same_evidence_cannot_flip():
    result = evaluate(_proposal(
        value="flask",
        rival_value="fastapi",
        evidence_ids=("e1",),
        prior_decision_id="d1",
        prior_value="fastapi",
        prior_evidence_ids=("e1",),
        confidence=0.99,
    ))
    assert result.status == "rejected"
    assert result.reason == "same_evidence"


def test_new_evidence_can_supersede_when_the_bar_is_met():
    result = evaluate(_proposal(
        value="flask",
        rival_value="fastapi",
        evidence_ids=("e1", "e2"),
        prior_decision_id="d1",
        prior_value="fastapi",
        prior_evidence_ids=("e1",),
        confidence=0.95,
    ))
    assert result.status == "bound"
    assert result.supersedes == "d1"
    assert result.dissent == "fastapi"


def test_contested_write_must_cite_both_values():
    result = evaluate(_proposal(
        value="flask",
        evidence_ids=("e2",),
        rival_value=None,
        prior_decision_id="d1",
        prior_value="fastapi",
        prior_evidence_ids=("e1",),
        confidence=0.95,
    ))
    assert result.status == "open"
    assert result.reason == "missing_rival"
```

**Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_decide.py -v`

Expected: FAIL, `swarm_memory.decide` cannot be imported.

**Step 3: Implement the rules**

```python
import math
from dataclasses import dataclass

from swarm_memory.risk import classify


@dataclass(frozen=True)
class Proposal:
    fact_key: str | None
    value: str
    agent_id: str
    evidence_ids: tuple[str, ...]
    write_class: str
    confidence: float | None
    declared_floor: str | None
    action: str | None
    multi_role: bool
    model_class: str | None
    rival_value: str | None
    prior_decision_id: str | None
    prior_value: str | None
    prior_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    final_class: str | None = None
    bar: float | None = None
    confidence: float | None = None
    value: str | None = None
    dissent: str | None = None
    supersedes: str | None = None


def evaluate(proposal: Proposal) -> Decision:
    if proposal.write_class == "trace":
        return Decision(status="ignored_trace", reason="trace")
    if proposal.write_class == "experience" or proposal.fact_key is None:
        return Decision(status="stored_experience", reason="experience")
    if proposal.write_class == "preference":
        return Decision(status="bound", reason="preference_recency", value=proposal.value, final_class="low", bar=None, confidence=proposal.confidence)
    risk = classify(
        fact_key=proposal.fact_key,
        declared_floor=proposal.declared_floor,
        action=proposal.action,
        multi_role=proposal.multi_role,
        has_prior=proposal.prior_decision_id is not None,
        model_class=proposal.model_class,
    )
    if proposal.confidence is None or isinstance(proposal.confidence, bool) or not isinstance(proposal.confidence, (int, float)) or not math.isfinite(proposal.confidence):
        return Decision(status="open", reason="missing_confidence", final_class=risk.final_class, bar=risk.bar)
    if proposal.prior_decision_id is not None:
        if proposal.rival_value is None:
            return Decision(status="open", reason="missing_rival", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
        if set(proposal.evidence_ids).issubset(set(proposal.prior_evidence_ids)):
            return Decision(status="rejected", reason="same_evidence", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
    if float(proposal.confidence) < risk.bar:
        return Decision(status="open", reason="below_bar", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
    return Decision(
        status="bound",
        reason="cleared_bar",
        final_class=risk.final_class,
        bar=risk.bar,
        confidence=float(proposal.confidence),
        value=proposal.value,
        dissent=proposal.prior_value,
        supersedes=proposal.prior_decision_id,
    )
```

**Step 4: Run the test and confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_decide.py tests/test_risk.py -v`

Expected: all passed.

**Step 5: Commit**

```bash
git add swarm_memory/decide.py tests/test_decide.py
git commit -m "feat: bind facts only when the risk bar is met"
```

## Task 3: SQLite record

**Files:**
- Create: `swarm_memory/store.py`
- Test: `tests/test_store.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from swarm_memory.store import Store


def test_binding_round_trip(tmp_path: Path):
    store = Store(tmp_path / "memory.sqlite")
    store.save_candidate("c1", "stack.web", "fastapi", "coder", ["e1"], "fact")
    store.save_instance(
        instance_id="d1",
        fact_key="stack.web",
        status="bound",
        final_class="standard",
        bar=0.80,
        confidence=0.90,
        value="fastapi",
        dissent=None,
        evidence_ids=["e1"],
        agent_id="coder",
        supersedes=None,
    )
    store.bind("stack.web", "d1", "fastapi", "standard")
    current = store.current_binding("stack.web")
    assert current["decision_id"] == "d1"
    assert current["value"] == "fastapi"
    assert store.instance("d1")["index_dirty"] == 1
```

**Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`

Expected: FAIL, `swarm_memory.store` cannot be imported.

**Step 3: Implement the store**

Use the standard library `sqlite3`. Create tables `candidates`, `decision_instances`, and `fact_bindings` on first open. `save_instance` sets `index_dirty` to 1 for status `bound` and 0 otherwise. `bind` upserts `fact_bindings`. `mark_indexed(decision_id)` sets `index_dirty` to 0. `current_binding` returns `None` when the key is absent.

Columns for `decision_instances`: `id`, `fact_key`, `status`, `final_class`, `bar`, `confidence`, `value`, `dissent`, `evidence_json`, `agent_id`, `supersedes`, `index_dirty`, `created_at`.

`created_at` is UTC ISO-8601 from `datetime.now(timezone.utc).isoformat()`.

**Step 4: Run the test and confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`

Expected: 1 passed.

**Step 5: Commit**

```bash
git add swarm_memory/store.py tests/test_store.py
git commit -m "feat: store decision bindings in sqlite"
```

## Task 4: Role card budget

**Files:**
- Create: `swarm_memory/card.py`
- Test: `tests/test_card.py`

**Step 1: Write the failing test**

```python
from swarm_memory.card import render_card


def test_bindings_come_before_open_conflicts_and_the_card_stops_at_2000_chars():
    bindings = [{"fact_key": "stack.web", "value": "fastapi", "decision_id": "d1", "confidence": 0.9}]
    opens = [{"fact_key": f"k{i}", "values": ["a", "b"]} for i in range(100)]
    text = render_card(bindings, opens, limit=2000)
    assert text.startswith("BINDINGS")
    assert "stack.web" in text
    assert len(text) <= 2000
```

**Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_card.py -v`

Expected: FAIL, `swarm_memory.card` cannot be imported.

**Step 3: Implement the card**

`render_card` writes a `BINDINGS` section, then an `OPEN` section. It stops appending lines when the next line would pass `limit`. The sections headers are kept even when the body is empty: `BINDINGS` then `OPEN`.

**Step 4: Run the test and confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_card.py -v`

Expected: 1 passed.

**Step 5: Commit**

```bash
git add swarm_memory/card.py tests/test_card.py
git commit -m "feat: render a bounded role card"
```

## Task 5: Recall filter

**Files:**
- Create: `swarm_memory/recall.py`
- Test: `tests/test_recall.py`

**Step 1: Write the failing test**

```python
from swarm_memory.recall import filter_hits


def test_stale_and_unidentified_hits_are_dropped():
    hits = [
        {"decision_id": "d1", "fact_key": "stack.web", "text": "current"},
        {"decision_id": "d0", "fact_key": "stack.web", "text": "old"},
        {"decision_id": None, "fact_key": "stack.web", "text": "no id"},
    ]
    bindings = {"stack.web": "d1"}
    kept = filter_hits(hits, bindings, limit=5, char_budget=2000)
    assert [hit["text"] for hit in kept] == ["current"]
```

**Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_recall.py -v`

Expected: FAIL, `swarm_memory.recall` cannot be imported.

**Step 3: Implement the filter**

Keep a hit when `decision_id` equals `bindings[fact_key]`. Stop at `limit` hits or at `char_budget` characters of `text`. The hit list passed in is test input. It is not a memory store.

**Step 4: Run the test and confirm it passes**

Run: `.venv/bin/python -m pytest tests/test_recall.py -v`

Expected: 1 passed.

**Step 5: Commit**

```bash
git add swarm_memory/recall.py tests/test_recall.py
git commit -m "feat: drop recall hits that are not the current binding"
```

## Task 6: Remember and recall service

**Files:**
- Create: `swarm_memory/service.py`
- Test: `tests/test_service.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from swarm_memory.service import MemoryService


class RecordingIndex:
    """Test double. Records index attempts. It is not a memory store."""

    def __init__(self):
        self.sentences = []

    def write_bound_sentence(self, decision_id, fact_key, text):
        self.sentences.append((decision_id, fact_key, text))


def test_open_conflict_does_not_index(tmp_path: Path):
    index = RecordingIndex()
    service = MemoryService(tmp_path / "memory.sqlite", index)
    result = service.remember(
        fact_key="genome.caller",
        value="dragen",
        agent_id="coder",
        evidence_ids=["e1"],
        write_class="fact",
        confidence=0.50,
    )
    assert result.status == "open"
    assert index.sentences == []
    assert service.store.current_binding("genome.caller") is None


def test_cleared_bar_indexes_after_sqlite_commit(tmp_path: Path):
    index = RecordingIndex()
    service = MemoryService(tmp_path / "memory.sqlite", index)
    result = service.remember(
        fact_key="style.quote",
        value="concise",
        agent_id="writer",
        evidence_ids=["e1"],
        write_class="fact",
        confidence=0.90,
        declared_floor="low",
    )
    assert result.status == "bound"
    assert index.sentences[0][1] == "style.quote"
    assert service.store.instance(result.decision_id)["index_dirty"] == 0
```

**Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_service.py -v`

Expected: FAIL, `swarm_memory.service` cannot be imported.

**Step 3: Implement the service**

`remember` builds a `Proposal`. When a current binding exists, set `prior_decision_id`, `prior_value`, `prior_evidence_ids`, and `rival_value` from that binding. Call `evaluate`. Persist a candidate. On `bound`, `save_instance`, `bind`, then `index.write_bound_sentence`. On index success, `mark_indexed`. On index exception, leave `index_dirty` at 1 and still return the bound decision. On `open` or `rejected`, save the instance and do not call the index. On `ignored_trace` and `stored_experience`, do not call the index. `stored_experience` still saves a candidate with that class.

`recall(query, hits)` calls `filter_hits` with bindings loaded from SQLite and appends a row to `recall_log` (`id`, `query`, `returned_ids_json`, `created_at`).

Generate decision ids with `uuid4`.

**Step 4: Run the test and confirm it passes**

Run: `.venv/bin/python -m pytest tests -v`

Expected: all tests passed. Report the exact count.

**Step 5: Commit**

```bash
git add swarm_memory/service.py tests/test_service.py
git commit -m "feat: remember through the decision record before indexing"
```

## Task 7: Index port without a live embedder

**Files:**
- Create: `swarm_memory/index.py`
- Test: `tests/test_index.py`

**Step 1: Write the failing test**

```python
import pytest

from swarm_memory.index import HyMemoryIndex


def test_index_refuses_to_construct_without_a_verified_embedding_model():
    with pytest.raises(RuntimeError, match="embedding model"):
        HyMemoryIndex(embedding_model=None)
```

**Step 2: Run the test and confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_index.py -v`

Expected: FAIL, `swarm_memory.index` cannot be imported.

**Step 3: Implement the guard**

```python
class HyMemoryIndex:
    def __init__(self, embedding_model: str | None):
        if not embedding_model:
            raise RuntimeError("Hy-Memory index requires a verified OpenRouter embedding model id")
        self.embedding_model = embedding_model

    def write_bound_sentence(self, decision_id: str, fact_key: str, text: str) -> None:
        raise RuntimeError("Hy-Memory index is not installed in this environment")
```

Do not import `hy_memory` in this task. The package was not installed when the plan was written.

**Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest tests -v`

Expected: all passed. Report the exact count.

**Step 5: Commit**

```bash
git add swarm_memory/index.py tests/test_index.py
git commit -m "feat: refuse an unverified embedding model for the index"
```

## Out of this plan

- Pointing `SwarmAgent` in `swarm_shared_memory.py` at `MemoryService`.
- A live Hy-Memory install and a live OpenRouter decision call.
- context-mode calls.
- Agno team wiring.
- Usefulness downranking from the recall log.

## Embedding gate

On 2026-10-17, `GET https://openrouter.ai/api/v1/models` returned 470 models and no embedding id. `openai/text-embedding-3-small` was absent. Before Task 7 is replaced with a live adapter, look up the catalog again and ask the user to pick an id. Do not reuse an id from memory.
