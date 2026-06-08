# SBIRSCOUT — SBIR/STTR topic discovery — DSIP + SBIR.gov + NIH digest with bid scoring

> Part of the **[Cognis Neural Suite](https://github.com/cognis-digital)** by [Cognis Digital](https://cognis.digital)
> Cognis Open Collaboration License (COCL) v1.0 · domain: `federal`

[![PyPI](https://img.shields.io/pypi/v/cognis-sbirscout.svg)](https://pypi.org/project/cognis-sbirscout/)
[![CI](https://github.com/cognis-digital/sbirscout/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/sbirscout/actions)
[![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE)

SBIR/STTR topic discovery — DSIP + SBIR.gov + NIH digest with bid scoring.

## Install

```bash
pip install cognis-sbirscout
```

For local development from this repo:

```bash
pip install -e .
```

## Quick start

```bash
sbirscout --version
sbirscout scan demos/                          # run against bundled demo
sbirscout scan demos/ --format sarif --out r.sarif --fail-on high
sbirscout mcp                                   # start as MCP server (Cognis.Studio / Claude Desktop / Cursor)
```

## Built-in demo scenarios

Every scenario folder includes a `SCENARIO.md` describing what it represents and what findings to expect.

- `demos/01-ai-security-capability-match/` — see [`SCENARIO.md`](demos/01-ai-security-capability-match/SCENARIO.md)
- `demos/02-low-match-quiet-day/` — see [`SCENARIO.md`](demos/02-low-match-quiet-day/SCENARIO.md)
- `demos/03-deadline-emergency/` — see [`SCENARIO.md`](demos/03-deadline-emergency/SCENARIO.md)

## How it fits the Cognis Neural Suite

This tool is one of 52 in the [Cognis Neural Suite](https://github.com/cognis-digital). The full suite + launcher lives at:

- Suite landing: https://cognis.digital
- All 52 repos: https://github.com/cognis-digital
- Cognis.Studio (Enterprise AI Workforce, MCP host): https://cognis.studio

Every Suite tool ships an MCP server, so Cognis.Studio agents can call them as scoped capabilities.

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md) for the collaboration-pull model.

## About

**[Cognis Digital](https://cognis.digital)** — Wyoming, USA · *Making Tomorrow Better Today: Advanced Cybersecurity, AI Innovation, and Blockchain Expertise.*
