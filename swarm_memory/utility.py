import math
from collections.abc import Mapping, Sequence

# An unseen item outranks one that was shown and ignored. One citation does not.
_C = 0.5
_PRIOR = 0.5
_PRIOR_WEIGHT = 1.0
_COST_WEIGHT = 0.05


def ucb_scores(
    decision_ids: Sequence[str],
    utilities: Mapping[str, tuple[float, float]],
    text_lengths: Mapping[str, float] | None = None,
) -> dict[str, float]:
    total_trials = sum(trials for _, trials in utilities.values())
    lengths = text_lengths or {}
    scores: dict[str, float] = {}
    for decision_id in decision_ids:
        successes, trials = utilities.get(decision_id, (0.0, 0.0))
        mean = (successes + _PRIOR_WEIGHT * _PRIOR) / (trials + _PRIOR_WEIGHT)
        bonus = _C * math.sqrt((2 * math.log(total_trials + 1)) / (trials + 1))
        penalty = _COST_WEIGHT * (float(lengths.get(decision_id, 0.0)) / 100)
        scores[decision_id] = mean + bonus - penalty
    return scores
