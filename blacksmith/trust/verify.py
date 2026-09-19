"""Verify detached minisign signatures on set YAML files."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from blacksmith.trust.paths import iter_trusted_pubkeys


@dataclass
class VerifyResult:
    """Outcome of a minisign verification attempt."""

    ok: bool
    message: str
    pubkey_used: Optional[Path] = None


def default_signature_path(config_path: Path) -> Path:
    """Sibling detached signature: set.yaml -> set.yaml.minisig."""
    path = Path(config_path).expanduser()
    return path.with_name(path.name + ".minisig")


def verify_set_signature(
    config_path: Path,
    signature_path: Optional[Path] = None,
    extra_pubkeys: Optional[Sequence[Path]] = None,
) -> VerifyResult:
    """
    Verify config_path against a detached minisign signature.

    Uses the minisign CLI on PATH. Tries each trusted pubkey until one succeeds.
    """
    config = Path(config_path).expanduser().resolve()
    if not config.is_file():
        return VerifyResult(ok=False, message=f"Config file not found: {config}")

    sig = (
        Path(signature_path).expanduser().resolve()
        if signature_path
        else default_signature_path(config).resolve()
    )
    if not sig.is_file():
        return VerifyResult(
            ok=False,
            message=(
                f"Signature file not found: {sig}. "
                "Create one with: blacksmith sign <file> "
                "or minisign -Sm <file>, or pass --signature PATH."
            ),
        )

    minisign = shutil.which("minisign")
    if not minisign:
        return VerifyResult(
            ok=False,
            message=(
                "minisign not found on PATH. Install minisign to use "
                "--require-signature (e.g. scoop install minisign, "
                "brew install minisign, or your distro package)."
            ),
        )

    pubkeys: List[Path] = iter_trusted_pubkeys(extra=extra_pubkeys)
    if not pubkeys:
        return VerifyResult(
            ok=False,
            message=(
                "No trusted public keys found. Add *.pub files under "
                "the packaged keys dir, your user trusted_keys directory, "
                "or pass --pubkey PATH."
            ),
        )

    last_err = ""
    for pub in pubkeys:
        cmd = [
            minisign,
            "-Vm",
            str(config),
            "-x",
            str(sig),
            "-p",
            str(pub),
        ]
        try:
            result = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            last_err = "minisign timed out"
            continue
        except OSError as exc:
            last_err = str(exc)
            continue

        if result.returncode == 0:
            return VerifyResult(
                ok=True,
                message=f"Signature verified with {pub.name}",
                pubkey_used=pub,
            )
        err = (result.stderr or result.stdout or "").strip()
        if err:
            last_err = err

    detail = f" Last minisign output: {last_err[:300]}" if last_err else ""
    return VerifyResult(
        ok=False,
        message=(
            "Signature invalid or signer not in the trusted key set."
            f"{detail}"
        ),
    )
