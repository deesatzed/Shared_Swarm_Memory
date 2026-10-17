class HyMemoryIndex:
    def __init__(self, embedding_model: str | None):
        if not embedding_model:
            raise RuntimeError("Hy-Memory index requires a verified OpenRouter embedding model id")
        self.embedding_model = embedding_model

    def write_bound_sentence(self, decision_id: str, fact_key: str, text: str) -> None:
        raise RuntimeError("Hy-Memory index is not installed in this environment")
