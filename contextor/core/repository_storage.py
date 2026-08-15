"""Dependency-neutral location of Contextor's central repository registry."""

from __future__ import annotations

import os
from pathlib import Path


def repository_registry_root() -> Path:
    """Return the central registry without importing higher-level path logic."""

    configured = os.environ.get("CONTEXTOR_REGISTRY_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    installation_root = Path(__file__).resolve().parents[2]
    return installation_root / ".contextor" / "repositories"


__all__ = ["repository_registry_root"]
