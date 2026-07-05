from __future__ import annotations

from openpyxl.utils.cell import range_boundaries

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.policy import PolicyError
from excel_mcp.schemas import SpreadsheetReadRangeRequest, SpreadsheetReadRangeResponse
from excel_mcp.session import WorkbookSession
from excel_mcp.utils import cell_value_for_json, source_ref
from excel_mcp.values import get_value_resolver


def read_range(
    session: WorkbookSession,
    request: SpreadsheetReadRangeRequest,
    config: ExcelMcpConfig,
    *,
    full: bool = False,
) -> SpreadsheetReadRangeResponse:
    if request.sheet not in session.workbook.sheetnames:
        raise PolicyError("sheet_not_found", "Sheet does not exist.")
    min_col, min_row, max_col, max_row = range_boundaries(request.range)
    cell_count = (max_col - min_col + 1) * (max_row - min_row + 1)
    if cell_count > config.max_read_range_cells:
        raise PolicyError("range_too_large", "Requested range exceeds max_read_range_cells.")

    ws = session.workbook[request.sheet]
    resolver = get_value_resolver(session) if "values" in request.include else None
    rows = []
    for row_idx in range(min_row, max_row + 1):
        row = []
        for col_idx in range(min_col, max_col + 1):
            cell = ws.cell(row_idx, col_idx)
            item = {"address": cell.coordinate}
            if "values" in request.include:
                # Return the computed number, not the formula string. Falls back to
                # the raw literal for non-formula cells.
                computed = resolver.resolve(request.sheet, cell.coordinate, cell.value)
                item["value"] = cell_value_for_json(computed)
            if "formulas" in request.include:
                item["formula"] = cell.value if isinstance(cell.value, str) and cell.value.startswith("=") else None
            if "number_formats" in request.include:
                item["number_format"] = cell.number_format
            if "comments" in request.include:
                item["comment"] = cell.comment.text if cell.comment else None
            if "hyperlinks" in request.include:
                item["hyperlink"] = cell.hyperlink.target if cell.hyperlink else None
            if "merged" in request.include:
                item["merged"] = any(cell.coordinate in merged for merged in ws.merged_cells.ranges)
            row.append(item)
        rows.append(row)
    ref = source_ref(session.path, request.sheet, request.range)

    # Anti-loop guard: repeatedly re-reading the same small range in one session usually
    # means the agent is poking cell-by-cell instead of using query/describe. Warn so it
    # stops looping. Only small ranges are tracked; large repeated reads are a different case.
    warnings: list[str] = []
    if resolver is not None and "computed_value_unavailable" in resolver.warnings:
        warnings.append(
            "Some formula cells have no cached value and could not be recomputed "
            "(install the 'recompute' extra to evaluate them). Those cells returned null."
        )
    if cell_count <= config.repeat_read_small_cells:
        key = f"{request.sheet}!{request.range}"
        prior = session.recent_read_ranges.count(key)
        session.recent_read_ranges.append(key)
        if len(session.recent_read_ranges) > 200:
            del session.recent_read_ranges[:-200]
        if prior + 1 >= config.repeat_read_warn_threshold:
            warnings.append(
                f"Range {key} has been read {prior + 1} times this session. "
                "Prefer 'query' or 'describe' over repeated small range reads."
            )

    truncated = not full and len(rows) > config.read_row_limit
    if truncated:
        rows = rows[: config.read_row_limit]

    response = SpreadsheetReadRangeResponse(
        ok=True, session_id=session.session_id, source_refs=[ref], cells=rows, warnings=warnings
    )
    if truncated:
        response.telemetry.truncated = True
        response.telemetry.rows_returned = config.read_row_limit
    return response
