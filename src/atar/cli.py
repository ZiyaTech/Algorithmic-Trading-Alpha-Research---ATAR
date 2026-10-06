"""Command-line entry point. No credentials or network calls."""
import argparse
import json
from pathlib import Path
from atar.config import load_config
from atar.demo import DEFAULT_CONFIG, run_demo, compare_pinbar
from atar.synthetic import market


def main(argv=None):
    parser = argparse.ArgumentParser(prog="atar")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run the synthetic staged-research example")
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--config", type=Path)
    demo.add_argument("--seed", type=int)
    comp = sub.add_parser("compare-pinbar", help="Compare active synthetic signal events")
    comp.add_argument("--seed", type=int, default=2026)
    comp.add_argument("--bars", type=int, default=3200)
    args = parser.parse_args(argv)
    try:
        if args.command == "compare-pinbar":
            result = compare_pinbar(market(seed=args.seed, bars=args.bars))
        else:
            config = load_config(args.config) if args.config else json.loads(json.dumps(DEFAULT_CONFIG))
            if args.seed is not None:
                config["seed"] = args.seed
            result = run_demo(args.output, config)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, RuntimeError, OSError, TypeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
