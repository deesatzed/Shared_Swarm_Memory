from dataclasses import dataclass

ORDER = ("low", "standard", "high", "critical")
BARS = {"low": 0.60, "standard": 0.80, "high": 0.92, "critical": 0.97}
HIGH_PREFIXES = ("clinical.", "genome.", "identity.", "auth.")
CRITICAL_ACTIONS = frozenset({"patient_facing", "delete", "publish"})


@dataclass(frozen=True)
class RiskResult:
    final_class: str
    bar: float
    floor: str


def _rank(name: str) -> int:
    return ORDER.index(name)


def _one_step_up(name: str) -> str:
    return ORDER[min(_rank(name) + 1, len(ORDER) - 1)]


def _floor(fact_key: str, declared_floor: str | None, action: str | None) -> str:
    if declared_floor == "critical" or action in CRITICAL_ACTIONS:
        return "critical"
    if declared_floor == "high" or fact_key.startswith(HIGH_PREFIXES):
        return "high"
    if declared_floor == "low":
        return "low"
    return "standard"


def classify(fact_key: str, declared_floor: str | None, action: str | None, multi_role: bool, has_prior: bool, model_class: str | None) -> RiskResult:
    floor = _floor(fact_key, declared_floor, action)
    current = floor
    if multi_role or has_prior:
        if _rank(current) < _rank("high"):
            current = "high"
    if model_class in ORDER and _rank(model_class) > _rank(current):
        current = _one_step_up(current)
    return RiskResult(final_class=current, bar=BARS[current], floor=floor)
