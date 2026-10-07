from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="VIBI Bank local demo applications")
    parser.add_argument(
        "interface",
        choices=("web", "desktop", "cli"),
        help="Choose the web, desktop, or command-line interface",
    )
    interface = parser.parse_args().interface
    if interface == "web":
        from .web import run
    elif interface == "desktop":
        from .desktop import run
    else:
        from .cli import run
    run()


if __name__ == "__main__":
    main()
