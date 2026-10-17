from collections.abc import Mapping, Sequence


def filter_hits(
    hits: Sequence[Mapping[str, object]],
    bindings: Mapping[object, object],
    limit: int,
    char_budget: int,
    scores: Mapping[object, float] | None = None,
    per_item_cap: int | None = None,
) -> list[Mapping[str, object]]:
    ordered = list(hits)
    if scores is not None:
        ordered.sort(key=lambda hit: float(scores.get(hit.get("decision_id"), 0.0)), reverse=True)
    kept: list[Mapping[str, object]] = []
    used = 0
    for hit in ordered:
        if len(kept) >= limit:
            break
        decision_id = hit.get("decision_id")
        if decision_id is None or decision_id != bindings.get(hit.get("fact_key")):
            continue
        size = len(hit["text"])
        if per_item_cap is not None and size > per_item_cap:
            continue
        if used + size > char_budget:
            continue
        kept.append(hit)
        used += size
    return kept
