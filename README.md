# Hy-Memory Agent Swarm Shared Memory Scaffold

Minimal, runnable scaffold showing how multiple agents (or a swarm) can share
long-term memory via the Hy-Memory SDK while using OpenRouter for all LLM and
embedding calls (no local GPU/CPU inference).

## Quick Start

```bash
pip install hy-memory==2.0.2

export OPENROUTER_API_KEY="sk-or-v1-..."

python swarm_shared_memory.py
```

## Key Concepts for Shared Memory

| Mechanism              | How to use for swarms                                      | Isolation level          |
|------------------------|------------------------------------------------------------|--------------------------|
| `user_id`              | Same value across all agents → shared memory pool         | Shared                   |
| `agent_id`             | Distinct per agent; omit in search to see everyone        | Optional private         |
| `source`               | Tag origin; filter with `include_sources` / `exclude_sources` | Orthogonal to agent_id |
| `workspace_id` + scene | Shared coding/working facts & experiences for a repo      | Project-level            |
| Mode                   | `lite` (pure vectors), `pro` (extract), `ultra` (System 2)| Cost vs richness         |

## Multi-Process / Distributed

The SDK includes a simple HTTP server (`python -m hy_memory.server`).
Agents in other processes can POST to `/api/v1/add` and `/api/v1/search`.
For higher concurrency prefer Qdrant over default Chroma, and be aware of
Kuzu's single-writer limit if using the graph.

## Customization

- Change `LLM_MODEL` / `EMBED_MODEL` to any OpenRouter models.
- Switch `mode` to `"ultra"` and call `client.evolve(user_id=...)` periodically
  for higher-level schema induction.
- Wrap the `SwarmAgent` class inside your existing agent framework (CrewAI,
  AutoGen, LangGraph, custom, etc.).
- For production multi-process, run one HyMemoryClient (or the HTTP server)
  as the single writer and have agents call it over HTTP or a queue.

See the official docs for full API details:
https://github.com/Tencent-Hunyuan/Hy-Memory
