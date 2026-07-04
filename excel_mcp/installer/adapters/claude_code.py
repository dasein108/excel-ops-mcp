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

    def is_installed(self) -> bool:
        if shutil.which("claude") is None:
            return False
        proc = _run(["claude", "mcp", "get", "excel-ops-mcp"], capture_output=True, text=True)
        return proc.returncode == 0

    def target(self) -> str | None:
        return "claude mcp add --scope user"

    def remove(self, *, dry_run: bool) -> ApplyResult:
        cmd = ["claude", "mcp", "remove", "--scope", "user", "excel-ops-mcp"]
        if dry_run:
            return ApplyResult(self.key, True, "dry-run", None, None, note=" ".join(cmd))
        proc = _run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return ApplyResult(self.key, True, "removed", None, None, note="claude mcp remove (user scope)")
        # `claude mcp remove` fails when the entry doesn't exist — treat as already absent.
        return ApplyResult(self.key, True, "absent", None, None)

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
