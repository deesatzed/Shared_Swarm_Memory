from swarm_memory.card import render_card


def test_bindings_come_before_open_conflicts_and_the_card_stops_at_2000_chars():
    bindings = [{"fact_key": "stack.web", "value": "fastapi", "decision_id": "d1", "confidence": 0.9}]
    opens = [{"fact_key": f"k{i}", "values": ["a", "b"]} for i in range(100)]
    text = render_card(bindings, opens, limit=2000)
    assert text.startswith("BINDINGS")
    assert "stack.web" in text
    assert len(text) <= 2000
