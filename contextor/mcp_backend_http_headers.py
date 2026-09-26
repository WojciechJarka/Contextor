"""HTTP credential helper for the persistent Contextor MCP backend.

This module is intended to be executed as a local MCP HTTP-header helper.

It does not start, stop, probe, or otherwise own the persistent backend
lifecycle. Backend startup is independent of the MCP client.

The Authorization value is intentionally emitted only to stdout for the
calling MCP client. It must not be logged or persisted by this module.
"""

from __future__ import annotations

import json
import sys

from contextor.mcp_backend_secret import (
    BackendSecretError,
    get_or_create_backend_token,
)


class BackendHttpHeadersError(RuntimeError):
    """The persistent backend credential helper could not produce headers."""


def build_backend_http_headers() -> dict[str, str]:
    """Return the persistent backend bearer Authorization header."""

    token = (
        get_or_create_backend_token()
    )

    if not token:
        raise BackendHttpHeadersError(
            "persistent Contextor MCP backend bearer token is unavailable"
        )

    return {
        "Authorization": f"Bearer {token}",
    }


def main() -> int:
    """Emit the MCP HTTP header map for a local client."""

    try:
        headers = (
            build_backend_http_headers()
        )

    except (
        BackendSecretError,
        BackendHttpHeadersError,
    ) as exc:
        print(
            f"[ERROR] {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            headers,
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "BackendHttpHeadersError",
    "build_backend_http_headers",
    "main",
]
