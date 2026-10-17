from pathlib import Path

from swarm_memory.service import MemoryService


class RecordingIndex:
    """Test double. Records index attempts. It is not a memory store."""

    def __init__(self):
        self.sentences = []

    def write_bound_sentence(self, decision_id, fact_key, text):
        self.sentences.append((decision_id, fact_key, text))


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
