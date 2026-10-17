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
