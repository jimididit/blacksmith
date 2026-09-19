"""Create detached minisign signatures on set YAML files."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from blacksmith.trust.verify import default_signature_path


@dataclass
class SignResult:
    """Outcome of a minisign signing attempt."""

    ok: bool
    message: str
    signature_path: Optional[Path] = None


def sign_set(
    config_path: Path,
    *,
    signature_path: Optional[Path] = None,
    secret_key: Optional[Path] = None,
) -> SignResult:
    """
    Sign config_path with minisign, writing a detached .minisig.

    Uses the minisign CLI on PATH. Passphrase prompts (if any) go to the
    inherited TTY - Blacksmith does not capture passwords.
    """
    config = Path(config_path).expanduser().resolve()
    if not config.is_file():
        return SignResult(ok=False, message=f"Config file not found: {config}")

    sig = (
        Path(signature_path).expanduser().resolve()
        if signature_path
        else default_signature_path(config).resolve()
    )

    if secret_key is not None:
        key = Path(secret_key).expanduser().resolve()
        if not key.is_file():
            return SignResult(ok=False, message=f"Secret key not found: {key}")
    else:
        key = None

    minisign = shutil.which("minisign")
    if not minisign:
        return SignResult(
            ok=False,
            message=(
                "minisign not found on PATH. Install minisign to use "
                "'blacksmith sign' (e.g. scoop install minisign, "
                "brew install minisign, or your distro package)."
            ),
        )

    cmd: List[str] = [minisign, "-Sm", str(config), "-x", str(sig)]
    if key is not None:
        cmd.extend(["-s", str(key)])

    try:
        # Inherit stdio so minisign can prompt for a passphrase on a TTY.
        result = subprocess.run(
            cmd,
            shell=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return SignResult(ok=False, message="minisign timed out while signing")
    except OSError as exc:
        return SignResult(ok=False, message=f"Failed to run minisign: {exc}")

    if result.returncode != 0:
        return SignResult(
            ok=False,
            message=(
                f"minisign failed with exit {result.returncode}. "
                "Check the secret key path and passphrase, then retry."
            ),
        )

    if not sig.is_file():
        return SignResult(
            ok=False,
            message=f"minisign exited 0 but signature file missing: {sig}",
        )

    return SignResult(
        ok=True,
        message=(
            f"Signed {config.name} -> {sig}. "
            "Publish the .minisig beside the YAML (or as {url}.minisig)."
        ),
        signature_path=sig,
    )
