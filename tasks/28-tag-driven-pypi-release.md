---
title: "Tag-driven PyPI Release"
status: partial
scope: release
source: "superpowers spec 2026-07-03 (approved)"
---

# Tag-driven PyPI Release

Release + publish `excel-ops-mcp` to PyPI with automatic version increment, driven by
git tags. No manual version edits, no bump commits. Tag is the single source of truth.

**Status note:** code components (CI, publish workflow, `hatch-vcs` dynamic version)
are wired. Remaining: the one-time manual prerequisites below (git init, GitHub repo,
PyPI trusted publisher, first tag) — not yet executed.

## Policy

- **Trigger:** push a `v*` git tag → CI publishes that version to PyPI.
- **Version source:** `hatch-vcs` derives the version from the git tag at build time.
  Between tags, builds get dev versions (`0.1.0.dev5+g<sha>`).
- **Bump:** developer chooses the next tag by SemVer. patch `v0.1.1`, minor `v0.2.0`,
  major `v1.0.0`.
- **Auth:** PyPI OIDC trusted publishing. No API token stored.

## Components

### 1. `.github/workflows/ci.yml`
Runs on push + PR to `main`. Single job: setup Python 3.12, install `.[dev]`, `pytest`.
Gate to catch breakage before tagging. No matrix, no publish.

### 2. `.github/workflows/publish-pypi.yml`
- Trigger: `push: tags: ['v*']`.
- `actions/checkout` must set `fetch-depth: 0` — hatch-vcs needs full tag history
  or the version resolves incorrectly.
- Steps: checkout → setup Python → install `.[dev]` + build/twine → pytest →
  `python -m build` → `twine check dist/*` → `pypa/gh-action-pypi-publish`.
- Keeps `permissions: id-token: write` for OIDC.

### 3. `pyproject.toml`
```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
# remove: version = "0.1.0"
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"
```
Also replace `REPLACE_ME` in project URLs with the real `owner/excel-ops-mcp`.

## One-time prerequisites (manual, outside CI)

1. `git init`, create GitHub repo, push.
2. PyPI → add a **pending trusted publisher** for project `excel-ops-mcp`: owner/repo +
   workflow filename `publish-pypi.yml`. Pending publisher lets the first upload
   create the project.
3. First release: `git tag v0.1.0 && git push origin v0.1.0`.

## Release ritual (steady state)

```
git tag v0.2.0
git push origin v0.2.0
```

## Non-goals (YAGNI)

- No Python test matrix.
- No TestPyPI dry-run.
- No auto-bump on push-to-main (needs bot commits / dev-versioning, noisy).
- No changelog automation.
