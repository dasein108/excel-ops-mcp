---
title: "Developer Publishing Guide"
status: done
phase: P1
---

# Task 21 — Developer Publishing Guide

Create a separate developer guide for local development, testing, packaging, and PyPI publishing.

## Scope

- Local editable install.
- Running tests.
- Building distributions.
- Manual PyPI publishing fallback.
- Trusted publishing setup.
- Release checklist.

## Acceptance Criteria

- Developer guide lives outside README.
- Includes `python -m build`.
- Includes `twine check`.
- Explains PyPI trusted publisher setup.
- Explains that GitHub releases trigger publishing.
- Does not require storing PyPI API tokens in GitHub secrets.

