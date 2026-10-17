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


def test_char_budget_and_limit_stop_the_list():
    hits = [
        {"decision_id": "d1", "fact_key": "a", "text": "one"},
        {"decision_id": "d2", "fact_key": "b", "text": "two"},
        {"decision_id": "d3", "fact_key": "c", "text": "three"},
    ]
    bindings = {"a": "d1", "b": "d2", "c": "d3"}
    kept = filter_hits(hits, bindings, limit=5, char_budget=3)
    assert [hit["text"] for hit in kept] == ["one"]
    kept_limit = filter_hits(hits, bindings, limit=1, char_budget=2000)
    assert [hit["text"] for hit in kept_limit] == ["one"]
