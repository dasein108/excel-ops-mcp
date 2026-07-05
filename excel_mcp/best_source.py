from __future__ import annotations

from excel_mcp.schemas import SheetInfo

_KIND_WEIGHT = {"summary": 100, "table": 60, "ledger": 40, "parameters": 20, "metadata": 5, "unknown": 0}


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
        best = max(sheet.regions, key=lambda r: (_KIND_WEIGHT.get(r.region_kind, 0), r.confidence))
        score = _KIND_WEIGHT.get(best.region_kind, 0) + best.confidence
        scored.append({"sheet": sheet.name, "reason": f"{best.region_kind} region (conf {best.confidence:.2f})", "score": round(score, 3)})
    return sorted(scored, key=lambda item: item["score"], reverse=True)
