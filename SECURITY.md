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
| Your own YAML | Same technical checks; offline trust-scan warnings (optional `--strict-trust` fail-closed) | Same - you own the IDs you write; trust scan is not a malware or reputation check |
| Third-party / shared `--file` YAML | Untrusted-source warning; non-interactive use requires `--yes` or `--dry-run`; allowlist blocks shell metacharacters and leading `-`; optional `--require-signature` verifies a detached minisign signature against bundled/user/`--pubkey` keys; offline trust-scan warnings (escalate with `--strict-trust`) | Cryptographic authenticity unless `--require-signature` succeeds; live "does this package exist?" on every install; rollback after partial failure; that packages are free of malware |
| Remote `--url` HTTPS YAML | Same pipeline as `--file` after a temp fetch; HTTPS only (rejects `http://` and non-HTTPS redirects); blocks obvious SSRF literal hosts (localhost, loopback, link-local, RFC1918 literals); timeout and max body size fail closed; REMOTE banner with final URL + SHA-256; optional `--require-signature` with auto-try `{url}.minisig` or `--signature` path/HTTPS URL; trust-scan findings fail closed | That the remote host is trustworthy; DNS-rebinding / full SSRF hardening; mandatory signatures for remote sets (planned as L4.2 `--allow-unsigned` policy); persistent cache of fetched YAML; malware scanning of package contents |

A valid-looking package ID still installs if the manager resolves it. Sharing a set shares a list of package-manager operands, not a verified supply chain.

Inline `|version` pins depend on the package manager and upstream repos reporting honest versions; they are not supply-chain proof.

Local `audit.jsonl` is a DFIR aid on the operator machine. It is not a tamper-evident ledger; anyone with filesystem access can edit or delete it.

## Safe workflow for unknown YAML

```bash
blacksmith validate path/to/set.yaml
blacksmith validate path/to/set.yaml --strict-trust
blacksmith install --file path/to/set.yaml --dry-run
blacksmith install --file path/to/set.yaml --strict-trust --yes
```

The offline trust scan flags oversized sets, optional denylist hits (bundled denylist is empty; reserved for known-bad IDs), kitchen-sink manager mixes, junk-looking IDs, and conflicting duplicate names. It does **not** scan package binaries for malware, check upstream reputation, or prove a set is safe. Absence of findings is not a green light.

Remote HTTPS sets use the same trust path after a one-shot fetch to a temp file (deleted when the command finishes). Prefer `blacksmith validate --url https://…` and `install --url … --dry-run` before `--yes`. A successful fetch does not mean the YAML is safe - treat it like `--file`. Remote `--url` fails closed when the trust scan reports findings (same as `--strict-trust` locally). Future L4.2 may hard-gate unsigned remote sets; today signatures stay opt-in with `--require-signature`.

Authors who want to publish a detached signature can run `blacksmith sign path/to/set.yaml` (optional `--secret-key`; requires the `minisign` CLI on PATH). Signing proves set file provenance for operators who pass `--require-signature`; it does not make packages safe. minisign is not a required Blacksmith dependency.

## Supported versions

Security fixes land on the latest released version on PyPI (`jdi-blacksmith`). Older versions are not backported unless noted in a release.
