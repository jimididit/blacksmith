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

## CI expectations

The workflow runs on pull requests to `main` (and `develop` if used). The aggregator job **CI** must succeed. It requires:

- Trust Boundary Gate
- Unit tests (matrix)
- Integration tests
- Security scan (`pip-audit` + Bandit)
- Package build

Quality lint (Ruff/mypy/yamllint) may still report warnings while the codebase is cleaned up; the trust gate and tests are hard failures.

## Releases

Tag `v*` on `main` after merge to trigger the release job (PyPI + GitHub Release). Prefer tagging only from `main` at a green commit.
