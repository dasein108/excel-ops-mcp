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
