---
title: "GitHub Release to PyPI Automation"
status: done
phase: P1
---

# Task 22 — GitHub Release to PyPI Automation

Add GitHub Actions workflow to publish the package to PyPI when a GitHub release is published.

## Scope

- Build source and wheel distributions.
- Run tests before publish.
- Publish to PyPI with trusted publishing.
- No checked-in credentials.

## Acceptance Criteria

- Workflow file exists under `.github/workflows/`.
- Trigger is `release: published`.
- Uses Python setup.
- Installs dev dependencies.
- Runs tests.
- Builds package.
- Publishes using `pypa/gh-action-pypi-publish`.
- Uses `id-token: write` permission.

