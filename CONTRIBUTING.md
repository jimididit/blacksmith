# Contributing to Blacksmith

## Branch & PR workflow (required)

**Do not commit or push directly to `main`.**

1. Create a feature branch from up-to-date `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/short-description
   ```
2. Implement and push the branch:
   ```bash
   git push -u origin HEAD
   ```
3. Open a pull request into `main` (`gh pr create` or GitHub UI).
4. Wait until the required **CI** check is green.
5. Merge only after CI is green. Do not merge with failing or skipped required checks.

Branch naming suggestions: `feat/…`, `fix/…`, `chore/…`, `security/…`.

## Local checks before pushing

```bash
pip install -e .
pip install pytest pytest-cov pytest-mock ruff mypy yamllint pip-audit bandit
pytest tests/ -v
# Trust boundary: no shell=True in package managers
# (also enforced in CI trust-gate job)
```

## Dependency lockfile

Runtime deps are ranged in `requirements.txt` and pinned in `requirements.lock`
(generated with [pip-tools](https://github.com/jazzband/pip-tools)).

Regenerate after changing `requirements.txt`:

```bash
pip install pip-tools
pip-compile --output-file=requirements.lock requirements.txt
```

CI runs `pip-audit -r requirements.lock` so the audited tree matches what we pin.
Install from the lock for reproducible local audits: `pip install -r requirements.lock`.

## CI expectations

The workflow runs on pull requests to `main` (and `develop` if used). The aggregator job **CI** must succeed. It requires:

- Trust Boundary Gate
- Unit tests (matrix)
- Integration tests
- Security scan (`pip-audit` + Bandit)
- Package build

Quality lint (Ruff/mypy/yamllint) may still report warnings while the codebase is cleaned up; the trust gate and tests are hard failures.

## Releases

1. Move items from `[Unreleased]` into a new version section in [`CHANGELOG.md`](CHANGELOG.md).
2. Bump the version (`scripts/bump_version.py` or edit `pyproject.toml` + `blacksmith/__init__.py`).
3. Merge to `main` with green **CI**, then tag `v*` on `main` to trigger the release job (PyPI + GitHub Release).

The release workflow pulls the matching `## [x.y.z]` section from `CHANGELOG.md` for the GitHub Release body (falls back to auto-generated notes if missing).

PyPI upload uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) via the GitHub Environment **`release`**, matching the publisher configured for `jdi-blacksmith`. No long-lived `PYPI_API_TOKEN` is required. After the first successful OIDC publish, delete any leftover `PYPI_API_TOKEN` repository secret if it still exists.
