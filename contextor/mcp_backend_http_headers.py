"""HTTP header bridge for the persistent Contextor MCP backend.

This module is intended to be executed as a local MCP HTTP-header helper.
It starts or reuses the persistent backend and emits exactly one JSON
header map on stdout.

The Authorization value is intentionally emitted only to stdout for the
calling MCP client. It must not be logged or persisted by this module.
"""

from __future__ import annotations

import json
import sys

from contextor.mcp_backend_control import (
    BackendControlError,
    start_backend,
)
from contextor.mcp_backend_secret import (
    BackendSecretError,
    read_backend_token,
)


class BackendHttpHeadersError(RuntimeError):
    """The persistent backend HTTP-header bridge could not produce headers."""


def build_backend_http_headers() -> dict[str, str]:
    """Start/reuse the backend and return its bearer Authorization header."""

    status = start_backend(
        timeout=8.0,
        probe_timeout=1.0,
    )

    if not status.ready:
        raise BackendHttpHeadersError(
            "persistent Contextor MCP backend is not ready"
        )

    token = read_backend_token()

    if token is None:
        raise BackendHttpHeadersError(
            "persistent Contextor MCP backend bearer token is unavailable"
        )

    return {
        "Authorization": f"Bearer {token}",
    }


def main() -> int:
    """Emit the MCP HTTP header map for a local client."""

    try:
        headers = build_backend_http_headers()
    except (
        BackendControlError,
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
