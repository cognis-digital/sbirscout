"""SBIRSCOUT command-line interface."""
from cognis_core import build_cli
from sbirscout.core import scan, TOOL_NAME, TOOL_VERSION

main = build_cli(
    tool_name=TOOL_NAME,
    tool_version=TOOL_VERSION,
    description="SBIR/STTR topic discovery — DSIP + SBIR.gov + NIH digest with bid scoring",
    scan_fn=scan,
)

if __name__ == "__main__":
    import sys
    sys.exit(main())
