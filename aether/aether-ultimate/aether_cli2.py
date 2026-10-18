#!/usr/bin/env python3
"""
Aether Universal CLI & Domain-Agnostic Swarm Runner (aether_cli.py)
Decouples the Aether runtime from any single vertical via pluggable DomainPacks.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from aether_core import (
    ConnectomeScaffoldGraph,
    FrozenLLMClient,
    HarnessConfig,
    HarnessDiff,
    NodeType,
    ProbeScenario,
    ScaffoldEdge,
    ScaffoldNode,
    ToolRegistry,
    ToolSpec,
    TraceAnomalyReport,
)
from aether_swarm import AetherSwarmOrchestrator
from openrouter_adapter import (
    LiveProposeProbeComposeEngine,
    OpenRouterConfig,
    OpenRouterFrozenLLM,
    build_llm_client,
)

logger = logging.getLogger("aether.cli")


class DeclarativeToolDef(BaseModel):
    name: str
    description: str
    trigger_keywords: list[str]
    cost_estimate: float = 0.10
    reliability_prior: float = 0.95
    simulated_output: str


class ProbeScenarioDef(BaseModel):
    scenario_id: str
    query: str
    expected_hard_trigger: str
    is_noise_query: bool = False


class EvolutionarySeedDef(BaseModel):
    missing_node: ScaffoldNode
    target_guardrail: str


class DomainPack(BaseModel):
    domain_id: str
    title: str
    description: str
    action_tokens: list[str] = Field(..., min_length=3)
    fast_bypass_utility_threshold: float = 0.30
    librarian_harness: HarnessConfig
    worker_harness: HarnessConfig
    verifier_harness: HarnessConfig
    tools: list[DeclarativeToolDef]
    initial_nodes: list[ScaffoldNode]
    initial_edges: list[ScaffoldEdge] = Field(default_factory=list)
    probe_scenarios: list[ProbeScenarioDef]
    evolution_seed: EvolutionarySeedDef


def get_builtin_domain_packs() -> dict[str, DomainPack]:
    sre_pack = DomainPack(
        domain_id="sre_ops",
        title="Autonomous SRE & Cloud Incident Response Swarm",
        description="Routes production alerts across metric tools, runbook connectomes, and rollback verifiers.",
        action_tokens=[
            "ACTION=trigger_auto_rollback",
            "ACTION=page_oncall_sre",
            "ACTION=scale_worker_pool",
            "ACTION=log_ok",
        ],
        librarian_harness=HarnessConfig(
            role_name="SRE_Telemetry_Librarian",
            version="1.0.0",
            system_prompt="Query infrastructure metrics and reconstruct sparse runbook cues.",
            guardrails=["Never fabricate metric values"],
            tool_threshold=0.35,
            scaffold_threshold=0.25,
            max_scaffold_hops=1,
        ),
        worker_harness=HarnessConfig(
            role_name="Incident_Commander_Worker",
            version="1.0.0",
            system_prompt="Select remediation token: ACTION=trigger_auto_rollback, ACTION=page_oncall_sre, ACTION=scale_worker_pool, or ACTION=log_ok.",
            guardrails=["Prefer immediate rollback on 5xx error spikes"],
            tool_threshold=0.99,
            scaffold_threshold=0.99,
            max_scaffold_hops=0,
        ),
        verifier_harness=HarnessConfig(
            role_name="Chaos_Safety_Verifier",
            version="1.0.0",
            system_prompt="Enforce rollback if error rate > 5%.",
            guardrails=["Never allow silent logging during SLA breach"],
            tool_threshold=0.99,
            scaffold_threshold=0.45,
            max_scaffold_hops=1,
        ),
        tools=[
            DeclarativeToolDef(
                name="prometheus_metrics_query",
                description="Queries p99 latency and 5xx rates",
                trigger_keywords=["latency", "5xx", "canary", "deploy", "db", "pool", "payment", "error"],
                simulated_output="http_5xx_rate=8.4% (canary_v42), db_pool_saturation=99.2%",
            )
        ],
        initial_nodes=[
            ScaffoldNode(
                node_id="node_canary_5xx_rule",
                node_type=NodeType.CLAIM,
                cue="5xx rate > 5% mandates immediate ACTION=trigger_auto_rollback",
                keywords=["5xx", "canary", "deploy", "error", "rollback"],
                provenance="SRE_Runbook",
                evidence_score=0.96,
            ),
            ScaffoldNode(
                node_id="node_routine_cron_noise",
                node_type=NodeType.SEED,
                cue="Nightly static asset cache warm-up job runs at 03:00 UTC",
                keywords=["cron", "heartbeat", "static", "ping", "routine"],
                provenance="Ops_Wiki",
                evidence_score=0.62,
            ),
        ],
        probe_scenarios=[
            ProbeScenarioDef(
                scenario_id="sre_probe_1",
                query="Canary deploy showing 5xx error spike and latency.",
                expected_hard_trigger="ACTION=trigger_auto_rollback",
            ),
            ProbeScenarioDef(
                scenario_id="sre_probe_2",
                query="Payment-service experiencing DB pool saturation and deadlock.",
                expected_hard_trigger="ACTION=page_oncall_sre",
            ),
            ProbeScenarioDef(
                scenario_id="sre_probe_3",
                query="Routine static ping cron check.",
                expected_hard_trigger="ACTION=log_ok",
                is_noise_query=True,
            ),
        ],
        evolution_seed=EvolutionarySeedDef(
            missing_node=ScaffoldNode(
                node_id="node_db_pool_exhaustion",
                node_type=NodeType.CLAIM,
                cue="DB connection pool saturation > 95% mandates ACTION=page_oncall_sre",
                keywords=["db", "pool", "saturation", "deadlock", "payment", "connection"],
                provenance="SRE_DB_Playbook",
                evidence_score=0.94,
            ),
            target_guardrail="Escalate DB connection pool saturation > 95% to ACTION=page_oncall_sre immediately",
        ),
    )
    return {sre_pack.domain_id: sre_pack}


class DomainPackSynthesizer:
    @classmethod
    def synthesize(
        cls, domain_id: str, description: str, model_name: str | None = None
    ) -> tuple[DomainPack, str]:
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        builtins = get_builtin_domain_packs()
        if domain_id in builtins:
            return builtins[domain_id], "Built-In Template"

        # Fallback or base dynamic builder
        pack = builtins["sre_ops"].model_copy(deep=True)
        pack.domain_id = domain_id
        pack.title = f"Custom Domain Swarm ({domain_id})"
        pack.description = description
        return pack, "Dynamic-Deterministic-Synthesizer"


class UniversalMockFrozenLLM(FrozenLLMClient):
    def __init__(self, action_tokens: list[str]) -> None:
        self.action_tokens = action_tokens
        self.default_action = action_tokens[-1]

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if "RECONSTRUCT_MEMORY_CUES" in system_prompt:
            return "[Reconstructed Connectome Context]: " + user_prompt.replace("\n", " | ")
        combined = f"{system_prompt}\n{user_prompt}".lower()
        for token in self.action_tokens[:-1]:
            if token.lower() in combined:
                return f"[Frozen LLM Output]: {token}"
        return f"[Frozen LLM Output]: {self.default_action}"


class UniversalSwarmOrchestrator(AetherSwarmOrchestrator):
    def __init__(self, pack: DomainPack, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.action_tokens = pack.action_tokens


class UniversalProposeProbeComposeEngine(LiveProposeProbeComposeEngine):
    def __init__(self, pack: DomainPack, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pack = pack

    def propose_candidates(
        self, current_harness: HarnessConfig, anomaly_report: TraceAnomalyReport
    ) -> list[HarnessDiff]:
        seed = self.pack.evolution_seed
        return [
            HarnessDiff(
                diff_id=f"{self.pack.domain_id}_cand_invariant",
                variant_type="invariant_agentic",
                description="Tighten scaffold_threshold to 0.48.",
                new_scaffold_threshold=0.48,
            ),
            HarnessDiff(
                diff_id=f"{self.pack.domain_id}_cand_domain_expand",
                variant_type="domain_connectome",
                description=f"Promote '{seed.missing_node.node_id}' into Connectome.",
                new_scaffold_threshold=0.22,
                promoted_nodes=[seed.missing_node],
            ),
            HarnessDiff(
                diff_id=f"{self.pack.domain_id}_cand_hybrid",
                variant_type="hybrid_pareto",
                description="Promote missing node and tune threshold.",
                new_scaffold_threshold=0.46,
                added_guardrails=[seed.target_guardrail],
                promoted_nodes=[seed.missing_node],
            ),
        ]


class AetherWorkspace:
    def __init__(self, base_dir: str | Path = ".") -> None:
        self.base_dir = Path(base_dir)
        self.domains_dir = self.base_dir / "domains"
        self.memory_dir = self.base_dir / "memory"
        self.traces_dir = self.base_dir / "traces"
        for d in (self.domains_dir, self.memory_dir, self.traces_dir):
            d.mkdir(parents=True, exist_ok=True)

    def domain_manifest_path(self, domain_id: str) -> Path:
        return self.domains_dir / f"{domain_id}.json"

    def connectome_db_path(self, domain_id: str) -> Path:
        return self.memory_dir / f"connectome_{domain_id}.sqlite"

    def save_and_seed_pack(self, pack: DomainPack) -> tuple[Path, Path]:
        manifest_path = self.domain_manifest_path(pack.domain_id)
        manifest_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
        db_path = self.connectome_db_path(pack.domain_id)
        connectome = ConnectomeScaffoldGraph(db_path)
        for node in pack.initial_nodes:
            connectome.write_evidence_gated(node, min_evidence_threshold=0.50)
        return manifest_path, db_path

    def load_domain_runtime(
        self, domain_id: str, model_name: str | None = None
    ) -> tuple[DomainPack, ConnectomeScaffoldGraph, ToolRegistry, FrozenLLMClient]:
        manifest_path = self.domain_manifest_path(domain_id)
        if not manifest_path.exists():
            builtins = get_builtin_domain_packs()
            pack = builtins.get(domain_id, builtins["sre_ops"])
            self.save_and_seed_pack(pack)

        pack = DomainPack.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        connectome = ConnectomeScaffoldGraph(self.connectome_db_path(domain_id))
        registry = ToolRegistry()
        for t in pack.tools:
            registry.register(
                ToolSpec(
                    name=t.name,
                    description=t.description,
                    trigger_keywords=set(t.trigger_keywords),
                    cost_estimate=t.cost_estimate,
                    reliability_prior=t.reliability_prior,
                    handler=lambda q, out=t.simulated_output: out,
                )
            )
        llm = build_llm_client(model=model_name)
        if not isinstance(llm, OpenRouterFrozenLLM):
            llm = UniversalMockFrozenLLM(pack.action_tokens)
        return pack, connectome, registry, llm


def main() -> None:
    parser = argparse.ArgumentParser(description="Aether Universal CLI")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run")
    p_run.add_argument("--domain", default="sre_ops")
    p_run.add_argument("--query", required=True)

    args = parser.parse_args()
    ws = AetherWorkspace()

    if args.command == "run":
        pack, connectome, registry, llm = ws.load_domain_runtime(args.domain)
        orchestrator = UniversalSwarmOrchestrator(
            pack=pack, llm=llm, connectome=connectome, registry=registry,
            librarian_harness=pack.librarian_harness,
            worker_harness=pack.worker_harness,
            verifier_harness=pack.verifier_harness,
        )
        res = orchestrator.dispatch(args.query)
        print(f"Result: {res.final_action} (Approved: {res.verifier_approved})")
    else:
        print("Aether Universal CLI operational. Use 'run --domain <id> --query <text>'")


if __name__ == "__main__":
    main()
