**Yes.** The cleanest way to give a CrewAI crew shared long-term memory with Hy-Memory is to expose it as two tools (`Remember` and `Recall`) that all agents share.  

They all write and read against the same `user_id`, so knowledge stored by one agent is immediately available to the others (and to future crew runs).

### Example

I added a ready-to-run example:




### How it works

1. **Shared HyMemoryClient** (OpenRouter for LLM + embeddings so nothing runs locally):

```python
hy_client = HyMemoryClient.from_config({
    "mode": "pro",
    "llm": {
        "model": "tencent/hy3-preview",
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
```

2. **Two tools** that wrap the client:

- `RememberTool` → `hy_client.add(..., user_id=SHARED_USER_ID, source="crewai")`
- `RecallTool` → `hy_client.search(..., user_ids=[SHARED_USER_ID])`

3. **Agents receive both tools**:

```python
researcher = Agent(
    role="Researcher",
    goal="...",
    backstory="Always Recall first, then Remember important findings.",
    tools=[remember_tool, recall_tool],
    verbose=True,
)
# same tools for analyst and writer
```

4. **Crew runs normally** (no need for CrewAI’s built-in `memory=True` if you want Hy-Memory to be the long-term store):

```python
crew = Crew(
    agents=[researcher, analyst, writer],
    tasks=[...],
    process=Process.sequential,
    verbose=True,
)
result = crew.kickoff(inputs={"topic": "your topic"})
```

### Quick start

```bash
pip install crewai hy-memory==2.0.2
export OPENROUTER_API_KEY="sk-or-v1-..."
python /workspace/artifacts/hy_memory_scaffold/crewai_hy_memory_example.py
```

### Notes

- **Shared vs private**: Keep the same `user_id` for shared memory. Use different `agent_id` values (or filter with `include_sources` / `agent_ids` on search) if you want isolation.
- **Coding/working scenes**: Pass `scene="coding"` (and optionally `workspace_id`) into `Remember` when agents are doing tool-using work.
- **CrewAI’s own memory**: You can still set `memory=True` on the Crew for short-term/task memory while using Hy-Memory tools for durable shared knowledge.
- **Multi-process**: If agents run in separate processes, start `python -m hy_memory.server` and have the tools call the HTTP endpoints instead of the in-process client.

The example is minimal on purpose so you can drop the tools into an existing crew. Adjust the backstories so agents know when to Recall before acting and Remember after important decisions.
