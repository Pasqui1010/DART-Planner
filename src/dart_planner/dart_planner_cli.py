import argparse
import os
import sys
from config.settings import get_config

# Import main entry points
from dart_planner.cloud.main import main as cloud_main
from dart_planner.edge.main import main as edge_main

def run(mode: str):
    config = get_config()
    print(f"Loaded config: {config}")
    if mode == "cloud":
        print("[DART-Planner] Running in CLOUD mode.")
        # cloud_main is async
        import asyncio
        asyncio.run(cloud_main())
    elif mode == "edge":
        print("[DART-Planner] Running in EDGE mode.")
        edge_main()
    else:
        print(f"Unknown mode: {mode}. Must be 'cloud' or 'edge'.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Unified DART-Planner CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the planner stack")
    run_parser.add_argument(
        "--mode",
        choices=["cloud", "edge"],
        required=True,
        help="Which mode to run: cloud or edge",
    )

    args = parser.parse_args()

    if args.command == "run":
        run(args.mode)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    # Print deprecation warning for old main*.py files
    print("[DEPRECATION WARNING] Please use 'dart planner run --mode=cloud|edge' instead of per-directory main.py files.")
    main() 
