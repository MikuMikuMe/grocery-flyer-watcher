"""CLI contract for humans, cron, systemd and coding agents."""
import argparse
import json
import sys
from .core import changed, read_snapshot, render_report
from .runner import load_config, run, seed


def main():
    parser = argparse.ArgumentParser(prog="grocery-flyer-watch")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "report"):
        sub.add_parser(name).add_argument("snapshot")
    compare = sub.add_parser("compare")
    compare.add_argument("snapshot")
    compare.add_argument("previous")
    for name in ("run", "seed"):
        p = sub.add_parser(name)
        p.add_argument("--config", required=True)
        p.add_argument("--input", required=name == "seed")
        if name == "run":
            p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "run":
            reports = run(load_config(args.config), args.input, args.dry_run)
            if reports:
                print("\n\n".join(reports))
        elif args.command == "seed":
            seed(load_config(args.config), read_snapshot(args.input))
            print("Baseline imported without publication or delivery")
        else:
            snapshot = read_snapshot(args.snapshot)
            if args.command == "validate":
                print("Valid public snapshot")
            elif args.command == "report":
                print(render_report(snapshot))
            else:
                print("CHANGED" if changed(read_snapshot(args.previous), snapshot) else "UNCHANGED")
        return 0
    except Exception as exc:
        # External errors can contain private recipients, credentials, or command output.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__,
                          "hint": "Check config, source verification, private state and adapter access; details suppressed."}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
