# Proposal: evidence must count, not only confidence

Date: 2026-10-17
Status: APPROVED 2026-10-17 by the user, with one change: the evidence rule applies to high and critical classes only (standard and low need none). Implemented on this branch; design document updated.

## Plain version

Today a fact binds when the proposing agent reports a confidence number above the bar. Nothing checks the number, and the evidence ids it cites can be any strings. A confidently wrong agent can bind a wrong fact. This proposal makes the evidence itself a condition for binding, so confidence alone is never enough.

## What the code does now (read from the repo)

- `swarm_memory/decide.py`: `evaluate` binds when `confidence >= bar`. It checks evidence only when replacing a bound value (the new ids must not be a subset of the old ones).
- A first write needs no evidence at all. The design says "both candidates are cited"; the code does not enforce it.
- `evidence_ids` are free strings. They are not looked up anywhere.
- Confidence above 1 is accepted.

## Proposed rules (the part you decide)

1. **Evidence ids must resolve.** Each id must name a stored `experience` candidate in SQLite. An unknown id counts as no evidence.
2. **Evidence must be independent of the proposer.** An experience written by the proposing agent does not count toward its own fact.
3. **Minimum distinct evidence by class**, counted after rules 1 and 2:

   | Class | Distinct counting evidence needed |
   |---|---|
   | low | 0 |
   | standard | 0 (user decision: not required) |
   | high | 2, from at least 2 different agents |
   | critical | 2, from at least 2 different agents |

4. **Confidence must be in [0, 1].** Anything else stays open.
5. Below the evidence minimum, the instance stays `open` with reason `insufficient_evidence`. Confidence is still recorded and the bar still applies on top.

The numbers in the table are my starting suggestion. They are not measured and you may want different ones.

## What this does not solve

- An agent can still write a false experience, and a second agent can still copy it. This raises the cost of a wrong bind. It does not prove correctness.
- Calibrating confidence against known answers (your option 2) is still open and needs a labeled set of real cases.

## Changes if approved

- `swarm_memory/store.py`: a lookup returning each experience's id and agent.
- `swarm_memory/service.py`: pass resolved evidence into `Proposal`.
- `swarm_memory/decide.py`: apply rules 2 to 5.
- Tests first, each failing before the code: unknown id, self-authored evidence, one agent supplying two ids on a high key, confidence 1.5, and a passing case.
- Existing tests that bind with made-up evidence strings will need real experiences written first. This affects `tests/test_decide.py` and `tests/test_service.py`.
- Update `docs/plans/2026-10-17-swarm-decision-memory-design.md` and the handoff in the same change.

## Decisions needed from you

1. Approve rules 1 to 5 as written, or change the table?
2. Should this apply to the first write on a standard key, or only to high and critical?
