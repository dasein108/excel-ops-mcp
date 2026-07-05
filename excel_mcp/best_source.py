from __future__ import annotations

from excel_mcp.schemas import RegionInfo, SheetInfo

_KIND_WEIGHT = {"summary": 100, "table": 60, "ledger": 40, "parameters": 20, "metadata": 5, "unknown": 0}

# Row-label keywords that mark a region as summary-shaped even when the persisted
# `region_kind` says "table". This only affects ranking, not `region_kind` itself,
# which stays untouched because it also drives duckdb table naming
# (see regions.py::detect_regions) that other tools/tests key off of.
_SUMMARY_ROW_LABEL_TERMS = ("total", "summary")


def _looks_like_summary(region: RegionInfo) -> bool:
    """Matrix-layout regions (e.g. a transposed dashboard) carry their descriptive
    labels as row values in the leading column rather than as column headers, so
    `_classify_region` in regions.py can't see them and falls back to "table".
    Recover that signal here from the region's sampled row text. Narrower keyword
    set than column-name classification ("total"/"summary" only) to avoid false
    positives like "Monthly Rent" matching a broader "month" substring check.
    """
    row_labels = " ".join(str(value).lower() for row in region.sample_rows for value in row.values() if isinstance(value, str))
    return any(term in row_labels for term in _SUMMARY_ROW_LABEL_TERMS)


def _effective_kind(region: RegionInfo) -> str:
    if region.region_kind == "table" and _looks_like_summary(region):
        return "summary"
    return region.region_kind


def rank_sources(sheets: list[SheetInfo]) -> list[dict]:
    """Rank sheets best-first for 'where is the clean aggregated data'.

    A summary/dashboard region beats a raw table beats a ledger. Ties break on
    the top region's detection confidence. Advisory only.
    """
    scored: list[dict] = []
    for sheet in sheets:
        if not sheet.regions:
            scored.append({"sheet": sheet.name, "reason": "no detected regions", "score": 0.0})
            continue
        best = max(sheet.regions, key=lambda r: (_KIND_WEIGHT.get(_effective_kind(r), 0), r.confidence))
        kind = _effective_kind(best)
        score = _KIND_WEIGHT.get(kind, 0) + best.confidence
        scored.append({"sheet": sheet.name, "reason": f"{kind} region (conf {best.confidence:.2f})", "score": round(score, 3)})
    return sorted(scored, key=lambda item: item["score"], reverse=True)
