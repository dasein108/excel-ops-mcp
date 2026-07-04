# Cross-Agent Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a one-command installer that bootstraps `uv`, then runs a TUI that wires the `excel-ops-mcp` MCP server into whichever of six LLM agents the user picks.

**Architecture:** A `curl | sh` (and PowerShell) bootstrap ensures `uv`/`uvx`, then runs a Python console script `excel-ops-mcp-install` that ships inside the `excel-ops-mcp` package under an optional `[install]` extra. The installer is a data-driven registry of per-agent adapters over three strategies — JSON file-merge, TOML file-merge, and the Claude Code CLI — each doing a safe, backed-up, idempotent upsert of one `excel-ops-mcp` entry.

**Tech Stack:** Python ≥3.11, `questionary` (TUI), `tomlkit` (TOML-preserving merge), stdlib `json`/`argparse`/`subprocess`, `hatchling` build.

## Global Constraints

- Python floor: `requires-python = ">=3.11"` (unchanged).
- Installer deps live ONLY under a new optional extra `install = ["questionary>=2.0", "tomlkit>=0.12"]`. Base package stays lean.
- New console script: `excel-ops-mcp-install = "excel_mcp.installer.cli:main"`.
- Server written everywhere is exactly: name `excel-ops-mcp`, command `uvx`, args `["excel-ops-mcp"]`.
- GUI apps (Claude Desktop, Cursor, Windsurf) get the ABSOLUTE `uvx` path (they don't inherit login-shell PATH); CLI agents (Claude Code, Codex, Gemini) get bare `uvx`.
- Safety, non-negotiable, every adapter: never clobber other servers/keys; back up the target to `<name>.bak` before writing; idempotent re-runs; malformed existing config → skip that agent with an error, never overwrite.
- Six agents in v1: `claude-desktop`, `claude-code`, `codex`, `gemini`, `cursor`, `windsurf`. (`openclaw`/`hermes` deferred — unverified.)
- OSes: macOS, Linux, Windows.
- Ships as release `v0.2.0`.
- CI must install the extra: `pip install -e ".[dev,install]"`.

## Confirmed per-agent facts (source of truth for adapters)

| key | label | strategy | path / command | format | gui |
|---|---|---|---|---|---|
| claude-desktop | Claude Desktop | json-file | mac `~/Library/Application Support/Claude/claude_desktop_config.json`; win `%APPDATA%\Claude\claude_desktop_config.json`; linux `~/.config/Claude/claude_desktop_config.json` | JSON `mcpServers` | yes |
| cursor | Cursor | json-file | `~/.cursor/mcp.json` (win `%USERPROFILE%\.cursor\mcp.json`) | JSON `mcpServers` | yes |
| windsurf | Windsurf | json-file | `~/.codeium/windsurf/mcp_config.json` | JSON `mcpServers` | yes |
| gemini | Gemini CLI | json-file | `~/.gemini/settings.json` | JSON `mcpServers` | no |
| codex | Codex | toml-file | `~/.codex/config.toml` | TOML `[mcp_servers.<name>]` | no |
| claude-code | Claude Code | cli | `claude mcp add --scope user excel-ops-mcp -- uvx excel-ops-mcp` | via CLI | no |

## File Structure

```
excel_mcp/installer/
  __init__.py         # package marker
  errors.py           # MalformedConfig exception
  spec.py             # ServerSpec + resolve_uvx_path()
  paths.py            # OS-aware config path resolvers
  merge.py            # backup_file, json_upsert_server, toml_upsert_server
  adapters/
    __init__.py
    base.py           # Adapter ABC, ApplyResult
    json_file.py      # JsonFileAdapter(JsonDescriptor)
    toml_file.py      # TomlFileAdapter(TomlDescriptor)
    claude_code.py    # ClaudeCodeCliAdapter
  registry.py         # build_registry() -> list[Adapter]
  tui.py              # questionary checkbox selection
  cli.py              # main(): argparse, orchestration, summary
install.sh            # POSIX bootstrap (repo root)
install.ps1           # PowerShell bootstrap (repo root)
tests/installer/
  __init__.py
  conftest.py         # tmp HOME/APPDATA fixture
  test_spec.py
  test_paths.py
  test_merge_json.py
  test_merge_toml.py
  test_json_adapter.py
  test_toml_adapter.py
  test_claude_code_adapter.py
  test_registry.py
  test_cli.py
```

---

### Task 1: Package scaffolding, extra, console script, CI

**Files:**
- Create: `excel_mcp/installer/__init__.py`
- Create: `excel_mcp/installer/cli.py` (temporary stub, replaced in Task 10)
- Create: `tests/installer/__init__.py`
- Create: `tests/installer/test_cli.py`
- Modify: `pyproject.toml` (add `[install]` extra + console script)
- Modify: `.github/workflows/ci.yml` and `.github/workflows/publish-pypi.yml` (install `[dev,install]`)

**Interfaces:**
- Produces: console entry `excel-ops-mcp-install` → `excel_mcp.installer.cli:main`; `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/installer/test_cli.py
from excel_mcp.installer.cli import main

def test_version_flag_exits_zero(capsys):
    rc = main(["--version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "excel-ops-mcp-install" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: excel_mcp.installer`.

- [ ] **Step 3: Create the package + stub main**

```python
# excel_mcp/installer/__init__.py
"""excel-ops-mcp cross-agent installer."""
```

```python
# excel_mcp/installer/cli.py
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="excel-ops-mcp-install")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args(argv)
    if args.version:
        print("excel-ops-mcp-install (excel-ops-mcp installer)")
        return 0
    print("excel-ops-mcp installer — run with a TTY to pick agents (Task 10).")
    return 0
```

```python
# tests/installer/__init__.py
```

- [ ] **Step 4: Add the extra + console script to pyproject**

In `pyproject.toml`, under `[project.optional-dependencies]` add:

```toml
install = [
  "questionary>=2.0",
  "tomlkit>=0.12",
]
```

Under `[project.scripts]` add the installer line (keep existing two):

```toml
excel-ops-mcp-install = "excel_mcp.installer.cli:main"
```

- [ ] **Step 5: Update CI to install the extra**

In `.github/workflows/ci.yml` and `.github/workflows/publish-pypi.yml`, change the install line from `pip install -e ".[dev]"` to:

```yaml
          python -m pip install -e ".[dev,install]"
```

- [ ] **Step 6: Install locally so the new deps are present**

Run: `.venv/bin/python -m pip install -e ".[dev,install]"`
Expected: installs `questionary`, `tomlkit`.

- [ ] **Step 7: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_cli.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add excel_mcp/installer tests/installer pyproject.toml .github/workflows
git commit -m "feat(installer): scaffold installer package, [install] extra, console script"
```

---

### Task 2: ServerSpec + uvx path resolution

**Files:**
- Create: `excel_mcp/installer/spec.py`
- Create: `tests/installer/test_spec.py`

**Interfaces:**
- Produces:
  - `resolve_uvx_path() -> str` — absolute path to `uvx` via `shutil.which`, else the string `"uvx"`.
  - `@dataclass(frozen=True) class ServerSpec` with fields `name: str`, `args: tuple[str, ...]`, `uvx_path: str`; methods `command_for(gui: bool) -> str` and `entry(gui: bool) -> dict`.
  - `default_spec() -> ServerSpec` → `ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), resolve_uvx_path())`.

- [ ] **Step 1: Write the failing test**

```python
# tests/installer/test_spec.py
from excel_mcp.installer.spec import ServerSpec, default_spec, resolve_uvx_path


def test_entry_uses_bare_uvx_for_cli_agents():
    spec = ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/opt/uv/bin/uvx")
    assert spec.entry(gui=False) == {"command": "uvx", "args": ["excel-ops-mcp"]}


def test_entry_uses_absolute_uvx_for_gui_agents():
    spec = ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/opt/uv/bin/uvx")
    assert spec.entry(gui=True) == {"command": "/opt/uv/bin/uvx", "args": ["excel-ops-mcp"]}


def test_default_spec_shape():
    spec = default_spec()
    assert spec.name == "excel-ops-mcp"
    assert spec.args == ("excel-ops-mcp",)


def test_resolve_uvx_falls_back_to_bare(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert resolve_uvx_path() == "uvx"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_spec.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement spec.py**

```python
# excel_mcp/installer/spec.py
from __future__ import annotations

import shutil
from dataclasses import dataclass


def resolve_uvx_path() -> str:
    found = shutil.which("uvx")
    return found if found else "uvx"


@dataclass(frozen=True)
class ServerSpec:
    name: str
    args: tuple[str, ...]
    uvx_path: str

    def command_for(self, gui: bool) -> str:
        return self.uvx_path if gui else "uvx"

    def entry(self, gui: bool) -> dict:
        return {"command": self.command_for(gui), "args": list(self.args)}


def default_spec() -> ServerSpec:
    return ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), resolve_uvx_path())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_spec.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/spec.py tests/installer/test_spec.py
git commit -m "feat(installer): ServerSpec with gui-aware uvx path resolution"
```

---

### Task 3: OS-aware config path resolvers

**Files:**
- Create: `excel_mcp/installer/paths.py`
- Create: `tests/installer/conftest.py`
- Create: `tests/installer/test_paths.py`

**Interfaces:**
- Produces (each returns `pathlib.Path | None`; `None` only when a platform lacks a location):
  `claude_desktop_path()`, `cursor_path()`, `windsurf_path()`, `gemini_path()`, `codex_path()`.
- Each reads `HOME`/`USERPROFILE`/`APPDATA` via `os.path.expanduser("~")` and `os.environ`, and branches on a `platform` argument defaulting to `sys.platform` so tests can force an OS.

- [ ] **Step 1: Write the shared fixture + failing test**

```python
# tests/installer/conftest.py
import os
from pathlib import Path

import pytest


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("APPDATA", str(home / "AppData" / "Roaming"))
    # os.path.expanduser on POSIX honors $HOME; ensure no cached override
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return home
```

```python
# tests/installer/test_paths.py
from excel_mcp.installer import paths


def test_cursor_path_under_home(fake_home):
    p = paths.cursor_path(platform="linux")
    assert p == fake_home / ".cursor" / "mcp.json"


def test_windsurf_path(fake_home):
    p = paths.windsurf_path(platform="darwin")
    assert p == fake_home / ".codeium" / "windsurf" / "mcp_config.json"


def test_codex_path(fake_home):
    assert paths.codex_path(platform="linux") == fake_home / ".codex" / "config.toml"


def test_gemini_path(fake_home):
    assert paths.gemini_path(platform="linux") == fake_home / ".gemini" / "settings.json"


def test_claude_desktop_mac(fake_home):
    p = paths.claude_desktop_path(platform="darwin")
    assert p == fake_home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_windows_uses_appdata(fake_home):
    p = paths.claude_desktop_path(platform="win32")
    assert p == fake_home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_linux_config_dir(fake_home):
    p = paths.claude_desktop_path(platform="linux")
    assert p == fake_home / ".config" / "Claude" / "claude_desktop_config.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_paths.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement paths.py**

```python
# excel_mcp/installer/paths.py
from __future__ import annotations

import os
import sys
from pathlib import Path


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _appdata() -> Path | None:
    value = os.environ.get("APPDATA")
    return Path(value) if value else None


def _plat(platform: str | None) -> str:
    return platform if platform is not None else sys.platform


def cursor_path(platform: str | None = None) -> Path:
    return _home() / ".cursor" / "mcp.json"


def windsurf_path(platform: str | None = None) -> Path:
    return _home() / ".codeium" / "windsurf" / "mcp_config.json"


def gemini_path(platform: str | None = None) -> Path:
    return _home() / ".gemini" / "settings.json"


def codex_path(platform: str | None = None) -> Path:
    return _home() / ".codex" / "config.toml"


def claude_desktop_path(platform: str | None = None) -> Path | None:
    system = _plat(platform)
    if system == "darwin":
        return _home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if system.startswith("win"):
        appdata = _appdata()
        if appdata is None:
            return None
        return appdata / "Claude" / "claude_desktop_config.json"
    return _home() / ".config" / "Claude" / "claude_desktop_config.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_paths.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/paths.py tests/installer/conftest.py tests/installer/test_paths.py
git commit -m "feat(installer): OS-aware per-agent config path resolvers"
```

---

### Task 4: JSON merge + backup

**Files:**
- Create: `excel_mcp/installer/errors.py`
- Create: `excel_mcp/installer/merge.py`
- Create: `tests/installer/test_merge_json.py`

**Interfaces:**
- Produces:
  - `class MalformedConfig(Exception)`.
  - `backup_file(path: Path) -> Path | None` — copies existing file to `<name>.bak` (append `.bak` to the full filename), returns the backup path or `None` if the source didn't exist.
  - `json_upsert_server(path: Path, root_key: str, name: str, entry: dict) -> str` — returns `"added"` or `"updated"`; creates parent dirs; preserves all other content; raises `MalformedConfig` if existing JSON is invalid or the root/`root_key` is not an object.

- [ ] **Step 1: Write the failing tests**

```python
# tests/installer/test_merge_json.py
import json

import pytest

from excel_mcp.installer.errors import MalformedConfig
from excel_mcp.installer.merge import backup_file, json_upsert_server


def test_creates_file_when_absent(tmp_path):
    cfg = tmp_path / "sub" / "mcp.json"
    action = json_upsert_server(cfg, "mcpServers", "excel-ops-mcp",
                                {"command": "uvx", "args": ["excel-ops-mcp"]})
    assert action == "added"
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["excel-ops-mcp"] == {"command": "uvx", "args": ["excel-ops-mcp"]}


def test_preserves_existing_servers_and_keys(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}))
    json_upsert_server(cfg, "mcpServers", "excel-ops-mcp",
                       {"command": "uvx", "args": ["excel-ops-mcp"]})
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["other"] == {"command": "x"}
    assert data["theme"] == "dark"
    assert "excel-ops-mcp" in data["mcpServers"]


def test_updates_existing_entry_idempotent(tmp_path):
    cfg = tmp_path / "mcp.json"
    entry = {"command": "uvx", "args": ["excel-ops-mcp"]}
    assert json_upsert_server(cfg, "mcpServers", "excel-ops-mcp", entry) == "added"
    assert json_upsert_server(cfg, "mcpServers", "excel-ops-mcp", entry) == "updated"
    data = json.loads(cfg.read_text())
    assert list(data["mcpServers"].keys()) == ["excel-ops-mcp"]  # no duplicate


def test_malformed_json_raises_and_does_not_overwrite(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("{ this is not json")
    with pytest.raises(MalformedConfig):
        json_upsert_server(cfg, "mcpServers", "excel-ops-mcp", {"command": "uvx", "args": []})
    assert cfg.read_text() == "{ this is not json"  # untouched


def test_backup_copies_existing(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("hello")
    bak = backup_file(cfg)
    assert bak == tmp_path / "mcp.json.bak"
    assert bak.read_text() == "hello"


def test_backup_none_when_absent(tmp_path):
    assert backup_file(tmp_path / "nope.json") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_merge_json.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement errors.py + merge.py (JSON parts)**

```python
# excel_mcp/installer/errors.py
from __future__ import annotations


class MalformedConfig(Exception):
    """Existing agent config could not be parsed; refuse to overwrite it."""
```

```python
# excel_mcp/installer/merge.py
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .errors import MalformedConfig


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_name(path.name + ".bak")
    shutil.copy2(path, backup)
    return backup


def json_upsert_server(path: Path, root_key: str, name: str, entry: dict) -> str:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise MalformedConfig(f"{path}: {exc}") from exc
        else:
            data = {}
        if not isinstance(data, dict):
            raise MalformedConfig(f"{path}: top-level JSON is not an object")
    else:
        data = {}

    servers = data.setdefault(root_key, {})
    if not isinstance(servers, dict):
        raise MalformedConfig(f"{path}: '{root_key}' is not an object")

    existed = name in servers
    servers[name] = entry

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "updated" if existed else "added"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_merge_json.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/errors.py excel_mcp/installer/merge.py tests/installer/test_merge_json.py
git commit -m "feat(installer): safe JSON upsert + backup with malformed-config guard"
```

---

### Task 5: TOML merge (Codex)

**Files:**
- Modify: `excel_mcp/installer/merge.py` (add `toml_upsert_server`)
- Create: `tests/installer/test_merge_toml.py`

**Interfaces:**
- Consumes: `MalformedConfig` from `errors.py`.
- Produces: `toml_upsert_server(path: Path, name: str, command: str, args: list[str]) -> str` → `"added"`/`"updated"`; writes `[mcp_servers.<name>]` with `command` + `args`; preserves other tables via `tomlkit`; raises `MalformedConfig` on unparseable TOML.

- [ ] **Step 1: Write the failing tests**

```python
# tests/installer/test_merge_toml.py
import tomllib

import pytest

from excel_mcp.installer.errors import MalformedConfig
from excel_mcp.installer.merge import toml_upsert_server


def test_creates_toml_when_absent(tmp_path):
    cfg = tmp_path / "config.toml"
    action = toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    assert action == "added"
    data = tomllib.loads(cfg.read_text())
    assert data["mcp_servers"]["excel-ops-mcp"] == {"command": "uvx", "args": ["excel-ops-mcp"]}


def test_preserves_other_tables(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('model = "gpt-5"\n\n[mcp_servers.other]\ncommand = "x"\nargs = []\n')
    toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    data = tomllib.loads(cfg.read_text())
    assert data["model"] == "gpt-5"
    assert data["mcp_servers"]["other"]["command"] == "x"
    assert data["mcp_servers"]["excel-ops-mcp"]["command"] == "uvx"


def test_idempotent_update(tmp_path):
    cfg = tmp_path / "config.toml"
    assert toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"]) == "added"
    assert toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"]) == "updated"
    data = tomllib.loads(cfg.read_text())
    assert list(data["mcp_servers"].keys()) == ["excel-ops-mcp"]


def test_malformed_toml_raises_and_preserves(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("this = = broken")
    with pytest.raises(MalformedConfig):
        toml_upsert_server(cfg, "excel-ops-mcp", "uvx", ["excel-ops-mcp"])
    assert cfg.read_text() == "this = = broken"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_merge_toml.py -v`
Expected: FAIL — `toml_upsert_server` missing.

- [ ] **Step 3: Add toml_upsert_server to merge.py**

Add these imports at the top of `merge.py` (alongside existing imports):

```python
import tomlkit
```

Append to `merge.py`:

```python
def toml_upsert_server(path: Path, name: str, command: str, args: list[str]) -> str:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            try:
                doc = tomlkit.parse(text)
            except Exception as exc:  # tomlkit raises tomlkit.exceptions.ParseError
                raise MalformedConfig(f"{path}: {exc}") from exc
        else:
            doc = tomlkit.document()
    else:
        doc = tomlkit.document()

    servers = doc.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table()
        doc["mcp_servers"] = servers

    existed = name in servers
    table = tomlkit.table()
    table["command"] = command
    table["args"] = args
    servers[name] = table

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return "updated" if existed else "added"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_merge_toml.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/merge.py tests/installer/test_merge_toml.py
git commit -m "feat(installer): TOML upsert for Codex via tomlkit"
```

---

### Task 6: Adapter base + JSON file adapter

**Files:**
- Create: `excel_mcp/installer/adapters/__init__.py`
- Create: `excel_mcp/installer/adapters/base.py`
- Create: `excel_mcp/installer/adapters/json_file.py`
- Create: `tests/installer/test_json_adapter.py`

**Interfaces:**
- Consumes: `ServerSpec` (Task 2), `backup_file`/`json_upsert_server` (Task 4), `MalformedConfig`.
- Produces:
  - `@dataclass class ApplyResult` fields: `key: str`, `ok: bool`, `action: str`, `path: str | None`, `backup: str | None`, `note: str | None = None`, `error: str | None = None`.
  - `class Adapter(ABC)` attrs `key: str`, `label: str`, `gui: bool`; methods `detect() -> bool`, `target() -> str | None`, `apply(spec: ServerSpec, *, dry_run: bool) -> ApplyResult`.
  - `@dataclass class JsonDescriptor`: `key`, `label`, `gui`, `path_fn: Callable[[], Path | None]`, `detect_dirs: tuple[Path | None, ...] = ()`, `cli_name: str | None = None`, `root_key: str = "mcpServers"`, `restart_note: str | None = None`.
  - `class JsonFileAdapter(Adapter)` built from a `JsonDescriptor`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/installer/test_json_adapter.py
import json

from excel_mcp.installer.adapters.json_file import JsonDescriptor, JsonFileAdapter
from excel_mcp.installer.spec import ServerSpec


def _spec():
    return ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/abs/uvx")


def test_apply_writes_gui_absolute_command(tmp_path):
    cfg = tmp_path / "mcp.json"
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=False)
    assert result.ok and result.action == "added"
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["excel-ops-mcp"]["command"] == "/abs/uvx"


def test_dry_run_writes_nothing(tmp_path):
    cfg = tmp_path / "mcp.json"
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=True)
    assert result.action == "dry-run"
    assert not cfg.exists()


def test_apply_backs_up_existing(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"x": {"command": "z"}}}))
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=False)
    assert result.backup == str(tmp_path / "mcp.json.bak")
    assert (tmp_path / "mcp.json.bak").exists()


def test_malformed_config_returns_error_result(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("{bad")
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True, path_fn=lambda: cfg)
    result = JsonFileAdapter(desc).apply(_spec(), dry_run=False)
    assert not result.ok
    assert result.action == "skipped"
    assert result.error


def test_detect_true_when_config_dir_exists(tmp_path):
    (tmp_path / ".cursor").mkdir()
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True,
                          path_fn=lambda: tmp_path / ".cursor" / "mcp.json",
                          detect_dirs=(tmp_path / ".cursor",))
    assert JsonFileAdapter(desc).detect() is True


def test_detect_false_when_nothing_present(tmp_path):
    desc = JsonDescriptor(key="cursor", label="Cursor", gui=True,
                          path_fn=lambda: tmp_path / ".cursor" / "mcp.json",
                          detect_dirs=(tmp_path / ".cursor",))
    assert JsonFileAdapter(desc).detect() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_json_adapter.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement base.py, adapters/__init__.py, json_file.py**

```python
# excel_mcp/installer/adapters/__init__.py
```

```python
# excel_mcp/installer/adapters/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..spec import ServerSpec


@dataclass
class ApplyResult:
    key: str
    ok: bool
    action: str  # "added" | "updated" | "skipped" | "dry-run"
    path: str | None
    backup: str | None
    note: str | None = None
    error: str | None = None


class Adapter(ABC):
    key: str
    label: str
    gui: bool

    @abstractmethod
    def detect(self) -> bool: ...

    @abstractmethod
    def target(self) -> str | None: ...

    @abstractmethod
    def apply(self, spec: ServerSpec, *, dry_run: bool) -> ApplyResult: ...
```

```python
# excel_mcp/installer/adapters/json_file.py
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..errors import MalformedConfig
from ..merge import backup_file, json_upsert_server
from ..spec import ServerSpec
from .base import Adapter, ApplyResult


@dataclass
class JsonDescriptor:
    key: str
    label: str
    gui: bool
    path_fn: Callable[[], Path | None]
    detect_dirs: tuple[Path | None, ...] = ()
    cli_name: str | None = None
    root_key: str = "mcpServers"
    restart_note: str | None = None


class JsonFileAdapter(Adapter):
    def __init__(self, desc: JsonDescriptor) -> None:
        self.desc = desc
        self.key = desc.key
        self.label = desc.label
        self.gui = desc.gui

    def detect(self) -> bool:
        path = self.desc.path_fn()
        if path is not None and path.exists():
            return True
        for d in self.desc.detect_dirs:
            if d is not None and d.exists():
                return True
        if self.desc.cli_name and shutil.which(self.desc.cli_name):
            return True
        return False

    def target(self) -> str | None:
        path = self.desc.path_fn()
        return str(path) if path else None

    def apply(self, spec: ServerSpec, *, dry_run: bool) -> ApplyResult:
        path = self.desc.path_fn()
        if path is None:
            return ApplyResult(self.key, False, "skipped", None, None,
                               error="no config path on this platform")
        if dry_run:
            return ApplyResult(self.key, True, "dry-run", str(path), None,
                               note=self.desc.restart_note)
        try:
            backup = backup_file(path)
            action = json_upsert_server(path, self.desc.root_key, spec.name, spec.entry(self.gui))
        except MalformedConfig as exc:
            return ApplyResult(self.key, False, "skipped", str(path), None, error=str(exc))
        return ApplyResult(self.key, True, action, str(path),
                           str(backup) if backup else None, note=self.desc.restart_note)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_json_adapter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/adapters tests/installer/test_json_adapter.py
git commit -m "feat(installer): Adapter base + data-driven JSON file adapter"
```

---

### Task 7: TOML file adapter (Codex)

**Files:**
- Create: `excel_mcp/installer/adapters/toml_file.py`
- Create: `tests/installer/test_toml_adapter.py`

**Interfaces:**
- Consumes: `toml_upsert_server`, `backup_file`, `MalformedConfig`, `ServerSpec`, `Adapter`/`ApplyResult`.
- Produces: `@dataclass class TomlDescriptor` (`key`, `label`, `gui=False`, `path_fn`, `detect_dirs=()`, `cli_name=None`, `restart_note=None`) and `class TomlFileAdapter(Adapter)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/installer/test_toml_adapter.py
import tomllib

from excel_mcp.installer.adapters.toml_file import TomlDescriptor, TomlFileAdapter
from excel_mcp.installer.spec import ServerSpec


def _spec():
    return ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/abs/uvx")


def test_apply_writes_bare_uvx_for_cli_agent(tmp_path):
    cfg = tmp_path / "config.toml"
    desc = TomlDescriptor(key="codex", label="Codex", path_fn=lambda: cfg)
    result = TomlFileAdapter(desc).apply(_spec(), dry_run=False)
    assert result.ok and result.action == "added"
    data = tomllib.loads(cfg.read_text())
    assert data["mcp_servers"]["excel-ops-mcp"]["command"] == "uvx"


def test_dry_run_writes_nothing(tmp_path):
    cfg = tmp_path / "config.toml"
    desc = TomlDescriptor(key="codex", label="Codex", path_fn=lambda: cfg)
    result = TomlFileAdapter(desc).apply(_spec(), dry_run=True)
    assert result.action == "dry-run"
    assert not cfg.exists()


def test_detect_via_cli_on_path(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda n: "/usr/bin/codex" if n == "codex" else None)
    desc = TomlDescriptor(key="codex", label="Codex", path_fn=lambda: tmp_path / "c.toml",
                          cli_name="codex")
    assert TomlFileAdapter(desc).detect() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_toml_adapter.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement toml_file.py**

```python
# excel_mcp/installer/adapters/toml_file.py
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..errors import MalformedConfig
from ..merge import backup_file, toml_upsert_server
from ..spec import ServerSpec
from .base import Adapter, ApplyResult


@dataclass
class TomlDescriptor:
    key: str
    label: str
    path_fn: Callable[[], Path | None]
    gui: bool = False
    detect_dirs: tuple[Path | None, ...] = ()
    cli_name: str | None = None
    restart_note: str | None = None


class TomlFileAdapter(Adapter):
    def __init__(self, desc: TomlDescriptor) -> None:
        self.desc = desc
        self.key = desc.key
        self.label = desc.label
        self.gui = desc.gui

    def detect(self) -> bool:
        path = self.desc.path_fn()
        if path is not None and path.exists():
            return True
        for d in self.desc.detect_dirs:
            if d is not None and d.exists():
                return True
        if self.desc.cli_name and shutil.which(self.desc.cli_name):
            return True
        return False

    def target(self) -> str | None:
        path = self.desc.path_fn()
        return str(path) if path else None

    def apply(self, spec: ServerSpec, *, dry_run: bool) -> ApplyResult:
        path = self.desc.path_fn()
        if path is None:
            return ApplyResult(self.key, False, "skipped", None, None,
                               error="no config path on this platform")
        if dry_run:
            return ApplyResult(self.key, True, "dry-run", str(path), None,
                               note=self.desc.restart_note)
        try:
            backup = backup_file(path)
            action = toml_upsert_server(path, spec.name, spec.command_for(self.gui), list(spec.args))
        except MalformedConfig as exc:
            return ApplyResult(self.key, False, "skipped", str(path), None, error=str(exc))
        return ApplyResult(self.key, True, action, str(path),
                           str(backup) if backup else None, note=self.desc.restart_note)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_toml_adapter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/adapters/toml_file.py tests/installer/test_toml_adapter.py
git commit -m "feat(installer): Codex TOML adapter"
```

---

### Task 8: Claude Code CLI adapter

**Files:**
- Create: `excel_mcp/installer/adapters/claude_code.py`
- Create: `tests/installer/test_claude_code_adapter.py`

**Interfaces:**
- Consumes: `ServerSpec`, `Adapter`/`ApplyResult`.
- Produces: `class ClaudeCodeCliAdapter(Adapter)` — `key="claude-code"`, `label="Claude Code"`, `gui=False`; detects `claude` on PATH; `apply` runs `claude mcp remove --scope user <name>` (ignore failure) then `claude mcp add --scope user <name> -- uvx <args...>`.
- Module-level `_run = subprocess.run` indirection so tests monkeypatch `excel_mcp.installer.adapters.claude_code._run`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/installer/test_claude_code_adapter.py
import subprocess

from excel_mcp.installer.adapters import claude_code as cc
from excel_mcp.installer.adapters.claude_code import ClaudeCodeCliAdapter
from excel_mcp.installer.spec import ServerSpec


def _spec():
    return ServerSpec("excel-ops-mcp", ("excel-ops-mcp",), "/abs/uvx")


def test_apply_builds_correct_add_command(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().apply(_spec(), dry_run=False)
    assert result.ok and result.action == "added"
    add_cmd = calls[-1]
    assert add_cmd == ["claude", "mcp", "add", "--scope", "user",
                       "excel-ops-mcp", "--", "uvx", "excel-ops-mcp"]


def test_apply_reports_error_on_nonzero(monkeypatch):
    def fake_run(cmd, **kw):
        if cmd[2] == "remove":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not found")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().apply(_spec(), dry_run=False)
    assert not result.ok
    assert result.action == "skipped"
    assert "boom" in (result.error or "")


def test_dry_run_shows_command_and_runs_nothing(monkeypatch):
    def fake_run(cmd, **kw):
        raise AssertionError("should not run in dry-run")

    monkeypatch.setattr(cc, "_run", fake_run)
    result = ClaudeCodeCliAdapter().apply(_spec(), dry_run=True)
    assert result.action == "dry-run"
    assert "claude mcp add" in (result.note or "")


def test_detect_uses_which(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda n: "/usr/bin/claude" if n == "claude" else None)
    assert ClaudeCodeCliAdapter().detect() is True
    monkeypatch.setattr(cc.shutil, "which", lambda n: None)
    assert ClaudeCodeCliAdapter().detect() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_claude_code_adapter.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement claude_code.py**

```python
# excel_mcp/installer/adapters/claude_code.py
from __future__ import annotations

import shutil
import subprocess

from ..spec import ServerSpec
from .base import Adapter, ApplyResult

_run = subprocess.run  # indirection point for tests


class ClaudeCodeCliAdapter(Adapter):
    key = "claude-code"
    label = "Claude Code"
    gui = False

    def detect(self) -> bool:
        return shutil.which("claude") is not None

    def target(self) -> str | None:
        return "claude mcp add --scope user"

    def apply(self, spec: ServerSpec, *, dry_run: bool) -> ApplyResult:
        add_cmd = ["claude", "mcp", "add", "--scope", "user", spec.name, "--", "uvx", *spec.args]
        if dry_run:
            return ApplyResult(self.key, True, "dry-run", None, None,
                               note=" ".join(add_cmd))
        # Make idempotent: remove any existing user-scope entry first (ignore failure).
        _run(["claude", "mcp", "remove", "--scope", "user", spec.name],
             capture_output=True, text=True)
        proc = _run(add_cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return ApplyResult(self.key, True, "added", None, None,
                               note="claude mcp add (user scope)")
        return ApplyResult(self.key, False, "skipped", None, None,
                           error=(proc.stderr or proc.stdout or "claude mcp add failed").strip())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_claude_code_adapter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/adapters/claude_code.py tests/installer/test_claude_code_adapter.py
git commit -m "feat(installer): Claude Code CLI adapter (idempotent user-scope add)"
```

---

### Task 9: Registry of the six agents

**Files:**
- Create: `excel_mcp/installer/registry.py`
- Create: `tests/installer/test_registry.py`

**Interfaces:**
- Consumes: `paths.*`, `JsonDescriptor`/`JsonFileAdapter`, `TomlDescriptor`/`TomlFileAdapter`, `ClaudeCodeCliAdapter`.
- Produces: `build_registry() -> list[Adapter]` returning six adapters in a stable order; `adapter_by_key(key: str) -> Adapter | None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/installer/test_registry.py
from excel_mcp.installer.registry import adapter_by_key, build_registry


def test_registry_has_six_expected_agents():
    keys = [a.key for a in build_registry()]
    assert keys == ["claude-desktop", "claude-code", "codex", "gemini", "cursor", "windsurf"]


def test_gui_flags_are_correct():
    by = {a.key: a for a in build_registry()}
    assert by["claude-desktop"].gui is True
    assert by["cursor"].gui is True
    assert by["windsurf"].gui is True
    assert by["gemini"].gui is False
    assert by["codex"].gui is False
    assert by["claude-code"].gui is False


def test_adapter_by_key_found_and_missing():
    assert adapter_by_key("cursor").label == "Cursor"
    assert adapter_by_key("nope") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_registry.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement registry.py**

```python
# excel_mcp/installer/registry.py
from __future__ import annotations

from pathlib import Path

from . import paths
from .adapters.base import Adapter
from .adapters.claude_code import ClaudeCodeCliAdapter
from .adapters.json_file import JsonDescriptor, JsonFileAdapter
from .adapters.toml_file import TomlDescriptor, TomlFileAdapter


def _home() -> Path:
    import os

    return Path(os.path.expanduser("~"))


def build_registry() -> list[Adapter]:
    home = _home()
    claude_desktop = JsonFileAdapter(JsonDescriptor(
        key="claude-desktop", label="Claude Desktop", gui=True,
        path_fn=paths.claude_desktop_path,
        detect_dirs=(
            home / "Library" / "Application Support" / "Claude",
            home / ".config" / "Claude",
        ),
        restart_note="Fully quit and relaunch Claude Desktop.",
    ))
    codex = TomlFileAdapter(TomlDescriptor(
        key="codex", label="Codex",
        path_fn=paths.codex_path,
        detect_dirs=(home / ".codex",),
        cli_name="codex",
        restart_note="Restart Codex.",
    ))
    gemini = JsonFileAdapter(JsonDescriptor(
        key="gemini", label="Gemini CLI", gui=False,
        path_fn=paths.gemini_path,
        detect_dirs=(home / ".gemini",),
        cli_name="gemini",
        restart_note="Restart the Gemini CLI.",
    ))
    cursor = JsonFileAdapter(JsonDescriptor(
        key="cursor", label="Cursor", gui=True,
        path_fn=paths.cursor_path,
        detect_dirs=(home / ".cursor",),
        restart_note="Reload Cursor and enable the server in Settings → MCP.",
    ))
    windsurf = JsonFileAdapter(JsonDescriptor(
        key="windsurf", label="Windsurf", gui=True,
        path_fn=paths.windsurf_path,
        detect_dirs=(home / ".codeium" / "windsurf",),
        restart_note="Click Refresh in the Cascade MCP panel.",
    ))
    return [claude_desktop, ClaudeCodeCliAdapter(), codex, gemini, cursor, windsurf]


def adapter_by_key(key: str) -> Adapter | None:
    for adapter in build_registry():
        if adapter.key == key:
            return adapter
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/installer/test_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add excel_mcp/installer/registry.py tests/installer/test_registry.py
git commit -m "feat(installer): registry of the six supported agents"
```

---

### Task 10: CLI orchestration + TUI

**Files:**
- Create: `excel_mcp/installer/tui.py`
- Modify: `excel_mcp/installer/cli.py` (replace the Task 1 stub)
- Modify: `tests/installer/test_cli.py` (add orchestration tests; keep `--version` test)

**Interfaces:**
- Consumes: `build_registry`, `adapter_by_key`, `default_spec`, `ApplyResult`.
- Produces:
  - `tui.select_agents(adapters: list[Adapter], detected: set[str]) -> list[str]` — questionary checkbox, detected pre-checked; returns chosen keys.
  - `cli.main(argv=None) -> int` supporting `--version`, `--list`, `--dry-run`, `--yes`, `--agents a,b`.
  - Selection logic: `--agents` → those keys (unknown key → error, rc 2); else `--yes` → detected; else if stdout is a TTY → `tui.select_agents`; else → detected.
  - Prints a per-agent summary; returns rc 0 if all applied ok or dry-run, rc 1 if any adapter failed.

- [ ] **Step 1: Write the failing tests**

```python
# tests/installer/test_cli.py  (append these; keep test_version_flag_exits_zero)
import json

from excel_mcp.installer.cli import main


def test_list_prints_agents(capsys):
    rc = main(["--list"])
    out = capsys.readouterr().out
    assert rc == 0
    for label in ["Claude Desktop", "Claude Code", "Codex", "Gemini CLI", "Cursor", "Windsurf"]:
        assert label in out


def test_agents_flag_applies_only_selected(fake_home, capsys):
    rc = main(["--agents", "cursor", "--yes"])
    out = capsys.readouterr().out
    assert rc == 0
    cfg = fake_home / ".cursor" / "mcp.json"
    assert cfg.exists()
    data = json.loads(cfg.read_text())
    assert "excel-ops-mcp" in data["mcpServers"]
    # gemini NOT touched
    assert not (fake_home / ".gemini" / "settings.json").exists()


def test_dry_run_writes_nothing(fake_home, capsys):
    rc = main(["--agents", "cursor", "--dry-run"])
    assert rc == 0
    assert not (fake_home / ".cursor" / "mcp.json").exists()


def test_unknown_agent_key_errors(capsys):
    rc = main(["--agents", "bogus", "--yes"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "bogus" in err
```

Note: `--agents cursor` avoids the `claude-code`/`codex`/`gemini` CLI `detect()` calling `shutil.which`, which is fine (returns bool). The `fake_home` fixture isolates writes.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/installer/test_cli.py -v`
Expected: FAIL — new behavior not implemented.

- [ ] **Step 3: Implement tui.py**

```python
# excel_mcp/installer/tui.py
from __future__ import annotations

from .adapters.base import Adapter


def select_agents(adapters: list[Adapter], detected: set[str]) -> list[str]:
    import questionary

    choices = [
        questionary.Choice(
            title=f"{a.label}" + ("  (detected)" if a.key in detected else "  (not found)"),
            value=a.key,
            checked=a.key in detected,
        )
        for a in adapters
    ]
    answer = questionary.checkbox(
        "Install excel-ops-mcp into which agents?", choices=choices
    ).ask()
    return answer or []
```

- [ ] **Step 4: Implement cli.py (replace stub)**

```python
# excel_mcp/installer/cli.py
from __future__ import annotations

import argparse
import sys

from .adapters.base import ApplyResult
from .registry import adapter_by_key, build_registry
from .spec import default_spec


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="excel-ops-mcp-install",
                                description="Install excel-ops-mcp into your LLM agents.")
    p.add_argument("--version", action="store_true", help="print version and exit")
    p.add_argument("--list", action="store_true", help="list supported agents + detection, then exit")
    p.add_argument("--dry-run", action="store_true", help="show what would change; write nothing")
    p.add_argument("--yes", action="store_true", help="no prompt; apply to detected (or --agents) set")
    p.add_argument("--agents", help="comma-separated agent keys to target")
    return p.parse_args(argv)


def _select_keys(args, adapters, detected) -> list[str]:
    if args.agents:
        return [k.strip() for k in args.agents.split(",") if k.strip()]
    if args.yes or not sys.stdout.isatty():
        return sorted(detected)
    from .tui import select_agents

    return select_agents(adapters, detected)


def _print_summary(results: list[ApplyResult]) -> None:
    print("\nSummary:")
    for r in results:
        if r.action == "dry-run":
            line = f"  ~ {r.key}: would write {r.path or r.note}"
        elif r.ok:
            where = r.path or "(via CLI)"
            line = f"  ✓ {r.key}: {r.action} → {where}"
            if r.backup:
                line += f"  (backup {r.backup})"
        else:
            line = f"  ✗ {r.key}: {r.error}"
        print(line)
        if r.ok and r.note and r.action != "dry-run":
            print(f"      next: {r.note}")


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if args.version:
        print("excel-ops-mcp-install (excel-ops-mcp installer)")
        return 0

    adapters = build_registry()
    detected = {a.key for a in adapters if a.detect()}

    if args.list:
        print("Supported agents:")
        for a in adapters:
            mark = "detected" if a.key in detected else "not found"
            print(f"  [{mark:>9}] {a.label:<16} {a.key}")
        return 0

    keys = _select_keys(args, adapters, detected)

    # Validate keys.
    valid = {a.key for a in adapters}
    unknown = [k for k in keys if k not in valid]
    if unknown:
        print(f"error: unknown agent(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"valid keys: {', '.join(sorted(valid))}", file=sys.stderr)
        return 2

    if not keys:
        print("No agents selected. Nothing to do.")
        return 0

    spec = default_spec()
    results: list[ApplyResult] = []
    for key in keys:
        adapter = adapter_by_key(key)
        assert adapter is not None  # validated above
        results.append(adapter.apply(spec, dry_run=args.dry_run))

    _print_summary(results)
    return 1 if any(not r.ok for r in results) else 0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/installer/test_cli.py -v`
Expected: PASS (all, including `--version`).

- [ ] **Step 6: Run the whole installer suite**

Run: `.venv/bin/python -m pytest tests/installer -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add excel_mcp/installer/cli.py excel_mcp/installer/tui.py tests/installer/test_cli.py
git commit -m "feat(installer): CLI orchestration, selection logic, TUI, summary"
```

---

### Task 11: Bootstrap scripts

**Files:**
- Create: `install.sh`
- Create: `install.ps1`

**Interfaces:**
- Produces: two bootstrap scripts that ensure `uv`, then exec `uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@"`.

- [ ] **Step 1: Write install.sh**

```sh
#!/bin/sh
# excel-ops-mcp installer bootstrap (POSIX).
# Usage: curl -LsSf https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.sh | sh
set -eu

if ! command -v uv >/dev/null 2>&1; then
  echo "excel-ops-mcp: installing uv (provides Python + uvx)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv installs to ~/.local/bin by default.
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v uvx >/dev/null 2>&1; then
  echo "excel-ops-mcp: uvx not found on PATH after installing uv." >&2
  echo "Add uv's bin dir to PATH (usually ~/.local/bin) and re-run." >&2
  exit 1
fi

echo "excel-ops-mcp: launching installer..."
exec uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install "$@"
```

- [ ] **Step 2: Write install.ps1**

```powershell
# excel-ops-mcp installer bootstrap (Windows PowerShell).
# Usage: powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.ps1 | iex"
$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "excel-ops-mcp: installing uv (provides Python + uvx)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) {
    Write-Error "uvx not found after installing uv. Add uv's bin dir to PATH and re-run."
    exit 1
}

Write-Host "excel-ops-mcp: launching installer..."
uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install $args
```

- [ ] **Step 3: Make install.sh executable + shellcheck if available**

Run: `chmod +x install.sh && { command -v shellcheck >/dev/null && shellcheck install.sh || echo "shellcheck not installed, skipping"; }`
Expected: no shellcheck errors (or skip message).

- [ ] **Step 4: Smoke-test the bootstrap path locally (uv already present)**

Run: `sh install.sh --list`
Expected: prints the supported-agents list (bootstrap falls through to the installer, which runs `--list`). This exercises the `uvx --from` path against the published package; if v0.2.0 isn't published yet, expect it to resolve the latest published version — acceptable for smoke, or test after Task 12 publish.

- [ ] **Step 5: Commit**

```bash
git add install.sh install.ps1
git commit -m "feat(installer): POSIX + PowerShell bootstrap scripts"
```

---

### Task 12: Docs, README, release v0.2.0

**Files:**
- Modify: `README.md` (add "One-command install" section near the top of install docs)
- Modify: `docs/DEVELOPMENT.md` (note the `[install]` extra + installer module)

**Interfaces:** none (docs + release).

- [ ] **Step 1: Add README install section**

Insert after the `### Recommended: uvx` block in `README.md`:

```markdown
### One-command install (all agents)

Bootstraps `uv` if needed, then opens a picker to install `excel-ops-mcp` into
Claude Desktop, Claude Code, Codex, Gemini CLI, Cursor, and/or Windsurf:

```bash
curl -LsSf https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.sh | sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/dasein108/excel-ops-mcp/main/install.ps1 | iex"
```

Non-interactive: `... | sh -s -- --agents cursor,claude-code --yes`.
Preview only: add `--dry-run`. List detection: `--list`.
```

- [ ] **Step 2: Note the extra in DEVELOPMENT.md**

Add under the developer-install section of `docs/DEVELOPMENT.md`:

```markdown
The cross-agent installer lives in `excel_mcp/installer/` and its deps are under
the optional `install` extra. For local work install both extras:

```bash
pip install -e ".[dev,install]"
```
```

- [ ] **Step 3: Run the full test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (existing + `tests/installer`).

- [ ] **Step 4: Commit**

```bash
git add README.md docs/DEVELOPMENT.md
git commit -m "docs(installer): one-command install instructions"
```

- [ ] **Step 5: Tag and release v0.2.0**

```bash
git push origin main
git tag v0.2.0
git push origin v0.2.0
```

Expected: `Publish to PyPI` workflow runs green; `excel-ops-mcp 0.2.0` appears on PyPI with the `excel-ops-mcp-install` entry point.

- [ ] **Step 6: Verify the published installer end-to-end**

Run: `uvx --from "excel-ops-mcp[install]" excel-ops-mcp-install --list`
Expected: prints the six agents with detection status.

---

## Self-Review

**Spec coverage:**
- Bootstrap (sh + ps1, ensure uv, run uvx) → Task 11. ✓
- Installer shipped in package + `[install]` extra + console script → Task 1. ✓
- ServerSpec + GUI-absolute-uvx rule → Task 2 (used by adapters in Tasks 6–8). ✓
- Per-OS paths → Task 3. ✓
- Safe merge + backup + malformed guard (JSON + TOML) → Tasks 4, 5. ✓
- Six adapters over three strategies → Tasks 6 (JSON×4), 7 (Codex TOML), 8 (Claude Code CLI), wired in Task 9. ✓
- TUI (questionary, pre-check detected) → Task 10. ✓
- CLI flags `--agents/--yes/--dry-run/--list` → Task 10. ✓
- Idempotent / never-clobber / backups tested → Tasks 4, 5, 6, 7, 8. ✓
- Docs + v0.2.0 release → Task 12. ✓
- `openclaw`/`hermes` deferred (unverified) — registry extensible → noted in Global Constraints. ✓

**Placeholder scan:** No TBD/TODO; every code step has complete code; every test step has real assertions. ✓

**Type consistency:** `ApplyResult(key, ok, action, path, backup, note, error)` used identically across json_file, toml_file, claude_code, and cli summary. `ServerSpec.entry(gui)` / `command_for(gui)` consistent between Tasks 2, 6, 7. `JsonDescriptor`/`TomlDescriptor` fields match their adapter constructors and registry usage (Task 9). Registry key order matches the `test_registry` assertion. ✓
