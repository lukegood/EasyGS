"""Helpers for locating EasyGS resources."""

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_ROOT.parent


def resolve_bundled_path(*relative_parts: str) -> Path:
    """Return a bundled resource path for installed or source checkouts."""
    package_candidate = _PACKAGE_ROOT.joinpath(*relative_parts)
    if package_candidate.exists():
        return package_candidate

    repo_candidate = _REPO_ROOT.joinpath(*relative_parts)
    if repo_candidate.exists():
        return repo_candidate

    if _PACKAGE_ROOT.joinpath(relative_parts[0]).exists():
        return package_candidate
    return repo_candidate


def resolve_software_path(name: str) -> Path:
    """Return a software asset path from the package or repo root."""
    return resolve_bundled_path("softwares", name)


def resolve_user_resources_root() -> Path:
    """Return the user-managed resources root.

    EASYGS_RESOURCES_DIR can be set to point at a different resource root.
    EASYGS_RESOURCE_DIR is also honored as a compatibility alias.
    """
    configured = os.environ.get("EASYGS_RESOURCES_DIR") or os.environ.get("EASYGS_RESOURCE_DIR")
    return Path(configured or "~/.easygs/resources").expanduser()


def resolve_user_resource_path(*relative_parts: str) -> Path:
    """Return a user-managed resource path under ~/.easygs/resources."""
    return resolve_user_resources_root().joinpath(*relative_parts)
