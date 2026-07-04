from pathlib import Path

from excel_mcp.server import resolve_config


def test_defaults_to_home_when_nothing_set():
    cfg = resolve_config(argv=[], environ={})
    assert cfg.allowed_roots == [Path.home()]


def test_allowed_root_args_repeatable():
    cfg = resolve_config(argv=["--allowed-root", "/a", "--allowed-root", "/b"], environ={})
    assert cfg.allowed_roots == [Path("/a"), Path("/b")]


def test_env_allowed_roots_pathsep():
    import os

    env = {"EXCEL_MCP_ALLOWED_ROOTS": os.pathsep.join(["/x", "/y"])}
    cfg = resolve_config(argv=[], environ=env)
    assert cfg.allowed_roots == [Path("/x"), Path("/y")]


def test_args_and_env_combine():
    cfg = resolve_config(argv=["--allowed-root", "/a"], environ={"EXCEL_MCP_ALLOWED_ROOTS": "/b"})
    assert cfg.allowed_roots == [Path("/a"), Path("/b")]


def test_cache_dir_from_arg_and_env():
    cfg = resolve_config(argv=["--cache-dir", "/tmp/c"], environ={})
    assert cfg.cache_dir == Path("/tmp/c")
    cfg2 = resolve_config(argv=[], environ={"EXCEL_MCP_CACHE_DIR": "/tmp/d"})
    assert cfg2.cache_dir == Path("/tmp/d")


def test_unknown_args_ignored():
    # FastMCP or the host may pass extra flags; resolve_config must not choke.
    cfg = resolve_config(argv=["--transport", "stdio", "--allowed-root", "/a"], environ={})
    assert cfg.allowed_roots == [Path("/a")]
