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


def test_an_oversized_hit_is_skipped_and_a_later_hit_can_fit():
    hits = [
        {"decision_id": "d1", "fact_key": "a", "text": "x" * 100},
        {"decision_id": "d2", "fact_key": "b", "text": "ok"},
    ]
    bindings = {"a": "d1", "b": "d2"}
    kept = filter_hits(hits, bindings, limit=5, char_budget=10, per_item_cap=10)
    assert [hit["text"] for hit in kept] == ["ok"]


def test_a_hit_over_the_item_cap_is_skipped_even_when_the_budget_allows_it():
    hits = [
        {"decision_id": "d1", "fact_key": "a", "text": "x" * 11},
        {"decision_id": "d2", "fact_key": "b", "text": "ok"},
    ]
    bindings = {"a": "d1", "b": "d2"}
    kept = filter_hits(hits, bindings, limit=5, char_budget=100, per_item_cap=10)
    assert [hit["text"] for hit in kept] == ["ok"]


def test_higher_utility_is_packed_first():
    hits = [
        {"decision_id": "d_low", "fact_key": "a", "text": "low"},
        {"decision_id": "d_high", "fact_key": "b", "text": "high"},
    ]
    bindings = {"a": "d_low", "b": "d_high"}
    kept = filter_hits(hits, bindings, limit=1, char_budget=2000, scores={"d_low": 0.1, "d_high": 0.9})
    assert [hit["text"] for hit in kept] == ["high"]
