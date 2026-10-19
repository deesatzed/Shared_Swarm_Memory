# Swarm Memory Comparison: Run File (GOAL_RUN_EXP.md)

> **For Claude:** REQUIRED SUB-SKILL: use superpowers:executing-plans (or the executing-plans skill) to carry out this plan task by task. Use test-driven development for every behavior change.

**Goal:** Measure whether our shared memory app stops agents from acting on stale or wrong exact values (M1, target zero), and whether it answers as well as the alternatives with less context (M2). The test runs five role agents through real repo history in three swarms: full context, search only, and our memory.

**Architecture:**
- `swarm_memory/` gains the approved additions: a key registry, harness captures, the capture rule for high and critical keys (replacing the two-agent rule), decision-model cases, read-back and re-check.
- `swarm_compare/` is the harness. It holds the OpenRouter client with a spending stop and a call log, the two real tasks, the three swarms, scoring, a resumable runner and a summary report.

**Tech stack:** Python 3.14.8, SQLite, httpx 0.28.1, pytest 9.1.1, all already in `/Volumes/WS4TB/Swarm_Mem_Share/.venv`. Models are listed in `swarm_compare/models.py` (user's choice, 2026-10-19).

**Design:** [docs/plans/2026-10-19-swarm-comparison-design.md](docs/plans/2026-10-19-swarm-comparison-design.md), approved section by section on 2026-10-19.

**How this plan was checked:** On 2026-10-19 every file in this plan was written into a scratch copy of this branch and run there:
- Without `--run-live`: 122 passed, 4 skipped. The skipped 4 are the live model checks.
- The answer-key tests ran against this repo's real git history.
- The runner refused to start without a spending limit, with exit code 3.
- No model was called.
- The runner's turn loop is exercised for the first time by the trial run (Task 13).

---

## Plain version

Five AI agents (planner, coder, tester, reviewer, release) read real versions of this project's documents in date order. They do it three times:
1. Each agent sees everything that came before.
2. Agents share a search box.
3. Agents share our memory app.

At the end every agent answers questions whose right answers come from git. We count:
- tokens and cost, as reported by the provider
- correct answers
- how often an agent relied on an out-of-date value

The build comes first and costs nothing. Paid model calls start only after the user sets a spending limit. After one trial run, the work stops so the user can review it.

## Workspace and rules

- **Work only here:** `/Volumes/WS4TB/Swarm_Mem_Share_exp`, branch `feat/swarm-comparison`. This is a separate git worktree of the main repo.
  - The main checkout `/Volumes/WS4TB/Swarm_Mem_Share` is on another session's branch, `aether-goal-1-7`. Do not switch it, reset it, or commit there.
- **Python:** `PY=/Volumes/WS4TB/Swarm_Mem_Share/.venv/bin/python`.
- **Test command:** `cd /Volumes/WS4TB/Swarm_Mem_Share_exp && $PY -B -m pytest tests -q -p no:cacheprovider`.
- **After a restart or compaction:** before anything else, read this file's step tracker and progress log, then `git -C /Volumes/WS4TB/Swarm_Mem_Share_exp log --oneline -15`.
- **Test-driven development:** write the test, run it and see it fail for the stated reason, write the code, then run the whole suite. Report exact counts.
- **Commits:** commit after each task, staging only the files the task names. Never use `git add -A` or `git add .`. End commit messages with the attribution line your session requires.
- **Never:** push, merge, open a pull request, delete a branch or force anything. Each of these needs a new instruction from the user.
- **Credentials:**
  - The key comes only from `OPENROUTER_API_KEY` in `SWARM_EXP_CREDENTIALS_FILE` (default `/Volumes/WS4TB/merged.env`).
  - Never `cat`, `source`, print, or grep that file.
  - Never stage `.env`, `merged.env` or anything under `swarm_compare/runs/`.
- **Models:** use only the ids in `swarm_compare/models.py`. If one fails with HTTP 404, stop and ask the user. Do not substitute another model.
- **Real data only:** tasks come from this repo's git history.
  - Unit tests pass explicit inputs to pure functions, as the existing suite does.
  - The only test double is `RecordingIndex`, which already exists in `tests/test_service.py` and is reused in `tests/test_swarms.py`. It records index writes and is not a memory store.
  - No fake HTTP transport, no recorded or replayed model responses, no simulated runs.
- **Repeated failures:** if the same failure survives a second fix attempt, stop patching. List the plausible causes, add logging that would confirm the likeliest one or two, then fix. Record the error, cause and fix in `ERROR_LOG.md` at the repo root (create it if missing) and commit it.
- **Reporting:** report only measured numbers: test counts, provider-reported tokens and cost, scores from the result files. No estimates of time or cost.

## Inputs only the user can give

| Input | Blocks | How |
|---|---|---|
| Spending limit in USD | Tasks 12 and later (every paid call) | `export SWARM_EXP_SPEND_LIMIT_USD=<amount>`. The limit covers everything in `swarm_compare/runs/calls.jsonl`, which includes live checks and all runs so far. |
| Go-ahead after the trial run | Task 14 | The user reviews the trial results and says so |

If the limit is not set when Task 12 is reached, stop. Tell the user that Tasks 1 to 11 are done, with test counts, and that paid calls wait on `SWARM_EXP_SPEND_LIMIT_USD`.

## Step tracker

| Task | Deliverable | Status | Evidence |
|---|---|---|---|
| 0 | Start-up checks | Not started | |
| 1 | Whole-word matching | Not started | |
| 2 | Key registry | Not started | |
| 3 | Capture rule replaces the two-agent rule | Not started | |
| 4 | Decision-model cases and answers | Not started | |
| 5 | Vector index | Not started | |
| 6 | OpenRouter client safety | Not started | |
| 7 | Real tasks and answer key | Not started | |
| 8 | Reply blocks and value scoring | Not started | |
| 9 | Prompts and the three swarms | Not started | |
| 10 | Scoring, report, runner | Not started | |
| 11 | Live-check tests (not run) | Not started | |
| 12 | Live checks (needs spending limit) | Not started | |
| 13 | Trial run, then stop for the user | Not started | |
| 14 | Full run (needs the user's go-ahead) | Not started | |

---

## Task 0: Start-up checks

**Files:** modify `.gitignore`.

**Step 1: confirm the place and the baseline**

```sh
cd /Volumes/WS4TB/Swarm_Mem_Share_exp
git branch --show-current          # expect: feat/swarm-comparison
git status --short                 # expect: nothing
$PY -B -m pytest tests -q -p no:cacheprovider   # expect: 54 passed
git cat-file -e ad5c20a667948e58a6667f928bf79b1b94d73786 && echo reachable   # task B needs this commit
```

If the branch is wrong, the tree is dirty, or the count is not 54, stop and report what you found.

**Step 2: ignore run files**

Append one line to `.gitignore`:

```
swarm_compare/runs/
```

**Step 3: commit**

```sh
git add .gitignore
git commit -m "chore: ignore swarm comparison run files"
```

---

## Task 1: Whole-word matching

Scoring, read-back, re-check and the capture rule all use one matching rule: whole words, case and spacing ignored.

**Files:**
- Test: `tests/test_text.py`
- Create: `swarm_memory/text.py`

**Step 1: write the failing test** `tests/test_text.py`:

````python
from swarm_memory.text import contains_words


def test_match_ignores_case_and_spacing():
    assert contains_words("Tests:  54 PASSED today", "54 passed")


def test_part_of_a_longer_number_does_not_match():
    assert not contains_words("540 passed", "54")
    assert not contains_words("0.920", "0.92")


def test_a_value_inside_a_path_matches():
    assert contains_words("origin is https://github.com/deesatzed/Shared_Swarm_Memory.git", "deesatzed/Shared_Swarm_Memory")


def test_an_empty_needle_never_matches():
    assert not contains_words("anything", "  ")
````

**Step 2:** run `$PY -B -m pytest tests/test_text.py -q -p no:cacheprovider`. Expected: fails with `ModuleNotFoundError: No module named 'swarm_memory.text'`.

**Step 3: write** `swarm_memory/text.py`:

````python
import re


def normalize(text: str) -> str:
    return " ".join(str(text).split()).casefold()


def contains_words(haystack: str, needle: str) -> bool:
    """True when needle appears in haystack as whole words, ignoring case and spacing."""
    target = normalize(needle)
    if not target:
        return False
    pattern = r"(?<!\w)" + re.escape(target) + r"(?!\w)"
    return re.search(pattern, normalize(haystack)) is not None
````

**Step 4:** run the whole suite. Expected: **58 passed**.

**Step 5:** `git add tests/test_text.py swarm_memory/text.py && git commit -m "feat: match values as whole words"`

---

## Task 2: Key registry

**Files:**
- Create: `swarm_compare/__init__.py` (empty)
- Create: `swarm_compare/keys.json`
- Test: `tests/test_registry.py`
- Create: `swarm_memory/registry.py`

**Step 1:** create the empty `swarm_compare/__init__.py`, then `swarm_compare/keys.json`.

Notes on the key choices:
- `roles` decides whose role card shows the key.
- More than one role raises the class to high (existing rule in `risk.py`).
- `model.decision` and `rule.bar_high` are high.
- `build.tests_passing`, `repo.remote` and `rule.evidence_reason` are standard for a first value. Replacing any bound value is high (existing rule).

````json
{
  "version": 1,
  "keys": {
    "build.tests_passing": {
      "type": "integer",
      "unit": "tests",
      "risk_floor": "standard",
      "sensitivity": "public",
      "shelf_life": "until the next test run",
      "roles": ["tester"],
      "description": "Number of main-suite tests that pass"
    },
    "repo.remote": {
      "type": "string",
      "unit": null,
      "risk_floor": "standard",
      "sensitivity": "public",
      "shelf_life": "until changed",
      "roles": ["release"],
      "description": "The project's git remote, or that none exists"
    },
    "model.decision": {
      "type": "string",
      "unit": null,
      "risk_floor": "high",
      "sensitivity": "public",
      "shelf_life": "until changed",
      "roles": ["coder", "reviewer"],
      "description": "Model id that makes routine decisions"
    },
    "rule.bar_high": {
      "type": "number",
      "unit": "confidence",
      "risk_floor": "high",
      "sensitivity": "public",
      "shelf_life": "until changed",
      "roles": ["reviewer"],
      "description": "Confidence a high-risk fact needs to bind"
    },
    "rule.evidence_reason": {
      "type": "string",
      "unit": null,
      "risk_floor": "standard",
      "sensitivity": "public",
      "shelf_life": "until changed",
      "roles": ["coder"],
      "description": "Status reason a high or critical fact gets when it lacks the required evidence"
    }
  }
}
````

**Step 2: write the failing test** `tests/test_registry.py`:

````python
import json
from pathlib import Path

import pytest

from swarm_memory.registry import Registry

KEYS = Path(__file__).resolve().parents[1] / "swarm_compare" / "keys.json"


def test_the_experiment_registry_loads_every_key():
    registry = Registry.load(KEYS)
    assert registry.get("model.decision").risk_floor == "high"
    assert registry.get("build.tests_passing").roles == ("tester",)
    assert registry.get("unknown.key") is None
    assert registry.get(None) is None


def test_keys_for_a_role_follow_the_roles_field():
    registry = Registry.load(KEYS)
    assert "model.decision" in registry.keys_for_role("coder")
    assert "model.decision" in registry.keys_for_role("reviewer")
    assert "model.decision" not in registry.keys_for_role("tester")


def test_an_unknown_risk_floor_is_refused(tmp_path: Path):
    path = tmp_path / "keys.json"
    path.write_text(json.dumps({"keys": {"a.b": {
        "type": "string", "risk_floor": "medium", "sensitivity": "public",
        "shelf_life": "until changed", "roles": ["coder"], "description": "x",
    }}}))
    with pytest.raises(ValueError, match="risk floor"):
        Registry.load(path)
````

**Step 3:** run `$PY -B -m pytest tests/test_registry.py -q -p no:cacheprovider`. Expected: fails with `No module named 'swarm_memory.registry'`.

**Step 4: write** `swarm_memory/registry.py`:

````python
import json
from dataclasses import dataclass
from pathlib import Path

RISK_FLOORS = ("low", "standard", "high", "critical")


@dataclass(frozen=True)
class KeySpec:
    key: str
    type: str
    unit: str | None
    risk_floor: str
    sensitivity: str
    shelf_life: str
    roles: tuple[str, ...]
    description: str


class Registry:
    def __init__(self, specs: dict[str, KeySpec]):
        self._specs = specs

    @classmethod
    def load(cls, path: Path | str) -> "Registry":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        specs: dict[str, KeySpec] = {}
        for key, entry in raw["keys"].items():
            if entry["risk_floor"] not in RISK_FLOORS:
                raise ValueError(f"{key}: unknown risk floor {entry['risk_floor']!r}")
            if not entry["roles"]:
                raise ValueError(f"{key}: no roles")
            specs[key] = KeySpec(
                key=key,
                type=entry["type"],
                unit=entry.get("unit"),
                risk_floor=entry["risk_floor"],
                sensitivity=entry["sensitivity"],
                shelf_life=entry["shelf_life"],
                roles=tuple(entry["roles"]),
                description=entry["description"],
            )
        return cls(specs)

    def get(self, key: str | None) -> KeySpec | None:
        if key is None:
            return None
        return self._specs.get(key)

    def keys_for_role(self, role: str) -> list[str]:
        return [key for key, spec in self._specs.items() if role in spec.roles]

    def specs(self) -> list[KeySpec]:
        return list(self._specs.values())
````

**Step 5:** run the whole suite. Expected: **61 passed**.

**Step 6:** `git add swarm_compare/__init__.py swarm_compare/keys.json tests/test_registry.py swarm_memory/registry.py && git commit -m "feat: declare fact keys in a registry"`

---

## Task 3: Capture rule replaces the two-agent rule

This is the approved change to the 2026-10-17 evidence gate. High and critical facts now need three things:
- a harness capture whose content contains the value
- an approval, for which `gemini-4-argon` is used in the harness
- a confidence, which comes from `d1-ultra` in the harness

These are also added in this task:
- **Registry floors:** when the service has a registry, an undeclared key becomes a note.
- **Binding state:** a binding is either `current` or `needs_recheck`.
- **Re-check.**
- **Role cards** built from the store.
- **Read-back.**
- **A reason on every `RememberResult`.**

The tests of the two-agent rule are rewritten, not silently deleted. The commit message in Step 11 lists them:
- `test_decide.py`: six tests (`standard_key_binds_without_independent_evidence`, `high_key_with_no_independent_evidence_stays_open`, `high_key_with_one_independent_evidence_stays_open`, `high_key_with_two_evidence_ids_from_one_agent_stays_open`, `critical_key_needs_two_agents_too`, `replacing_a_standard_value_counts_as_high_and_needs_evidence`)
- `test_service.py`: five tests (`high_key_with_unknown_evidence_ids_stays_open`, `high_key_does_not_count_the_proposers_own_experience`, `high_key_with_two_experiences_from_one_other_agent_stays_open`, `high_key_with_two_independent_agents_binds`, `a_fact_candidate_id_is_not_evidence`), plus `preference_cannot_replace_a_bound_fact`, which now binds from a capture

`Store.experience_agents` is removed because nothing uses it any more.

**Files:**
- Test (replace whole file): `tests/test_decide.py`, `tests/test_service.py`, `tests/test_store.py`
- Create: `swarm_memory/readback.py`
- Modify (replace whole file): `swarm_memory/decide.py`, `swarm_memory/store.py`, `swarm_memory/service.py`

**Step 1: replace** `tests/test_decide.py` with:

````python
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
        capture_has_value=False,
        approved=None,
        blocked_reason=None,
    )
    base.update(kwargs)
    return Proposal(**base)


def test_first_clinical_write_below_bar_stays_open():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.90))
    assert result.status == "open"
    assert result.bar == 0.92


def test_first_clinical_write_at_bar_binds():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.92, capture_has_value=True, approved=True))
    assert result.status == "bound"
    assert result.value == "fastapi"


def test_missing_confidence_stays_open():
    result = evaluate(_proposal(confidence=None))
    assert result.status == "open"
    assert result.reason == "missing_confidence"


def test_nan_confidence_stays_open():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=float("nan")))
    assert result.status == "open"
    assert result.reason == "missing_confidence"


def test_infinite_confidence_stays_open():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=float("inf")))
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
        capture_has_value=True,
        approved=True,
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


def test_preference_on_a_fact_key_is_rejected():
    result = evaluate(_proposal(
        fact_key="genome.caller",
        write_class="preference",
        confidence=0.99,
    ))
    assert result.status == "rejected"
    assert result.reason == "preference_key"


def test_preference_without_finite_confidence_stays_open():
    result = evaluate(_proposal(
        fact_key="preference.tone",
        write_class="preference",
        confidence=float("nan"),
    ))
    assert result.status == "open"
    assert result.reason == "missing_confidence"


def test_preference_replaces_an_older_preference_without_the_fact_bar():
    result = evaluate(_proposal(
        fact_key="preference.tone",
        value="warm",
        write_class="preference",
        confidence=0.5,
        evidence_ids=("e1",),
        prior_decision_id="d1",
        prior_value="cool",
        prior_evidence_ids=("e1",),
    ))
    assert result.status == "bound"
    assert result.dissent == "cool"
    assert result.supersedes == "d1"


def test_standard_key_binds_without_a_capture():
    result = evaluate(_proposal(confidence=0.85))
    assert result.status == "bound"


def test_high_key_without_a_capture_stays_open():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.99, approved=True))
    assert result.status == "open"
    assert result.reason == "no_capture"


def test_high_key_with_a_capture_but_no_approval_stays_open():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.99, capture_has_value=True))
    assert result.status == "open"
    assert result.reason == "not_approved"


def test_high_key_with_a_refused_approval_stays_open():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.99, capture_has_value=True, approved=False))
    assert result.status == "open"
    assert result.reason == "not_approved"


def test_high_key_with_a_capture_and_approval_binds():
    result = evaluate(_proposal(fact_key="genome.caller", confidence=0.99, capture_has_value=True, approved=True))
    assert result.status == "bound"


def test_critical_key_needs_a_capture_and_approval_too():
    missing = evaluate(_proposal(action="publish", confidence=0.99, approved=True))
    complete = evaluate(_proposal(action="publish", confidence=0.99, capture_has_value=True, approved=True))
    assert missing.status == "open"
    assert missing.reason == "no_capture"
    assert complete.status == "bound"


def test_replacing_a_standard_value_counts_as_high_and_needs_a_capture():
    result = evaluate(_proposal(
        value="flask",
        rival_value="fastapi",
        evidence_ids=("e1", "e2"),
        prior_decision_id="d1",
        prior_value="fastapi",
        prior_evidence_ids=("e1",),
        confidence=0.95,
        approved=True,
    ))
    assert result.status == "open"
    assert result.reason == "no_capture"


def test_a_blocked_reason_keeps_the_fact_open_with_that_reason():
    result = evaluate(_proposal(confidence=None, blocked_reason="decision_model_unavailable"))
    assert result.status == "open"
    assert result.reason == "decision_model_unavailable"
    assert result.bar == 0.80


def test_confidence_above_one_stays_open():
    result = evaluate(_proposal(confidence=1.5))
    assert result.status == "open"
    assert result.reason == "confidence_out_of_range"


def test_negative_confidence_stays_open():
    result = evaluate(_proposal(confidence=-0.1))
    assert result.status == "open"
    assert result.reason == "confidence_out_of_range"
````

**Step 2: replace** `tests/test_store.py` with:

````python
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


def test_capture_round_trip(tmp_path: Path):
    store = Store(tmp_path / "memory.sqlite")
    store.save_capture("A-1", "HANDOFF.md", "6136de0", "40 passed", "hash")
    assert store.capture("A-1")["content"] == "40 passed"
    assert store.capture("A-9") is None


def test_a_binding_that_needs_recheck_is_not_current(tmp_path: Path):
    store = Store(tmp_path / "memory.sqlite")
    store.bind("stack.web", "d1", "fastapi", "standard")
    assert store.binding_ids() == {"stack.web": "d1"}
    store.mark_needs_recheck("stack.web")
    assert store.binding_ids() == {}
    assert store.bindings(["stack.web"]) == []
    assert store.current_binding("stack.web")["state"] == "needs_recheck"
````

**Step 3: replace** `tests/test_service.py` with:

````python
from pathlib import Path

from swarm_memory.registry import Registry
from swarm_memory.service import MemoryService

KEYS = Path(__file__).resolve().parents[1] / "swarm_compare" / "keys.json"


class RecordingIndex:
    """Test double. Records index attempts. It is not a memory store."""

    def __init__(self):
        self.sentences = []

    def write_bound_sentence(self, decision_id, fact_key, text):
        self.sentences.append((decision_id, fact_key, text))


def _experience(service, agent_id, text):
    return service.remember(
        fact_key=None,
        value=text,
        agent_id=agent_id,
        evidence_ids=[],
        write_class="experience",
        confidence=None,
    ).candidate_id


class BoomIndex:
    def write_bound_sentence(self, decision_id, fact_key, text):
        raise RuntimeError("index down")


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


def test_index_failure_keeps_the_binding_and_leaves_it_dirty(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", BoomIndex())
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
    assert service.store.current_binding("style.quote")["value"] == "concise"
    assert service.store.instance(result.decision_id)["index_dirty"] == 1


def test_recall_drops_a_stale_hit_and_logs_the_ids(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    bound = service.remember(
        fact_key="style.quote",
        value="concise",
        agent_id="writer",
        evidence_ids=["e1"],
        write_class="fact",
        confidence=0.90,
        declared_floor="low",
    )
    hits = [
        {"decision_id": bound.decision_id, "fact_key": "style.quote", "text": "current"},
        {"decision_id": "old", "fact_key": "style.quote", "text": "stale"},
    ]
    kept = service.recall("how should we write", hits)
    assert [hit["text"] for hit in kept] == ["current"]
    logged = service.store.latest_recall()
    assert logged["query"] == "how should we write"
    assert bound.decision_id in logged["returned_ids"]


def test_preference_cannot_replace_a_bound_fact(tmp_path: Path):
    index = RecordingIndex()
    service = MemoryService(tmp_path / "memory.sqlite", index)
    service.record_capture(capture_id="c1", source="run.log", ref="r1", content="caller: dragen")
    service.remember(
        fact_key="genome.caller",
        value="dragen",
        agent_id="coder",
        evidence_ids=["c1"],
        write_class="fact",
        confidence=0.95,
        approved=True,
    )
    service.remember(
        fact_key="genome.caller",
        value="unreviewed",
        agent_id="coder",
        evidence_ids=["e1"],
        write_class="preference",
        confidence=float("nan"),
    )
    assert service.store.current_binding("genome.caller")["value"] == "dragen"
    assert len(index.sentences) == 1


def test_the_same_fact_value_is_not_written_again(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    first = service.remember(
        fact_key="style.quote",
        value="concise",
        agent_id="writer",
        evidence_ids=["e1"],
        write_class="fact",
        confidence=0.90,
        declared_floor="low",
    )
    second = service.remember(
        fact_key="style.quote",
        value="concise",
        agent_id="writer",
        evidence_ids=["e2"],
        write_class="fact",
        confidence=0.99,
        declared_floor="low",
    )
    assert second.status == "duplicate"
    assert second.decision_id == first.decision_id
    assert service.store.instance(first.decision_id)["index_dirty"] == 0
    assert len(service.index.sentences) == 1


def test_the_same_preference_value_is_not_written_again(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    first = service.remember(
        fact_key="preference.tone",
        value="brief",
        agent_id="writer",
        evidence_ids=["e1"],
        write_class="preference",
        confidence=0.90,
    )
    second = service.remember(
        fact_key="preference.tone",
        value="brief",
        agent_id="writer",
        evidence_ids=["e2"],
        write_class="preference",
        confidence=0.20,
    )
    assert second.status == "duplicate"
    assert second.decision_id == first.decision_id
    assert len(service.index.sentences) == 1


def test_recall_puts_a_used_fact_ahead_of_an_ignored_one(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    ignored = service.remember(
        fact_key="style.quote",
        value="concise",
        agent_id="writer",
        evidence_ids=["e1"],
        write_class="fact",
        confidence=0.90,
        declared_floor="low",
    )
    used = service.remember(
        fact_key="style.form",
        value="bullets",
        agent_id="writer",
        evidence_ids=["e1"],
        write_class="fact",
        confidence=0.90,
        declared_floor="low",
    )
    for _ in range(8):
        service.note_use(ignored.decision_id, used=False)
        service.note_use(used.decision_id, used=True)
    hits = [
        {"decision_id": ignored.decision_id, "fact_key": "style.quote", "text": "quote"},
        {"decision_id": used.decision_id, "fact_key": "style.form", "text": "form"},
    ]
    kept = service.recall("style", hits)
    assert kept[0]["decision_id"] == used.decision_id


def _high_write(service, evidence_ids, approved=True):
    return service.remember(
        fact_key="genome.caller",
        value="dragen",
        agent_id="coder",
        evidence_ids=evidence_ids,
        write_class="fact",
        confidence=0.99,
        approved=approved,
    )


def test_an_experience_write_returns_its_candidate_id(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    assert _experience(service, "reviewer_a", "run log") is not None


def test_high_key_binds_when_a_capture_states_the_value_and_it_is_approved(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    service.record_capture(capture_id="c1", source="run.log", ref="r1", content="caller: dragen")
    result = _high_write(service, ["c1"])
    assert result.status == "bound"
    binding = service.store.current_binding("genome.caller")
    assert binding["value"] == "dragen"
    assert binding["capture_id"] == "c1"


def test_high_key_stays_open_when_the_cited_capture_lacks_the_value(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    service.record_capture(capture_id="c1", source="run.log", ref="r1", content="caller: gatk")
    result = _high_write(service, ["c1"])
    assert result.status == "open"
    assert result.reason == "no_capture"
    assert service.store.current_binding("genome.caller") is None


def test_high_key_with_an_unknown_capture_id_stays_open(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    assert _high_write(service, ["c9"]).status == "open"


def test_an_agent_experience_is_not_a_capture(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    note = _experience(service, "reviewer_a", "caller: dragen")
    assert _high_write(service, [note]).status == "open"


def test_high_key_without_approval_stays_open(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    service.record_capture(capture_id="c1", source="run.log", ref="r1", content="caller: dragen")
    assert _high_write(service, ["c1"], approved=None).reason == "not_approved"
    assert _high_write(service, ["c1"], approved=False).reason == "not_approved"


def test_an_undeclared_key_is_kept_as_a_note(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex(), Registry.load(KEYS))
    result = service.remember(
        fact_key="build.color", value="green", agent_id="coder", evidence_ids=[],
        write_class="fact", confidence=0.99,
    )
    assert result.status == "undeclared_key"
    assert result.decision_id is None
    assert service.store.current_binding("build.color") is None


def test_the_registry_floor_sets_the_class(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex(), Registry.load(KEYS))
    service.record_capture(capture_id="A-3", source="HANDOFF.md", ref="9318598", content="54 passed")
    standard = service.remember(
        fact_key="build.tests_passing", value="54", agent_id="tester", evidence_ids=[],
        write_class="fact", confidence=0.85,
    )
    high = service.remember(
        fact_key="model.decision", value="liquid/d1-ultra", agent_id="coder", evidence_ids=["A-3"],
        write_class="fact", confidence=0.99, approved=True,
    )
    assert standard.status == "bound"
    assert high.status == "open"
    assert service.store.instance(high.decision_id)["final_class"] == "high"


def _bind_from_source(service, content):
    service.record_capture(capture_id="A-1", source="HANDOFF.md", ref="6136de0", content=content)
    return service.remember(
        fact_key="build.tests_passing", value="40", agent_id="tester", evidence_ids=["A-1"],
        write_class="fact", confidence=0.85,
    )


def test_recheck_moves_a_value_the_source_no_longer_states(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex(), Registry.load(KEYS))
    bound = _bind_from_source(service, "40 passed")
    assert service.recheck("HANDOFF.md", "54 passed") == ["build.tests_passing"]
    assert service.store.current_binding("build.tests_passing")["state"] == "needs_recheck"
    assert bound.decision_id not in service.store.binding_ids().values()
    assert "build.tests_passing" not in service.role_card(["build.tests_passing"])


def test_recheck_keeps_a_value_the_source_still_states(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex(), Registry.load(KEYS))
    _bind_from_source(service, "40 passed")
    assert service.recheck("HANDOFF.md", "still 40 passed") == []
    assert service.recheck("OTHER.md", "54 passed") == []
    assert service.store.current_binding("build.tests_passing")["state"] == "current"


def test_role_card_lists_current_values_for_the_given_keys(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex(), Registry.load(KEYS))
    bound = _bind_from_source(service, "40 passed")
    card = service.role_card(["build.tests_passing"])
    assert "build.tests_passing value=40" in card
    assert bound.decision_id in card
    assert "build.tests_passing" not in service.role_card(["repo.remote"])


def test_read_back_reports_match_difference_recheck_and_unbound(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex(), Registry.load(KEYS))
    _bind_from_source(service, "40 passed")
    first = service.read_back([
        {"key": "build.tests_passing", "value": "40 passed"},
        {"key": "build.tests_passing", "value": "54"},
        {"key": "repo.remote", "value": "none"},
    ])
    assert [item.status for item in first] == ["match", "differs", "unbound"]
    service.recheck("HANDOFF.md", "54 passed")
    second = service.read_back([{"key": "build.tests_passing", "value": "40"}])
    assert second[0].status == "needs_recheck"
````

**Step 4:** run the whole suite. Expected: failures. `test_decide.py` fails with `TypeError` for `capture_has_value`. `test_service.py` and `test_store.py` fail with `AttributeError` or `ImportError`, for example `record_capture`, `save_capture`, `swarm_memory.readback`.

**Step 5: write** `swarm_memory/readback.py`:

````python
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from swarm_memory.text import contains_words

BLOCKING = frozenset({"differs", "needs_recheck"})


@dataclass(frozen=True)
class ReadBack:
    key: str
    value: str
    status: str
    bound_value: str | None
    decision_id: str | None


def read_back(
    relied_on: Iterable[Mapping[str, object]],
    lookup: Callable[[str], Mapping[str, object] | None],
) -> list[ReadBack]:
    """Check each relied-on value against the binding for its key.

    status is match, differs, needs_recheck (binding is not current), or unbound.
    """
    results: list[ReadBack] = []
    for item in relied_on:
        key = item.get("key")
        value = item.get("value")
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        binding = lookup(key)
        if binding is None:
            results.append(ReadBack(key, value, "unbound", None, None))
            continue
        bound_value = str(binding["value"])
        decision_id = str(binding["decision_id"])
        if binding.get("state", "current") != "current":
            status = "needs_recheck"
        elif contains_words(value, bound_value):
            status = "match"
        else:
            status = "differs"
        results.append(ReadBack(key, value, status, bound_value, decision_id))
    return results
````

**Step 6: replace** `swarm_memory/decide.py` with:

````python
import math
from dataclasses import dataclass

from swarm_memory.risk import classify


EVIDENCE_CLASSES = frozenset({"high", "critical"})


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
    capture_has_value: bool = False
    approved: bool | None = None
    blocked_reason: str | None = None


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


def _confidence_missing(confidence: float | None) -> bool:
    return confidence is None or isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence)


def evaluate(proposal: Proposal) -> Decision:
    if proposal.write_class == "trace":
        return Decision(status="ignored_trace", reason="trace")
    if proposal.write_class == "experience" or proposal.fact_key is None:
        return Decision(status="stored_experience", reason="experience")
    if proposal.write_class == "preference":
        if proposal.fact_key is None or not proposal.fact_key.startswith("preference."):
            return Decision(status="rejected", reason="preference_key")
        if _confidence_missing(proposal.confidence):
            return Decision(status="open", reason="missing_confidence")
        has_prior = proposal.prior_decision_id is not None
        return Decision(
            status="bound",
            reason="preference_recency",
            final_class="low",
            bar=None,
            confidence=float(proposal.confidence),
            value=proposal.value,
            dissent=proposal.prior_value if has_prior else None,
            supersedes=proposal.prior_decision_id if has_prior else None,
        )
    risk = classify(
        fact_key=proposal.fact_key,
        declared_floor=proposal.declared_floor,
        action=proposal.action,
        multi_role=proposal.multi_role,
        has_prior=proposal.prior_decision_id is not None,
        model_class=proposal.model_class,
    )
    if proposal.blocked_reason is not None:
        return Decision(status="open", reason=proposal.blocked_reason, final_class=risk.final_class, bar=risk.bar)
    if _confidence_missing(proposal.confidence):
        return Decision(status="open", reason="missing_confidence", final_class=risk.final_class, bar=risk.bar)
    if not 0 <= proposal.confidence <= 1:
        return Decision(status="open", reason="confidence_out_of_range", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
    if proposal.prior_decision_id is not None:
        if proposal.rival_value is None:
            return Decision(status="open", reason="missing_rival", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
        if set(proposal.evidence_ids).issubset(set(proposal.prior_evidence_ids)):
            return Decision(status="rejected", reason="same_evidence", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
    if float(proposal.confidence) < risk.bar:
        return Decision(status="open", reason="below_bar", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
    if risk.final_class in EVIDENCE_CLASSES:
        if not proposal.capture_has_value:
            return Decision(status="open", reason="no_capture", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
        if proposal.approved is not True:
            return Decision(status="open", reason="not_approved", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
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
````

**Step 7: replace** `swarm_memory/store.py` with:

````python
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    fact_key TEXT,
                    value TEXT,
                    agent_id TEXT,
                    evidence_json TEXT,
                    write_class TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS decision_instances (
                    id TEXT PRIMARY KEY,
                    fact_key TEXT,
                    status TEXT,
                    final_class TEXT,
                    bar REAL,
                    confidence REAL,
                    value TEXT,
                    dissent TEXT,
                    evidence_json TEXT,
                    agent_id TEXT,
                    supersedes TEXT,
                    index_dirty INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS fact_bindings (
                    fact_key TEXT PRIMARY KEY,
                    decision_id TEXT,
                    value TEXT,
                    risk_floor TEXT,
                    updated_at TEXT,
                    capture_id TEXT,
                    state TEXT NOT NULL DEFAULT 'current'
                );
                CREATE TABLE IF NOT EXISTS captures (
                    id TEXT PRIMARY KEY,
                    source TEXT,
                    ref TEXT,
                    content TEXT,
                    content_hash TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS recall_log (
                    id TEXT PRIMARY KEY,
                    query TEXT,
                    returned_ids_json TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS memory_utility (
                    decision_id TEXT PRIMARY KEY,
                    successes REAL NOT NULL,
                    trials REAL NOT NULL
                );
                """
            )

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_candidate(self, candidate_id: str, fact_key: str | None, value: str, agent_id: str, evidence_ids: list[str], write_class: str) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO candidates (id, fact_key, value, agent_id, evidence_json, write_class, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (candidate_id, fact_key, value, agent_id, json.dumps(evidence_ids), write_class, _utc_now()),
            )

    def save_capture(self, capture_id: str, source: str, ref: str, content: str, content_hash: str) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO captures (id, source, ref, content, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (capture_id, source, ref, content, content_hash, _utc_now()),
            )

    def capture(self, capture_id: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM captures WHERE id = ?", (capture_id,)).fetchone()
        return None if row is None else dict(row)

    def save_instance(
        self,
        instance_id: str,
        fact_key: str | None,
        status: str,
        final_class: str | None,
        bar: float | None,
        confidence: float | None,
        value: str | None,
        dissent: str | None,
        evidence_ids: list[str],
        agent_id: str,
        supersedes: str | None,
    ) -> None:
        index_dirty = 1 if status == "bound" else 0
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO decision_instances (
                    id, fact_key, status, final_class, bar, confidence, value, dissent,
                    evidence_json, agent_id, supersedes, index_dirty, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instance_id,
                    fact_key,
                    status,
                    final_class,
                    bar,
                    confidence,
                    value,
                    dissent,
                    json.dumps(evidence_ids),
                    agent_id,
                    supersedes,
                    index_dirty,
                    _utc_now(),
                ),
            )

    def bind(self, fact_key: str, decision_id: str, value: str, risk_floor: str, capture_id: str | None = None) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO fact_bindings (fact_key, decision_id, value, risk_floor, updated_at, capture_id, state)
                VALUES (?, ?, ?, ?, ?, ?, 'current')
                ON CONFLICT(fact_key) DO UPDATE SET
                    decision_id = excluded.decision_id,
                    value = excluded.value,
                    risk_floor = excluded.risk_floor,
                    updated_at = excluded.updated_at,
                    capture_id = excluded.capture_id,
                    state = 'current'
                """,
                (fact_key, decision_id, value, risk_floor, _utc_now(), capture_id),
            )

    def mark_needs_recheck(self, fact_key: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE fact_bindings SET state = 'needs_recheck', updated_at = ? WHERE fact_key = ?",
                (_utc_now(), fact_key),
            )

    def current_bindings_from(self, source: str) -> list[dict]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT b.fact_key, b.value FROM fact_bindings b
                JOIN captures c ON c.id = b.capture_id
                WHERE b.state = 'current' AND c.source = ?
                """,
                (source,),
            ).fetchall()
        return [dict(row) for row in rows]

    def bindings(self, fact_keys) -> list[dict]:
        keys = list(fact_keys)
        if not keys:
            return []
        marks = ",".join("?" for _ in keys)
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT b.fact_key, b.value, b.decision_id, i.confidence FROM fact_bindings b
                LEFT JOIN decision_instances i ON i.id = b.decision_id
                WHERE b.state = 'current' AND b.fact_key IN ({marks})
                ORDER BY b.fact_key
                """,
                keys,
            ).fetchall()
        return [dict(row) for row in rows]

    def open_values(self, fact_keys) -> list[dict]:
        """Values of open instances newer than the key's binding, grouped by key."""
        keys = list(fact_keys)
        if not keys:
            return []
        marks = ",".join("?" for _ in keys)
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT i.fact_key, i.value FROM decision_instances i
                LEFT JOIN fact_bindings b ON b.fact_key = i.fact_key
                WHERE i.status = 'open' AND i.fact_key IN ({marks})
                  AND (b.updated_at IS NULL OR i.created_at > b.updated_at)
                ORDER BY i.fact_key, i.created_at
                """,
                keys,
            ).fetchall()
        grouped: dict[str, list[str]] = {}
        for row in rows:
            values = grouped.setdefault(row["fact_key"], [])
            if row["value"] not in values:
                values.append(row["value"])
        return [{"fact_key": key, "values": values} for key, values in grouped.items()]

    def mark_indexed(self, decision_id: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE decision_instances SET index_dirty = 0 WHERE id = ?",
                (decision_id,),
            )

    def current_binding(self, fact_key: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT decision_id, value, state, capture_id FROM fact_bindings WHERE fact_key = ?",
                (fact_key,),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def instance(self, decision_id: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM decision_instances WHERE id = ?",
                (decision_id,),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["index_dirty"] = int(data["index_dirty"])
        return data

    def binding_ids(self) -> dict[str, str]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT fact_key, decision_id FROM fact_bindings WHERE state = 'current'"
            ).fetchall()
        return {row["fact_key"]: row["decision_id"] for row in rows}

    def note_use(self, decision_id: str, reward: float) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO memory_utility (decision_id, successes, trials)
                VALUES (?, ?, 1)
                ON CONFLICT(decision_id) DO UPDATE SET
                    successes = successes + excluded.successes,
                    trials = trials + 1
                """,
                (decision_id, reward),
            )

    def utilities(self) -> dict[str, tuple[float, float]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT decision_id, successes, trials FROM memory_utility"
            ).fetchall()
        return {row["decision_id"]: (float(row["successes"]), float(row["trials"])) for row in rows}

    def log_recall(self, query: str, returned_ids: list[str]) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO recall_log (id, query, returned_ids_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid4()), query, json.dumps(list(returned_ids)), _utc_now()),
            )

    def latest_recall(self) -> dict[str, object] | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT query, returned_ids_json
                FROM recall_log
                ORDER BY created_at DESC, rowid DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return {"query": row["query"], "returned_ids": list(json.loads(row["returned_ids_json"]))}
````

A new SQLite file gets the new columns. An older file made before this change keeps its old `fact_bindings` table, because `CREATE TABLE IF NOT EXISTS` doesn't alter it. Every run in this plan makes a new file.

**Step 8: replace** `swarm_memory/service.py` with:

````python
import hashlib
import json
from dataclasses import dataclass
from uuid import uuid4

from swarm_memory.card import render_card
from swarm_memory.decide import Proposal, evaluate
from swarm_memory.readback import ReadBack, read_back
from swarm_memory.recall import filter_hits
from swarm_memory.store import Store
from swarm_memory.text import contains_words
from swarm_memory.utility import ucb_scores


@dataclass(frozen=True)
class RememberResult:
    status: str
    decision_id: str | None
    candidate_id: str | None = None
    reason: str | None = None


class MemoryService:
    def __init__(self, path, index, registry=None):
        self.store = Store(path)
        self.index = index
        self.registry = registry

    def record_capture(self, *, capture_id: str, source: str, ref: str, content: str) -> None:
        """Harness only. Agents are never given this method."""
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.store.save_capture(capture_id, source, ref, content, digest)

    def capture_with_value(self, capture_ids, value: str) -> str | None:
        """First cited capture whose content states the value, or None."""
        for capture_id in capture_ids:
            capture = self.store.capture(capture_id)
            if capture is not None and contains_words(capture["content"], value):
                return capture_id
        return None

    def remember(
        self,
        *,
        fact_key: str | None,
        value: str,
        agent_id: str,
        evidence_ids,
        write_class: str,
        confidence: float | None,
        declared_floor: str | None = None,
        action: str | None = None,
        multi_role: bool = False,
        model_class: str | None = None,
        approved: bool | None = None,
        blocked_reason: str | None = None,
    ) -> RememberResult:
        if self.registry is not None and write_class == "fact" and fact_key is not None:
            spec = self.registry.get(fact_key)
            if spec is None:
                candidate_id = str(uuid4())
                self.store.save_candidate(candidate_id, fact_key, value, agent_id, list(evidence_ids), "experience")
                return RememberResult(status="undeclared_key", decision_id=None, candidate_id=candidate_id, reason="undeclared_key")
            declared_floor = spec.risk_floor
            multi_role = multi_role or len(spec.roles) > 1

        prior_decision_id = None
        prior_value = None
        prior_evidence_ids: tuple[str, ...] = ()
        rival_value = None
        if fact_key is not None:
            binding = self.store.current_binding(fact_key)
            if binding is not None:
                if write_class in {"fact", "preference"} and binding["value"] == value:
                    return RememberResult(status="duplicate", decision_id=binding["decision_id"], reason="duplicate")
                prior_decision_id = binding["decision_id"]
                prior_value = binding["value"]
                rival_value = prior_value
                instance = self.store.instance(prior_decision_id)
                if instance is None:
                    prior_evidence_ids = ()
                else:
                    prior_evidence_ids = tuple(json.loads(instance["evidence_json"]))

        capture_id = self.capture_with_value(evidence_ids, value)
        proposal = Proposal(
            fact_key=fact_key,
            value=value,
            agent_id=agent_id,
            evidence_ids=tuple(evidence_ids),
            write_class=write_class,
            confidence=confidence,
            declared_floor=declared_floor,
            action=action,
            multi_role=multi_role,
            model_class=model_class,
            rival_value=rival_value,
            prior_decision_id=prior_decision_id,
            prior_value=prior_value,
            prior_evidence_ids=prior_evidence_ids,
            capture_has_value=capture_id is not None,
            approved=approved,
            blocked_reason=blocked_reason,
        )
        decision = evaluate(proposal)
        if decision.status == "ignored_trace":
            return RememberResult(status="ignored_trace", decision_id=None)

        candidate_class = "experience" if decision.status == "stored_experience" else write_class
        candidate_id = str(uuid4())
        self.store.save_candidate(
            candidate_id,
            fact_key,
            value,
            agent_id,
            list(evidence_ids),
            candidate_class,
        )
        if decision.status not in {"open", "rejected", "bound"}:
            return RememberResult(status=decision.status, decision_id=None, candidate_id=candidate_id, reason=decision.reason)

        decision_id = str(uuid4())
        self.store.save_instance(
            instance_id=decision_id,
            fact_key=fact_key,
            status=decision.status,
            final_class=decision.final_class,
            bar=decision.bar,
            confidence=decision.confidence,
            value=value,
            dissent=decision.dissent,
            evidence_ids=list(evidence_ids),
            agent_id=agent_id,
            supersedes=decision.supersedes,
        )
        if decision.status != "bound":
            return RememberResult(status=decision.status, decision_id=decision_id, candidate_id=candidate_id, reason=decision.reason)

        self.store.bind(fact_key, decision_id, value, decision.final_class or "low", capture_id=capture_id)
        text = f"{fact_key} value={value} decision_id={decision_id}"
        try:
            self.index.write_bound_sentence(decision_id, fact_key, text)
        except Exception:
            return RememberResult(status="bound", decision_id=decision_id, candidate_id=candidate_id, reason=decision.reason)
        self.store.mark_indexed(decision_id)
        return RememberResult(status="bound", decision_id=decision_id, candidate_id=candidate_id, reason=decision.reason)

    def recheck(self, source: str, content: str) -> list[str]:
        """Move each binding whose source no longer states its value to needs_recheck."""
        moved = []
        for binding in self.store.current_bindings_from(source):
            if not contains_words(content, binding["value"]):
                self.store.mark_needs_recheck(binding["fact_key"])
                moved.append(binding["fact_key"])
        return moved

    def role_card(self, fact_keys, limit: int = 2000) -> str:
        keys = list(fact_keys)
        return render_card(self.store.bindings(keys), self.store.open_values(keys), limit=limit)

    def read_back(self, relied_on) -> list[ReadBack]:
        return read_back(relied_on, self.store.current_binding)

    def note_use(self, decision_id: str, *, used: bool) -> None:
        self.store.note_use(decision_id, 1.0 if used else 0.0)

    def recall(self, query: str, hits):
        decision_ids: list[str] = []
        text_lengths: dict[str, int] = {}
        for hit in hits:
            decision_id = hit.get("decision_id")
            if not isinstance(decision_id, str):
                continue
            decision_ids.append(decision_id)
            text = hit.get("text")
            text_lengths[decision_id] = len(text) if isinstance(text, str) else 0
        scores = ucb_scores(decision_ids, self.store.utilities(), text_lengths)
        kept = filter_hits(
            hits,
            self.store.binding_ids(),
            limit=5,
            char_budget=2000,
            scores=scores,
            per_item_cap=500,
        )
        returned_ids = [str(hit["decision_id"]) for hit in kept]
        self.store.log_recall(query, returned_ids)
        return kept
````

**Step 9:** run the whole suite. Expected: **71 passed**.

**Step 10: update the design record of the old rule.** Change the documents that state the two-agent rule as current:
- In `docs/plans/2026-10-17-swarm-decision-memory-design.md`, replace the `agent_confidence_bind` bullet that begins "For a high or critical class" with: "For a high or critical class (including any replacement of a bound value), a cited harness capture must contain the value and the approval model must approve; otherwise the instance stays open as `no_capture` or `not_approved` (changed 2026-10-19; see `2026-10-19-swarm-comparison-design.md`)."
- In the same file, replace the failure-table row "High or critical write without two independent experiences" with: "| High or critical write without a capture that states the value, or without approval | Instance stays open as `no_capture` or `not_approved`. No index write. |"
- Add one line under the Status line of `docs/plans/2026-10-17-evidence-gate-proposal.md`: "Superseded 2026-10-19 by the capture rule in `2026-10-19-swarm-comparison-design.md`."

**Step 11: commit**

```sh
git add tests/test_decide.py tests/test_store.py tests/test_service.py swarm_memory/readback.py \
  swarm_memory/decide.py swarm_memory/store.py swarm_memory/service.py \
  docs/plans/2026-10-17-swarm-decision-memory-design.md docs/plans/2026-10-17-evidence-gate-proposal.md
git commit -F - <<'MSG'
feat: bind high and critical facts only from a harness capture with approval

Replaces the two-agent evidence rule (user approval 2026-10-19).
Rewritten in test_decide.py: standard_key_binds_without_independent_evidence,
high_key_with_no/one_independent_evidence_stays_open,
high_key_with_two_evidence_ids_from_one_agent_stays_open,
critical_key_needs_two_agents_too,
replacing_a_standard_value_counts_as_high_and_needs_evidence.
Rewritten in test_service.py: high_key_with_unknown_evidence_ids_stays_open,
high_key_does_not_count_the_proposers_own_experience,
high_key_with_two_experiences_from_one_other_agent_stays_open,
high_key_with_two_independent_agents_binds, a_fact_candidate_id_is_not_evidence,
preference_cannot_replace_a_bound_fact.
MSG
```

---

## Task 4: Decision-model cases and answers

`d1-ultra` gets one yes/no (`noul`) question per candidate value. The documented System One response gives `{"type": "noul", "noul": <probability>}`. The `choice` type's probability field is not documented.
- The proposed value binds only when it has the highest probability.
- A rival scoring higher or a tie keeps the fact open.
- Code still applies the bar.

**Files:**
- Test: `tests/test_decision_models.py`
- Create: `swarm_memory/decision_models.py`

**Step 1: write the failing test** `tests/test_decision_models.py`:

````python
from swarm_memory.decision_models import decision_case, excerpt, parse_approval, pick


def test_excerpt_keeps_lines_that_state_a_candidate_and_their_neighbours():
    content = "\n".join(f"line {n}" for n in range(20)) + "\nrunner is liquid/d1-ultra\nend"
    text = excerpt(content, ["liquid/d1-ultra"], context=1)
    assert text.splitlines() == ["line 19", "runner is liquid/d1-ultra", "end"]


def test_excerpt_marks_a_gap_between_separate_matches():
    content = "a 40\nb\nc\nd\ne\nf 54"
    assert excerpt(content, ["40", "54"], context=0) == "a 40\n...\nf 54"


def test_case_has_one_noul_question_per_candidate():
    capture = {"id": "B-3", "source": "design.md", "ref": "ad5c20a", "content": "uses liquid/d1-ultra"}
    state, questions = decision_case(
        fact_key="model.decision", description="Model id that makes routine decisions",
        candidates=["liquid/d1-ultra", "liquid/lfm-2.5-24b-a2b"], current_value="liquid/lfm-2.5-24b-a2b",
        capture=capture,
    )
    assert "capture B-3" in state
    assert "uses liquid/d1-ultra" in state
    assert sorted(questions) == ["candidate_0", "candidate_1"]
    assert questions["candidate_0"]["type"] == "noul"


def test_case_says_when_the_capture_is_missing():
    state, _ = decision_case(fact_key="k", description="d", candidates=["v"], current_value=None, capture=None)
    assert "No harness capture" in state


def test_pick_returns_the_proposed_value_probability():
    result = pick({"candidate_0": {"type": "noul", "noul": 0.97}, "candidate_1": {"type": "noul", "noul": 0.1}}, 2)
    assert result.probability == 0.97
    assert result.reason is None


def test_pick_refuses_missing_or_out_of_range_probabilities():
    assert pick({"candidate_0": {"type": "noul"}}, 1).reason == "decision_model_unavailable"
    assert pick({"candidate_0": {"noul": 1.2}}, 1).reason == "decision_model_unavailable"
    assert pick({"candidate_0": {"noul": True}}, 1).reason == "decision_model_unavailable"
    assert pick(None, 1).reason == "decision_model_unavailable"


def test_pick_reports_a_preferred_rival_and_a_tie():
    assert pick({"candidate_0": {"noul": 0.3}, "candidate_1": {"noul": 0.9}}, 2).reason == "decision_prefers_other"
    assert pick({"candidate_0": {"noul": 0.9}, "candidate_1": {"noul": 0.9}}, 2).reason == "decision_ambiguous"


def test_approval_needs_json_with_approve_true():
    assert parse_approval('```json\n{"approve": true, "reason": "stated"}\n```') is True
    assert parse_approval('{"approve": "yes"}') is False
    assert parse_approval("I approve.") is False
    assert parse_approval("") is False
    assert parse_approval(None) is False
````

**Step 2:** run it. Expected: `No module named 'swarm_memory.decision_models'`.

**Step 3: write** `swarm_memory/decision_models.py`:

````python
"""Packing cases for the decision models and reading their answers.

d1-ultra is asked one yes/no (noul) question per candidate value, because the
documented System One response gives a probability for noul answers. Code, not
the model, applies the bar.
"""

import json
import math
import re
from dataclasses import dataclass

from swarm_memory.text import contains_words

APPROVAL_SYSTEM = (
    "You review one proposed fact for a team's shared memory. Approve only if the quoted "
    "source clearly states the proposed value as the CURRENT value of the key. "
    'Reply with only a JSON object: {"approve": true or false, "reason": "<one sentence>"}'
)


@dataclass(frozen=True)
class Pick:
    probability: float | None
    reason: str | None


def excerpt(content: str, needles, context: int = 3, limit: int = 4000) -> str:
    """Lines that state any needle, with nearby lines, joined in source order."""
    lines = content.splitlines()
    keep: set[int] = set()
    for number, line in enumerate(lines):
        if any(contains_words(line, needle) for needle in needles):
            keep.update(range(max(0, number - context), min(len(lines), number + context + 1)))
    if not keep:
        return ""
    parts: list[str] = []
    previous = None
    for number in sorted(keep):
        if previous is not None and number != previous + 1:
            parts.append("...")
        parts.append(lines[number])
        previous = number
    text = "\n".join(parts)
    return text if len(text) <= limit else text[:limit]


def decision_case(*, fact_key: str, description: str, candidates, current_value: str | None, capture: dict | None) -> tuple[str, dict]:
    """Return the System One state text and questions for one fact key."""
    if capture is None:
        source = "No harness capture matches the cited id."
    else:
        quoted = excerpt(capture["content"], candidates)
        source = (
            f"Cited source: capture {capture['id']}, {capture['source']} at {capture['ref']}.\n"
            + ("Source excerpt:\n" + quoted if quoted else "The cited source does not contain any candidate value.")
        )
    state = "\n".join([
        "Shared memory decision for one fact key.",
        f"Key: {fact_key} ({description})",
        f"Current bound value: {current_value if current_value is not None else 'none'}",
        source,
    ])
    questions = {
        f"candidate_{index}": {
            "type": "noul",
            "instructions": f"Does the source state that the CURRENT value of {fact_key} is exactly '{value}'?",
        }
        for index, value in enumerate(candidates)
    }
    return state, questions


def pick(answers, candidate_count: int) -> Pick:
    """Probability for candidate 0, the proposed value, or the reason it cannot bind."""
    probabilities: list[float] = []
    for index in range(candidate_count):
        answer = answers.get(f"candidate_{index}") if isinstance(answers, dict) else None
        value = answer.get("noul") if isinstance(answer, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            return Pick(None, "decision_model_unavailable")
        probabilities.append(float(value))
    if not probabilities:
        return Pick(None, "decision_model_unavailable")
    top = max(probabilities)
    if probabilities.count(top) > 1:
        return Pick(probabilities[0], "decision_ambiguous")
    if probabilities[0] != top:
        return Pick(probabilities[0], "decision_prefers_other")
    return Pick(probabilities[0], None)


def approval_prompt(state: str, value: str) -> str:
    return f"{state}\n\nProposed value: '{value}'. Approve binding it as the current value?"


def parse_approval(text) -> bool:
    """True only for a JSON object whose approve field is true."""
    if not isinstance(text, str):
        return False
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match is None:
        return False
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and data.get("approve") is True
````

**Step 4:** run the whole suite. Expected: **79 passed**.

**Step 5:** `git add tests/test_decision_models.py swarm_memory/decision_models.py && git commit -m "feat: pack decision cases and read decision answers"`

---

## Task 5: Vector index

This one index serves both the search-only swarm and our memory's recall, through the existing `write_bound_sentence` port. Hy-Memory stays uninstalled.

**Files:**
- Test: `tests/test_vector_index.py`
- Create: `swarm_memory/vector_index.py`

**Step 1: write the failing test** `tests/test_vector_index.py`:

````python
import pytest

from swarm_memory.vector_index import VectorIndex, cosine, top_matches


def test_cosine_of_parallel_and_orthogonal_vectors():
    assert cosine([1.0, 0.0], [2.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 3.0]) == pytest.approx(0.0)
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_top_matches_orders_by_similarity_and_drops_vectors():
    items = [
        {"text": "far", "vector": [0.0, 1.0]},
        {"text": "near", "vector": [1.0, 0.1]},
        {"text": "middle", "vector": [1.0, 1.0]},
    ]
    result = top_matches([1.0, 0.0], items, limit=2)
    assert [item["text"] for item in result] == ["near", "middle"]
    assert "vector" not in result[0]


def test_index_refuses_an_empty_model_id():
    with pytest.raises(RuntimeError, match="embedding model"):
        VectorIndex(embed=None, embedding_model="")


def test_saved_items_from_another_model_are_refused():
    index = VectorIndex(embed=None, embedding_model="model-a")
    with pytest.raises(RuntimeError, match="different embedding model"):
        index.load({"embedding_model": "model-b", "items": []})
````

**Step 2:** run it. Expected: `No module named 'swarm_memory.vector_index'`.

**Step 3: write** `swarm_memory/vector_index.py`:

````python
import math
from collections.abc import Callable, Mapping, Sequence

Embed = Callable[[list[str]], list[list[float]]]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def top_matches(query_vector: Sequence[float], items: Sequence[Mapping[str, object]], limit: int) -> list[dict]:
    """Items ordered by cosine similarity to the query, without their vectors."""
    ranked = sorted(items, key=lambda item: cosine(query_vector, item["vector"]), reverse=True)
    return [{key: value for key, value in item.items() if key != "vector"} for item in ranked[:limit]]


class VectorIndex:
    """In-process embedding index. Holds vectors from one embedding model only."""

    def __init__(self, embed: Embed, embedding_model: str):
        if not embedding_model:
            raise RuntimeError("VectorIndex requires an embedding model id")
        self.embed = embed
        self.embedding_model = embedding_model
        self.items: list[dict] = []

    def add(self, texts: list[str], metas: list[dict]) -> None:
        if not texts:
            return
        vectors = self.embed(texts)
        for text, meta, vector in zip(texts, metas, vectors, strict=True):
            self.items.append({**meta, "text": text, "vector": vector})

    def write_bound_sentence(self, decision_id: str, fact_key: str, text: str) -> None:
        self.add([text], [{"decision_id": decision_id, "fact_key": fact_key}])

    def search(self, query: str, limit: int) -> list[dict]:
        if not self.items:
            return []
        [query_vector] = self.embed([query])
        return top_matches(query_vector, self.items, limit)

    def dump(self) -> dict:
        return {"embedding_model": self.embedding_model, "items": self.items}

    def load(self, data: dict | None) -> None:
        if not data:
            return
        if data["embedding_model"] != self.embedding_model:
            raise RuntimeError("Saved index uses a different embedding model")
        self.items = list(data["items"])
````

**Step 4:** run the whole suite. Expected: **83 passed**.

**Step 5:** `git add tests/test_vector_index.py swarm_memory/vector_index.py && git commit -m "feat: add an in-process embedding index"`

---

## Task 6: OpenRouter client safety

The endpoints and response shapes come from the 2026-10-18 model check, `aether/aether_workspace/scripts/check_models.py` on branch `aether-goal-1-7`, and OpenRouter's System One documentation:
- Chat returns `choices[0].message.content` and `usage.prompt_tokens/completion_tokens/cost`.
- System One returns `answers` and `usage.input_tokens/output_tokens/cost`.
- Embeddings return `data[i].embedding`, with 3,072 values for `google/gemini-embedding-2`.

**Files:**
- Test: `tests/test_openrouter_safety.py`
- Create: `swarm_compare/models.py`, `swarm_compare/openrouter.py`

**Step 1: write the failing test** `tests/test_openrouter_safety.py`:

````python
import json
from pathlib import Path

import pytest

from swarm_compare.openrouter import (
    CallLog, SpendLimitNotSet, SpendLimitReached, SpendMeter, read_key, redact, retry_wait, usage_numbers,
)


def test_redact_hides_key_shaped_strings():
    assert redact("auth failed for sk-or-v1-abc123_XYZ") == "auth failed for sk-[REDACTED]"


def test_read_key_takes_only_the_named_variable(tmp_path: Path):
    path = tmp_path / "creds.env"
    path.write_text(
        "# OPENROUTER_API_KEY=commented-out\n"
        "OTHER_KEY=not-this\n"
        "export OPENROUTER_API_KEY='first-value'\n"
        "OPENROUTER_API_KEY=last-value # trailing note\n"
    )
    assert read_key(path) == "last-value"


def test_read_key_fails_when_the_variable_is_absent(tmp_path: Path):
    path = tmp_path / "creds.env"
    path.write_text("OTHER_KEY=x\n")
    with pytest.raises(RuntimeError, match="not found"):
        read_key(path)


def test_retry_policy():
    assert retry_wait(429, "3", 0) == 3.0
    assert retry_wait(503, None, 1) == 2.0
    assert retry_wait(None, None, 2) == 4.0
    assert retry_wait(500, None, 3) is None
    for status in (400, 401, 402, 403, 404):
        assert retry_wait(status, None, 0) is None


def test_usage_numbers_read_both_naming_styles():
    assert usage_numbers({"usage": {"prompt_tokens": 18, "completion_tokens": 3, "cost": 1e-05}}) == (18, 3, 1e-05)
    assert usage_numbers({"usage": {"input_tokens": 56, "output_tokens": 0, "cost": 2e-06}}) == (56, 0, 2e-06)
    assert usage_numbers({"choices": []}) == (None, None, None)


def test_meter_stops_once_the_limit_is_reached():
    meter = SpendMeter(0.01)
    meter.add(0.006)
    meter.check()
    meter.add(0.005)
    with pytest.raises(SpendLimitReached):
        meter.check()


def test_meter_requires_the_limit_variable(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SWARM_EXP_SPEND_LIMIT_USD", raising=False)
    with pytest.raises(SpendLimitNotSet):
        SpendMeter.from_env(CallLog(tmp_path / "calls.jsonl"))


def test_meter_starts_from_the_spend_already_logged(tmp_path: Path, monkeypatch):
    log = CallLog(tmp_path / "calls.jsonl")
    log.append({"run_id": "r", "cost": 0.25})
    log.append({"run_id": "r", "cost": None})
    with log.path.open("a") as handle:
        handle.write('{"run_id": "partial"')
    monkeypatch.setenv("SWARM_EXP_SPEND_LIMIT_USD", "1.0")
    meter = SpendMeter.from_env(log)
    assert meter.spent == 0.25
    assert len(log.records()) == 2


def test_call_log_redacts_keys(tmp_path: Path):
    log = CallLog(tmp_path / "calls.jsonl")
    log.append({"error": "bad key sk-or-v1-secret"})
    assert "secret" not in log.path.read_text()
    assert json.loads(log.path.read_text())["error"] == "bad key sk-[REDACTED]"
````

**Step 2:** run it. Expected: `No module named 'swarm_compare.openrouter'`.

**Step 3: write** `swarm_compare/models.py`:

````python
"""Model ids chosen by the user on 2026-10-19. Change them only on the user's instruction."""

AGENT_MODEL = "deepseek/deepseek-v4.1-flash-1017"
DECISION_MODEL = "liquid/d1-ultra"
APPROVAL_MODEL = "google/gemini-4-argon"
EMBEDDING_MODEL = "google/gemini-embedding-2"
````

**Step 4: write** `swarm_compare/openrouter.py`:

````python
"""OpenRouter calls with a spending stop, retries, and a call log.

The key is read from one variable in one file and is never logged.
"""

import hashlib
import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

API_ROOT = "https://openrouter.ai/api/v1"
DEFAULT_CREDENTIALS = "/Volumes/WS4TB/merged.env"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRIES = 3
_KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-]+")


class SpendLimitNotSet(RuntimeError):
    pass


class SpendLimitReached(RuntimeError):
    pass


class CallFailed(RuntimeError):
    def __init__(self, status: int | None, message: str):
        self.status = status
        super().__init__(f"HTTP {status if status is not None else 'unavailable'}: {message}")


def redact(text: str) -> str:
    return _KEY_PATTERN.sub("sk-[REDACTED]", text)


def read_key(path: Path | str) -> str:
    """Return OPENROUTER_API_KEY from a dotenv-style file. Reads no other setting.

    When the name is assigned more than once, the last assignment wins, as in a shell.
    """
    found = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text.startswith("export "):
            text = text[len("export "):].lstrip()
        name, sep, value = text.partition("=")
        if not sep or name.strip() != "OPENROUTER_API_KEY":
            continue
        value = value.strip()
        if value[:1] in {'"', "'"}:
            value = value[1:].split(value[0], 1)[0]
        else:
            value = value.split(" #", 1)[0].strip()
        if value:
            found = value
    if found is None:
        raise RuntimeError(f"OPENROUTER_API_KEY not found in {path}")
    return found


def credentials_path() -> Path:
    return Path(os.environ.get("SWARM_EXP_CREDENTIALS_FILE", DEFAULT_CREDENTIALS))


def retry_wait(status: int | None, retry_after: str | None, attempt: int) -> float | None:
    """Seconds to wait before another try, or None to stop. attempt counts from 0."""
    if attempt >= MAX_RETRIES:
        return None
    if status is not None and status not in RETRY_STATUSES:
        return None
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            pass
    return float(2 ** attempt)


def usage_numbers(data) -> tuple[int | None, int | None, float | None]:
    usage = data.get("usage") if isinstance(data, dict) else None
    if not isinstance(usage, dict):
        return None, None, None
    prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
    completion = usage.get("completion_tokens", usage.get("output_tokens"))
    cost = usage.get("cost")
    prompt = prompt if isinstance(prompt, int) and not isinstance(prompt, bool) else None
    completion = completion if isinstance(completion, int) and not isinstance(completion, bool) else None
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost):
        cost = None
    return prompt, completion, None if cost is None else float(cost)


class CallLog:
    """One JSON object per line, appended as each call returns."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        line = redact(json.dumps(record, ensure_ascii=False))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def total_cost(self) -> float:
        return sum(row["cost"] for row in self.records() if isinstance(row.get("cost"), (int, float)))


class SpendMeter:
    def __init__(self, limit_usd: float, spent_usd: float = 0.0):
        if not math.isfinite(limit_usd) or limit_usd <= 0:
            raise ValueError("spending limit must be a positive number")
        self.limit = limit_usd
        self.spent = spent_usd

    @classmethod
    def from_env(cls, log: CallLog) -> "SpendMeter":
        raw = os.environ.get("SWARM_EXP_SPEND_LIMIT_USD", "").strip()
        if not raw:
            raise SpendLimitNotSet("SWARM_EXP_SPEND_LIMIT_USD is not set; no paid call is allowed")
        return cls(float(raw), log.total_cost())

    def check(self) -> None:
        if self.spent >= self.limit:
            raise SpendLimitReached(f"spent {self.spent:.6f} of the {self.limit:.6f} USD limit")

    def add(self, cost: float | None) -> None:
        if cost is not None:
            self.spent += cost


@dataclass(frozen=True)
class CallResult:
    data: dict
    served_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost: float | None


def _summary(kind: str, data: dict):
    if "choices" in data:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None
    if "answers" in data:
        return data["answers"]
    if isinstance(data.get("data"), list):
        return {"vectors": len(data["data"])}
    return None


class OpenRouter:
    def __init__(self, key: str, meter: SpendMeter, log: CallLog, timeout: float = 120.0):
        self.meter = meter
        self.log = log
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/deesatzed/Shared_Swarm_Memory",
                "X-Title": "Swarm memory comparison",
            },
        )

    def close(self) -> None:
        self._client.close()

    def _post(self, path: str, payload: dict, *, run_id: str, kind: str) -> CallResult:
        body = json.dumps(payload, ensure_ascii=False)
        request_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        attempt = 0
        while True:
            self.meter.check()
            status = None
            retry_after = None
            error = None
            try:
                response = self._client.post(f"{API_ROOT}{path}", content=body)
                status = response.status_code
                retry_after = response.headers.get("retry-after")
                if response.is_success:
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("response is not a JSON object")
                    if isinstance(data.get("error"), dict):
                        code = data["error"].get("code")
                        status = code if isinstance(code, int) else status
                        error = str(data["error"].get("message", "error object in response"))
                    else:
                        prompt, completion, cost = usage_numbers(data)
                        self.meter.add(cost)
                        result = CallResult(data, data.get("model"), prompt, completion, cost)
                        self.log.append({
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "run_id": run_id,
                            "kind": kind,
                            "status": "ok",
                            "requested_model": payload.get("model"),
                            "served_model": result.served_model,
                            "request_id": data.get("id"),
                            "request_sha256": request_hash,
                            "request_chars": len(body),
                            "prompt_tokens": prompt,
                            "completion_tokens": completion,
                            "cost": cost,
                            "usage_missing": cost is None,
                            "attempt": attempt,
                            "output": _summary(kind, data),
                        })
                        return result
                else:
                    error = response.text[:500]
            except (httpx.HTTPError, ValueError) as exc:
                error = f"{type(exc).__name__}: {exc}"
            self.log.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "kind": kind,
                "status": "error",
                "requested_model": payload.get("model"),
                "http_status": status,
                "error": redact(error or "request failed"),
                "request_sha256": request_hash,
                "attempt": attempt,
            })
            wait = retry_wait(status, retry_after, attempt)
            if wait is None:
                raise CallFailed(status, redact(error or "request failed"))
            time.sleep(wait)
            attempt += 1

    def chat(self, model: str, system: str, user: str, *, run_id: str, kind: str,
             max_tokens: int = 2000, temperature: float = 0.2) -> tuple[str, CallResult]:
        result = self._post("/chat/completions", {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }, run_id=run_id, kind=kind)
        try:
            content = result.data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = None
        return (content if isinstance(content, str) else ""), result

    def decide(self, model: str, state: str, questions: dict, *, run_id: str, kind: str) -> dict | None:
        result = self._post("/systemone", {"model": model, "state": state, "questions": questions},
                            run_id=run_id, kind=kind)
        answers = result.data.get("answers")
        return answers if isinstance(answers, dict) else None

    def embed(self, model: str, inputs: list[str], *, run_id: str, kind: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(inputs), 64):
            batch = inputs[start:start + 64]
            result = self._post("/embeddings", {"model": model, "input": batch, "encoding_format": "float"},
                                run_id=run_id, kind=kind)
            rows = result.data.get("data")
            if not isinstance(rows, list) or len(rows) != len(batch):
                raise CallFailed(None, "embedding response has the wrong number of vectors")
            vectors.extend(row["embedding"] for row in rows)
        return vectors
````

**Step 5:** run the whole suite. Expected: **92 passed**.

**Step 6:** `git add tests/test_openrouter_safety.py swarm_compare/models.py swarm_compare/openrouter.py && git commit -m "feat: add the OpenRouter client with a spending stop and call log"`

---

## Task 7: Real tasks and answer key

Strings were checked in each state with `git show` on 2026-10-19:
- **Task A:**
  - `40 passed` and `no git remote` appear at `6136de0` and `379afbc`, and not at `9318598`.
  - `54 passed` and `deesatzed/Shared_Swarm_Memory` appear only at `9318598`.
- **Task B:**
  - `insufficient_evidence` first appears at `3dbc1a4`, and `d1-ultra` first appears at `ad5c20a`.
  - `ad5c20a` still names `lfm-2.5-24b-a2b` on line 19. This is a known hard case: re-check alone won't catch it.
- `0.92` appears in all six states.
- No state contains a key-shaped string or an email address.

**Files:**
- Create: `swarm_compare/tasks/A.json`, `swarm_compare/tasks/B.json`
- Test: `tests/test_compare_tasks.py`
- Create: `swarm_compare/tasks.py`

**Step 1:** create `swarm_compare/tasks/A.json`:

````json
{
  "id": "A",
  "title": "Handoff history",
  "states": [
    {"capture_id": "A-1", "path": "HANDOFF_2026-10-17.md", "commit": "6136de0c2d064f3256c28eaa376ed3aba9fcc436"},
    {"capture_id": "A-2", "path": "HANDOFF_2026-10-17.md", "commit": "379afbcef8cf7f0248650e667404ac328e0ed70e"},
    {"capture_id": "A-3", "path": "HANDOFF_2026-10-17.md", "commit": "93185982f7c37c11811d912036663613de8c6da6"}
  ],
  "questions": [
    {"id": "A-q1", "key": "build.tests_passing", "question": "How many main-suite tests pass now?", "expect": ["54"], "stale": ["40"], "answer_at": "A-3"},
    {"id": "A-q2", "key": "repo.remote", "question": "What is the project's git remote now?", "expect": ["deesatzed/Shared_Swarm_Memory"], "stale": ["no git remote", "no remote"], "answer_at": "A-3"},
    {"id": "A-q3", "key": "rule.bar_high", "question": "What confidence does a high-risk fact need to bind?", "expect": ["0.92"], "stale": [], "answer_at": "all", "control": true}
  ]
}
````

and `swarm_compare/tasks/B.json`:

````json
{
  "id": "B",
  "title": "Design history",
  "states": [
    {"capture_id": "B-1", "path": "docs/plans/2026-10-17-swarm-decision-memory-design.md", "commit": "113818630a9ebeedff3a5c44973465b0ef3a7fd4"},
    {"capture_id": "B-2", "path": "docs/plans/2026-10-17-swarm-decision-memory-design.md", "commit": "3dbc1a46af2df6afd263f7cc92e255e1860a003d"},
    {"capture_id": "B-3", "path": "docs/plans/2026-10-17-swarm-decision-memory-design.md", "commit": "ad5c20a667948e58a6667f928bf79b1b94d73786"}
  ],
  "questions": [
    {"id": "B-q1", "key": "model.decision", "question": "Which model makes routine decisions now?", "expect": ["d1-ultra"], "stale": ["lfm-2.5-24b-a2b"], "answer_at": "B-3"},
    {"id": "B-q2", "key": "rule.evidence_reason", "question": "What status reason does a high or critical fact get when it lacks the required evidence?", "expect": ["insufficient_evidence"], "stale": [], "answer_at": "B-3"},
    {"id": "B-q3", "key": "rule.bar_high", "question": "What confidence does a high-risk fact need to bind?", "expect": ["0.92"], "stale": [], "answer_at": "all", "control": true}
  ]
}
````

**Step 2: write the failing test** `tests/test_compare_tasks.py`:

````python
"""The answer key must rest on real git history."""

import re
from pathlib import Path

import pytest

from swarm_compare.tasks import load_task, stale_by_key, state_text, task_ids
from swarm_memory.registry import Registry
from swarm_memory.text import contains_words

KEYS = Path(__file__).resolve().parents[1] / "swarm_compare" / "keys.json"


def _texts(task):
    return {state.capture_id: state_text(state) for state in task.states}


def test_both_tasks_are_present():
    assert task_ids() == ["A", "B"]


@pytest.mark.parametrize("task_id", ["A", "B"])
def test_expected_values_appear_where_the_task_says(task_id):
    task = load_task(task_id)
    texts = _texts(task)
    order = [state.capture_id for state in task.states]
    for question in task.questions:
        targets = order if question.answer_at == "all" else [question.answer_at]
        for capture_id in targets:
            for expected in question.expect:
                assert contains_words(texts[capture_id], expected), (question.id, capture_id, expected)


@pytest.mark.parametrize("task_id", ["A", "B"])
def test_stale_values_appear_in_an_earlier_state(task_id):
    task = load_task(task_id)
    texts = _texts(task)
    order = [state.capture_id for state in task.states]
    for question in task.questions:
        earlier = order[:order.index(question.answer_at)] if question.answer_at != "all" else []
        for stale in question.stale:
            assert any(contains_words(texts[capture_id], stale) for capture_id in earlier), (question.id, stale)


@pytest.mark.parametrize("task_id", ["A", "B"])
def test_no_state_contains_a_key_or_an_email_address(task_id):
    for text in _texts(load_task(task_id)).values():
        assert re.search(r"sk-[A-Za-z0-9_-]{8,}", text) is None
        assert re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", text) is None


@pytest.mark.parametrize("task_id", ["A", "B"])
def test_question_keys_are_registered(task_id):
    registry = Registry.load(KEYS)
    for question in load_task(task_id).questions:
        assert registry.get(question.key) is not None, question.id


def test_stale_strings_are_grouped_by_key():
    assert stale_by_key(load_task("A"))["repo.remote"] == ("no git remote", "no remote")
````

**Step 3:** run it. Expected: `No module named 'swarm_compare.tasks'`.

**Step 4: write** `swarm_compare/tasks.py`:

````python
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
TASKS = PACKAGE / "tasks"


def repo_root() -> Path:
    return Path(os.environ.get("SWARM_EXP_REPO", PACKAGE.parent))


@dataclass(frozen=True)
class State:
    capture_id: str
    path: str
    commit: str


@dataclass(frozen=True)
class Question:
    id: str
    key: str | None
    question: str
    expect: tuple[str, ...]
    stale: tuple[str, ...]
    answer_at: str
    control: bool


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    states: tuple[State, ...]
    questions: tuple[Question, ...]


def task_ids() -> list[str]:
    return sorted(path.stem for path in TASKS.glob("*.json"))


def load_task(task_id: str) -> Task:
    raw = json.loads((TASKS / f"{task_id}.json").read_text(encoding="utf-8"))
    return Task(
        id=raw["id"],
        title=raw["title"],
        states=tuple(State(**state) for state in raw["states"]),
        questions=tuple(
            Question(
                id=q["id"],
                key=q.get("key"),
                question=q["question"],
                expect=tuple(q["expect"]),
                stale=tuple(q.get("stale", [])),
                answer_at=q["answer_at"],
                control=bool(q.get("control", False)),
            )
            for q in raw["questions"]
        ),
    )


def state_text(state: State) -> str:
    """The document exactly as it was at that commit."""
    completed = subprocess.run(
        ["git", "-C", str(repo_root()), "show", f"{state.commit}:{state.path}"],
        check=True, capture_output=True, text=True,
    )
    return completed.stdout


def stale_by_key(task: Task) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for question in task.questions:
        if question.key and question.stale:
            result[question.key] = tuple(dict.fromkeys(result.get(question.key, ()) + question.stale))
    return result
````

**Step 5:** run the whole suite. Expected: **102 passed**. If an answer-key test fails, the task file is wrong, not the history. Fix the JSON and record the change in the progress log.

**Step 6:** `git add swarm_compare/tasks/A.json swarm_compare/tasks/B.json tests/test_compare_tasks.py swarm_compare/tasks.py && git commit -m "feat: add the two real tasks with a git-checked answer key"`

---

## Task 8: Reply blocks and value scoring

Scoring reads only JSON value fields. An agent's prose can mention an old value without counting as a stale action.

**Files:**
- Test: `tests/test_blocks.py`
- Create: `swarm_compare/blocks.py`

**Step 1: write the failing test** `tests/test_blocks.py`:

````python
from swarm_compare.blocks import (
    is_correct, last_json_block, parse_answers, parse_turn_block, stale_hits, stale_relied,
)

TURN = """Tests went from 40 to 54.

```json
{"relies_on": [{"key": "build.tests_passing", "value": 54, "decision_id": "d1"},
               {"key": "", "value": "dropped"}],
 "facts": [{"key": "build.tests_passing", "value": "54", "capture_id": "A-3"},
           {"key": "repo.remote", "value": "x"}]}
```
"""


def test_the_last_fenced_block_wins():
    text = '```json\n{"a": 1}\n```\nlater\n```\n{"a": 2}\n```'
    assert last_json_block(text) == {"a": 2}
    assert last_json_block("no block") is None
    assert last_json_block(None) is None


def test_turn_block_keeps_complete_entries_and_turns_numbers_into_text():
    block = parse_turn_block(TURN)
    assert block["relies_on"] == [{"key": "build.tests_passing", "value": "54", "decision_id": "d1"}]
    assert block["facts"] == [{"key": "build.tests_passing", "value": "54", "capture_id": "A-3"}]


def test_turn_block_needs_a_relies_on_list():
    assert parse_turn_block('```json\n{"facts": []}\n```') is None


def test_answers_are_read_by_question_id():
    text = '```json\n{"answers": [{"id": "A-q1", "value": "54 passed"}], "relies_on": []}\n```'
    assert parse_answers(text) == {"answers": {"A-q1": "54 passed"}, "relies_on": []}
    assert parse_answers('```json\n{"relies_on": []}\n```') is None


def test_scoring_uses_whole_words():
    assert is_correct("54 passed", ["54"])
    assert not is_correct("540 passed", ["54"])
    assert not is_correct("", ["54"])
    assert stale_hits("was 40, now 54", ["40"]) == ["40"]
    assert stale_hits(None, ["40"]) == []


def test_stale_relied_checks_only_the_strings_listed_for_that_key():
    relied = [
        {"key": "build.tests_passing", "value": "40", "decision_id": ""},
        {"key": "repo.remote", "value": "40", "decision_id": ""},
    ]
    assert stale_relied(relied, {"build.tests_passing": ("40",)}) == [relied[0]]
````

**Step 2:** run it. Expected: `No module named 'swarm_compare.blocks'`.

**Step 3: write** `swarm_compare/blocks.py`:

````python
"""Reading the agents' JSON blocks and scoring their values."""

import json
import re

from swarm_memory.text import contains_words

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def last_json_block(text) -> dict | None:
    if not isinstance(text, str):
        return None
    for raw in reversed(_FENCE.findall(text)):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _text(value) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _entries(items, names: tuple[str, ...], optional: tuple[str, ...] = ()) -> list[dict]:
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = {name: _text(item.get(name)) for name in names}
        if any(value is None or value == "" for value in row.values()):
            continue
        for name in optional:
            row[name] = _text(item.get(name)) or ""
        out.append(row)
    return out


def parse_turn_block(text) -> dict | None:
    """{"relies_on": [...], "facts": [...]} from the last fenced JSON block, or None."""
    data = last_json_block(text)
    if data is None:
        return None
    relies = data.get("relies_on")
    facts = data.get("facts", [])
    if not isinstance(relies, list) or not isinstance(facts, list):
        return None
    return {
        "relies_on": _entries(relies, ("key", "value"), ("decision_id",)),
        "facts": _entries(facts, ("key", "value", "capture_id")),
    }


def parse_answers(text) -> dict | None:
    """{"answers": {question_id: value}, "relies_on": [...]}, or None."""
    data = last_json_block(text)
    if data is None or not isinstance(data.get("answers"), list):
        return None
    answers = {row["id"]: row["value"] for row in _entries(data["answers"], ("id", "value"))}
    relies = data.get("relies_on", [])
    return {
        "answers": answers,
        "relies_on": _entries(relies, ("key", "value"), ("decision_id",)) if isinstance(relies, list) else [],
    }


def is_correct(value: str | None, expect) -> bool:
    return bool(value) and all(contains_words(value, expected) for expected in expect)


def stale_hits(value: str | None, stale) -> list[str]:
    if not value:
        return []
    return [item for item in stale if contains_words(value, item)]


def stale_relied(relied_on, stale_by_key) -> list[dict]:
    """Relied-on items whose value states a stale string listed for that key."""
    return [item for item in relied_on if stale_hits(item["value"], stale_by_key.get(item["key"], ()))]
````

**Step 4:** run the whole suite. Expected: **108 passed**.

**Step 5:** `git add tests/test_blocks.py swarm_compare/blocks.py && git commit -m "feat: parse agent reply blocks and score values"`

---

## Task 9: Prompts and the three swarms

All three swarms use the same role prompts and reply format. Only the context differs:
- **Full context:** every earlier state and message.
- **Search only:** the top 5 matches, packed to 2,000 characters.
- **Our memory:** the role card plus recall.

The memory swarm also handles each proposed fact in this order. Each step stops the fact before any paid call that isn't needed:
1. registry
2. duplicate
3. capture, for high and critical keys
4. `d1-ultra`
5. bar
6. `gemini-4-argon`, for high and critical keys

**Files:**
- Test: `tests/test_swarms.py`
- Create: `swarm_compare/prompts.py`, `swarm_compare/swarms.py`

**Step 1: write the failing test** `tests/test_swarms.py`:

````python
from pathlib import Path

from swarm_compare.swarms import FullContextSwarm, MemorySwarm, chunk, pack, work_query
from swarm_compare.tasks import State
from swarm_memory.registry import Registry
from swarm_memory.service import MemoryService

KEYS = Path(__file__).resolve().parents[1] / "swarm_compare" / "keys.json"


class RecordingIndex:
    """Test double. Records index attempts. It is not a memory store."""

    def __init__(self):
        self.sentences = []

    def write_bound_sentence(self, decision_id, fact_key, text):
        self.sentences.append((decision_id, fact_key, text))


def _state(capture_id, commit="abcdef0123"):
    return State(capture_id=capture_id, path="HANDOFF.md", commit=commit)


def test_chunks_stay_within_the_size():
    text = "\n\n".join(["short"] * 50 + ["x" * 900])
    pieces = chunk(text, size=400)
    assert all(0 < len(piece) <= 400 for piece in pieces)
    assert "".join(pieces).count("x") == 900


def test_pack_skips_a_hit_that_does_not_fit():
    hits = [{"text": "a" * 1500}, {"text": "b" * 600}, {"text": "c" * 400}]
    assert [hit["text"][0] for hit in pack(hits, limit=5, budget=2000)] == ["a", "c"]


def test_work_query_holds_the_focus_and_the_changed_lines():
    query = work_query("tester", "40 passed\nsame", "54 passed\nsame")
    assert query.startswith("tester: test counts")
    assert "54 passed" in query
    assert "40 passed" not in query


def test_full_context_shows_earlier_states_and_messages_but_not_the_newest_state_twice():
    swarm = FullContextSwarm()
    swarm.begin_round(_state("A-1"), "first text")
    swarm.after_turn("planner", _state("A-1"), "plan note", {"relies_on": [], "facts": []})
    swarm.end_round(_state("A-1"), "first text")
    swarm.begin_round(_state("A-2"), "second text")
    _, body = swarm.context("coder", "")
    assert "first text" in body
    assert "plan note" in body
    assert "second text" not in body
    assert "A-2: the newest version" in body


def _memory_swarm(tmp_path):
    registry = Registry.load(KEYS)
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex(), registry)
    return MemorySwarm(service, index=None, registry=registry, client=None, run_id="test")


def test_an_undeclared_key_never_reaches_a_model(tmp_path: Path):
    swarm = _memory_swarm(tmp_path)
    outcome = swarm.handle_fact("coder", {"key": "build.color", "value": "green", "capture_id": "A-1"})
    assert outcome["status"] == "undeclared_key"


def test_a_repeated_value_never_reaches_a_model(tmp_path: Path):
    swarm = _memory_swarm(tmp_path)
    swarm.begin_round(_state("A-1"), "40 passed")
    swarm.service.remember(fact_key="build.tests_passing", value="40", agent_id="tester",
                           evidence_ids=["A-1"], write_class="fact", confidence=0.85)
    outcome = swarm.handle_fact("tester", {"key": "build.tests_passing", "value": "40", "capture_id": "A-1"})
    assert outcome["status"] == "duplicate"


def test_a_high_key_without_a_capture_never_reaches_a_model(tmp_path: Path):
    swarm = _memory_swarm(tmp_path)
    swarm.begin_round(_state("B-3"), "the runner is liquid/lfm-2.5-24b-a2b")
    outcome = swarm.handle_fact("coder", {"key": "model.decision", "value": "liquid/d1-ultra", "capture_id": "B-3"})
    assert outcome["status"] == "open"
    assert outcome["reason"] == "no_capture"


def test_a_new_round_moves_a_value_its_source_dropped(tmp_path: Path):
    swarm = _memory_swarm(tmp_path)
    swarm.begin_round(State("A-1", "HANDOFF.md", "c1"), "40 passed")
    swarm.service.remember(fact_key="build.tests_passing", value="40", agent_id="tester",
                           evidence_ids=["A-1"], write_class="fact", confidence=0.85)
    swarm.begin_round(State("A-3", "HANDOFF.md", "c3"), "54 passed")
    assert swarm.rechecked == [{"round": "A-3", "key": "build.tests_passing"}]
````

**Step 2:** run it. Expected: `No module named 'swarm_compare.swarms'`.

**Step 3: write** `swarm_compare/prompts.py`:

````python
"""Prompts shared by all three swarms. Only the context header differs."""

ROLES = ("planner", "coder", "tester", "reviewer", "release")

FOCUS = {
    "planner": "what the team should do next, and in what order",
    "coder": "the code, the models it calls, and the rules it must follow",
    "tester": "test counts and how the work is verified",
    "reviewer": "whether rules and decisions are being followed",
    "release": "branches, remotes, pushes, and what may be shared",
}

FULL_HEADER = "Everything earlier in this task, in order:"
SEARCH_HEADER = (
    "Search results from the team's shared store of earlier documents and notes "
    "(best matches; they may be out of date):"
)
MEMORY_HEADER = "Your role card and recall from the team's shared memory (current bound values only):"

TURN_SHAPE = """```json
{"relies_on": [{"key": "<fact key>", "value": "<exact value>", "decision_id": "<id, or empty>"}],
 "facts": [{"key": "<fact key>", "value": "<exact value>", "capture_id": "<capture id of the document that states it>"}]}
```"""

ANSWER_SHAPE = """```json
{"answers": [{"id": "<question id>", "value": "<short exact value>"}],
 "relies_on": [{"key": "<fact key>", "value": "<exact value>", "decision_id": "<id, or empty>"}]}
```"""

FORMAT_RETRY = "Your reply did not end with a JSON block in the required shape. Reply again in full, ending with exactly one fenced JSON block of this shape:\n" + TURN_SHAPE
FORMAT_RETRY_ANSWERS = "Your reply was not one JSON block in the required shape. Reply again with only one fenced JSON block of this shape:\n" + ANSWER_SHAPE


def system_prompt(role: str, registry) -> str:
    keys = "\n".join(f"- {spec.key}: {spec.description}" for spec in registry.specs())
    return f"""You are the {role} on a five-agent software team: planner, coder, tester, reviewer and release.
Your focus: {FOCUS[role]}.
The team maintains the Shared_Swarm_Memory project. Each round you are shown the newest version of one project document, with its capture id.

Fact keys the team uses (use these exact names):
{keys}

Unless a message asks for a different reply, write a short note for the team (under 150 words) on what matters for your focus and what you will do next, then end with exactly one fenced JSON block of this shape:
{TURN_SHAPE}
In relies_on, list every fact key value your note depends on. In facts, list the fact key values the newest document states as current, with that document's capture id. Copy values exactly from their source."""


def work_prompt(header: str, body: str, state, content: str) -> str:
    return (
        f"{header}\n{body or '(nothing yet)'}\n\n"
        f"Newest document: capture {state.capture_id}, {state.path} at commit {state.commit[:7]}\n"
        f"<<<\n{content}\n>>>"
    )


def question_prompt(header: str, body: str, questions) -> str:
    listed = "\n".join(f"- {question.id}: {question.question}" for question in questions)
    return (
        f"{header}\n{body or '(nothing)'}\n\n"
        "Answer each question for the project as it stands now, using only the context above. "
        f"Reply with only one fenced JSON block of this shape:\n{ANSWER_SHAPE}\n\nQuestions:\n{listed}"
    )


def readback_retry(blocked) -> str:
    lines = ["Read-back check: these values in your reply do not match the team's shared memory."]
    for item in blocked:
        if item.status == "needs_recheck":
            lines.append(f"- {item.key}: you used '{item.value}'. That value is waiting for a re-check against its source; do not use it.")
        else:
            lines.append(f"- {item.key}: you used '{item.value}'. The current bound value is '{item.bound_value}' (decision {item.decision_id}).")
    lines.append("Reply again in full, in the same format, using current values.")
    return "\n".join(lines)
````

**Step 4: write** `swarm_compare/swarms.py`:

````python
"""The three swarms. Each decides what shared context an agent sees."""

import difflib

from swarm_compare import prompts
from swarm_compare.models import APPROVAL_MODEL, DECISION_MODEL
from swarm_compare.openrouter import CallFailed
from swarm_memory.decide import EVIDENCE_CLASSES
from swarm_memory.decision_models import APPROVAL_SYSTEM, approval_prompt, decision_case, parse_approval, pick
from swarm_memory.risk import classify

SEARCH_LIMIT = 5
CHAR_BUDGET = 2000
CHUNK_CHARS = 400


def chunk(text: str, size: int = CHUNK_CHARS) -> list[str]:
    """Paragraph-first pieces of at most size characters."""
    pieces: list[str] = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        while len(paragraph) > size:
            cut = paragraph.rfind("\n", 0, size)
            if cut <= 0:
                cut = size
            head = paragraph[:cut].strip()
            if head:
                pieces.append(head)
            paragraph = paragraph[cut:].strip()
        if paragraph:
            pieces.append(paragraph)
    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 2 + len(piece) <= size:
            chunks[-1] += "\n\n" + piece
        else:
            chunks.append(piece)
    return chunks


def pack(hits, limit: int = SEARCH_LIMIT, budget: int = CHAR_BUDGET) -> list[dict]:
    """Keep hits in order; skip one that would pass the budget."""
    kept: list[dict] = []
    used = 0
    for hit in hits:
        if len(kept) >= limit:
            break
        size = len(hit["text"])
        if used + size > budget:
            continue
        kept.append(hit)
        used += size
    return kept


def work_query(role: str, previous: str, current: str) -> str:
    """Search text for a work turn: the role's focus plus the lines that changed."""
    changed = [
        line[1:]
        for line in difflib.unified_diff(previous.splitlines(), current.splitlines(), lineterm="", n=0)
        if line.startswith("+") and not line.startswith("+++")
    ]
    return (f"{role}: {prompts.FOCUS[role]}\n" + "\n".join(changed))[:CHAR_BUDGET]


def question_query(questions) -> str:
    return "\n".join(question.question for question in questions)


class FullContextSwarm:
    kind = "full"

    def __init__(self):
        self.history: list[dict] = []
        self.current: str | None = None

    def begin_round(self, state, content: str) -> None:
        self.current = state.capture_id
        self.history.append({"type": "state", "capture_id": state.capture_id, "path": state.path,
                             "commit": state.commit, "content": content})

    def context(self, role: str, query: str) -> tuple[str, str]:
        parts = []
        for entry in self.history:
            if entry["type"] == "state" and entry["capture_id"] == self.current:
                parts.append(f"[Document capture {entry['capture_id']}: the newest version, shown below]")
            elif entry["type"] == "state":
                parts.append(f"[Document capture {entry['capture_id']}, {entry['path']} at commit {entry['commit'][:7]}]\n{entry['content']}")
            else:
                parts.append(f"[{entry['role']}, round {entry['round']}]\n{entry['text']}")
        return prompts.FULL_HEADER, "\n\n".join(parts)

    def after_turn(self, role: str, state, text: str, block: dict) -> list:
        self.history.append({"type": "message", "role": role, "round": state.capture_id, "text": text})
        return []

    def read_back(self, relied_on) -> list:
        return []

    def end_round(self, state, content: str) -> None:
        self.current = None

    def dump(self) -> dict:
        return {"history": self.history}

    def load(self, data: dict | None) -> None:
        self.history = list(data["history"]) if data else []


class SearchSwarm:
    kind = "search"

    def __init__(self, index):
        self.index = index

    def begin_round(self, state, content: str) -> None:
        pass

    def context(self, role: str, query: str) -> tuple[str, str]:
        hits = pack(self.index.search(query, limit=SEARCH_LIMIT))
        return prompts.SEARCH_HEADER, "\n---\n".join(f"[{hit['source']}] {hit['text']}" for hit in hits)

    def after_turn(self, role: str, state, text: str, block: dict) -> list:
        pieces = chunk(text)
        self.index.add(pieces, [{"source": f"{role}, round {state.capture_id}"} for _ in pieces])
        return []

    def read_back(self, relied_on) -> list:
        return []

    def end_round(self, state, content: str) -> None:
        pieces = chunk(content)
        self.index.add(pieces, [{"source": f"document {state.capture_id} at {state.commit[:7]}"} for _ in pieces])

    def dump(self) -> dict:
        return {"index": self.index.dump()}

    def load(self, data: dict | None) -> None:
        if data:
            self.index.load(data["index"])


class MemorySwarm:
    kind = "memory"

    def __init__(self, service, index, registry, client, run_id: str):
        self.service = service
        self.index = index
        self.registry = registry
        self.client = client
        self.run_id = run_id
        self.outcomes: list[dict] = []
        self.rechecked: list[dict] = []
        self.recalled: dict[str, list[dict]] = {}

    def begin_round(self, state, content: str) -> None:
        self.service.record_capture(capture_id=state.capture_id, source=state.path, ref=state.commit, content=content)
        for key in self.service.recheck(state.path, content):
            self.rechecked.append({"round": state.capture_id, "key": key})

    def context(self, role: str, query: str) -> tuple[str, str]:
        card = self.service.role_card(self.registry.keys_for_role(role))
        kept = self.service.recall(query, self.index.search(query, limit=20))
        self.recalled[role] = list(kept)
        recall = "\n".join(hit["text"] for hit in kept)
        return prompts.MEMORY_HEADER, f"{card}\nRECALL\n{recall}"

    def after_turn(self, role: str, state, text: str, block: dict) -> list:
        for fact in block["facts"]:
            self.outcomes.append({"round": state.capture_id, **self.handle_fact(role, fact)})
        for hit in self.recalled.pop(role, []):
            used = any(item["key"] == hit["fact_key"] for item in block["relies_on"])
            self.service.note_use(hit["decision_id"], used=used)
        return self.read_back(block["relies_on"])

    def read_back(self, relied_on) -> list:
        return self.service.read_back(relied_on)

    def end_round(self, state, content: str) -> None:
        pass

    def handle_fact(self, role: str, fact: dict) -> dict:
        key, value, capture_id = fact["key"], fact["value"], fact["capture_id"]
        outcome: dict = {"role": role, "key": key, "value": value, "capture_id": capture_id}

        def remember(**extra) -> dict:
            result = self.service.remember(fact_key=key, value=value, agent_id=role, evidence_ids=[capture_id],
                                           write_class="fact", **extra)
            outcome.update(status=result.status, reason=result.reason, decision_id=result.decision_id)
            return outcome

        spec = self.registry.get(key)
        if spec is None:
            return remember(confidence=None)
        binding = self.service.store.current_binding(key)
        if binding is not None and binding["value"] == value:
            return remember(confidence=None)
        risk = classify(fact_key=key, declared_floor=spec.risk_floor, action=None,
                        multi_role=len(spec.roles) > 1, has_prior=binding is not None, model_class=None)
        needs_capture = risk.final_class in EVIDENCE_CLASSES
        if needs_capture and self.service.capture_with_value([capture_id], value) is None:
            return remember(confidence=None, blocked_reason="no_capture")
        candidates = [value] + ([binding["value"]] if binding is not None else [])
        state, questions = decision_case(
            fact_key=key, description=spec.description, candidates=candidates,
            current_value=binding["value"] if binding is not None else None,
            capture=self.service.store.capture(capture_id),
        )
        try:
            answers = self.client.decide(DECISION_MODEL, state, questions, run_id=self.run_id, kind="decision")
        except CallFailed:
            return remember(confidence=None, blocked_reason="decision_model_unavailable")
        choice = pick(answers, len(candidates))
        outcome["probability"] = choice.probability
        if choice.reason is not None:
            return remember(confidence=None, blocked_reason=choice.reason)
        approved = None
        if needs_capture and choice.probability >= risk.bar:
            try:
                text, _ = self.client.chat(APPROVAL_MODEL, APPROVAL_SYSTEM, approval_prompt(state, value),
                                           run_id=self.run_id, kind="approval", temperature=0.0)
                approved = parse_approval(text)
            except CallFailed:
                approved = False
            outcome["approved"] = approved
        return remember(confidence=choice.probability, approved=approved)

    def dump(self) -> dict:
        return {"index": self.index.dump(), "outcomes": self.outcomes, "rechecked": self.rechecked}

    def load(self, data: dict | None) -> None:
        if data:
            self.index.load(data["index"])
            self.outcomes = list(data["outcomes"])
            self.rechecked = list(data["rechecked"])
````

**Step 5:** run the whole suite. Expected: **116 passed**.

**Step 6:** `git add tests/test_swarms.py swarm_compare/prompts.py swarm_compare/swarms.py && git commit -m "feat: add the full-context, search-only and memory swarms"`

---

## Task 10: Scoring, report, runner

**How the runner works:**
- It saves a checkpoint after every complete round: the turns, the swarm state, and a copy of the memory SQLite file.
- A restart resumes from the last complete round, and skips runs whose result says `complete`.
- Calls made during an interrupted round stay in the call log and count toward that run's usage.
- The run is marked `"resumed": true`.

**Files:**
- Test: `tests/test_runner_and_report.py`
- Create: `swarm_compare/scoring.py`, `swarm_compare/report.py`, `swarm_compare/runner.py`

**Step 1: write the failing test** `tests/test_runner_and_report.py`:

````python
from pathlib import Path

from swarm_compare.report import comparable, render, summary_rows
from swarm_compare.runner import load_checkpoint, save_checkpoint
from swarm_compare.scoring import score_run, usage_for
from swarm_compare.tasks import load_task


def test_a_checkpoint_restores_the_round_and_the_memory_file(tmp_path: Path):
    run_dir = tmp_path / "A-memory-r1"
    run_dir.mkdir()
    (run_dir / "memory.sqlite").write_bytes(b"after round one")
    save_checkpoint(run_dir, 1, {"history": []}, [{"role": "planner"}])
    (run_dir / "memory.sqlite").write_bytes(b"partial round two")
    data = load_checkpoint(run_dir)
    assert data["round_done"] == 1
    assert data["turns"] == [{"role": "planner"}]
    assert (run_dir / "memory.sqlite").read_bytes() == b"after round one"


def test_without_a_checkpoint_a_partial_memory_file_is_removed(tmp_path: Path):
    run_dir = tmp_path / "A-memory-r1"
    run_dir.mkdir()
    (run_dir / "memory.sqlite").write_bytes(b"partial")
    data = load_checkpoint(run_dir)
    assert data["round_done"] == 0
    assert not (run_dir / "memory.sqlite").exists()


def test_usage_counts_only_successful_calls_of_that_run():
    records = [
        {"run_id": "A-full-r1", "status": "ok", "kind": "agent", "prompt_tokens": 10, "completion_tokens": 2, "cost": 0.5},
        {"run_id": "A-full-r1", "status": "ok", "kind": "agent", "prompt_tokens": 5, "completion_tokens": 1, "cost": None, "usage_missing": True},
        {"run_id": "A-full-r1", "status": "error", "kind": "agent"},
        {"run_id": "A-search-r1", "status": "ok", "kind": "agent", "prompt_tokens": 99, "completion_tokens": 9, "cost": 9.0},
    ]
    usage = usage_for(records, "A-full-r1")
    assert usage["calls"] == 2
    assert usage["failed_attempts"] == 1
    assert usage["total_tokens"] == 18
    assert usage["cost_usd"] == 0.5
    assert usage["usage_missing_calls"] == 1


def _turn(relied_before, relied_after=None, checks_after=()):
    return {"relied_before": relied_before, "relied_after": relied_after if relied_after is not None else relied_before,
            "checks_after": list(checks_after), "format_retry": False, "format_failure": False, "readback_retry": False}


def test_scores_count_blocked_values_only_before_read_back():
    task = load_task("A")
    stale_item = {"key": "build.tests_passing", "value": "40", "decision_id": ""}
    turns = [_turn([stale_item], [stale_item], [{"status": "differs"}])]
    answers = [{"before": {"A-q1": "40", "A-q2": "deesatzed/Shared_Swarm_Memory", "A-q3": "0.92"},
                "after": {"A-q1": "40", "A-q2": "deesatzed/Shared_Swarm_Memory", "A-q3": "0.92"},
                "blocked_after": ["A-q1"], "format_retry": False, "format_failure": False, "readback_retry": True}]
    memory = score_run(task, "memory", turns, answers)
    full = score_run(task, "full", turns, answers)
    assert (memory["stale_relied_before"], memory["stale_relied_after"]) == (1, 0)
    assert (full["stale_relied_before"], full["stale_relied_after"]) == (1, 1)
    assert (memory["stale_answers_before"], memory["stale_answers_after"]) == (1, 0)
    assert (memory["correct_before"], memory["correct_after"], memory["answers_total"]) == (2, 2, 3)
    assert full["stale_answers_after"] == 1


def _result(task, swarm, repeat, status="complete"):
    scores = dict.fromkeys(["answers_total", "correct_before", "correct_after", "stale_answers_before",
                            "stale_answers_after", "stale_relied_before", "stale_relied_after"], 1)
    usage = {"total_tokens": 100, "cost_usd": 0.01, "usage_missing_calls": 0}
    return {"task": task, "swarm": swarm, "repeat": repeat, "status": status, "scores": scores, "usage": usage}


def test_only_repeats_finished_by_all_three_swarms_are_compared():
    results = [_result("A", kind, 1) for kind in ("full", "search", "memory")]
    results += [_result("A", "full", 2), _result("A", "search", 2), _result("A", "memory", 2, "incomplete")]
    kept = comparable(results)
    assert len(kept) == 3
    assert {result["repeat"] for result in kept} == {1}


def test_summary_sums_each_swarm():
    results = [_result("A", kind, repeat) for kind in ("full", "search", "memory") for repeat in (1, 2)]
    rows = summary_rows(results)
    assert [row["swarm"] for row in rows] == ["full", "search", "memory"]
    assert rows[0]["runs"] == 2
    assert rows[0]["total_tokens"] == 200
    text = render(rows, excluded=0)
    assert "| Our memory | 2 |" in text
````

**Step 2:** run it. Expected: `No module named 'swarm_compare.report'`.

**Step 3: write** `swarm_compare/scoring.py`:

````python
"""Per-run numbers: usage from the call log, and answer and stale-value scores."""

from swarm_compare.blocks import is_correct, stale_hits, stale_relied
from swarm_compare.tasks import stale_by_key
from swarm_memory.readback import BLOCKING


def usage_for(records, run_id: str) -> dict:
    rows = [row for row in records if row.get("run_id") == run_id]
    ok = [row for row in rows if row.get("status") == "ok"]
    by_kind: dict[str, dict] = {}
    for row in ok:
        kind = by_kind.setdefault(row["kind"], {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0})
        kind["calls"] += 1
        kind["prompt_tokens"] += row.get("prompt_tokens") or 0
        kind["completion_tokens"] += row.get("completion_tokens") or 0
        kind["cost_usd"] += row.get("cost") or 0.0
    prompt = sum(kind["prompt_tokens"] for kind in by_kind.values())
    completion = sum(kind["completion_tokens"] for kind in by_kind.values())
    return {
        "calls": len(ok),
        "failed_attempts": len(rows) - len(ok),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "cost_usd": sum(kind["cost_usd"] for kind in by_kind.values()),
        "usage_missing_calls": sum(1 for row in ok if row.get("usage_missing")),
        "by_kind": by_kind,
    }


def _unblocked(items, checks, kind: str) -> list[dict]:
    if kind != "memory":
        return list(items)
    return [item for item, check in zip(items, checks) if check["status"] not in BLOCKING]


def score_run(task, kind: str, turns: list[dict], answer_rows: list[dict]) -> dict:
    stale = stale_by_key(task)
    relied_before = sum(len(stale_relied(turn["relied_before"], stale)) for turn in turns)
    relied_after = sum(
        len(stale_relied(_unblocked(turn["relied_after"], turn["checks_after"], kind), stale)) for turn in turns
    )
    totals = {"answers_total": 0, "correct_before": 0, "correct_after": 0,
              "stale_answers_before": 0, "stale_answers_after": 0}
    for row in answer_rows:
        blocked = set(row.get("blocked_after", [])) if kind == "memory" else set()
        for question in task.questions:
            before = row["before"].get(question.id)
            after = row["after"].get(question.id)
            totals["answers_total"] += 1
            totals["correct_before"] += is_correct(before, question.expect)
            totals["stale_answers_before"] += bool(stale_hits(before, question.stale))
            if question.id not in blocked:
                totals["correct_after"] += is_correct(after, question.expect)
                totals["stale_answers_after"] += bool(stale_hits(after, question.stale))
    return {
        **totals,
        "relied_total": sum(len(turn["relied_before"]) for turn in turns),
        "stale_relied_before": relied_before,
        "stale_relied_after": relied_after,
        "format_retries": sum(row["format_retry"] for row in turns + answer_rows),
        "format_failures": sum(row["format_failure"] for row in turns + answer_rows),
        "readback_retries": sum(row["readback_retry"] for row in turns + answer_rows),
    }
````

**Step 4: write** `swarm_compare/report.py`:

````python
"""Summary table across runs. Only tasks and repeats finished by all three swarms count."""

import json
from pathlib import Path

KINDS = ("full", "search", "memory")
LABELS = {"full": "Full context", "search": "Search only", "memory": "Our memory"}


def load_results(results_dir: Path) -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(Path(results_dir).glob("*.json"))]


def comparable(results: list[dict]) -> list[dict]:
    groups: dict[tuple, dict] = {}
    for result in results:
        if result["status"] == "complete":
            groups.setdefault((result["task"], result["repeat"]), {})[result["swarm"]] = result
    return [result for group in groups.values() if set(group) == set(KINDS) for result in group.values()]


def summary_rows(results: list[dict]) -> list[dict]:
    rows = []
    for kind in KINDS:
        runs = [result for result in results if result["swarm"] == kind]
        if not runs:
            continue

        def total(section: str, field: str) -> float:
            return sum(run[section][field] for run in runs)

        rows.append({
            "swarm": kind,
            "runs": len(runs),
            "answers_total": total("scores", "answers_total"),
            "correct_before": total("scores", "correct_before"),
            "correct_after": total("scores", "correct_after"),
            "stale_answers_before": total("scores", "stale_answers_before"),
            "stale_answers_after": total("scores", "stale_answers_after"),
            "stale_relied_before": total("scores", "stale_relied_before"),
            "stale_relied_after": total("scores", "stale_relied_after"),
            "total_tokens": total("usage", "total_tokens"),
            "cost_usd": total("usage", "cost_usd"),
            "usage_missing_calls": total("usage", "usage_missing_calls"),
        })
    return rows


def render(rows: list[dict], excluded: int) -> str:
    lines = [
        "# Swarm comparison results",
        "",
        "Counts are summed over the runs shown. \"Before\" is the agents' own output; \"after\" is what remains once",
        "the memory swarm's read-back check blocks mismatched values (the other swarms have no read-back, so their",
        "before and after are the same). Tokens and cost are the provider's reported usage for every call in the runs.",
        "",
        "| Swarm | Runs | Correct answers (before / after) | Stale answers (before / after) | Stale relied-on values (before / after) | Tokens | Cost (USD) | Calls without usage |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {LABELS[row['swarm']]} | {row['runs']} "
            f"| {row['correct_before']} / {row['correct_after']} of {row['answers_total']} "
            f"| {row['stale_answers_before']} / {row['stale_answers_after']} "
            f"| {row['stale_relied_before']} / {row['stale_relied_after']} "
            f"| {row['total_tokens']} | {row['cost_usd']:.6f} | {row['usage_missing_calls']} |"
        )
    lines += ["", f"Runs left out because not all three swarms finished that task and repeat: {excluded}."]
    return "\n".join(lines) + "\n"


def write_summary(results_dir: Path) -> str:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    results = load_results(results_dir)
    kept = comparable(results)
    text = render(summary_rows(kept), len(results) - len(kept))
    (results_dir / "summary.md").write_text(text, encoding="utf-8")
    return text
````

**Step 5: write** `swarm_compare/runner.py`:

````python
"""Run the swarms on the real tasks and write one result file per run.

    python -m swarm_compare.runner --task A --swarms full,search,memory --repeats 1
    python -m swarm_compare.runner --report

Needs SWARM_EXP_SPEND_LIMIT_USD. Reads only OPENROUTER_API_KEY from
SWARM_EXP_CREDENTIALS_FILE (default /Volumes/WS4TB/merged.env).
"""

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from swarm_compare import prompts
from swarm_compare.blocks import parse_answers, parse_turn_block
from swarm_compare.models import AGENT_MODEL, APPROVAL_MODEL, DECISION_MODEL, EMBEDDING_MODEL
from swarm_compare.openrouter import (
    CallFailed, CallLog, OpenRouter, SpendLimitNotSet, SpendLimitReached, SpendMeter, credentials_path, read_key,
)
from swarm_compare.report import write_summary
from swarm_compare.scoring import score_run, usage_for
from swarm_compare.swarms import FullContextSwarm, MemorySwarm, SearchSwarm, question_query, work_query
from swarm_compare.tasks import PACKAGE, load_task, repo_root, state_text, task_ids
from swarm_memory.readback import BLOCKING
from swarm_memory.registry import Registry
from swarm_memory.service import MemoryService
from swarm_memory.vector_index import VectorIndex

RUNS = PACKAGE / "runs"
RESULTS = PACKAGE / "results"
KEYS = PACKAGE / "keys.json"
KINDS = ("full", "search", "memory")
STOP_STATUSES = frozenset({401, 402, 403})


def save_checkpoint(run_dir: Path, round_done: int, swarm_state: dict, turns: list) -> None:
    sqlite_name = None
    memory = run_dir / "memory.sqlite"
    if memory.exists():
        sqlite_name = f"checkpoint-r{round_done}.sqlite"
        shutil.copyfile(memory, run_dir / sqlite_name)
    temporary = run_dir / "checkpoint.json.tmp"
    temporary.write_text(json.dumps({"round_done": round_done, "swarm_state": swarm_state,
                                     "turns": turns, "sqlite": sqlite_name}), encoding="utf-8")
    temporary.replace(run_dir / "checkpoint.json")


def load_checkpoint(run_dir: Path) -> dict:
    """State after the last complete round. With no checkpoint, a partial memory file is removed."""
    run_dir.mkdir(parents=True, exist_ok=True)
    memory = run_dir / "memory.sqlite"
    path = run_dir / "checkpoint.json"
    if not path.exists():
        memory.unlink(missing_ok=True)
        return {"round_done": 0, "swarm_state": None, "turns": [], "sqlite": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("sqlite"):
        shutil.copyfile(run_dir / data["sqlite"], memory)
    return data


def build_swarm(kind: str, run_dir: Path, client, registry, run_id: str):
    def embed(texts):
        return client.embed(EMBEDDING_MODEL, texts, run_id=run_id, kind="embedding")

    if kind == "full":
        return FullContextSwarm()
    if kind == "search":
        return SearchSwarm(VectorIndex(embed, EMBEDDING_MODEL))
    index = VectorIndex(embed, EMBEDDING_MODEL)
    service = MemoryService(run_dir / "memory.sqlite", index, registry)
    return MemorySwarm(service, index, registry, client, run_id)


def take_turn(swarm, client, registry, run_id: str, role: str, state, content: str, previous: str) -> dict:
    system = prompts.system_prompt(role, registry)
    header, body = swarm.context(role, work_query(role, previous, content))
    user = prompts.work_prompt(header, body, state, content)
    text, _ = client.chat(AGENT_MODEL, system, user, run_id=run_id, kind="agent")
    block = parse_turn_block(text)
    format_retry = block is None
    if format_retry:
        text, _ = client.chat(AGENT_MODEL, system, user + "\n\n" + prompts.FORMAT_RETRY,
                              run_id=run_id, kind="agent_format_retry")
        block = parse_turn_block(text)
    format_failure = block is None
    block = block or {"relies_on": [], "facts": []}
    checks = swarm.after_turn(role, state, text, block)
    relied_after, checks_after, readback_retry = block["relies_on"], checks, False
    blocked = [check for check in checks if check.status in BLOCKING]
    if blocked:
        readback_retry = True
        retry_text, _ = client.chat(AGENT_MODEL, system, user + "\n\n" + prompts.readback_retry(blocked),
                                    run_id=run_id, kind="agent_readback_retry")
        retry_block = parse_turn_block(retry_text)
        relied_after = retry_block["relies_on"] if retry_block else []
        checks_after = swarm.read_back(relied_after)
    return {
        "round": state.capture_id,
        "role": role,
        "text": text,
        "format_retry": format_retry,
        "format_failure": format_failure,
        "facts": block["facts"],
        "relied_before": block["relies_on"],
        "checks_before": [asdict(check) for check in checks],
        "readback_retry": readback_retry,
        "relied_after": relied_after,
        "checks_after": [asdict(check) for check in checks_after],
    }


def _keyed(task, answers: dict) -> list[dict]:
    return [{"key": q.key, "value": answers[q.id], "question_id": q.id}
            for q in task.questions if q.key and q.id in answers]


def answer_questions(swarm, client, registry, run_id: str, role: str, task) -> dict:
    system = prompts.system_prompt(role, registry)
    header, body = swarm.context(role, question_query(task.questions))
    user = prompts.question_prompt(header, body, task.questions)
    text, _ = client.chat(AGENT_MODEL, system, user, run_id=run_id, kind="agent_answers")
    parsed = parse_answers(text)
    format_retry = parsed is None
    if format_retry:
        text, _ = client.chat(AGENT_MODEL, system, user + "\n\n" + prompts.FORMAT_RETRY_ANSWERS,
                              run_id=run_id, kind="agent_format_retry")
        parsed = parse_answers(text)
    before = parsed["answers"] if parsed else {}
    keyed = _keyed(task, before)
    checks = swarm.read_back(keyed)
    after, checks_after, readback_retry = dict(before), checks, False
    blocked = [check for check in checks if check.status in BLOCKING]
    if blocked:
        readback_retry = True
        retry_text, _ = client.chat(AGENT_MODEL, system, user + "\n\n" + prompts.readback_retry(blocked),
                                    run_id=run_id, kind="agent_readback_retry")
        retried = parse_answers(retry_text)
        if retried:
            after = dict(retried["answers"])
        keyed = _keyed(task, after)
        checks_after = swarm.read_back(keyed)
    blocked_after = [item["question_id"] for item, check in zip(keyed, checks_after) if check.status in BLOCKING]
    return {
        "role": role,
        "text": text,
        "format_retry": format_retry,
        "format_failure": parsed is None,
        "before": before,
        "after": after,
        "checks_before": [asdict(check) for check in checks],
        "readback_retry": readback_retry,
        "checks_after": [asdict(check) for check in checks_after],
        "blocked_after": blocked_after,
    }


def _commit() -> str:
    return subprocess.run(["git", "-C", str(repo_root()), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()


def run_one(task, kind: str, repeat: int, client, log: CallLog, registry) -> str:
    run_id = f"{task.id}-{kind}-r{repeat}"
    result_path = RESULTS / f"{run_id}.json"
    if result_path.exists() and json.loads(result_path.read_text(encoding="utf-8"))["status"] == "complete":
        return "skipped (already complete)"
    run_dir = RUNS / run_id
    checkpoint = load_checkpoint(run_dir)
    swarm = build_swarm(kind, run_dir, client, registry, run_id)
    swarm.load(checkpoint["swarm_state"])
    turns = list(checkpoint["turns"])
    answer_rows: list[dict] = []
    status, error, stop = "complete", None, None
    try:
        for number in range(checkpoint["round_done"], len(task.states)):
            state = task.states[number]
            content = state_text(state)
            previous = state_text(task.states[number - 1]) if number > 0 else ""
            swarm.begin_round(state, content)
            for role in prompts.ROLES:
                turns.append(take_turn(swarm, client, registry, run_id, role, state, content, previous))
            swarm.end_round(state, content)
            save_checkpoint(run_dir, number + 1, swarm.dump(), turns)
        for role in prompts.ROLES:
            answer_rows.append(answer_questions(swarm, client, registry, run_id, role, task))
    except SpendLimitReached as exc:
        status, error, stop = "incomplete", str(exc), exc
    except CallFailed as exc:
        status, error = "failed", str(exc)
        stop = exc if exc.status in STOP_STATUSES else None
    result = {
        "run_id": run_id,
        "task": task.id,
        "swarm": kind,
        "repeat": repeat,
        "status": status,
        "error": error,
        "resumed": checkpoint["round_done"] > 0,
        "code_commit": _commit(),
        "models": {"agent": AGENT_MODEL, "decision": DECISION_MODEL, "approval": APPROVAL_MODEL,
                   "embedding": EMBEDDING_MODEL},
        "usage": usage_for(log.records(), run_id),
        "scores": score_run(task, kind, turns, answer_rows),
        "memory": swarm.dump() if kind == "memory" else None,
        "turns": turns,
        "answers": answer_rows,
    }
    if result["memory"] is not None:
        result["memory"].pop("index", None)
    RESULTS.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if stop is not None:
        raise stop
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", choices=task_ids(), action="append")
    parser.add_argument("--swarms", default=",".join(KINDS))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--first-repeat", type=int, default=1)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    if args.report:
        print(write_summary(RESULTS))
        return 0
    kinds = [kind for kind in args.swarms.split(",") if kind]
    if not kinds or any(kind not in KINDS for kind in kinds):
        parser.error(f"--swarms must be a comma-separated subset of {','.join(KINDS)}")
    log = CallLog(RUNS / "calls.jsonl")
    try:
        meter = SpendMeter.from_env(log)
    except SpendLimitNotSet as exc:
        print(f"Not started: {exc}", file=sys.stderr)
        return 3
    client = OpenRouter(read_key(credentials_path()), meter, log)
    registry = Registry.load(KEYS)
    try:
        for task_id in args.task or task_ids():
            task = load_task(task_id)
            for repeat in range(args.first_repeat, args.first_repeat + args.repeats):
                for kind in kinds:
                    status = run_one(task, kind, repeat, client, log, registry)
                    print(f"{task.id}-{kind}-r{repeat}: {status}. Spent {meter.spent:.6f} of {meter.limit:.6f} USD.",
                          flush=True)
    except (SpendLimitReached, CallFailed) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        print(write_summary(RESULTS))
        return 2
    finally:
        client.close()
    print(write_summary(RESULTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
````

**Step 6:** run the whole suite. Expected: **122 passed**.

**Step 7: check the runner refuses to spend without a limit**

```sh
env -u SWARM_EXP_SPEND_LIMIT_USD $PY -B -m swarm_compare.runner --task A --swarms full; echo "exit=$?"
# expect: "Not started: SWARM_EXP_SPEND_LIMIT_USD is not set; no paid call is allowed" and exit=3
```

**Step 8:** `git add tests/test_runner_and_report.py swarm_compare/scoring.py swarm_compare/report.py swarm_compare/runner.py && git commit -m "feat: add the resumable runner, scoring and summary report"`

---

## Task 11: Live-check tests (written, not run)

**Files:**
- Create: `tests/conftest.py`, `tests/test_live_models.py`

**Step 1: write** `tests/conftest.py`:

````python
import pytest


def pytest_addoption(parser):
    parser.addoption("--run-live", action="store_true", default=False, help="run tests that call paid models")


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls a paid model; runs only with --run-live")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return
    skip = pytest.mark.skip(reason="calls a paid model; needs --run-live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
````

**Step 2: write** `tests/test_live_models.py`:

````python
"""One real call per model. Run only with --run-live and SWARM_EXP_SPEND_LIMIT_USD set."""

import pytest

from swarm_compare.models import AGENT_MODEL, APPROVAL_MODEL, DECISION_MODEL, EMBEDDING_MODEL
from swarm_compare.openrouter import CallLog, OpenRouter, SpendMeter, credentials_path, read_key
from swarm_compare.runner import RUNS
from swarm_memory.decision_models import APPROVAL_SYSTEM, approval_prompt, parse_approval

pytestmark = pytest.mark.live
RUN_ID = "live-check"


@pytest.fixture(scope="module")
def client():
    log = CallLog(RUNS / "calls.jsonl")
    live = OpenRouter(read_key(credentials_path()), SpendMeter.from_env(log), log)
    yield live
    live.close()


def test_agent_model_follows_an_exact_instruction(client):
    text, result = client.chat(AGENT_MODEL, "Reply with exactly SWARM_OK and nothing else.", "Connection check.",
                               run_id=RUN_ID, kind="live_check", max_tokens=64, temperature=0.0)
    assert text.strip() == "SWARM_OK"
    assert result.cost is not None


def test_decision_model_returns_a_noul_probability(client):
    answers = client.decide(DECISION_MODEL, "The color is green.",
                            {"q": {"type": "noul", "instructions": "Does the state say the color is green?"}},
                            run_id=RUN_ID, kind="live_check")
    probability = answers["q"]["noul"]
    assert isinstance(probability, float)
    assert 0.5 < probability <= 1.0


def test_approval_model_returns_parseable_json(client):
    state = ("Key: model.decision (Model id that makes routine decisions)\n"
             "Source excerpt:\nThe user selected liquid/d1-ultra for typed decisions.")
    text, _ = client.chat(APPROVAL_MODEL, APPROVAL_SYSTEM, approval_prompt(state, "liquid/d1-ultra"),
                          run_id=RUN_ID, kind="live_check", temperature=0.0)
    assert parse_approval(text) is True


def test_embedding_model_returns_3072_dimensions(client):
    [vector] = client.embed(EMBEDDING_MODEL, ["The color is green."], run_id=RUN_ID, kind="live_check")
    assert len(vector) == 3072
````

**Step 3:** run the whole suite without `--run-live`. Expected: **122 passed, 4 skipped**.

**Step 4:** `git add tests/conftest.py tests/test_live_models.py && git commit -m "test: add opt-in live checks for the four models"`

**Step 5:** update this file's tracker and progress log, then commit it (`git add GOAL_RUN_EXP.md`).

---

## Task 12: Live checks (paid; needs the spending limit)

**Gate:** `SWARM_EXP_SPEND_LIMIT_USD` must be set in the environment. If it is not, stop here and report as described under "Inputs only the user can give".

**Step 1:**

```sh
$PY -B -m pytest tests/test_live_models.py --run-live -v -p no:cacheprovider
```

Expected: 4 passed. Each test makes one real call, and every call is written to `swarm_compare/runs/calls.jsonl`.

**Step 2: if a check fails**
- **HTTP 401, 402 or 403:** stop and tell the user. These are key, credit or permission problems.
- **HTTP 404:** stop and ask the user. The model id is not available, and only the user chooses replacements.
- **The decision check fails on the response shape:** that means `answers["q"]["noul"]` is missing. Record the actual answer object from the call log in the progress log. Then stop and ask the user before changing `swarm_memory/decision_models.py`.
- **The approval check returns no parseable JSON:** record the reply text from the log. Raising `max_tokens` (default 2,000) is allowed once. Otherwise stop and report.

**Step 3: write a receipt.** Copy the live-check records into a committed receipt. The records hold outputs and usage, never the key or headers.

```sh
$PY -B -c "import json, pathlib; rows=[json.loads(l) for l in pathlib.Path('swarm_compare/runs/calls.jsonl').read_text().splitlines() if l.strip()]; out=pathlib.Path('swarm_compare/receipts/live-check-'+__import__('datetime').date.today().isoformat()+'.json'); out.parent.mkdir(exist_ok=True); out.write_text(json.dumps([r for r in rows if r.get('run_id')=='live-check'], indent=1)+'\n')"
grep -c 'sk-' swarm_compare/receipts/live-check-*.json   # expect 0
```

**Step 4:** `git add swarm_compare/receipts/ && git commit -m "docs: record the live model checks"`. Update the tracker and progress log with the four results, the served model ids and the reported cost.

---

## Task 13: Trial run, then stop

**Step 1:**

```sh
cd /Volumes/WS4TB/Swarm_Mem_Share_exp
$PY -B -m swarm_compare.runner --task A --repeats 1
```

This runs task A, repeat 1, in all three swarms, in the order full, search, memory. Each run makes:
- 15 work turns
- 5 answer turns
- retries
- for search and memory: embedding calls
- for memory: `d1-ultra` and `gemini-4-argon` calls

Output:
- `swarm_compare/results/A-<swarm>-r1.json`
- `swarm_compare/results/summary.md`

Exit codes:
- 0: complete
- 2: stopped by the spending limit or by an auth failure. The summary is still written.
- 3: the limit is not set

**Step 2: check the results before reporting**
- Every result file has `"status": "complete"`. If not, report its `error`.
- `usage.usage_missing_calls` is 0. If not, report it: those calls have no cost figure.
- `grep -c 'sk-' swarm_compare/results/*.json` gives 0 for every file.

**Step 3:** `git add swarm_compare/results/ && git commit -m "docs: record the trial comparison run"`. Update the tracker and progress log.

**Step 4: STOP.** Report to the user in plain language:
- the summary table
- spend so far, from the runner's printed line
- format failures and read-back retries, from each result's `scores`
- the memory swarm's fact outcomes, counted by `status` and `reason` from `memory.outcomes`
- any surprises

Then ask whether to run the full comparison. Do not start Task 14 without a yes.

---

## Task 14: Full run (only after the user says go)

**Step 1:**

```sh
$PY -B -m swarm_compare.runner --repeats 3
```

This runs both tasks with repeats 1–3. Runs already complete, such as the trial, are skipped.

If the spending limit stops the work, the summary covers only task/repeat sets that all three swarms finished. Report how many runs were left out.

**Step 2:** check the same items as Task 13 Step 2, commit `swarm_compare/results/`, then update the tracker and progress log.

**Step 3: report**
- the summary table
- for M1: stale-value actions after read-back in the memory swarm, with the target of zero met or not met
- for M2: correct answers and tokens for each swarm
- runs left out
- failures

Do not merge or push. Ask the user what to do next.

---

## Completion

The goal is complete when Tasks 0–14 have evidence in the tracker and the results are committed. "Complete" means the comparison has been run and reported. It does not mean the memory app won. Whichever way the numbers fall, they are the result.

## Progress log

Append one entry per working session:

```text
Date / task:
Change and purpose:
Command, result, exit code (exact test counts):
Evidence path or commit:
Decision or assumption:
Blocker or open item:
Next action:
```

- 2026-10-19 / planning: The design was approved and committed (`3db623e`). This plan was written and its code checked in a scratch copy: 122 passed and 4 skipped without `--run-live`, and no model was called. Next action: Task 0.
