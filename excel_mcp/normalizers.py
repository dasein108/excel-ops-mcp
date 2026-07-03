from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


PERCENT_HINTS = (
    "apy",
    "apr",
    "yield",
    "rate",
    "pct",
    "percent",
    "доход",
    "доходность",
    "ставк",
    "процент",
)


@dataclass(frozen=True)
class PercentValue:
    kind: str
    num: float | None
    min: float | None
    max: float | None


def is_percent_like_column(name: str, values: list[Any]) -> bool:
    lowered = name.lower()
    if any(hint in lowered for hint in PERCENT_HINTS):
        return True
    parsed = [parse_percent_value(value) for value in values if value not in (None, "")]
    if not parsed:
        return False
    usable = [item for item in parsed if item.kind in {"number", "percent", "range"}]
    return len(usable) >= max(2, len(parsed) // 2)


def parse_percent_value(value: Any) -> PercentValue:
    if value is None or value == "":
        return PercentValue("empty", None, None, None)
    if isinstance(value, str) and value.strip().startswith("="):
        return PercentValue("formula", None, None, None)
    if isinstance(value, bool):
        return PercentValue("other", None, None, None)
    if isinstance(value, (int, float)):
        number = float(value)
        return PercentValue("number", number, number, number)

    text = str(value).strip().replace(",", ".")
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return PercentValue("other", None, None, None)

    has_percent = "%" in text or "процент" in text.lower()
    if len(numbers) >= 2:
        low, high = min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
        if has_percent or high > 1:
            low /= 100
            high /= 100
        return PercentValue("range", None, low, high)

    number = numbers[0]
    if has_percent or number > 1:
        number /= 100
        return PercentValue("percent", number, number, number)
    return PercentValue("number", number, number, number)


def derived_percent_column_names(name: str) -> list[str]:
    return [f"{name}__kind", f"{name}__num", f"{name}__min", f"{name}__max"]
