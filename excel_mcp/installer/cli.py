from __future__ import annotations

import argparse
import sys

from .adapters.base import Adapter, ApplyResult
from .registry import adapter_by_key, build_registry
from .spec import default_spec


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="excel-ops-mcp-install",
                                description="Install excel-ops-mcp into your LLM agents.")
    p.add_argument("--version", action="store_true", help="print version and exit")
    p.add_argument("--list", action="store_true", help="list supported agents + status, then exit")
    p.add_argument("--dry-run", action="store_true", help="show what would change; write nothing")
    p.add_argument("--agents", help="comma-separated agent keys to install (non-interactive)")
    p.add_argument("--uninstall", help="comma-separated agent keys to remove (non-interactive)")
    return p.parse_args(argv)


def _resolve_keys(raw: str, adapters: list[Adapter]) -> tuple[list[str], list[str]]:
    """Split a comma list into (valid_keys, unknown_keys)."""
    valid = {a.key for a in adapters}
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    unknown = [k for k in keys if k not in valid]
    return keys, unknown


def _print_summary(results: list[ApplyResult]) -> None:
    if not results:
        print("No changes.")
        return
    print("\nSummary:")
    for r in results:
        if r.action == "dry-run":
            print(f"  ~ {r.key}: {r.note or 'would change'}  ({r.path or 'via CLI'})")
        elif r.action == "absent":
            print(f"  - {r.key}: not installed, nothing to remove")
        elif r.ok:
            where = r.path or "(via CLI)"
            line = f"  ✓ {r.key}: {r.action} → {where}"
            if r.backup:
                line += f"  (backup {r.backup})"
            print(line)
            if r.note:
                print(f"      next: {r.note}")
        else:
            print(f"  ✗ {r.key}: {r.error}")


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if args.version:
        print("excel-ops-mcp-install (excel-ops-mcp installer)")
        return 0

    adapters = build_registry()
    detected = {a.key for a in adapters if a.detect()}
    installed = {a.key for a in adapters if a.is_installed()}

    if args.list:
        print("Supported agents:")
        for a in adapters:
            if a.key in installed:
                status = "installed"
            elif a.key in detected:
                status = "detected"
            else:
                status = "not found"
            print(f"  [{status:>9}] {a.label:<16} {a.key}")
        return 0

    spec = default_spec()

    # Non-interactive uninstall.
    if args.uninstall:
        keys, unknown = _resolve_keys(args.uninstall, adapters)
        if unknown:
            print(f"error: unknown agent(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        results = [adapter_by_key(k).remove(dry_run=args.dry_run) for k in keys]
        _print_summary(results)
        return 1 if any(not r.ok for r in results) else 0

    # Non-interactive install.
    if args.agents:
        keys, unknown = _resolve_keys(args.agents, adapters)
        if unknown:
            print(f"error: unknown agent(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        results = [adapter_by_key(k).apply(spec, dry_run=args.dry_run) for k in keys]
        _print_summary(results)
        return 1 if any(not r.ok for r in results) else 0

    # Interactive: choose install/uninstall, pick agents (nothing checked by default).
    if not sys.stdin.isatty():
        print("No terminal available. Use --agents KEYS to install or --uninstall KEYS to remove.")
        print("Run with --list to see agent keys and status.")
        return 0

    from .tui import run_interactive

    mode, keys = run_interactive(adapters, detected, installed)
    if not keys:
        print("No agents selected. Nothing to do.")
        return 0
    if mode == "uninstall":
        results = [adapter_by_key(k).remove(dry_run=args.dry_run) for k in keys]
    else:
        results = [adapter_by_key(k).apply(spec, dry_run=args.dry_run) for k in keys]
    _print_summary(results)
    return 1 if any(not r.ok for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
