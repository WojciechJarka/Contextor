import multiprocessing
import os
import sys


def main() -> None:
    if sys.platform == "win32":
        from contextor.mcp_backend_job import (
            protect_host_owned_mcp,
            protect_persistent_backend,
        )

        role = os.environ.get(
            "CONTEXTOR_MCP_SERVER_ROLE",
            "host-owned",
        ).strip().lower()

        if role == "persistent-backend":
            protect_persistent_backend()
        elif role == "host-owned":
            protect_host_owned_mcp()

    from contextor.mcp_server import main as run_server

    run_server()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
