import multiprocessing
import os
import sys


def main() -> None:
    if (
        sys.platform == "win32"
        and os.environ.get("CONTEXTOR_MCP_SERVER_ROLE")
        == "persistent-backend"
    ):
        from contextor.mcp_backend_job import (
            protect_persistent_backend,
        )

        protect_persistent_backend()

    from contextor.mcp_server import main as run_server

    run_server()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
