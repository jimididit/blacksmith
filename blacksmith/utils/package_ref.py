"""Parse and compare package ID version pins (name|version)."""

from typing import Optional, Tuple


def parse_package_ref(ref: str) -> Tuple[str, Optional[str]]:
    """Split 'name|ver' -> (name, ver); bare name -> (name, None).

    Does not validate charset (caller uses validate_package_id first).
    """
    if "|" not in ref:
        return ref, None
    name, version = ref.split("|", 1)
    return name, version if version else None


def versions_equal(a: str, b: str) -> bool:
    """True if equal after stripping one leading 'v'/'V' from each; case-sensitive thereafter."""

    def norm(s: str) -> str:
        if s[:1] in ("v", "V") and len(s) > 1:
            return s[1:]
        return s

    return norm(a) == norm(b)
