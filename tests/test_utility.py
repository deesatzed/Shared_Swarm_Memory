from swarm_memory.utility import ucb_scores


def test_a_cited_memory_outranks_one_that_was_shown_and_ignored():
    utilities = {"cited": (6.0, 8.0), "ignored": (0.0, 8.0)}
    scores = ucb_scores(["cited", "ignored"], utilities)
    assert scores["cited"] > scores["ignored"]


def test_an_unseen_memory_outranks_one_that_was_ignored():
    utilities = {"ignored": (0.0, 8.0)}
    scores = ucb_scores(["ignored", "unseen"], utilities)
    assert scores["unseen"] > scores["ignored"]
