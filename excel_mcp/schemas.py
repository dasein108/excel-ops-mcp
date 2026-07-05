from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Telemetry(BaseModel):
    cache: Literal["hit", "miss", "none"] = "none"
    elapsed_ms: int | None = None
    rows_scanned: int | None = None
    rows_returned: int | None = None
    truncated: bool = False
    estimated_cells_avoided: int | None = None


class BaseResponse(BaseModel):
    ok: bool
    session_id: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    telemetry: Telemetry = Field(default_factory=Telemetry)
    error: ErrorInfo | None = None


class SpreadsheetOpenRequest(BaseModel):
    path: str | None = None
    content_base64: str | None = None
    filename: str | None = None


class SpreadsheetOpenResponse(BaseResponse):
    path: str | None = None
    file_size: int | None = None
    mtime: float | None = None


class WorkbookListRequest(BaseModel):
    glob: str | None = None
    limit: int = 200


class WorkbookInfo(BaseModel):
    path: str
    size: int
    modified: float


class WorkbookListResponse(BaseResponse):
    root_paths: list[str] = Field(default_factory=list)
    workbooks: list[WorkbookInfo] = Field(default_factory=list)


class SpreadsheetDescribeRequest(BaseModel):
    session_id: str
    detail: Literal["compact", "standard"] = "compact"


class ColumnInfo(BaseModel):
    name: str
    index: int
    type: str
    source_ref: str


class RegionInfo(BaseModel):
    region_id: str
    table_name: str
    sheet: str
    bounds: str
    header_row: int | None = None
    data_start_row: int | None = None
    row_count: int
    column_count: int
    region_kind: Literal["table", "ledger", "parameters", "summary", "metadata", "unknown"]
    orientation: Literal["tabular", "matrix"] = "tabular"
    confidence: float
    columns: list[ColumnInfo] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    source_ref: str


class SheetInfo(BaseModel):
    name: str
    bounds: str
    hidden: bool = False
    merged_ranges_count: int = 0
    merged_ranges_sample: list[str] = Field(default_factory=list)
    formula_count: int = 0
    named_ranges: list[str] = Field(default_factory=list)
    excel_tables: list[str] = Field(default_factory=list)
    regions: list[RegionInfo] = Field(default_factory=list)
    source_ref: str


class SpreadsheetDescribeResponse(BaseResponse):
    file_name: str | None = None
    sheet_count: int = 0
    sheets: list[SheetInfo] = Field(default_factory=list)


class SpreadsheetQueryRequest(BaseModel):
    session_id: str
    sql: str
    limit: int | None = None


class SpreadsheetQueryResponse(BaseResponse):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0


class SpreadsheetReadRangeRequest(BaseModel):
    session_id: str
    sheet: str
    range: str
    include: list[Literal["values", "formulas", "number_formats", "comments", "hyperlinks", "styles", "merged"]] = Field(
        default_factory=lambda: ["values"]
    )


class SpreadsheetReadRangeResponse(BaseResponse):
    cells: list[list[dict[str, Any]]] = Field(default_factory=list)


class SpreadsheetTraceRequest(BaseModel):
    session_id: str
    sheet: str
    cell: str
    depth: int = 1


class SpreadsheetTraceResponse(BaseResponse):
    target: dict[str, Any] = Field(default_factory=dict)
    depth: int = 1


class SpreadsheetWriteRequest(BaseModel):
    session_id: str
    operations: list[dict[str, Any]]
    dry_run: bool = True


class SpreadsheetWriteResponse(BaseResponse):
    staged_id: str | None = None
    accepted_operations: int = 0
    rejected_operations: list[dict[str, Any]] = Field(default_factory=list)
    touched_ranges: list[str] = Field(default_factory=list)
    changes: list[dict[str, Any]] = Field(default_factory=list)


class SpreadsheetCommitRequest(BaseModel):
    session_id: str
    staged_id: str
    output_path: str | None = None
    overwrite: bool = False


class SpreadsheetCommitResponse(BaseResponse):
    output_path: str | None = None
    changed_ranges: list[str] = Field(default_factory=list)
    changes: list[dict[str, Any]] = Field(default_factory=list)


class SpreadsheetDiffRequest(BaseModel):
    session_id: str
    staged_id: str | None = None


class SpreadsheetDiffResponse(BaseResponse):
    changed_ranges: list[str] = Field(default_factory=list)
    changes: list[dict[str, Any]] = Field(default_factory=list)


class SpreadsheetSummaryRequest(BaseModel):
    session_id: str
    sheet: str
    range: str
    growth: bool = False


class SpreadsheetSummaryResponse(BaseResponse):
    sheet: str | None = None
    range: str | None = None
    count: int = 0
    skipped: int = 0
    total: float | None = None
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    yoy_growth_pct: list[float] = Field(default_factory=list)


def error_response(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return BaseResponse(ok=False, error=ErrorInfo(code=code, message=message, details=details or {})).model_dump()
