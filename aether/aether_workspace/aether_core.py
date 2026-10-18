#!/usr/bin/env python3
"""
Aether: Decision-Swarm & Reconstructive Memory Harness Runtime
Implements Phases 0-4 of the Aether Handoff Specification:
  - Phase 0: Strict Pydantic Data Models, Harness Loader, Improvement Library
  - Phase 1: Tool Registry & Sub-millisecond Fast Decision Layer
  - Phase 2: SQLite Connectome Scaffold Graph & Gated Reconstructive Memory
  - Phase 3: Multi-Criteria Decision Scorer & Pareto Frontier Calculator
  - Phase 4: Automated Propose-Probe-Compose Trace Analyzer & Harness Updater
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol

from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("aether")


class NodeType(str, Enum):
    ENTITY = "entity"
    EVENT = "event"
    CLAIM = "claim"
    SKILL = "skill"
    OUTCOME = "outcome"
    SEED = "seed"


class EdgeType(str, Enum):
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    ASSOCIATIVE = "associative"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    USED_WITH_OUTCOME = "used_with_outcome"


class ScaffoldNode(BaseModel):
    node_id: str = Field(default_factory=lambda: f"node_{uuid.uuid4().hex[:8]}")
    node_type: NodeType
    cue: str
    keywords: list[str] = Field(default_factory=list)
    provenance: str
    evidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    last_used: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ScaffoldEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: f"edge_{uuid.uuid4().hex[:8]}")
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_count: int = Field(default=1, ge=1)


class CriterionWeights(BaseModel):
    reliability_lift: float = Field(default=0.30, ge=0.0, le=1.0)
    token_latency_cost: float = Field(default=0.25, ge=0.0, le=1.0)
    safety_robustness: float = Field(default=0.20, ge=0.0, le=1.0)
    reusability: float = Field(default=0.15, ge=0.0, le=1.0)
    evidence_strength: float = Field(default=0.10, ge=0.0, le=1.0)

    def normalize(self) -> dict[str, float]:
        data = self.model_dump()
        total = sum(data.values())
        if total == 0:
            raise ValueError("Criterion weights cannot all be zero.")
        return {k: v / total for k, v in data.items()}


class CandidateScore(BaseModel):
    candidate_id: str
    description: str
    scores: dict[str, float]
    weighted_total: float = 0.0
    is_pareto_optimal: bool = False
    quarantined: bool = False
    quarantine_reasons: list[str] = Field(default_factory=list)
    rationale: str = ""


class DecisionRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context_summary: str
    weights_used: dict[str, float]
    candidates: list[CandidateScore]
    selected_candidate_id: str | None = None
    adoption_rationale: str


class RoutingDecision(BaseModel):
    action: str
    selected_tool: str | None = None
    tool_score: float = 0.0
    selected_scaffolds: list[ScaffoldNode] = Field(default_factory=list)
    scaffold_score: float = 0.0
    expected_utility: float = 0.0
    latency_ms: float = 0.0
    rationale: str = ""


class HarnessConfig(BaseModel):
    role_name: str
    version: str = "1.0.0"
    system_prompt: str
    guardrails: list[str]
    tool_threshold: float = 0.45
    scaffold_threshold: float = 0.40
    max_scaffold_hops: int = 1
    weights: CriterionWeights = Field(default_factory=CriterionWeights)


class ExecutionTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: f"tr_{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    harness_version: str
    query: str
    routing_decision: RoutingDecision
    tool_executed: str | None = None
    reconstructed_node_ids: list[str] = Field(default_factory=list)
    estimated_tokens: int = 0
    total_latency_ms: float = 0.0
    guardrail_passed: bool = True
    verification_status: str = "not_run"
    verifier_critique: str = "OK"
    response_text: str = ""
    response_preview: str = ""


class TraceAnomalyReport(BaseModel):
    total_traces: int
    avg_tokens: float
    avg_latency_ms: float
    guardrail_pass_rate: float
    unnecessary_reconstruction_rate: float
    missed_hard_trigger_count: int
    detected_failure_modes: list[str]


class HarnessDiff(BaseModel):
    diff_id: str
    variant_type: str
    description: str
    new_tool_threshold: float | None = None
    new_scaffold_threshold: float | None = None
    new_max_scaffold_hops: int | None = None
    added_guardrails: list[str] = Field(default_factory=list)
    system_prompt_append: str | None = None
    promoted_nodes: list[ScaffoldNode] = Field(default_factory=list)
    promoted_edges: list[ScaffoldEdge] = Field(default_factory=list)


@dataclass
class ProbeScenario:
    scenario_id: str
    query: str
    expected_hard_trigger: str | None = None
    is_noise_query: bool = False


class ConnectomeScaffoldGraph:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS scaffold_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    cue TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    evidence_score REAL NOT NULL,
                    last_used TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scaffold_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    weight REAL NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES scaffold_nodes(node_id),
                    FOREIGN KEY(target_id) REFERENCES scaffold_nodes(node_id)
                );
                CREATE INDEX IF NOT EXISTS idx_edges_source ON scaffold_edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_nodes_score ON scaffold_nodes(evidence_score);
                """
            )

    def clone_to_memory(self) -> ConnectomeScaffoldGraph:
        clone = ConnectomeScaffoldGraph(":memory:")
        self.conn.backup(clone.conn)
        return clone

    def write_evidence_gated(self, node: ScaffoldNode, min_evidence_threshold: float = 0.60) -> bool:
        if node.evidence_score < min_evidence_threshold:
            return False
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO scaffold_nodes
                (node_id, node_type, cue, keywords_json, provenance, evidence_score, last_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.node_id,
                    node.node_type.value,
                    node.cue,
                    json.dumps([k.lower() for k in node.keywords]),
                    node.provenance,
                    node.evidence_score,
                    node.last_used,
                ),
            )
        return True

    def link_nodes(self, edge: ScaffoldEdge) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO scaffold_edges
                (edge_id, source_id, target_id, edge_type, weight, evidence_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.edge_id,
                    edge.source_id,
                    edge.target_id,
                    edge.edge_type.value,
                    edge.weight,
                    edge.evidence_count,
                ),
            )

    def activate_subgraph(self, query_tokens: set[str], max_hops: int = 1) -> list[tuple[ScaffoldNode, float]]:
        cursor = self.conn.execute("SELECT * FROM scaffold_nodes")
        rows = cursor.fetchall()
        activated: dict[str, tuple[ScaffoldNode, float]] = {}

        for row in rows:
            keywords = set(json.loads(row["keywords_json"]))
            if not keywords:
                continue
            overlap = len(query_tokens.intersection(keywords))
            if overlap > 0:
                lexical_score = overlap / max(len(keywords), 1)
                activation = (0.65 * lexical_score) + (0.35 * row["evidence_score"])
                node = ScaffoldNode(
                    node_id=row["node_id"],
                    node_type=NodeType(row["node_type"]),
                    cue=row["cue"],
                    keywords=list(keywords),
                    provenance=row["provenance"],
                    evidence_score=row["evidence_score"],
                    last_used=row["last_used"],
                )
                activated[node.node_id] = (node, round(activation, 4))

        current_frontier = list(activated.keys())
        for _ in range(max_hops):
            if not current_frontier:
                break
            placeholders = ",".join("?" for _ in current_frontier)
            edge_rows = self.conn.execute(
                f"SELECT * FROM scaffold_edges WHERE source_id IN ({placeholders})",
                current_frontier,
            ).fetchall()

            next_frontier: list[str] = []
            for edge in edge_rows:
                target_id = edge["target_id"]
                _, parent_score = activated[edge["source_id"]]
                propagated_score = round(parent_score * edge["weight"] * 0.85, 4)

                if target_id not in activated or propagated_score > activated[target_id][1]:
                    target_row = self.conn.execute(
                        "SELECT * FROM scaffold_nodes WHERE node_id = ?", (target_id,)
                    ).fetchone()
                    if target_row:
                        target_node = ScaffoldNode(
                            node_id=target_row["node_id"],
                            node_type=NodeType(target_row["node_type"]),
                            cue=target_row["cue"],
                            keywords=json.loads(target_row["keywords_json"]),
                            provenance=target_row["provenance"],
                            evidence_score=target_row["evidence_score"],
                            last_used=target_row["last_used"],
                        )
                        activated[target_id] = (target_node, propagated_score)
                        next_frontier.append(target_id)
            current_frontier = next_frontier

        return sorted(activated.values(), key=lambda x: x[1], reverse=True)


@dataclass
class ToolSpec:
    name: str
    description: str
    trigger_keywords: set[str]
    cost_estimate: float
    reliability_prior: float
    handler: Callable[[str], str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def all_tools(self) -> list[ToolSpec]:
        return list(self._tools.values())


class FastDecisionLayer:
    def __init__(self, registry: ToolRegistry, connectome: ConnectomeScaffoldGraph) -> None:
        self.registry = registry
        self.connectome = connectome

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return {tok for tok in cleaned.split() if len(tok) > 2}

    def route(self, query: str, harness: HarnessConfig) -> RoutingDecision:
        start_ns = time.perf_counter_ns()
        tokens = self._tokenize(query)

        best_tool: str | None = None
        best_tool_score = 0.0

        for tool in self.registry.all_tools():
            overlap = len(tokens.intersection(tool.trigger_keywords))
            if overlap == 0:
                continue
            match_ratio = min(overlap / 2.0, 1.0)
            utility = (match_ratio * tool.reliability_prior) - (0.25 * tool.cost_estimate)
            if utility > best_tool_score:
                best_tool_score = round(utility, 4)
                best_tool = tool.name

        activated_nodes = self.connectome.activate_subgraph(tokens, max_hops=harness.max_scaffold_hops)
        selected_scaffolds: list[ScaffoldNode] = []
        top_scaffold_score = 0.0

        for node, score in activated_nodes:
            if score >= harness.scaffold_threshold:
                selected_scaffolds.append(node)
                top_scaffold_score = max(top_scaffold_score, score)

        use_tool = best_tool is not None and best_tool_score >= harness.tool_threshold
        use_scaffold = len(selected_scaffolds) > 0

        if use_tool and use_scaffold:
            action = "tool_and_reconstruct"
        elif use_tool:
            action = "tool_only"
        elif use_scaffold:
            action = "reconstruct_only"
        else:
            action = "direct"

        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        combined_utility = round(max(best_tool_score, top_scaffold_score), 4)

        return RoutingDecision(
            action=action,
            selected_tool=best_tool if use_tool else None,
            tool_score=best_tool_score,
            selected_scaffolds=selected_scaffolds[:4],
            scaffold_score=top_scaffold_score,
            expected_utility=combined_utility,
            latency_ms=round(elapsed_ms, 3),
            rationale=f"Router ({elapsed_ms:.3f}ms): Tool={best_tool} ({best_tool_score:.2f}), Scaffolds={len(selected_scaffolds)}.",
        )


class MultiCriteriaDecisionModel:
    @staticmethod
    def evaluate(
        context_summary: str,
        weights: CriterionWeights,
        candidates: list[CandidateScore],
        min_safety_score: float = 7.0,
        min_evidence_score: float = 6.5,
    ) -> DecisionRecord:
        if not candidates:
            raise ValueError("Cannot evaluate an empty candidate list.")
        norm_weights = weights.normalize()

        for cand in candidates:
            safety_score = cand.scores.get("safety_robustness", 0.0)
            evidence_score = cand.scores.get("evidence_strength", 0.0)
            if safety_score < min_safety_score:
                cand.quarantined = True
                cand.quarantine_reasons.append(
                    f"safety_robustness {safety_score} is below {min_safety_score}"
                )
            if evidence_score < min_evidence_score:
                cand.quarantined = True
                cand.quarantine_reasons.append(
                    f"evidence_strength {evidence_score} is below {min_evidence_score}"
                )
            total = sum(cand.scores.get(crit, 0.0) * w for crit, w in norm_weights.items())
            cand.weighted_total = round(total, 4)

        viable = [c for c in candidates if not c.quarantined]
        for i, cand_a in enumerate(viable):
            dominated = False
            for j, cand_b in enumerate(viable):
                if i == j:
                    continue
                better_or_equal_all = all(cand_b.scores.get(k, 0.0) >= cand_a.scores.get(k, 0.0) for k in norm_weights)
                strictly_better_one = any(cand_b.scores.get(k, 0.0) > cand_a.scores.get(k, 0.0) for k in norm_weights)
                if better_or_equal_all and strictly_better_one:
                    dominated = True
                    break
            cand_a.is_pareto_optimal = not dominated

        ranked = sorted(candidates, key=lambda c: (not c.quarantined, c.is_pareto_optimal, c.weighted_total), reverse=True)
        winner = ranked[0] if viable else None

        if winner is None:
            return DecisionRecord(
                context_summary=context_summary,
                weights_used=norm_weights,
                candidates=ranked,
                selected_candidate_id=None,
                adoption_rationale="No candidate adopted: all candidates are quarantined.",
            )

        return DecisionRecord(
            context_summary=context_summary,
            weights_used=norm_weights,
            candidates=ranked,
            selected_candidate_id=winner.candidate_id,
            adoption_rationale=f"Adopted '{winner.candidate_id}' (Weighted: {winner.weighted_total:.2f}/10.0, Pareto: {winner.is_pareto_optimal}).",
        )


class FrozenLLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


class MockFrozenLLM:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if "RECONSTRUCT_MEMORY_CUES" in system_prompt:
            return "[Reconstructed Context]: " + user_prompt.replace("\n", " | ")
        combined = f"{system_prompt}\n{user_prompt}".lower()
        actions = []
        if "escalate_human" in combined or "spo2 < 88%" in combined or "halt" in combined or "rollback" in combined:
            actions.append("ACTION=escalate_human")
        if not actions:
            actions.append("ACTION=silent_log")
        return f"[Frozen LLM Decision]: {', '.join(actions)}"


class AetherAgentRuntime:
    def __init__(
        self,
        harness: HarnessConfig,
        router: FastDecisionLayer,
        registry: ToolRegistry,
        llm: FrozenLLMClient,
        trace_log_path: str | Path = "traces/execution_traces.jsonl",
    ) -> None:
        self.harness = harness
        self.router = router
        self.registry = registry
        self.llm = llm
        self.trace_log_path = Path(trace_log_path)
        self.trace_log_path.parent.mkdir(parents=True, exist_ok=True)

    def reconstruct_memory(self, seeds: list[ScaffoldNode], query: str) -> str:
        cues_formatted = "\n".join(f"- [{s.node_type.value.upper()}] {s.cue} (Evidence: {s.evidence_score})" for s in seeds)
        recon_prompt = "RECONSTRUCT_MEMORY_CUES: Expand these sparse connectome cues into concise operational context."
        return self.llm.generate(system_prompt=recon_prompt, user_prompt=f"Task: {query}\nCues:\n{cues_formatted}")

    def execute(self, query: str, expected_hard_trigger: str | None = None, persist_trace: bool = True) -> ExecutionTrace:
        t0 = time.perf_counter_ns()
        decision = self.router.route(query, self.harness)
        context_parts = []

        if decision.selected_tool:
            tool_spec = self.registry.get(decision.selected_tool)
            if tool_spec:
                context_parts.append(f"[Tool Output]: {tool_spec.handler(query)}")

        if decision.selected_scaffolds:
            reconstructed = self.reconstruct_memory(decision.selected_scaffolds, query)
            context_parts.append(reconstructed)

        assembled_prompt = f"{self.harness.system_prompt}\nGuardrails: {'; '.join(self.harness.guardrails)}"
        full_user_input = "\n".join(context_parts) + f"\n\nTask: {query}" if context_parts else query
        response = self.llm.generate(assembled_prompt, full_user_input)
        elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

        verification_status = "not_run"
        guardrail_passed = False
        critique = "NOT_VERIFIED: no expected hard trigger was supplied"
        if expected_hard_trigger:
            if expected_hard_trigger.lower() in response.lower():
                verification_status = "passed"
                guardrail_passed = True
                critique = "OK"
            else:
                verification_status = "failed"
                critique = f"MISSED_TRIGGER: Expected '{expected_hard_trigger}'"

        estimated_tokens = (len(assembled_prompt) + len(full_user_input) + len(response)) // 4

        trace = ExecutionTrace(
            harness_version=self.harness.version,
            query=query,
            routing_decision=decision,
            tool_executed=decision.selected_tool,
            reconstructed_node_ids=[n.node_id for n in decision.selected_scaffolds],
            estimated_tokens=estimated_tokens,
            total_latency_ms=round(elapsed_ms, 3),
            guardrail_passed=guardrail_passed,
            verification_status=verification_status,
            verifier_critique=critique,
            response_text=response,
            response_preview=response[:160],
        )

        if persist_trace:
            with self.trace_log_path.open("a", encoding="utf-8") as f:
                # Full model output stays in the in-memory trace for behavior and
                # handoffs; persistent trace logs retain only the display preview.
                f.write(json.dumps(trace.model_dump(exclude={"response_text"})) + "\n")
        return trace


class TraceAnalyzer:
    @staticmethod
    def analyze(traces: list[ExecutionTrace], scenarios: list[Any] | None = None) -> TraceAnomalyReport:
        noise_queries = {s.query for s in scenarios if getattr(s, "is_noise_query", False)} if scenarios else set()
        total = len(traces)
        if total == 0:
            return TraceAnomalyReport(
                total_traces=0,
                avg_tokens=0.0,
                avg_latency_ms=0.0,
                guardrail_pass_rate=0.0,
                unnecessary_reconstruction_rate=0.0,
                missed_hard_trigger_count=0,
                detected_failure_modes=["NO_TRACES: No traces available for analysis."],
            )
        avg_tokens = sum(t.estimated_tokens for t in traces) / total
        avg_latency = sum(t.total_latency_ms for t in traces) / total
        passed = sum(1 for t in traces if t.guardrail_passed)
        missed_triggers = total - passed

        unnecessary_recons = sum(1 for t in traces if t.reconstructed_node_ids and (t.query in noise_queries or t.routing_decision.scaffold_score < 0.45))
        failure_modes = []
        if missed_triggers > 0:
            failure_modes.append(f"INCOMPLETE_VERIFICATION: {missed_triggers}/{total} missed hard triggers.")
        if unnecessary_recons > 0:
            failure_modes.append(f"OVER_RECONSTRUCTION_BLOAT: {unnecessary_recons} unnecessary recons.")

        return TraceAnomalyReport(
            total_traces=total,
            avg_tokens=round(avg_tokens, 2),
            avg_latency_ms=round(avg_latency, 3),
            guardrail_pass_rate=round(passed / total, 4),
            unnecessary_reconstruction_rate=round(unnecessary_recons / total, 4),
            missed_hard_trigger_count=missed_triggers,
            detected_failure_modes=failure_modes,
        )


class ProposeProbeComposeEngine:
    def __init__(self, registry: ToolRegistry, connectome: ConnectomeScaffoldGraph, llm: FrozenLLMClient, library: Any) -> None:
        self.registry = registry
        self.connectome = connectome
        self.llm = llm
        self.library = library

    @staticmethod
    def _bump_version(version_str: str) -> str:
        parts = [int(x) for x in version_str.split(".")]
        parts[1] += 1
        return ".".join(str(p) for p in parts)

    @staticmethod
    def apply_diff(base_harness: HarnessConfig, diff: HarnessDiff, target_connectome: ConnectomeScaffoldGraph) -> HarnessConfig:
        updated = base_harness.model_copy(deep=True)
        updated.version = ProposeProbeComposeEngine._bump_version(base_harness.version)
        if diff.new_tool_threshold is not None:
            updated.tool_threshold = diff.new_tool_threshold
        if diff.new_scaffold_threshold is not None:
            updated.scaffold_threshold = diff.new_scaffold_threshold
        if diff.new_max_scaffold_hops is not None:
            updated.max_scaffold_hops = diff.new_max_scaffold_hops
        for g in diff.added_guardrails:
            if g not in updated.guardrails:
                updated.guardrails.append(g)
        for node in diff.promoted_nodes:
            target_connectome.write_evidence_gated(node, min_evidence_threshold=0.60)
        return updated
