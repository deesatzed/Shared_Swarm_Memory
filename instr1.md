**Hy-Memory is well-suited for agent swarms with shared memory.**  

It uses a three-layer scope (`user_id` → `agent_id` → `session_id`) plus an orthogonal `source` tag. Agents that share the same `user_id` can see each other’s memories by default; you can still isolate with `agent_id` or filter by `source`. Coding/working scenes add `workspace_id` (and optional `branch`) for project-level shared facts and experiences.

### Scaffold

I created a ready-to-run scaffold that uses OpenRouter (so no local GPU/CPU for the LLM or embeddings) and demonstrates the main patterns:

- Shared chat memory (preferences/facts)
- Shared coding/working workspace memory
- Optional System 2 evolution (`ultra` mode)
- Notes on multi-process use via the built-in HTTP server

**Files** (in `/workspace/artifacts/hy_memory_scaffold/`):






### Quick start

```bash
pip install hy-memory==2.0.2
export OPENROUTER_API_KEY="sk-or-v1-..."
python /workspace/artifacts/hy_memory_scaffold/swarm_shared_memory.py
```

### Core patterns (from the scaffold)

```python
from hy_memory import HyMemoryClient

client = HyMemoryClient.from_config({
    "mode": "pro",                          # or "lite" / "ultra"
    "llm": {
        "model": "tencent/hy3-preview",     # any OpenRouter model
        "api_key": OPENROUTER_KEY,
        "base_url": "https://openrouter.ai/api/v1",
    },
    "embedder": {
        "model": "openai/text-embedding-3-small",
        "api_key": OPENROUTER_KEY,
        "base_url": "https://openrouter.ai/api/v1",
        "embedding_dims": 1536,
    },
    "vector_store": {"provider": "chroma", "embedding_dims": 1536},
})

# All agents share the same user_id
SHARED_USER = "swarm_project_alpha"

# Agent A writes
client.add("Prefer type hints + pytest", user_id=SHARED_USER, agent_id="planner", source="planner")

# Agent B recalls everything under that user (omit agent_ids)
results = client.search("coding standards?", user_ids=[SHARED_USER])

# Or filter by source / agent
results = client.search(
    "coding standards?",
    user_ids=[SHARED_USER],
    include_sources=["planner", "reviewer"],
)
```

For coding scenes, pass `scene="coding"` (or `"working"`) plus `workspace_id` so facts and reusable experiences are shared across the swarm for that repo.

### Multi-process / distributed agents

The SDK ships a simple threaded HTTP server:

```bash
python -m hy_memory.server --host 127.0.0.1 --port 19527
```

Agents in other processes can then `POST` to `/api/v1/add` and `/api/v1/search`. This gives a single writer (safer with the default local backends). For higher concurrency, switch the vector store to Qdrant.

### Recommendations

| Need                        | Approach                                      |
|----------------------------|-----------------------------------------------|
| Pure shared recall         | Same `user_id`, omit `agent_ids` on search   |
| Private + shared           | Distinct `agent_id`; filter when needed      |
| Provenance / filtering     | `source` + `include_sources` / `exclude_sources` |
| Project/repo memory        | `scene="coding"` + shared `workspace_id`     |
| Higher-level schemas       | `mode="ultra"` + periodic `client.evolve()`  |
| No local inference         | Point LLM + embedder at OpenRouter           |
| Multi-process              | HTTP server or shared Qdrant backend         |

The scaffold is intentionally minimal so you can drop the `SwarmAgent` wrapper (or just the `add`/`search` calls) into CrewAI, AutoGen, LangGraph, custom loops, etc. Adjust the models, mode, and isolation to fit your swarm.
