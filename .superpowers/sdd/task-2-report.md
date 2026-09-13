# Task 2 Report: Group JSON mode and unsupported commands

**Status:** DONE
**Branch:** `feat/l6-json-output`

## Summary

Added the root `--json` option, stored JSON mode in the Click context, prevented
the bare interactive menu in JSON mode, and added stable fail-closed JSON errors
for all non-v1 commands: `audit`, `create`, `export`, `uninstall`, and
`validate`.

## TDD Evidence

### RED

Command:

```text
python -m pytest tests/test_json_out.py -q
```

Before implementation, the six new CLI cases failed because Click rejected
`--json` as an unknown option. Result: **6 failed, 3 passed**.

### GREEN

Focused verification:

```text
python -m pytest tests/test_json_out.py tests/test_cli.py -q
13 passed in 0.41s
```

Full regression suite:

```text
python -m pytest -q
196 passed in 1.68s
```

## Implementation

- Root `cli` accepts `--json` and persists it as `ctx.obj["json"]`.
- Bare `blacksmith --json` emits a `json_unsupported` envelope for
  `interactive` and exits 2 without entering Questionary.
- `reject_json_if_unsupported` checks `JSON_COMMANDS` and emits a stable error.
- Every currently registered non-v1 command invokes the helper before command
  work.
- Tests assert the envelope command, error code, and exit behavior.

## Verification

- `git diff --check` passed.
- IDE diagnostics reported no linter errors.
- `graphify update .` completed after code edits.

## Concerns

None for Task 2. Supported v1 command JSON payloads are intentionally handled
by later tasks.
