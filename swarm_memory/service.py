import json
from dataclasses import dataclass
from uuid import uuid4

from swarm_memory.decide import Proposal, evaluate
from swarm_memory.recall import filter_hits
from swarm_memory.store import Store


@dataclass(frozen=True)
class RememberResult:
    status: str
    decision_id: str | None


class MemoryService:
    def __init__(self, path, index):
        self.store = Store(path)
        self.index = index

    def remember(
        self,
        *,
        fact_key: str | None,
        value: str,
        agent_id: str,
        evidence_ids,
        write_class: str,
        confidence: float | None,
        declared_floor: str | None = None,
        action: str | None = None,
        multi_role: bool = False,
        model_class: str | None = None,
    ) -> RememberResult:
        prior_decision_id = None
        prior_value = None
        prior_evidence_ids: tuple[str, ...] = ()
        rival_value = None
        if fact_key is not None:
            binding = self.store.current_binding(fact_key)
            if binding is not None:
                prior_decision_id = binding["decision_id"]
                prior_value = binding["value"]
                rival_value = prior_value
                instance = self.store.instance(prior_decision_id)
                if instance is None:
                    prior_evidence_ids = ()
                else:
                    prior_evidence_ids = tuple(json.loads(instance["evidence_json"]))

        proposal = Proposal(
            fact_key=fact_key,
            value=value,
            agent_id=agent_id,
            evidence_ids=tuple(evidence_ids),
            write_class=write_class,
            confidence=confidence,
            declared_floor=declared_floor,
            action=action,
            multi_role=multi_role,
            model_class=model_class,
            rival_value=rival_value,
            prior_decision_id=prior_decision_id,
            prior_value=prior_value,
            prior_evidence_ids=prior_evidence_ids,
        )
        decision = evaluate(proposal)
        if decision.status == "ignored_trace":
            return RememberResult(status="ignored_trace", decision_id=None)

        candidate_class = "experience" if decision.status == "stored_experience" else write_class
        self.store.save_candidate(
            str(uuid4()),
            fact_key,
            value,
            agent_id,
            list(evidence_ids),
            candidate_class,
        )
        if decision.status not in {"open", "rejected", "bound"}:
            return RememberResult(status=decision.status, decision_id=None)

        decision_id = str(uuid4())
        self.store.save_instance(
            instance_id=decision_id,
            fact_key=fact_key,
            status=decision.status,
            final_class=decision.final_class,
            bar=decision.bar,
            confidence=decision.confidence,
            value=value,
            dissent=decision.dissent,
            evidence_ids=list(evidence_ids),
            agent_id=agent_id,
            supersedes=decision.supersedes,
        )
        if decision.status != "bound":
            return RememberResult(status=decision.status, decision_id=decision_id)

        self.store.bind(fact_key, decision_id, value, decision.final_class or "low")
        text = f"{fact_key} value={value} decision_id={decision_id}"
        try:
            self.index.write_bound_sentence(decision_id, fact_key, text)
        except Exception:
            return RememberResult(status="bound", decision_id=decision_id)
        self.store.mark_indexed(decision_id)
        return RememberResult(status="bound", decision_id=decision_id)

    def recall(self, query: str, hits):
        kept = filter_hits(hits, self.store.binding_ids(), limit=5, char_budget=2000)
        returned_ids = [str(hit["decision_id"]) for hit in kept]
        self.store.log_recall(query, returned_ids)
        return kept
