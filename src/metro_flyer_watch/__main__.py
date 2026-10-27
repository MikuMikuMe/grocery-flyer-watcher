"""CLI to validate, compare and render public Metro flyer snapshots."""
import argparse
from .core import changed, read_snapshot, render_report


def main():
    parser = argparse.ArgumentParser(description="Metro Kingston flyer")
    parser.add_argument("command", choices=("validate", "report", "compare"))
    parser.add_argument("snapshot")
    parser.add_argument("previous", nargs="?")
    args = parser.parse_args()
    current = read_snapshot(args.snapshot)
    if args.command == "validate":
        print("Valid public snapshot")
    elif args.command == "report":
        print(render_report(current))
    else:
        if not args.previous:
            parser.error("compare needs a previous snapshot")
        print("CHANGED" if changed(read_snapshot(args.previous), current) else "UNCHANGED")


if __name__ == "__main__":
    main()
