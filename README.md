# AI Usage Tracker (Shannon Scud)

> "Observe the unseen — every token counts."

**Version**: 0.1.0
**Status**: Phase 2B Complete
**License**: MIT

---

## What is AI Usage Tracker?

**AI Usage Tracker** (formerly Shannon Scud) is a comprehensive token usage observability stack for Claude Code sessions. It tracks, monitors, and visualizes AI token consumption across development work.

### Purpose

- 📊 **Track token usage** — Every Claude Code session automatically tracked
- 💰 **Monitor costs** — Real-time cost calculation by model and task type
- 📈 **Visualize trends** — Grafana dashboards for usage patterns
- ⚠️ **Budget alerts** — Warning when approaching daily token limits

### Origins

Originally developed as part of **Volt Oracle** (Scudd's research Oracle), AI Usage Tracker is now an independent, open-source tool for anyone tracking Claude Code usage.

---

## Quick Start

### 1. Track Tokens (Daily Usage)

```bash
# Record token usage
cd ~/Documents/Project/ai-usage-tracker
python3 token-tracker.py record \
  --task-type debugging \
  --model claude-sonnet-4-5 \
  --input-tokens 15000 \
  --output-tokens 5000
```

### 2. Deploy with Docker

```bash
# Start observability stack
docker-compose -f docker-compose.observability.yml up -d

# Access Grafana
open http://localhost:3030
```

### 3. Integrate with VSCode Plugin

**Stop Hook** (automatic token tracking):
```bash
# Install to ~/.claude/plugins/ai-usage-tracker/
./scripts/deploy-to-plugins.sh
```

---

## Architecture

```
┌─────────────────┐
│ Claude Code     │
│ Session         │
└────────┬────────┘
         │
         │ Stop Hook (auto)
         ↓
┌─────────────────┐
│ Token Tracker   │ ← Records usage
│ (Python)        │   to token-metrics.jsonl
└────────┬────────┘
         │
         ↓
┌�─────────────────┐
│ Prometheus      │ ← Scrapes /metrics endpoint
│ Exporter        │   every 15 seconds
└────────┬────────┘
         │
         ├───────────┐
         ↓           ↓
┌──────────────┐ ┌─────────────┐
│ Prometheus  │ │  Grafana    │ ← Visualization
│ (TSDB)       │ │  (Dashboards)│
└──────────────┘ └─────────────┘
```

---

## Documentation

### User Guides
- **[USER_GUIDE.md](USER_GUIDE.md)** — Token tracking commands, budget tiers
- **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)** — Docker deployment guide
- **[DOCKER_DEBUG_COMMANDS.md](DOCKER_DEBUG_COMMANDS.md)** — Troubleshooting reference

### Architecture & Status
- **[OBSERVABILITY-STACK.md](OBSERVABILITY-STACK.md)** — Architecture overview
- **[GRAFANA_PROVISIONING_GUIDE.md](GRAFANA_PROVISIONING_GUIDE.md)** — Dashboard setup
- **[SHANNON-SCUD-PROGRESS.md](SHANNON-SCUD-PROGRESS.md)** — Implementation status

### Knowledge Base (Shared with Volt Oracle)
- **Public Learnings** — Generic patterns (Docker, Python, Git)
- **Retrospectives** — Development narratives

---

## Features

### ✅ Implemented (Phase 1-2B)

- **Phase 1**: Manual token tracking via CLI
- **Phase 2A**: Prometheus exporter with /metrics endpoint
- **Phase 2B**: Grafana dashboards with auto-provisioning

### 🚧 Planned (Phase 3-4)

- **Phase 3**: Budget alerts (Slack/email on threshold)
- **Phase 4**: MCP server for real-time budget checking

---

## Installation

### From Source

```bash
# Clone repository
git clone https://github.com/jodunk/ai-usage-tracker.git
cd ai-usage-tracker

# Install dependencies
pip install -r requirements.txt  # (when available)
```

### VSCode Plugin (Coming Soon)

```bash
# Install as VSCode extension
cp -r . ~/.claude/plugins/ai-usage-tracker/

# Reload VSCode window
# Code → Reload Window
```

---

## Configuration

### Token Budget Tiers

| Tier | Daily Limit (USD) | Alerts |
|------|------------------|--------|
| Standard | $5.00 | 80% ($4.00), 100% ($5.00) |
| Pro | $20.00 | 80% ($16.00), 100% ($20.00) |
| Enterprise | $100.00 | 80% ($80.00), 100% ($100.00) |

**Config**: `token-budget-config.yaml`

---

## Development

### Project Structure

```
ai-usage-tracker/
├── token-tracker.py        # Core tracker CLI
├── prometheus_exporter.py  # Metrics HTTP server
├── token-budget-config.yaml # Budget configuration
├── docker-compose.observability.yml
├── docs/                    # User guides
│   ├── PATTERNS/          # Public learnings
│   └── ...
└── grafana/                # Dashboards
    ├── grafana-dashboard.json
    └── grafana-datasource.yml
```

### Contributing

Contributions welcome! Please read:
- [CONTRIBUTING.md](CONTRIBUTING.md) (coming soon)
- [Code of Conduct](CODE_OF_CONDUCT.md) (coming soon)

---

## Knowledge Sharing

This project shares **public learnings** with the community. Generic patterns (Docker, debugging, Python) are documented in `docs/PATTERNS/` and synced from Volt Oracle's knowledge base.

### Public Learnings

- **[Docker YAML Import Mystery](docs/PATTERNS/2026-01-31_docker-yaml-import-mystery.md)** — Module import failures in containers
- **[VSCode Stop Hook Token Tracking](docs/PATTERNS/2026-01-31_vscode-stop-hook-token-tracking.md)** — Automatic session tracking

---

## Related Projects

- **[Volt Oracle](https://github.com/jodunk/volt-oracle)** — Research Oracle that spawned this tool
- **[Oracle Framework](https://github.com/Soul-Brews-Studio/oracle-framework)** — Philosophy behind Nothing is Deleted

---

## License

MIT License - see [LICENSE](LICENSE) file for details

---

## Credits

**Created by**: Scudd (Volt Oracle)
**Born**: 24 January 2026
**Extracted**: 31 January 2026

Oracle Principle: **Nothing is Deleted** — All token usage preserved for time-travel debugging.

---

**Last Updated**: 2026-01-31
**Version**: 0.1.0
**Status**: ✅ Ready for Use
