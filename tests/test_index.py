import pytest

from swarm_memory.index import HyMemoryIndex


def test_index_refuses_to_construct_without_a_verified_embedding_model():
    with pytest.raises(RuntimeError, match="embedding model"):
        HyMemoryIndex(embedding_model=None)


def test_index_refuses_an_empty_embedding_model_id():
    with pytest.raises(RuntimeError, match="embedding model"):
        HyMemoryIndex(embedding_model="")


def test_write_is_refused_until_the_index_is_installed():
    index = HyMemoryIndex(embedding_model="a-non-empty-id")
    assert index.embedding_model == "a-non-empty-id"
    with pytest.raises(RuntimeError, match="not installed"):
        index.write_bound_sentence("d1", "stack.web", "sentence")
