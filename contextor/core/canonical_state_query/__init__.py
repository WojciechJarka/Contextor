"""Stable façade for the canonical LIVE schema and projection runtime."""

from .contract import (
    LANGUAGE_V1,
    LANGUAGE_VERSION,
    SCHEMA_V1,
    CANONICAL_QUERY_SCHEMA_VERSION,
    describe_contract,
)
from .runtime import execute_projection, validate_request

__all__ = [
    "LANGUAGE_V1",
    "LANGUAGE_VERSION",
    "SCHEMA_V1",
    "CANONICAL_QUERY_SCHEMA_VERSION",
    "describe_contract",
    "execute_projection",
    "validate_request",
]
