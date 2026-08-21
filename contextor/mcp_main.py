import multiprocessing


def main() -> None:
    from contextor.mcp_server import main as run_server

    run_server()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
