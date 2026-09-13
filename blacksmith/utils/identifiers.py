"""Safe package ID and search-query validation for subprocess argv use."""

import re
from typing import Optional, Tuple

# Package IDs become argv elements (shell=False). Allow common PM ID shapes:
# apt/pacman (git, testssl.sh), winget (Publisher.Package), flatpak (org.foo.Bar).
# Optional Chocolatey pin: name|version where version starts with a digit.
# Reject leading '-' (flag injection) and shell/cmd metacharacters.
_PACKAGE_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._+\-@/:]*"
    r"(?:\|[0-9][A-Za-z0-9._+\-]*)?$"
)

# Search queries may include spaces; still reject shell metacharacters.
_SEARCH_META_RE = re.compile(r"[&|;`$<>(){}!\\\n\r\"']")
_MAX_SEARCH_LEN = 200


def validate_package_id(package_id: str) -> Tuple[bool, Optional[str]]:
    """
    Return (ok, error_message) for a manager-specific package ID.

    Safe for use as a subprocess argv element without a shell.
    """
    if not isinstance(package_id, str) or not package_id.strip():
        return False, "Package ID must be a non-empty string"
    if package_id != package_id.strip():
        return False, f"Package ID has leading/trailing whitespace: {package_id!r}"
    if package_id.startswith("-"):
        return False, f"Package ID must not start with '-': {package_id!r}"
    if not _PACKAGE_ID_RE.fullmatch(package_id):
        return False, (
            f"Package ID contains disallowed characters: {package_id!r}. "
            "Allowed: letters, digits, ._-+@/: and optional |version"
        )
    return True, None


def validate_search_query(query: str) -> Tuple[bool, Optional[str]]:
    """Return (ok, error_message) for a package-manager search query."""
    if not isinstance(query, str) or not query.strip():
        return False, "Search query must be a non-empty string"
    if query.startswith("-"):
        return False, f"Search query must not start with '-': {query!r}"
    if len(query) > _MAX_SEARCH_LEN:
        return False, f"Search query exceeds {_MAX_SEARCH_LEN} characters"
    if _SEARCH_META_RE.search(query):
        return False, f"Search query contains disallowed characters: {query!r}"
    return True, None


def is_safe_package_id(package_id: str) -> bool:
    """True if package_id passes validate_package_id."""
    ok, _ = validate_package_id(package_id)
    return ok


def is_safe_search_query(query: str) -> bool:
    """True if query passes validate_search_query."""
    ok, _ = validate_search_query(query)
    return ok
