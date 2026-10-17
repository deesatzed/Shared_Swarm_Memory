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
