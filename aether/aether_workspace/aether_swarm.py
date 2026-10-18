#!/usr/bin/env python3
"""Aether Multi-Agent Swarm Orchestrator."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from aether_core import (
    AetherAgentRuntime,
    ConnectomeScaffoldGraph,
    ExecutionTrace,
    FastDecisionLayer,
    FrozenLLMClient,
    HarnessConfig,
    ToolRegistry,
)

logger = logging.getLogger("aether.swarm")


class HandoffPacket(BaseModel):
    packet_id: str = Field(default_factory=lambda: f"pkt_{uuid.uuid4().hex[:8]}")
    from_role: str
    to_role: str
    payload: str
    activated_scaffolds: list[str] = Field(default_factory=list)
    tool_used: str | None = None


class SwarmExecutionResult(BaseModel):
    swarm_run_id: str = Field(default_factory=lambda: f"swm_{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    query: str
    fast_path_bypass: bool
    roles_invoked: list[str]
    handoffs: list[HandoffPacket]
    final_action: str
    verifier_status: str
    verifier_approved: bool
    total_tokens: int
    total_latency_ms: float


class AetherSwarmOrchestrator:
    def __init__(
        self,
        llm: FrozenLLMClient,
        connectome: ConnectomeScaffoldGraph,
        registry: ToolRegistry,
        librarian_harness: HarnessConfig,
        worker_harness: HarnessConfig,
        verifier_harness: HarnessConfig,
        fast_bypass_utility_threshold: float = 0.30,
        swarm_log_path: str | Path = "traces/swarm_runs.jsonl",
    ) -> None:
        self.llm = llm
        self.connectome = connectome
        self.registry = registry
        self.router = FastDecisionLayer(registry=registry, connectome=connectome)
        self.fast_bypass_utility_threshold = fast_bypass_utility_threshold
        self.swarm_log_path = Path(swarm_log_path)
        self.swarm_log_path.parent.mkdir(parents=True, exist_ok=True)
        trace_dir = self.swarm_log_path.parent

        self.librarian = AetherAgentRuntime(harness=librarian_harness, router=self.router, registry=registry, llm=llm, trace_log_path=trace_dir / "librarian_traces.jsonl")
        self.worker = AetherAgentRuntime(harness=worker_harness, router=self.router, registry=registry, llm=llm, trace_log_path=trace_dir / "worker_traces.jsonl")
        self.verifier = AetherAgentRuntime(harness=verifier_harness, router=self.router, registry=registry, llm=llm, trace_log_path=trace_dir / "verifier_traces.jsonl")

    def _extract_action_token(self, text: str) -> str:
        for token in ("ACTION=escalate_human", "ACTION=wake_specialist", "ACTION=silent_log", "ACTION=trigger_auto_rollback", "ACTION=page_oncall_sre", "ACTION=log_ok"):
            if token.lower() in text.lower():
                return token
        return "ACTION=silent_log"

    def dispatch(self, query: str, expected_hard_trigger: str | None = None) -> SwarmExecutionResult:
        t0 = time.perf_counter_ns()
        handoffs = []
        roles_invoked = []
        total_tokens = 0

        triage_decision = self.router.route(query, self.librarian.harness)
        if triage_decision.expected_utility < self.fast_bypass_utility_threshold:
            worker_trace = self.worker.execute(query, expected_hard_trigger=expected_hard_trigger)
            roles_invoked.append(self.worker.harness.role_name)
            total_tokens += worker_trace.estimated_tokens
            final_action = self._extract_action_token(worker_trace.response_text)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            return SwarmExecutionResult(
                query=query,
                fast_path_bypass=True,
                roles_invoked=roles_invoked,
                handoffs=handoffs,
                final_action=final_action,
                verifier_status="not_run",
                verifier_approved=False,
                total_tokens=total_tokens,
                total_latency_ms=round(elapsed_ms, 3),
            )

        lib_trace = self.librarian.execute(query, persist_trace=True)
        roles_invoked.append(self.librarian.harness.role_name)
        total_tokens += lib_trace.estimated_tokens

        lib_to_worker = HandoffPacket(
            from_role=self.librarian.harness.role_name,
            to_role=self.worker.harness.role_name,
            payload=f"Task: {query}\nTool: {lib_trace.tool_executed}\nSynthesis: {lib_trace.response_text}",
            activated_scaffolds=lib_trace.reconstructed_node_ids,
            tool_used=lib_trace.tool_executed,
        )
        handoffs.append(lib_to_worker)

        worker_trace = self.worker.execute(lib_to_worker.payload, persist_trace=True)
        roles_invoked.append(self.worker.harness.role_name)
        total_tokens += worker_trace.estimated_tokens
        worker_action = self._extract_action_token(worker_trace.response_text)

        worker_to_verifier = HandoffPacket(
            from_role=self.worker.harness.role_name,
            to_role=self.verifier.harness.role_name,
            payload=f"{lib_to_worker.payload}\nProposed: {worker_action}",
            activated_scaffolds=lib_trace.reconstructed_node_ids,
            tool_used=lib_trace.tool_executed,
        )
        handoffs.append(worker_to_verifier)

        verifier_trace = self.verifier.execute(worker_to_verifier.payload, expected_hard_trigger=expected_hard_trigger, persist_trace=True)
        roles_invoked.append(self.verifier.harness.role_name)
        total_tokens += verifier_trace.estimated_tokens
        verifier_action = self._extract_action_token(verifier_trace.response_text)

        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        return SwarmExecutionResult(
            query=query,
            fast_path_bypass=False,
            roles_invoked=roles_invoked,
            handoffs=handoffs,
            final_action=verifier_action,
            verifier_status=verifier_trace.verification_status,
            verifier_approved=verifier_trace.verification_status == "passed",
            total_tokens=total_tokens,
            total_latency_ms=round(elapsed_ms, 3),
        )
