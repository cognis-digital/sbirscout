"""Command-line interface for SBIRSCOUT."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from typing import List, Optional, Sequence

from . import TOOL_NAME, TOOL_VERSION
from .core import (
    ScoredTopic,
    SOURCES,
    _profile_from_raw,
    digest,
    load_topics,
)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def _build_profile(args: argparse.Namespace):
    if getattr(args, "profile", None):
        with open(args.profile, "r", encoding="utf-8") as fh:
            return _profile_from_raw(json.load(fh))
    caps = []
    if getattr(args, "capabilities", None):
        caps = [c.strip() for c in args.capabilities.split(",") if c.strip()]
    phases = ["I"]
    if getattr(args, "phases", None):
        phases = [p.strip() for p in args.phases.split(",") if p.strip()]
    return _profile_from_raw(
        {
            "capabilities": caps,
            "preferred_phases": phases,
            "has_research_partner": bool(getattr(args, "research_partner", False)),
            "min_award": float(getattr(args, "min_award", 0) or 0),
        }
    )


def _render_table(result: dict) -> str:
    lines: List[str] = []
    lines.append(f"SBIRSCOUT digest  generated={result['generated']}  topics={result['total_topics']}")
    rec = result["by_recommendation"]
    lines.append(
        f"  GO={rec.get('GO', 0)}  CONSIDER={rec.get('CONSIDER', 0)}  PASS={rec.get('PASS', 0)}"
    )
    if result["by_source"]:
        srcs = "  ".join(f"{k}:{v}" for k, v in result["by_source"].items())
        lines.append(f"  sources: {srcs}")
    lines.append("")
    lines.append(f"{'SCORE':>5}  {'REC':<8} {'PROG':<5} {'PH':<3} {'ID':<14} TITLE")
    lines.append("-" * 78)
    for t in result["topics"]:
        title = t["title"][:42]
        lines.append(
            f"{t['score']:>5.1f}  {t['bid_recommendation']:<8} {t['program']:<5} "
            f"{t['phase']:<3} {t['topic_id'][:14]:<14} {title}"
        )
        if t["reasons"]:
            lines.append(f"        - {'; '.join(t['reasons'])}")
    return "\n".join(lines)


def _cmd_scout(args: argparse.Namespace) -> int:
    topics = load_topics(args.input)
    if not topics:
        print("sbirscout: no topics found in input", file=sys.stderr)
        return 2
    profile = _build_profile(args)
    result = digest(topics, profile, today=_parse_date(args.today), top=args.top)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(_render_table(result))
    return 0


def _cmd_sources(args: argparse.Namespace) -> int:
    if args.format == "json":
        print(json.dumps(SOURCES, indent=2))
    else:
        for key, label in SOURCES.items():
            print(f"{key:<10} {label}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="SBIR/STTR topic discovery and bid scoring (DSIP + SBIR.gov + NIH).",
    )
    p.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    p.add_argument(
        "--format", choices=["table", "json"], default="table", help="output format"
    )
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("scout", help="rank topics from a digest file against a profile")
    s.add_argument("input", help="path to topics JSON ({'topics': [...]} or a list)")
    s.add_argument("--profile", help="path to capability-profile JSON")
    s.add_argument("--capabilities", help="comma-separated capability keywords")
    s.add_argument("--phases", help="comma-separated preferred phases (I,II,III,DIRECT_II)")
    s.add_argument("--research-partner", action="store_true", help="firm has an STTR research partner")
    s.add_argument("--min-award", type=float, default=0.0, help="minimum acceptable award ceiling")
    s.add_argument("--today", help="override today's date (YYYY-MM-DD) for deadline math")
    s.add_argument("--top", type=int, default=None, help="limit to top N results")
    s.set_defaults(func=_cmd_scout)

    src = sub.add_parser("sources", help="list supported normalized sources")
    src.set_defaults(func=_cmd_sources)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f"sbirscout: file not found: {e.filename}", file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as e:
        print(f"sbirscout: invalid input: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
