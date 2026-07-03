---
title: "Financial Operations Recipes and Examples"
status: done
phase: P2
---

# Task 11 — Financial Operations Recipes and Examples

Provide examples and prompt recipes for common accounting, bookkeeping, marketing operations, SEO, and research workflows.

## Scope

- Examples only; avoid adding separate domain-specific tools unless repeated usage proves it is needed.
- SQL recipes over detected DuckDB tables.
- Write operation examples with dry-run and commit.

## Deliverables

Recipe examples:

- bookkeeping categorization
- duplicate transaction detection
- invoice/payment matching
- monthly totals by category
- vendor spend ranking
- aging buckets
- variance analysis
- campaign performance rollups
- SEO keyword export cleanup
- lead/research enrichment tables

Each recipe should show:

- describe-first workflow
- SQL query
- optional write operations
- dry-run review
- commit pattern

## Acceptance Criteria

- Recipes run against small fixture workbooks.
- Examples do not require Google Sheets or Numbers.
- Examples demonstrate source citations and diffs.
- Documentation is concise enough to fit into MCP usage guidance.

## Notes

These recipes should teach the model the intended behavior: inspect, query, dry-run, then commit.

