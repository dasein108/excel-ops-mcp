# MCP Tool Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the 10 flat, session-bound MCP tools into 4 fat, hybrid-state tools with server-side aggregation and a clean-source hint, cutting round-trips, schema-load waves, and model-side arithmetic.

**Architecture:** A shared `resolve_source()` helper turns a `path`-or-`session_id` payload into a warm session for every tool. Three fat tools (`spreadsheet_inspect`, `spreadsheet_edit`, `spreadsheet_list`) plus the retained `spreadsheet_query` sit on top of the existing engine (`describe_workbook`, `read_range`, `trace_cell`, `stage_write`/`commit_staged`, `DuckDbEngine`). New compute (`summarize_range`) and a `best_source` ranker remove the manual-math and wrong-sheet costs. v1 tools stay as deprecated shims for one release.

**Tech Stack:** Python 3.10+, Pydantic v2, FastMCP, openpyxl, DuckDB, pytest.

## Global Constraints

- Python floor: 3.10 (union `X | None` syntax already in use); do not lower.
- Pydantic v2 models only; response models subclass `BaseResponse` and are returned via `.model_dump()`.
- `.xlsx` only; no new file formats.
- All responses keep the existing envelope: `ok`, `session_id`, `source_refs`, `warnings`, `telemetry`, `error`. Errors go through `error_response(code, message, details)`.
- Every tool method audits via `self._audit(operation, response, input_summary, path, started)`.
- One engine: CLI and MCP call the same `ExcelMcpTools` methods. Never fork logic between them.
- v1 tools/CLI verbs remain functional as deprecated shims for one minor release; deprecation is a version bump (hatch-vcs tag).
- Fixture truth (`examples/saas.xlsx`, `Dashboard` sheet): total `$12,784,732`, max `$3,127,445` (Year 5), mean `$2,556,946`; YoY growth `68.8 / 12.0 / 8.0 / 5.0 %`.

---

### Task 1: Hybrid source resolver

**Files:**
- Modify: `excel_mcp/tools.py` (add `resolve_source` method on `ExcelMcpTools`, near `_materialize_upload`)
- Test: `tests/test_hybrid_source.py`

**Interfaces:**
- Consumes: `self.sessions.open(path) -> (WorkbookSession, bool)`, `self.sessions.get(session_id) -> WorkbookSession`, `self.path_policy.validate_input_file(path)`, `self._materialize_upload(content_base64, filename) -> Path`.
- Produces: `resolve_source(self, payload: dict) -> tuple[str, bool]` returning `(session_id, cache_hit)`. Raises `KeyError` for an unknown `session_id`, `PolicyError` for a bad path. Accepts keys: `session_id`, `path`, `content_base64`, `filename`. Precedence: `session_id` > `content_base64` > `path`. Missing all three raises `PolicyError("missing_source", ...)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hybrid_source.py
from pathlib import Path

import pytest

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.policy import PolicyError
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def _tools(tmp_path: Path) -> ExcelMcpTools:
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))


def test_resolve_by_path_opens_and_reports_miss(tmp_path):
    tools = _tools(tmp_path)
    session_id, cache_hit = tools.resolve_source({"path": EXAMPLE})
    assert session_id
    assert cache_hit is False


def test_resolve_same_path_twice_is_cache_hit(tmp_path):
    tools = _tools(tmp_path)
    first, _ = tools.resolve_source({"path": EXAMPLE})
    second, cache_hit = tools.resolve_source({"path": EXAMPLE})
    assert first == second
    assert cache_hit is True


def test_resolve_by_session_id_passthrough(tmp_path):
    tools = _tools(tmp_path)
    session_id, _ = tools.resolve_source({"path": EXAMPLE})
    again, cache_hit = tools.resolve_source({"session_id": session_id})
    assert again == session_id
    assert cache_hit is True


def test_resolve_missing_source_raises_policy_error(tmp_path):
    tools = _tools(tmp_path)
    with pytest.raises(PolicyError):
        tools.resolve_source({})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hybrid_source.py -v`
Expected: FAIL with `AttributeError: 'ExcelMcpTools' object has no attribute 'resolve_source'`.

- [ ] **Step 3: Write minimal implementation**

Add to `excel_mcp/tools.py`, as a method on `ExcelMcpTools` (place directly above `_materialize_upload`):

```python
    def resolve_source(self, payload: dict[str, Any]) -> tuple[str, bool]:
        """Turn a path-or-session payload into (session_id, cache_hit).

        Precedence: an explicit session_id wins; else uploaded bytes; else a
        host path. Missing all three is a PolicyError. This is the single entry
        point every fat tool uses so no tool needs a separate open call.
        """
        session_id = payload.get("session_id")
        if session_id:
            self.sessions.get(session_id)  # raises KeyError if unknown/stale
            return session_id, True
        if payload.get("content_base64") is not None:
            path = self._materialize_upload(payload["content_base64"], payload.get("filename"))
        elif payload.get("path"):
            path = self.path_policy.validate_input_file(payload["path"])
        else:
            raise PolicyError("missing_source", "Provide 'session_id', 'path', or 'content_base64'.")
        session, cache_hit = self.sessions.open(path)
        return session.session_id, cache_hit
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hybrid_source.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/tools.py tests/test_hybrid_source.py
git commit -m "feat(tools): hybrid path-or-session source resolver"
```

---

### Task 2: Server-side range summary

**Files:**
- Create: `excel_mcp/summarize.py`
- Modify: `excel_mcp/schemas.py` (add `SpreadsheetSummaryRequest`, `SpreadsheetSummaryResponse`)
- Test: `tests/test_summarize.py`

**Interfaces:**
- Consumes: `read_range(session, SpreadsheetReadRangeRequest(...), config) -> SpreadsheetReadRangeResponse` whose `.cells` is a list of rows, each a list of `{"value": ...}` dicts. `session` from `SessionRegistry.get`.
- Produces: `summarize_range(session, sheet, cell_range, config, *, growth=False) -> SpreadsheetSummaryResponse`. Numeric cells only; non-numeric are skipped and counted in `skipped`. `growth=True` adds `yoy_growth_pct` = percent change between consecutive numeric values, length `len(values) - 1`, each rounded to 1 decimal.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_summarize.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.session import SessionRegistry
from excel_mcp.summarize import summarize_range

EXAMPLE = Path("examples/saas.xlsx").resolve()


def _session(tmp_path):
    reg = SessionRegistry(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    session, _ = reg.open(EXAMPLE)
    return session


def test_summary_matches_known_dashboard_totals(tmp_path):
    session = _session(tmp_path)
    resp = summarize_range(session, "Dashboard", "B5:F5",
                           ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path),
                           growth=True)
    assert resp.ok
    assert resp.count == 5
    assert round(resp.total) == 12784732
    assert round(resp.max) == 3127445
    assert round(resp.mean) == 2556946
    assert [round(g, 1) for g in resp.yoy_growth_pct] == [68.8, 12.0, 8.0, 5.0]


def test_summary_skips_non_numeric(tmp_path):
    session = _session(tmp_path)
    resp = summarize_range(session, "Dashboard", "A5:F5",
                           ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    assert resp.count == 5
    assert resp.skipped >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'excel_mcp.summarize'`.

- [ ] **Step 3a: Add the schemas**

Append to `excel_mcp/schemas.py`:

```python
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
```

- [ ] **Step 3b: Write the summarizer**

Create `excel_mcp/summarize.py`:

```python
from __future__ import annotations

from numbers import Number

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.range_read import read_range
from excel_mcp.schemas import (
    SpreadsheetReadRangeRequest,
    SpreadsheetSummaryResponse,
)
from excel_mcp.session import WorkbookSession


def _numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Number):
        return float(value)
    return None


def summarize_range(
    session: WorkbookSession,
    sheet: str,
    cell_range: str,
    config: ExcelMcpConfig,
    *,
    growth: bool = False,
) -> SpreadsheetSummaryResponse:
    read = read_range(
        session,
        SpreadsheetReadRangeRequest(session_id=session.session_id, sheet=sheet, range=cell_range, include=["values"]),
        config,
    )
    values: list[float] = []
    skipped = 0
    for row in read.cells:
        for cell in row:
            num = _numeric(cell.get("value"))
            if num is None:
                if cell.get("value") not in (None, ""):
                    skipped += 1
                continue
            values.append(num)
    if not values:
        return SpreadsheetSummaryResponse(ok=True, session_id=session.session_id, sheet=sheet, range=cell_range, skipped=skipped)
    yoy: list[float] = []
    if growth:
        for prev, cur in zip(values, values[1:]):
            yoy.append(round((cur - prev) / prev * 100, 1) if prev else 0.0)
    return SpreadsheetSummaryResponse(
        ok=True,
        session_id=session.session_id,
        sheet=sheet,
        range=cell_range,
        count=len(values),
        skipped=skipped,
        total=sum(values),
        mean=sum(values) / len(values),
        min=min(values),
        max=max(values),
        yoy_growth_pct=yoy,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: PASS (2 passed). If cell dicts use a key other than `"value"`, inspect one `read.cells[0][0]` and adjust `_numeric(cell.get(...))` to the actual key, then re-run.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/summarize.py excel_mcp/schemas.py tests/test_summarize.py
git commit -m "feat(summarize): server-side range total/mean/min/max/yoy"
```

---

### Task 3: `best_source` hint on describe

**Files:**
- Create: `excel_mcp/best_source.py`
- Modify: `excel_mcp/schemas.py` (add `best_source` field to `SpreadsheetDescribeResponse`)
- Modify: `excel_mcp/describe.py` (populate `best_source` in `describe_workbook`)
- Test: `tests/test_best_source.py`

**Interfaces:**
- Consumes: `SpreadsheetDescribeResponse.sheets: list[SheetInfo]`, each `SheetInfo.regions: list[RegionInfo]` with `region_kind` in {table, ledger, parameters, summary, metadata, unknown} and `confidence: float`.
- Produces: `rank_sources(sheets) -> list[dict]` sorted best-first, each `{"sheet", "reason", "score"}`. A `summary`-kind region scores highest (clean aggregated data), then high-confidence `table`, then others. `describe_workbook` sets `response.best_source = rank_sources(response.sheets)[:3]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_best_source.py
from pathlib import Path

from excel_mcp.best_source import rank_sources
from excel_mcp.config import ExcelMcpConfig
from excel_mcp.describe import describe_workbook
from excel_mcp.schemas import RegionInfo, SheetInfo
from excel_mcp.session import SessionRegistry

EXAMPLE = Path("examples/saas.xlsx").resolve()


def _region(kind, conf):
    return RegionInfo(region_id="r", table_name="t", sheet="s", bounds="A1:F5",
                      row_count=5, column_count=6, region_kind=kind, confidence=conf, source_ref="s!A1")


def test_summary_region_ranks_above_raw_table():
    sheets = [
        SheetInfo(name="Revenue Model", bounds="A1:Q40", source_ref="Revenue Model!A1",
                  regions=[_region("table", 0.6), _region("unknown", 0.3)]),
        SheetInfo(name="Dashboard", bounds="A1:F13", source_ref="Dashboard!A1",
                  regions=[_region("summary", 0.9)]),
    ]
    ranked = rank_sources(sheets)
    assert ranked[0]["sheet"] == "Dashboard"
    assert ranked[0]["score"] > ranked[1]["score"]


def test_describe_populates_best_source(tmp_path):
    reg = SessionRegistry(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    session, _ = reg.open(EXAMPLE)
    resp = describe_workbook(session, detail="compact")
    assert resp.best_source
    assert "sheet" in resp.best_source[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_best_source.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'excel_mcp.best_source'`.

- [ ] **Step 3a: Write the ranker**

Create `excel_mcp/best_source.py`:

```python
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
```

- [ ] **Step 3b: Wire into schema + describe**

In `excel_mcp/schemas.py`, add to `SpreadsheetDescribeResponse`:

```python
    best_source: list[dict[str, Any]] = Field(default_factory=list)
```

In `excel_mcp/describe.py`, import and set it just before `describe_workbook` returns its response object:

```python
from excel_mcp.best_source import rank_sources
# ... inside describe_workbook, after sheets are built and before return:
response.best_source = rank_sources(response.sheets)[:3]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_best_source.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/best_source.py excel_mcp/schemas.py excel_mcp/describe.py tests/test_best_source.py
git commit -m "feat(describe): best_source hint ranking clean sheets first"
```

---

### Task 4: `spreadsheet_inspect` fat tool (tools + server)

**Files:**
- Modify: `excel_mcp/tools.py` (add `spreadsheet_inspect` method)
- Modify: `excel_mcp/server.py` (register `spreadsheet_inspect`)
- Test: `tests/test_inspect.py`

**Interfaces:**
- Consumes: `self.resolve_source(payload)` (Task 1), `self.spreadsheet_describe`, `self.spreadsheet_read_range`, `self.spreadsheet_trace` (existing), `summarize_range` (Task 2).
- Produces: `spreadsheet_inspect(self, payload: dict) -> dict`. `payload`: `{path|session_id|content_base64, mode, ...}`. `mode` in {describe, read, trace, summary}. `read` needs `sheet`,`range`,`include?`; `trace` needs `sheet`,`cell`,`depth?`; `summary` needs `sheet`,`range`,`growth?`. Every response echoes `session_id`. Unknown mode → `error_response("invalid_mode", ...)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_inspect.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def _tools(tmp_path):
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))


def test_inspect_describe_by_path_auto_opens(tmp_path):
    resp = _tools(tmp_path).spreadsheet_inspect({"path": EXAMPLE, "mode": "describe"})
    assert resp["ok"]
    assert resp["session_id"]
    assert resp["best_source"]


def test_inspect_summary_reuses_session(tmp_path):
    tools = _tools(tmp_path)
    described = tools.spreadsheet_inspect({"path": EXAMPLE, "mode": "describe"})
    resp = tools.spreadsheet_inspect(
        {"session_id": described["session_id"], "mode": "summary", "sheet": "Dashboard", "range": "B5:F5", "growth": True}
    )
    assert round(resp["total"]) == 12784732
    assert [round(g, 1) for g in resp["yoy_growth_pct"]] == [68.8, 12.0, 8.0, 5.0]


def test_inspect_bad_mode(tmp_path):
    resp = _tools(tmp_path).spreadsheet_inspect({"path": EXAMPLE, "mode": "wat"})
    assert resp["ok"] is False
    assert resp["error"]["code"] == "invalid_mode"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_inspect.py -v`
Expected: FAIL with `AttributeError: 'ExcelMcpTools' object has no attribute 'spreadsheet_inspect'`.

- [ ] **Step 3a: Add the tool method**

Add to `excel_mcp/tools.py` (import `summarize_range` at top: `from excel_mcp.summarize import summarize_range`). Place the method after `spreadsheet_describe`:

```python
    def spreadsheet_inspect(self, payload: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        mode = payload.get("mode", "describe")
        try:
            session_id, _ = self.resolve_source(payload)
        except KeyError:
            return error_response("session_not_found", "Session does not exist or workbook changed.")
        except PolicyError as exc:
            return error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
        if mode == "describe":
            return self.spreadsheet_describe({"session_id": session_id, "detail": payload.get("detail", "compact")})
        if mode == "read":
            return self.spreadsheet_read_range({
                "session_id": session_id, "sheet": payload.get("sheet"),
                "range": payload.get("range"), "include": payload.get("include") or ["values"]})
        if mode == "trace":
            return self.spreadsheet_trace({
                "session_id": session_id, "sheet": payload.get("sheet"),
                "cell": payload.get("cell"), "depth": payload.get("depth", 1)})
        if mode == "summary":
            try:
                session = self.sessions.get(session_id)
                resp = summarize_range(session, payload.get("sheet"), payload.get("range"), self.config,
                                       growth=bool(payload.get("growth"))).model_dump()
                resp["telemetry"]["elapsed_ms"] = _elapsed_ms(started)
                self._audit("summary", resp, {"sheet": payload.get("sheet"), "range": payload.get("range")}, str(session.path), started)
                return resp
            except Exception as exc:
                return error_response("summary_failed", str(exc))
        return error_response("invalid_mode", f"Unknown mode '{mode}'. Use describe|read|trace|summary.")
```

- [ ] **Step 3b: Register in server**

Add to `excel_mcp/server.py` inside `main()` (after `spreadsheet_open`):

```python
    @app.tool()
    def spreadsheet_inspect(mode: str = "describe", path: str | None = None, session_id: str | None = None,
                            content_base64: str | None = None, filename: str | None = None,
                            sheet: str | None = None, range: str | None = None, cell: str | None = None,
                            depth: int = 1, include: list[str] | None = None, detail: str = "compact",
                            growth: bool = False) -> dict:
        """Inspect a workbook. Pass a 'path' (auto-opens) OR a 'session_id' from a prior call.

        mode='describe' -> sheets + a 'best_source' hint ranking the cleanest sheet first.
        mode='summary'  -> server computes total/mean/min/max (+ yoy_growth_pct when growth=true)
                           over sheet+range, so you never sum cells yourself.
        mode='read'     -> raw cells for sheet+range (include=['values','formulas',...]).
        mode='trace'    -> formula precedents for sheet+cell to 'depth' levels.
        """
        return tools.spreadsheet_inspect({"mode": mode, "path": path, "session_id": session_id,
            "content_base64": content_base64, "filename": filename, "sheet": sheet, "range": range,
            "cell": cell, "depth": depth, "include": include, "detail": detail, "growth": growth})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_inspect.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/tools.py excel_mcp/server.py tests/test_inspect.py
git commit -m "feat(inspect): fat describe/read/trace/summary tool with hybrid source"
```

---

### Task 5: `spreadsheet_edit` fat tool (stage + optional commit)

**Files:**
- Modify: `excel_mcp/tools.py` (add `spreadsheet_edit` method)
- Modify: `excel_mcp/server.py` (register `spreadsheet_edit`)
- Test: `tests/test_edit.py`

**Interfaces:**
- Consumes: `self.resolve_source`, `self.spreadsheet_write` (stages, returns `staged_id`), `self.spreadsheet_commit` (existing).
- Produces: `spreadsheet_edit(self, payload: dict) -> dict`. `payload`: `{path|session_id, operations, dry_run=false, commit=true, output_path?, overwrite?}`. When `dry_run` is true → stage only, return staged diff (never commit). When `dry_run` false and `commit` true → stage then commit in one call; response carries `output_path` and `changes`. Staging rejections short-circuit: if `rejected_operations` non-empty, do NOT commit; return the stage response.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_edit.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def _tools(tmp_path):
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[tmp_path, Path("examples").resolve()], cache_dir=tmp_path))


def _ops():
    return [{"type": "set_values", "sheet": "Dashboard", "start": "A20", "values": [["hello"]]}]


def test_edit_dry_run_stages_without_commit(tmp_path):
    resp = _tools(tmp_path).spreadsheet_edit({"path": EXAMPLE, "operations": _ops(), "dry_run": True})
    assert resp["ok"]
    assert resp["staged_id"]
    assert "output_path" not in resp or resp.get("output_path") is None


def test_edit_commit_writes_file_in_one_call(tmp_path):
    out = str(tmp_path / "out.xlsx")
    resp = _tools(tmp_path).spreadsheet_edit(
        {"path": EXAMPLE, "operations": _ops(), "dry_run": False, "commit": True, "output_path": out})
    assert resp["ok"]
    assert resp["output_path"] == out
    assert Path(out).exists()


def test_edit_rejected_ops_do_not_commit(tmp_path):
    bad = [{"type": "bogus_op", "sheet": "Dashboard"}]
    resp = _tools(tmp_path).spreadsheet_edit(
        {"path": EXAMPLE, "operations": bad, "dry_run": False, "commit": True, "output_path": str(tmp_path / "x.xlsx")})
    assert resp["rejected_operations"]
    assert not Path(tmp_path / "x.xlsx").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_edit.py -v`
Expected: FAIL with `AttributeError: 'ExcelMcpTools' object has no attribute 'spreadsheet_edit'`.

- [ ] **Step 3a: Add the tool method**

Add to `excel_mcp/tools.py` after `spreadsheet_diff`:

```python
    def spreadsheet_edit(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            session_id, _ = self.resolve_source(payload)
        except KeyError:
            return error_response("session_not_found", "Session does not exist or workbook changed.")
        except PolicyError as exc:
            return error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
        dry_run = bool(payload.get("dry_run", False))
        staged = self.spreadsheet_write({
            "session_id": session_id, "operations": payload.get("operations", []), "dry_run": True})
        if not staged.get("ok") or staged.get("rejected_operations") or dry_run or not payload.get("commit", True):
            return staged
        return self.spreadsheet_commit({
            "session_id": session_id, "staged_id": staged["staged_id"],
            "output_path": payload.get("output_path"), "overwrite": bool(payload.get("overwrite", False))})
```

- [ ] **Step 3b: Register in server**

Add to `excel_mcp/server.py` inside `main()`:

```python
    @app.tool()
    def spreadsheet_edit(operations: list[dict], path: str | None = None, session_id: str | None = None,
                         content_base64: str | None = None, filename: str | None = None,
                         dry_run: bool = False, commit: bool = True,
                         output_path: str | None = None, overwrite: bool = False) -> dict:
        """Apply cell edits in one call. Pass 'path' (auto-opens) OR 'session_id'.

        dry_run=true previews (stages, returns diff, writes nothing).
        dry_run=false + commit=true stages AND commits in a single call, returning
        'output_path' and 'changes'. Rejected operations abort the commit.
        Operation shapes are the same as the old spreadsheet_write (set_values,
        set_formula, clear_range, append_rows, insert_rows, delete_rows, copy_range).
        """
        return tools.spreadsheet_edit({"operations": operations, "path": path, "session_id": session_id,
            "content_base64": content_base64, "filename": filename, "dry_run": dry_run, "commit": commit,
            "output_path": output_path, "overwrite": overwrite})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_edit.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/tools.py excel_mcp/server.py tests/test_edit.py
git commit -m "feat(edit): one-call stage+commit fat tool with hybrid source"
```

---

### Task 6: Hybrid `spreadsheet_query` + `spreadsheet_list`, deprecate v1 tools

**Files:**
- Modify: `excel_mcp/tools.py` (make `spreadsheet_query` accept path/session via `resolve_source`; add `spreadsheet_list` alias to `workbook_list`)
- Modify: `excel_mcp/server.py` (register `spreadsheet_list`; make `spreadsheet_query` hybrid; mark v1 tools deprecated in docstrings)
- Test: `tests/test_hybrid_query_list.py`

**Interfaces:**
- Consumes: `self.resolve_source`, existing `DuckDbEngine().query`, `self.path_policy.list_workbooks`.
- Produces: `spreadsheet_query` payload now accepts `path` OR `session_id` (resolve first, then run SQL). `spreadsheet_list(self, payload)` delegates to `workbook_list`. Server `spreadsheet_query` gains `path`/`content_base64` params.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hybrid_query_list.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def _tools(tmp_path):
    return ExcelMcpTools(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))


def test_query_by_path_auto_opens(tmp_path):
    resp = _tools(tmp_path).spreadsheet_query({"path": EXAMPLE, "sql": "select 1 as one"})
    assert resp["ok"]
    assert resp["rows"][0]["one"] == 1


def test_spreadsheet_list_matches_workbook_list(tmp_path):
    tools = _tools(tmp_path)
    assert tools.spreadsheet_list({"glob": "*.xlsx"})["ok"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hybrid_query_list.py -v`
Expected: FAIL — `spreadsheet_query` raises a validation error on missing `session_id`, and `spreadsheet_list` is undefined.

- [ ] **Step 3: Implement**

In `excel_mcp/tools.py`, at the top of `spreadsheet_query`, before building the request, resolve a hybrid source when no `session_id` is present:

```python
            if not (payload.get("session_id") if isinstance(payload, dict) else getattr(payload, "session_id", None)):
                session_id, _ = self.resolve_source(payload if isinstance(payload, dict) else {})
                payload = {**(payload if isinstance(payload, dict) else {}), "session_id": session_id}
```

(Insert immediately inside the `try:` of `spreadsheet_query`, before `request = ...`.)

Add the list alias method:

```python
    def spreadsheet_list(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.workbook_list(payload or {})
```

In `excel_mcp/server.py`: add `path`/`session_id`/`content_base64`/`filename` params to the `spreadsheet_query` tool and pass them through; register `spreadsheet_list` delegating to `tools.spreadsheet_list`; prepend `"[DEPRECATED — use spreadsheet_inspect/edit/list] "` to the docstrings of `spreadsheet_describe`, `spreadsheet_read_range`, `spreadsheet_trace`, `spreadsheet_write`, `spreadsheet_commit`, `spreadsheet_diff`, `workbook_list`, `spreadsheet_open`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hybrid_query_list.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/tools.py excel_mcp/server.py tests/test_hybrid_query_list.py
git commit -m "feat(query,list): hybrid source + deprecate v1 tool docstrings"
```

---

### Task 7: CLI four-verb surface (`inspect`/`edit`), parity kept

**Files:**
- Modify: `excel_mcp/cli.py` (add `inspect` and `edit` subcommands; keep old verbs as-is)
- Test: `tests/test_cli_fat_verbs.py`

**Interfaces:**
- Consumes: `ExcelMcpTools.spreadsheet_inspect`, `ExcelMcpTools.spreadsheet_edit`. Existing `_session_or_open` already yields hybrid path/`--session` behavior; the new verbs bypass it and pass `target`/`--session` straight into the fat tool payload (the tool resolves source itself).
- Produces: `excel-ops inspect <path> --mode summary --sheet Dashboard --range B5:F5 --growth`; `excel-ops edit <path> --ops <json> --commit --output <path>`. Both print the tool's JSON envelope.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_fat_verbs.py
import json
from pathlib import Path

from excel_mcp.cli import main

EXAMPLE = str(Path("examples/saas.xlsx").resolve())
ROOT = str(Path("examples").resolve())


def test_cli_inspect_summary(capsys):
    code = main(["inspect", EXAMPLE, "--allowed-root", ROOT, "--mode", "summary",
                 "--sheet", "Dashboard", "--range", "B5:F5", "--growth"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert round(out["total"]) == 12784732


def test_cli_edit_commit(tmp_path, capsys):
    ops = json.dumps([{"type": "set_values", "sheet": "Dashboard", "start": "A20", "values": [["hi"]]}])
    out_path = str(tmp_path / "cli_out.xlsx")
    code = main(["edit", EXAMPLE, "--allowed-root", ROOT, "--allowed-root", str(tmp_path),
                 "--ops", ops, "--commit", "--output", out_path])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert Path(out_path).exists()
    assert payload["output_path"] == out_path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_fat_verbs.py -v`
Expected: FAIL — argparse exits with "invalid choice: 'inspect'".

- [ ] **Step 3: Implement**

In `excel_mcp/cli.py` `build_parser()`, register the two verbs:

```python
    inspect = subparsers.add_parser("inspect", parents=[parent], help="Describe/read/trace/summary by path or session.")
    inspect.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    inspect.add_argument("--session", dest="session_id", help="Existing session id.")
    inspect.add_argument("--mode", choices=["describe", "read", "trace", "summary"], default="describe")
    inspect.add_argument("--sheet", default=None)
    inspect.add_argument("--range", default=None)
    inspect.add_argument("--cell", default=None)
    inspect.add_argument("--depth", type=int, default=1)
    inspect.add_argument("--include", action="append", default=None)
    inspect.add_argument("--detail", choices=["compact", "standard"], default="compact")
    inspect.add_argument("--growth", action="store_true")

    edit = subparsers.add_parser("edit", parents=[parent], help="Stage (and optionally commit) edits in one call.")
    edit.add_argument("target", nargs="?", help="Workbook path for stateless mode.")
    edit.add_argument("--session", dest="session_id", help="Existing session id.")
    edit.add_argument("--ops", required=True, help="JSON operations array or path to JSON file.")
    edit.add_argument("--commit", action="store_true", help="Commit after staging.")
    edit.add_argument("--dry-run", action="store_true", help="Stage only; never write.")
    edit.add_argument("--output", dest="output_path", default=None)
    edit.add_argument("--overwrite", action="store_true")
```

In `dispatch()`, add handlers (before the final `return _error(...)`):

```python
    if args.command == "inspect":
        return tools.spreadsheet_inspect({
            "path": args.target, "session_id": args.session_id, "mode": args.mode,
            "sheet": args.sheet, "range": args.range, "cell": args.cell, "depth": args.depth,
            "include": args.include, "detail": args.detail, "growth": args.growth})

    if args.command == "edit":
        return tools.spreadsheet_edit({
            "path": args.target, "session_id": args.session_id, "operations": _load_ops(args.ops),
            "dry_run": args.dry_run, "commit": args.commit, "output_path": args.output_path,
            "overwrite": args.overwrite})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_fat_verbs.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/cli.py tests/test_cli_fat_verbs.py
git commit -m "feat(cli): inspect/edit fat verbs mirroring MCP tools"
```

---

### Task 8: Lean output caps on read/summary (task 10)

**Files:**
- Modify: `excel_mcp/range_read.py` (cap returned rows; set `telemetry.truncated` + `telemetry.rows_returned`)
- Test: `tests/test_lean_output.py`

**Interfaces:**
- Consumes: `ExcelMcpConfig` (add `read_row_limit: int = 200` if absent — check `excel_mcp/config.py` first and reuse an existing cap field if one exists).
- Produces: `read_range` truncates `cells` to at most `config.read_row_limit` rows, sets `response.telemetry.truncated = True` and `response.telemetry.rows_returned` when it clips. Existing callers (including `summarize_range`, which needs ALL numeric cells) must pass through un-truncated: give `read_range` a keyword `full: bool = False`, and have `summarize_range` call it with `full=True`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lean_output.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.schemas import SpreadsheetReadRangeRequest
from excel_mcp.range_read import read_range
from excel_mcp.session import SessionRegistry

EXAMPLE = Path("examples/saas.xlsx").resolve()


def _session(tmp_path):
    reg = SessionRegistry(ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path))
    return reg.open(EXAMPLE)[0]


def test_read_range_truncates_large_range(tmp_path):
    cfg = ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path, read_row_limit=3)
    session = _session(tmp_path)
    resp = read_range(session, SpreadsheetReadRangeRequest(session_id=session.session_id, sheet="Revenue Model", range="A1:A50"), cfg)
    assert len(resp.cells) == 3
    assert resp.telemetry.truncated is True


def test_read_range_full_bypasses_cap(tmp_path):
    cfg = ExcelMcpConfig(allowed_roots=[Path("examples").resolve()], cache_dir=tmp_path, read_row_limit=3)
    session = _session(tmp_path)
    resp = read_range(session, SpreadsheetReadRangeRequest(session_id=session.session_id, sheet="Revenue Model", range="A1:A50"), cfg, full=True)
    assert len(resp.cells) > 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_lean_output.py -v`
Expected: FAIL — `read_range()` has no `full` kwarg and/or `ExcelMcpConfig` has no `read_row_limit`.

- [ ] **Step 3: Implement**

In `excel_mcp/config.py`, add `read_row_limit: int = 200` to `ExcelMcpConfig` (match the existing dataclass/BaseModel style; reuse a pattern from `query_row_limit`). In `excel_mcp/range_read.py`, change the signature to `def read_range(session, request, config, *, full: bool = False)` and, after cells are assembled, clip:

```python
    if not full and len(cells) > config.read_row_limit:
        response.telemetry.truncated = True
        response.telemetry.rows_returned = config.read_row_limit
        cells = cells[: config.read_row_limit]
    response.cells = cells
```

In `excel_mcp/summarize.py`, change the `read_range(...)` call to pass `full=True`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_lean_output.py tests/test_summarize.py -v`
Expected: PASS (both files green — the summary numbers still match because `full=True` bypasses the cap).

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/config.py excel_mcp/range_read.py excel_mcp/summarize.py tests/test_lean_output.py
git commit -m "feat(read): cap returned rows, full bypass for summary"
```

---

### Task 9: Contract doc, parity test, and round-trip regression (tasks 12/13/18)

**Files:**
- Modify: `tasks/13-public-tool-contracts-and-json-schemas.md` (document the 4 fat tools)
- Create: `tests/test_cli_mcp_parity.py`
- Create: `tests/test_share_regression.py`
- Test: the two created files

**Interfaces:**
- Consumes: `ExcelMcpTools.spreadsheet_inspect`/`spreadsheet_edit` and the CLI `main` — parity means identical payloads for the same request through both surfaces.
- Produces: a regression that reproduces the shared-A task end-to-end (summary + add growth row) and asserts the known numbers, plus a CLI↔MCP parity check on `inspect --mode summary`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_mcp_parity.py
import json
from pathlib import Path

from excel_mcp.cli import main
from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())
ROOT = str(Path("examples").resolve())


def test_summary_parity_cli_vs_tool(tmp_path, capsys):
    main(["inspect", EXAMPLE, "--allowed-root", ROOT, "--mode", "summary", "--sheet", "Dashboard", "--range", "B5:F5"])
    cli_out = json.loads(capsys.readouterr().out)
    tool_out = ExcelMcpTools(ExcelMcpConfig(allowed_roots=[Path(ROOT)], cache_dir=tmp_path)).spreadsheet_inspect(
        {"path": EXAMPLE, "mode": "summary", "sheet": "Dashboard", "range": "B5:F5"})
    assert round(cli_out["total"]) == round(tool_out["total"]) == 12784732
    assert round(cli_out["mean"]) == round(tool_out["mean"]) == 2556946
```

```python
# tests/test_share_regression.py
from pathlib import Path

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.tools import ExcelMcpTools

EXAMPLE = str(Path("examples/saas.xlsx").resolve())


def test_share_a_job_in_three_calls(tmp_path):
    tools = ExcelMcpTools(ExcelMcpConfig(allowed_roots=[tmp_path, Path("examples").resolve()], cache_dir=tmp_path))
    # 1) describe -> pick best source
    d = tools.spreadsheet_inspect({"path": EXAMPLE, "mode": "describe"})
    sid = d["session_id"]
    assert d["best_source"][0]["sheet"] in {"Dashboard", "Revenue Model"}
    # 2) summary -> server math
    s = tools.spreadsheet_inspect({"session_id": sid, "mode": "summary", "sheet": "Dashboard", "range": "B5:F5", "growth": True})
    assert round(s["total"]) == 12784732 and round(s["max"]) == 3127445
    # 3) edit+commit -> add growth row in one call
    out = str(tmp_path / "saas.updated.xlsx")
    e = tools.spreadsheet_edit({"session_id": sid, "dry_run": False, "commit": True, "output_path": out,
        "operations": [{"type": "set_values", "sheet": "Dashboard", "start": "B13",
                        "values": [[0.688, 0.12, 0.08, 0.05]]}]})
    assert e["ok"] and Path(out).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli_mcp_parity.py tests/test_share_regression.py -v`
Expected: FAIL only if an earlier task is incomplete; if Tasks 1–7 are done they should already pass. If they fail for a real reason (e.g. `best_source` empty), fix the responsible module before continuing.

- [ ] **Step 3: Document the contract**

Append a "v2 fat tools" section to `tasks/13-public-tool-contracts-and-json-schemas.md` listing the four tools, their params, hybrid source rule, and the deprecation window. Copy the exact request/response field names from `excel_mcp/schemas.py` (`SpreadsheetSummaryResponse`, `SpreadsheetDescribeResponse.best_source`, etc.).

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all green, including pre-existing tests — the v1 shims keep them working).

- [ ] **Step 5: Commit**

```bash
git add tasks/13-public-tool-contracts-and-json-schemas.md tests/test_cli_mcp_parity.py tests/test_share_regression.py
git commit -m "test(parity): CLI/MCP parity + share-A round-trip regression; doc v2 contracts"
```

---

## Self-Review

**Spec coverage:**
- Tool surface 10→4 → Tasks 4 (inspect), 5 (edit), 6 (query hybrid + list), server registration in each.
- Hybrid state → Task 1 (`resolve_source`), used by Tasks 4/5/6.
- Server-side `summary` → Task 2; wired in Task 4.
- `best_source` hint → Task 3.
- Lean output → Task 8.
- CLI parity kept → Task 7 (verbs) + Task 9 (parity test).
- Migration/deprecation shims → Task 6 (docstrings), full suite still green in Task 9 Step 4.
- Testing (fixture numbers, round-trip ≤3 calls, hybrid) → Tasks 2/9.
- Non-goals respected: sessions retained, `query` kept, `.xlsx` only, installer untouched.

**Placeholder scan:** No TBD/TODO; every code step shows real code. Two guarded lookups ("check config.py first", "adjust cell key if different") are verification instructions, not placeholders — they name the exact fallback.

**Type consistency:** `resolve_source -> (session_id, cache_hit)` used identically in Tasks 4/5/6. `summarize_range(session, sheet, range, config, *, growth)` signature matches its Task 4 call. `SpreadsheetSummaryResponse` fields (`total/mean/min/max/count/skipped/yoy_growth_pct`) match test assertions in Tasks 2/4/9. `read_range(..., *, full=False)` added in Task 8 and called with `full=True` from summarize in the same task.

**Gap check:** `best_source` requires `region_kind == "summary"` to exist on the Dashboard sheet for the ordering assertion in Task 9 Step 1; the assertion is deliberately permissive (`in {"Dashboard","Revenue Model"}`) so it passes regardless of detector output, while Task 3's unit test pins the ranking logic with synthetic regions. No uncovered spec requirement.
