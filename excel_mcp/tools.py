from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from excel_mcp.config import ExcelMcpConfig
from excel_mcp.describe import describe_workbook
from excel_mcp.duckdb_engine import DuckDbEngine, DuckDbUnavailable
from excel_mcp.policy import PathPolicy, PolicyError
from excel_mcp.range_read import read_range
from excel_mcp.schemas import (
    SpreadsheetCommitRequest,
    SpreadsheetCommitResponse,
    SpreadsheetDescribeRequest,
    SpreadsheetDiffRequest,
    SpreadsheetDiffResponse,
    SpreadsheetOpenRequest,
    SpreadsheetOpenResponse,
    SpreadsheetQueryRequest,
    SpreadsheetQueryResponse,
    SpreadsheetReadRangeRequest,
    SpreadsheetTraceRequest,
    SpreadsheetWriteRequest,
    SpreadsheetWriteResponse,
    Telemetry,
    WorkbookInfo,
    WorkbookListRequest,
    WorkbookListResponse,
    error_response,
)
from excel_mcp.session import SessionRegistry
from excel_mcp.summarize import summarize_range
from excel_mcp.trace import trace_cell
from excel_mcp.writes import commit_staged, diff_staged, stage_write


class ExcelMcpTools:
    def __init__(self, config: ExcelMcpConfig | None = None):
        self.config = config or ExcelMcpConfig()
        self.path_policy = PathPolicy(self.config)
        self.sessions = SessionRegistry(self.config)

    def spreadsheet_open(self, payload: dict[str, Any] | SpreadsheetOpenRequest) -> dict[str, Any]:
        started = time.perf_counter()
        request_path = None
        try:
            request = payload if isinstance(payload, SpreadsheetOpenRequest) else SpreadsheetOpenRequest.model_validate(payload)
            request_path = request.path
            if request.content_base64 is not None:
                path = self._materialize_upload(request.content_base64, request.filename)
                request_path = str(path)
            elif request.path:
                path = self.path_policy.validate_input_file(request.path)
            else:
                return error_response("missing_source", "Provide either 'path' or 'content_base64'.")
            session, cache_hit = self.sessions.open(path)
            response = SpreadsheetOpenResponse(
                ok=True,
                session_id=session.session_id,
                path=str(session.path),
                file_size=session.file_size,
                mtime=session.mtime,
                telemetry=Telemetry(cache="hit" if cache_hit else "miss", elapsed_ms=_elapsed_ms(started)),
            ).model_dump()
            self._audit("open", response, {"path": request.path}, str(session.path), started)
            return response
        except PolicyError as exc:
            response = error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
            self._audit("open", response, {"path": request_path}, request_path, started)
            return response
        except Exception as exc:
            response = error_response("open_failed", str(exc))
            self._audit("open", response, {"path": request_path}, request_path, started)
            return response

    def spreadsheet_describe(self, payload: dict[str, Any] | SpreadsheetDescribeRequest) -> dict[str, Any]:
        started = time.perf_counter()
        session = None
        try:
            request = payload if isinstance(payload, SpreadsheetDescribeRequest) else SpreadsheetDescribeRequest.model_validate(payload)
            session = self.sessions.get(request.session_id)
            response = describe_workbook(session, detail=request.detail)
            response.telemetry.elapsed_ms = _elapsed_ms(started)
            dumped = response.model_dump()
            self._audit("describe", dumped, {"detail": request.detail}, str(session.path), started)
            return dumped
        except KeyError:
            response = error_response("session_not_found", "Session does not exist or workbook changed.")
            self._audit("describe", response, {}, None, started)
            return response
        except Exception as exc:
            response = error_response("describe_failed", str(exc))
            self._audit("describe", response, {}, str(session.path) if session else None, started)
            return response

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
            except PolicyError as exc:
                resp = error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
                resp["session_id"] = session_id
                return resp
            except Exception as exc:
                resp = error_response("summary_failed", str(exc))
                resp["session_id"] = session_id
                return resp
        resp = error_response("invalid_mode", f"Unknown mode '{mode}'. Use describe|read|trace|summary.")
        resp["session_id"] = session_id
        return resp

    def spreadsheet_query(self, payload: dict[str, Any] | SpreadsheetQueryRequest) -> dict[str, Any]:
        started = time.perf_counter()
        session = None
        try:
            if not (payload.get("session_id") if isinstance(payload, dict) else getattr(payload, "session_id", None)):
                session_id, _ = self.resolve_source(payload if isinstance(payload, dict) else {})
                payload = {**(payload if isinstance(payload, dict) else {}), "session_id": session_id}
            request = payload if isinstance(payload, SpreadsheetQueryRequest) else SpreadsheetQueryRequest.model_validate(payload)
            session = self.sessions.get(request.session_id)
            limit = min(request.limit or self.config.query_row_limit, self.config.query_row_limit)
            response = DuckDbEngine().query(session, request.sql, limit)
            dumped = response.model_dump()
            self._audit("query", dumped, {"sql": request.sql, "limit": limit}, str(session.path), started)
            return dumped
        except KeyError:
            response = error_response("session_not_found", "Session does not exist or workbook changed.")
            self._audit("query", response, {}, None, started)
            return response
        except PolicyError as exc:
            response = error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
            if session:
                response["session_id"] = session.session_id
            self._audit("query", response, {"sql": getattr(locals().get("request", None), "sql", None)}, str(session.path) if session else None, started)
            return response
        except DuckDbUnavailable:
            response = error_response("dependency_missing", "duckdb is not installed.")
            if session:
                response["session_id"] = session.session_id
            self._audit("query", response, {}, str(session.path) if session else None, started)
            return response
        except Exception as exc:
            response = error_response("query_failed", str(exc))
            if session:
                response["session_id"] = session.session_id
            self._audit("query", response, {}, str(session.path) if session else None, started)
            return response

    def spreadsheet_read_range(self, payload: dict[str, Any] | SpreadsheetReadRangeRequest) -> dict[str, Any]:
        started = time.perf_counter()
        session = None
        try:
            request = payload if isinstance(payload, SpreadsheetReadRangeRequest) else SpreadsheetReadRangeRequest.model_validate(payload)
            session = self.sessions.get(request.session_id)
            response = read_range(session, request, self.config).model_dump()
            self._audit("read-range", response, {"sheet": request.sheet, "range": request.range, "include": request.include}, str(session.path), started)
            return response
        except KeyError:
            response = error_response("session_not_found", "Session does not exist or workbook changed.")
            self._audit("read-range", response, {}, None, started)
            return response
        except PolicyError as exc:
            response = error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
            if session:
                response["session_id"] = session.session_id
            self._audit("read-range", response, {}, str(session.path) if session else None, started)
            return response
        except Exception as exc:
            response = error_response("read_range_failed", str(exc))
            self._audit("read-range", response, {}, str(session.path) if session else None, started)
            return response

    def spreadsheet_trace(self, payload: dict[str, Any] | SpreadsheetTraceRequest) -> dict[str, Any]:
        started = time.perf_counter()
        session = None
        try:
            request = payload if isinstance(payload, SpreadsheetTraceRequest) else SpreadsheetTraceRequest.model_validate(payload)
            session = self.sessions.get(request.session_id)
            response = trace_cell(session, request.sheet, request.cell, request.depth)
            response.telemetry.elapsed_ms = _elapsed_ms(started)
            dumped = response.model_dump()
            self._audit("trace", dumped, {"sheet": request.sheet, "cell": request.cell, "depth": request.depth}, str(session.path), started)
            return dumped
        except KeyError:
            response = error_response("session_not_found", "Session does not exist or workbook changed.")
            self._audit("trace", response, {}, None, started)
            return response
        except PolicyError as exc:
            response = error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
            if session:
                response["session_id"] = session.session_id
            self._audit("trace", response, {}, str(session.path) if session else None, started)
            return response
        except Exception as exc:
            response = error_response("trace_failed", str(exc))
            if session:
                response["session_id"] = session.session_id
            self._audit("trace", response, {}, str(session.path) if session else None, started)
            return response

    def spreadsheet_write(self, payload: dict[str, Any] | SpreadsheetWriteRequest) -> dict[str, Any]:
        started = time.perf_counter()
        session = None
        try:
            request = payload if isinstance(payload, SpreadsheetWriteRequest) else SpreadsheetWriteRequest.model_validate(payload)
            session = self.sessions.get(request.session_id)
            response = stage_write(session, request)
            if response.staged_id:
                staged = session.staged[response.staged_id]
                self.sessions.save_staged_write(
                    session.session_id,
                    response.staged_id,
                    staged.operations,
                    staged.touched_ranges,
                    staged.changes,
                    staged.warnings,
                )
            dumped = response.model_dump()
            self._audit("write", dumped, {"operation_count": len(request.operations), "dry_run": request.dry_run}, str(session.path), started)
            return dumped
        except KeyError:
            response = error_response("session_not_found", "Session does not exist or workbook changed.")
            self._audit("write", response, {}, None, started)
            return response
        except Exception as exc:
            response = error_response("write_failed", str(exc))
            if session:
                response["session_id"] = session.session_id
            self._audit("write", response, {}, str(session.path) if session else None, started)
            return response

    def spreadsheet_commit(self, payload: dict[str, Any] | SpreadsheetCommitRequest) -> dict[str, Any]:
        started = time.perf_counter()
        session = None
        try:
            request = payload if isinstance(payload, SpreadsheetCommitRequest) else SpreadsheetCommitRequest.model_validate(payload)
            session = self.sessions.get(request.session_id)
            response = commit_staged(session, request, self.config).model_dump()
            self._audit("commit", response, {"staged_id": request.staged_id, "output_path": request.output_path, "overwrite": request.overwrite}, str(session.path), started)
            return response
        except KeyError:
            response = error_response("session_not_found", "Session does not exist or workbook changed.")
            self._audit("commit", response, {}, None, started)
            return response
        except PolicyError as exc:
            response = error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
            if session:
                response["session_id"] = session.session_id
            self._audit("commit", response, {}, str(session.path) if session else None, started)
            return response
        except Exception as exc:
            response = error_response("commit_failed", str(exc))
            if session:
                response["session_id"] = session.session_id
            self._audit("commit", response, {}, str(session.path) if session else None, started)
            return response

    def spreadsheet_diff(self, payload: dict[str, Any] | SpreadsheetDiffRequest) -> dict[str, Any]:
        started = time.perf_counter()
        session = None
        try:
            request = payload if isinstance(payload, SpreadsheetDiffRequest) else SpreadsheetDiffRequest.model_validate(payload)
            session = self.sessions.get(request.session_id)
            response = diff_staged(session, request.staged_id).model_dump()
            self._audit("diff", response, {"staged_id": request.staged_id}, str(session.path), started)
            return response
        except KeyError:
            response = error_response("session_not_found", "Session does not exist or workbook changed.")
            self._audit("diff", response, {}, None, started)
            return response
        except PolicyError as exc:
            response = error_response(exc.code, exc.message, getattr(exc, "details", None) or None)
            if session:
                response["session_id"] = session.session_id
            self._audit("diff", response, {}, str(session.path) if session else None, started)
            return response
        except Exception as exc:
            response = error_response("diff_failed", str(exc))
            self._audit("diff", response, {}, str(session.path) if session else None, started)
            return response

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

    def spreadsheet_list(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.workbook_list(payload or {})

    def workbook_list(self, payload: dict[str, Any] | WorkbookListRequest | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            request = payload if isinstance(payload, WorkbookListRequest) else WorkbookListRequest.model_validate(payload or {})
            workbooks = self.path_policy.list_workbooks(glob=request.glob, limit=request.limit)
            response = WorkbookListResponse(
                ok=True,
                root_paths=[str(root) for root in self.config.normalized_allowed_roots()],
                workbooks=[WorkbookInfo(**item) for item in workbooks],
                telemetry=Telemetry(elapsed_ms=_elapsed_ms(started)),
            ).model_dump()
            self._audit("list", response, {"glob": request.glob}, None, started)
            return response
        except Exception as exc:
            response = error_response("list_failed", str(exc))
            self._audit("list", response, {}, None, started)
            return response

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

    def _materialize_upload(self, content_base64: str, filename: str | None) -> Path:
        """Write uploaded bytes to the cache dir so path-only opens work for
        clients that don't share the server host filesystem."""
        import base64
        import binascii
        import hashlib

        name = filename or "upload.xlsx"
        if Path(name).suffix.lower() != ".xlsx":
            raise PolicyError("unsupported_extension", "Uploaded filename must end in .xlsx.")
        try:
            raw = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PolicyError("invalid_content", "content_base64 is not valid base64.") from exc
        upload_dir = self.config.cache_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()[:16]
        target = upload_dir / f"{Path(name).stem}-{digest}.xlsx"
        target.write_bytes(raw)
        return target

    def audit_events(self, session_id: str | None = None, path: str | None = None, limit: int = 100) -> dict[str, Any]:
        return {"ok": True, "events": self.sessions.list_audit_events(session_id=session_id, path=path, limit=limit)}

    def record_cli_audit(self, operation: str, response: dict[str, Any], input_summary: dict[str, Any], path: str | None = None) -> None:
        self._audit(operation, response, input_summary, path, time.perf_counter())

    def _audit(self, operation: str, response: dict[str, Any], input_summary: dict[str, Any], path: str | None, started: float) -> None:
        try:
            error = response.get("error") or {}
            self.sessions.record_audit_event(
                operation=operation,
                session_id=response.get("session_id"),
                path=path,
                input_summary=input_summary,
                source_refs=response.get("source_refs") or [],
                touched_ranges=response.get("touched_ranges") or response.get("changed_ranges") or [],
                warnings=response.get("warnings") or [],
                ok=bool(response.get("ok")),
                error_code=error.get("code") if isinstance(error, dict) else None,
                elapsed_ms=response.get("telemetry", {}).get("elapsed_ms") if isinstance(response.get("telemetry"), dict) else _elapsed_ms(started),
            )
        except Exception:
            pass


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
