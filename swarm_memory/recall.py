from collections.abc import Mapping, Sequence


def filter_hits(
    hits: Sequence[Mapping[str, object]],
    bindings: Mapping[object, object],
    limit: int,
    char_budget: int,
) -> list[Mapping[str, object]]:
    kept: list[Mapping[str, object]] = []
    used = 0
    for hit in hits:
        if len(kept) >= limit:
            break
        decision_id = hit.get("decision_id")
        if decision_id is None or decision_id != bindings.get(hit.get("fact_key")):
            continue
        size = len(hit["text"])
        if used + size > char_budget:
            break
        kept.append(hit)
        used += size
    return kept
