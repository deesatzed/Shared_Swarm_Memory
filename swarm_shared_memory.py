#!/usr/bin/env python3
"""
Hy-Memory Shared Memory Scaffold for Agent Swarms
==================================================

Demonstrates how multiple agents (or a swarm) can share long-term memory
using the Hy-Memory SDK with OpenRouter (no local LLM/embedding resources).

Patterns covered:
- Shared user_id → agents can recall each other's memories
- agent_id isolation (optional private memories)
- source tagging + include/exclude filtering
- Chat scene (preferences, facts)
- Coding/Working scene (shared workspace facts + experiences)
- Periodic System 2 evolution (ultra mode)
- Optional: HTTP server mode for multi-process agents

Requirements:
  pip install hy-memory==2.0.2
  # or: pip install "hy-memory[qdrant]==2.0.2" for better multi-process concurrency

Set your OpenRouter key:
  export OPENROUTER_API_KEY="sk-or-v1-..."
"""

import os
import time
from typing import Optional, List, Dict, Any
from hy_memory import HyMemoryClient

# ---------------------------------------------------------------------------
# Configuration (OpenRouter so nothing runs locally for inference)
# ---------------------------------------------------------------------------

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-v1-YOUR_KEY_HERE")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Choose models freely on OpenRouter
LLM_MODEL = "tencent/hy3-preview"          # or "anthropic/claude-sonnet-4", "deepseek/deepseek-chat", etc.
EMBED_MODEL = "openai/text-embedding-3-small"
EMBED_DIMS = 1536

SHARED_USER_ID = "swarm_project_alpha"     # All agents share this user_id for shared memory
WORKSPACE_ID = "github.com/your-org/your-repo"  # For coding/working scenes

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def make_client(mode: str = "pro") -> HyMemoryClient:
    """Create a HyMemoryClient pointed at OpenRouter.
    
    mode: 'lite' (pure vectors, no LLM), 'pro' (extract + reconcile), 'ultra' (full System 2)
    """
    return HyMemoryClient.from_config({
        "mode": mode,
        "llm": {
            "model": LLM_MODEL,
            "api_key": OPENROUTER_KEY,
            "base_url": OPENROUTER_BASE,
        },
        "embedder": {
            "model": EMBED_MODEL,
            "api_key": OPENROUTER_KEY,
            "base_url": OPENROUTER_BASE,
            "embedding_dims": EMBED_DIMS,
        },
        "vector_store": {
            "provider": "chroma",          # local; switch to "qdrant" for multi-process
            "embedding_dims": EMBED_DIMS,
        },
        # Optional: enable graph for ultra/pro richer schemas
        # "graph_store": {"provider": "kuzu"},
    })


# ---------------------------------------------------------------------------
# Agent helper (thin wrapper so each agent has an identity)
# ---------------------------------------------------------------------------

class SwarmAgent:
    """Lightweight agent that talks to a shared HyMemoryClient."""

    def __init__(
        self,
        name: str,
        client: HyMemoryClient,
        user_id: str = SHARED_USER_ID,
        agent_id: Optional[str] = None,
        source: Optional[str] = None,
    ):
        self.name = name
        self.client = client
        self.user_id = user_id
        self.agent_id = agent_id or name
        self.source = source or name.lower()

    def remember(self, content: str | List[Dict], scene: Optional[str] = None, **kwargs) -> None:
        """Write a memory (plain text or OpenAI-style messages)."""
        self.client.add(
            content,
            user_id=self.user_id,
            agent_id=self.agent_id,
            source=self.source,
            scene=scene,
            **kwargs,
        )
        print(f"[{self.name}] remembered: {str(content)[:80]}...")

    def recall(
        self,
        query: str,
        agent_ids: Optional[List[str]] = None,
        include_sources: Optional[List[str]] = None,
        exclude_sources: Optional[List[str]] = None,
        scene: Optional[str] = None,
        limit: int = 8,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search shared (or filtered) memory."""
        result = self.client.search(
            query,
            user_ids=[self.user_id],
            agent_ids=agent_ids,               # None = all agents under this user
            include_sources=include_sources,
            exclude_sources=exclude_sources,
            scene=scene,
            limit=limit,
            **kwargs,
        )
        return result

    def print_memories(self, result: Dict[str, Any], label: str = "Recall") -> None:
        print(f"\n=== {self.name} {label} ===")
        memories = result.get("memories", {})
        for channel, items in memories.items():
            if not items:
                continue
            print(f"  [{channel}]")
            for m in items[:5]:
                score = m.get("score", 0)
                content = m.get("content", "")[:120]
                print(f"    ({score:.2f}) {content}")
        if "facts" in result:
            print("  [facts]", result["facts"])
        if "experiences" in result:
            print("  [experiences]", result["experiences"])


# ---------------------------------------------------------------------------
# Demo: Chat shared memory (preferences, facts)
# ---------------------------------------------------------------------------

def demo_chat_shared_memory(client: HyMemoryClient) -> None:
    print("\n" + "=" * 60)
    print("DEMO 1: Chat Shared Memory (preferences / facts)")
    print("=" * 60)

    planner = SwarmAgent("Planner", client)
    coder = SwarmAgent("Coder", client)
    reviewer = SwarmAgent("Reviewer", client)

    # Agents write different things
    planner.remember("The project uses Python 3.12 and prefers type hints + pytest.")
    planner.remember("User prefers concise answers with code examples and hates long preambles.")
    coder.remember("We decided to use FastAPI + SQLAlchemy 2.0 for the new service.")
    reviewer.remember("Always run ruff + mypy before marking a PR ready.")

    # Any agent can recall the shared knowledge
    result = coder.recall("What stack and style preferences do we have?")
    coder.print_memories(result, "shared stack/style")

    # Filter to only one source if desired
    result = reviewer.recall(
        "coding standards",
        include_sources=["reviewer", "planner"],
    )
    reviewer.print_memories(result, "filtered sources")


# ---------------------------------------------------------------------------
# Demo: Coding / Working shared workspace memory
# ---------------------------------------------------------------------------

def demo_coding_shared_workspace(client: HyMemoryClient) -> None:
    print("\n" + "=" * 60)
    print("DEMO 2: Coding Scene – Shared Workspace Facts & Experiences")
    print("=" * 60)

    # Simulate tool-using agents working on the same repo
    def make_tool_trace(task: str, tool_name: str, result: str) -> List[Dict]:
        return [
            {"role": "user", "content": task},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": tool_name, "arguments": "{}"},
                }],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "name": tool_name,
                "content": result,
            },
        ]

    coder = SwarmAgent("Coder", client)
    debugger = SwarmAgent("Debugger", client)

    # Coder records a fix
    coder.remember(
        make_tool_trace(
            "Fix the timeout in search client",
            "apply_patch",
            "Patched src/search.py: increased timeout from 5s to 30s and added retry.",
        ),
        scene="coding",
        workspace_id=WORKSPACE_ID,
        branch="fix/search-timeout",
    )

    # Debugger records an experience
    debugger.remember(
        make_tool_trace(
            "Investigate flaky test in auth module",
            "run_tests",
            "Flaky because of race on session token refresh. Fixed by adding lock.",
        ),
        scene="coding",
        workspace_id=WORKSPACE_ID,
    )

    # Any agent can recall coding facts/experiences for the workspace
    result = coder.recall(
        "How was the search timeout fixed?",
        scene="coding",
        workspace_id=WORKSPACE_ID,
    )
    coder.print_memories(result, "coding recall")


# ---------------------------------------------------------------------------
# Demo: System 2 evolution (ultra mode)
# ---------------------------------------------------------------------------

def demo_evolve(client: HyMemoryClient) -> None:
    print("\n" + "=" * 60)
    print("DEMO 3: System 2 Evolution (ultra mode)")
    print("=" * 60)
    print("Calling client.evolve() to induce schemas / higher-level structures...")
    # Note: requires mode="ultra" and graph enabled for full effect
    try:
        client.evolve(user_id=SHARED_USER_ID)
        print("Evolution complete.")
    except Exception as e:
        print(f"(evolve skipped or failed – ensure ultra mode + graph: {e})")


# ---------------------------------------------------------------------------
# Optional: Multi-process via HTTP server
# ---------------------------------------------------------------------------

def print_http_server_instructions() -> None:
    print("\n" + "=" * 60)
    print("OPTIONAL: Multi-process / Remote Agents via HTTP Server")
    print("=" * 60)
    print("""
Start the server once (single writer, concurrent readers via threads):

  export OPENROUTER_API_KEY=sk-or-v1-...
  # set other MEMORY_* vars or use from_config in a wrapper
  python -m hy_memory.server --host 127.0.0.1 --port 19527

Then agents (even in other processes or containers) can POST to:

  POST http://127.0.0.1:19527/api/v1/add
  POST http://127.0.0.1:19527/api/v1/search

Example payload for add:
  {
    "text": "We use pytest for all new modules",
    "user_id": "swarm_project_alpha",
    "agent_id": "tester",
    "source": "tester"
  }

For better multi-process concurrency, switch vector_store to Qdrant
(run a local Qdrant container) and set MEMORY_VECTOR_STORE=qdrant.
Note: Kuzu graph has single-writer locking; prefer Neo4j or disable graph
for high-concurrency swarms.
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if "YOUR_KEY_HERE" in OPENROUTER_KEY:
        print("WARNING: Set OPENROUTER_API_KEY environment variable.")
        print("Continuing with placeholder (calls will fail).")

    print("Initializing shared HyMemoryClient (OpenRouter)...")
    # Use 'pro' for normal use; switch to 'ultra' for System 2 demos
    client = make_client(mode="pro")

    try:
        demo_chat_shared_memory(client)
        demo_coding_shared_workspace(client)
        # demo_evolve(client)   # uncomment if using mode="ultra"
    finally:
        client.close()

    print_http_server_instructions()
    print("\nDone. Adapt SwarmAgent.remember / .recall for your real agents.")


if __name__ == "__main__":
    main()
