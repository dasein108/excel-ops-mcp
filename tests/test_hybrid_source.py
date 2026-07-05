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
