from collections.abc import Mapping, Sequence


def _binding_line(item: Mapping[str, object]) -> str:
    return (
        f"{item['fact_key']} value={item['value']} "
        f"decision_id={item['decision_id']} confidence={item['confidence']}"
    )


def _open_line(item: Mapping[str, object]) -> str:
    values = item["values"]
    if isinstance(values, (list, tuple)):
        rendered = ",".join(str(value) for value in values)
    else:
        rendered = str(values)
    return f"{item['fact_key']} values={rendered}"


def _within(lines: list[str], limit: int) -> bool:
    return len("\n".join(lines)) <= limit


def render_card(
    bindings: Sequence[Mapping[str, object]],
    opens: Sequence[Mapping[str, object]],
    limit: int = 2000,
) -> str:
    lines = ["BINDINGS"]
    blocked = False
    for item in bindings:
        line = _binding_line(item)
        if not _within(lines + [line, "OPEN"], limit):
            blocked = True
            break
        lines.append(line)
    if _within(lines + ["OPEN"], limit):
        lines.append("OPEN")
        if not blocked:
            for item in opens:
                line = _open_line(item)
                if not _within(lines + [line], limit):
                    break
                lines.append(line)
    return "\n".join(lines)
