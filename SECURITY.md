# Security

## Reporting a vulnerability

If you believe you have found a security issue in Blacksmith itself (the CLI, install path, or packaging), please open a [private security advisory](https://github.com/jimididit/blacksmith/security/advisories/new) on GitHub, or contact the maintainer via the channels listed in the README.

Do not file a public issue for unpatched vulnerabilities.

Please include:

- Blacksmith version (`blacksmith --version`)
- OS and Python version
- Steps to reproduce
- Impact (what an attacker could do)

## Scope

Blacksmith installs software by invoking local package managers (`apt`, `winget`, `brew`, and others). Treat set YAML like code you are willing to run.

| Source | Guarantees | Does not guarantee |
|--------|------------|--------------------|
| Built-in sets | Schema validation; argv allowlist; managers run with `shell=False` | Upstream packages are benign, correctly named, or version-pinned |
| Your own YAML | Same technical checks | Same - you own the IDs you write |
| Third-party / shared `--file` YAML | Untrusted-source warning; non-interactive use requires `--yes` or `--dry-run`; allowlist blocks shell metacharacters and leading `-`; optional `--require-signature` verifies a detached minisign signature against bundled/user/`--pubkey` keys | Cryptographic authenticity unless `--require-signature` succeeds; live "does this package exist?" on every install; rollback after partial failure |

A valid-looking package ID still installs if the manager resolves it. Sharing a set shares a list of package-manager operands, not a verified supply chain.

Inline `|version` pins depend on the package manager and upstream repos reporting honest versions; they are not supply-chain proof.

Local `audit.jsonl` is a DFIR aid on the operator machine. It is not a tamper-evident ledger; anyone with filesystem access can edit or delete it.

## Safe workflow for unknown YAML

```bash
blacksmith validate path/to/set.yaml
blacksmith install --file path/to/set.yaml --dry-run
blacksmith install --file path/to/set.yaml --yes
```

## Supported versions

Security fixes land on the latest released version on PyPI (`jdi-blacksmith`). Older versions are not backported unless noted in a release.
