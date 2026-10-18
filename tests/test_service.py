from pathlib import Path

from swarm_memory.service import MemoryService


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
    e1 = _experience(service, "reviewer_a", "run log one")
    e2 = _experience(service, "reviewer_b", "run log two")
    service.remember(
        fact_key="genome.caller",
        value="dragen",
        agent_id="coder",
        evidence_ids=[e1, e2],
        write_class="fact",
        confidence=0.95,
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


def _high_write(service, evidence_ids, agent_id="coder"):
    return service.remember(
        fact_key="genome.caller",
        value="dragen",
        agent_id=agent_id,
        evidence_ids=evidence_ids,
        write_class="fact",
        confidence=0.99,
    )


def test_an_experience_write_returns_its_candidate_id(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    assert _experience(service, "reviewer_a", "run log") is not None


def test_high_key_with_unknown_evidence_ids_stays_open(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    result = _high_write(service, ["e1", "e2"])
    assert result.status == "open"
    assert service.store.current_binding("genome.caller") is None


def test_high_key_does_not_count_the_proposers_own_experience(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    own = _experience(service, "coder", "my own note")
    other = _experience(service, "reviewer_a", "run log")
    result = _high_write(service, [own, other])
    assert result.status == "open"


def test_high_key_with_two_experiences_from_one_other_agent_stays_open(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    ids = [_experience(service, "reviewer_a", "log one"), _experience(service, "reviewer_a", "log two")]
    assert _high_write(service, ids).status == "open"


def test_high_key_with_two_independent_agents_binds(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    ids = [_experience(service, "reviewer_a", "log one"), _experience(service, "reviewer_b", "log two")]
    result = _high_write(service, ids)
    assert result.status == "bound"
    assert service.store.current_binding("genome.caller")["value"] == "dragen"


def test_a_fact_candidate_id_is_not_evidence(tmp_path: Path):
    service = MemoryService(tmp_path / "memory.sqlite", RecordingIndex())
    fact_a = service.remember(
        fact_key="style.quote", value="x", agent_id="reviewer_a", evidence_ids=[],
        write_class="fact", confidence=0.9, declared_floor="low",
    )
    assert fact_a.candidate_id is not None
    result = _high_write(service, [fact_a.candidate_id, fact_a.decision_id])
    assert result.status == "open"
