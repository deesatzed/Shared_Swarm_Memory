from dataclasses import dataclass

from swarm_memory.risk import classify


@dataclass(frozen=True)
class Proposal:
    fact_key: str | None
    value: str
    agent_id: str
    evidence_ids: tuple[str, ...]
    write_class: str
    confidence: float | None
    declared_floor: str | None
    action: str | None
    multi_role: bool
    model_class: str | None
    rival_value: str | None
    prior_decision_id: str | None
    prior_value: str | None
    prior_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    final_class: str | None = None
    bar: float | None = None
    confidence: float | None = None
    value: str | None = None
    dissent: str | None = None
    supersedes: str | None = None


def evaluate(proposal: Proposal) -> Decision:
    if proposal.write_class == "trace":
        return Decision(status="ignored_trace", reason="trace")
    if proposal.write_class == "experience" or proposal.fact_key is None:
        return Decision(status="stored_experience", reason="experience")
    if proposal.write_class == "preference":
        return Decision(status="bound", reason="preference_recency", value=proposal.value, final_class="low", bar=None, confidence=proposal.confidence)
    risk = classify(
        fact_key=proposal.fact_key,
        declared_floor=proposal.declared_floor,
        action=proposal.action,
        multi_role=proposal.multi_role,
        has_prior=proposal.prior_decision_id is not None,
        model_class=proposal.model_class,
    )
    if proposal.confidence is None or isinstance(proposal.confidence, bool) or not isinstance(proposal.confidence, (int, float)):
        return Decision(status="open", reason="missing_confidence", final_class=risk.final_class, bar=risk.bar)
    if proposal.prior_decision_id is not None:
        if proposal.rival_value is None:
            return Decision(status="open", reason="missing_rival", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
        if set(proposal.evidence_ids).issubset(set(proposal.prior_evidence_ids)):
            return Decision(status="rejected", reason="same_evidence", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
    if float(proposal.confidence) < risk.bar:
        return Decision(status="open", reason="below_bar", final_class=risk.final_class, bar=risk.bar, confidence=float(proposal.confidence))
    return Decision(
        status="bound",
        reason="cleared_bar",
        final_class=risk.final_class,
        bar=risk.bar,
        confidence=float(proposal.confidence),
        value=proposal.value,
        dissent=proposal.prior_value,
        supersedes=proposal.prior_decision_id,
    )
