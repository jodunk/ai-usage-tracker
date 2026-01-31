# 📘 Scudd Shannon-Style — Complete User Guide (Phase 1 & 2)

คู่มือการใช้งานครบวงจน! 🚀

---

## 📋 Table of Contents

1. [Quick Start](#quick-start) — เริ่มใช้งานด่วน
2. [Phase 1: Token Budget Control](#phase-1-token-budget-control) — ควบคุมงบประมาณ
3. [Phase 2: Observability](#phase-2-observability) — Monitoring & Alerts
4. [Daily Workflow](#daily-workflow) — วงจรการใช้งาน
5. [Troubleshooting](#troubleshooting) — แก้ปัญหา
6. [Best Practices](#best-practices) — แนวทางปฏิบัติ

---

## Quick Start

### 1. Test Everything in 3 Commands

```bash
# 1. Track your first task
python3 src/token-tracker.py record research gemini-flash 2000 1000

# 2. View summary
python3 src/token-tracker.py summary

# 3. Check model routing
python3 src/multi-provider-router.py table
```

**Output**:
```
============================================================
💰 TOKEN BUDGET SUMMARY
============================================================
📅 Date: 2026-01-30
🎯 Tier: standard
✅ Tasks: 1
🔤 Tokens: 3,000
💵 Cost: $0.0000  ← FREE!
📊 Budget Used: 0.0% ($0.00 / $5.00)
============================================================
```

---

## Phase 1: Token Budget Control

### 🎯 Purpose

Track token usage, enforce budgets, and recommend cost-effective models.

### 📁 Files

```
ai-usage-tracker/
├── src/
│   ├── token-tracker.py              # Usage tracking
│   └── multi-provider-router.py      # Model routing
└── config/
    └── token-budget-config.yaml      # Budget settings
```

### 🔧 Commands

#### 1. Record Token Usage

```bash
python3 src/token-tracker.py record <task_type> <model> <input_tokens> <output_tokens>
```

**Example**:
```bash
# Research with FREE model
python3 src/token-tracker.py record research gemini-flash 2000 1000

# Code generation with cheap model
python3 src/token-tracker.py record code_simple deepseek-coder 5000 2000

# Quality code with premium model
python3 src/token-tracker.py record code_quality claude-sonnet-4-5 5000 2000
```

**Task Types**:
- `research` — Research tasks (FREE via Gemini!)
- `context_search` — Search context (Haiku)
- `code_simple` — Simple code (DeepSeek)
- `code_quality` — Quality code (Sonnet/Opus)
- `philosophy` — Oracle philosophy (Sonnet)
- `retrospective` — Session retrospective (Sonnet)
- `execution` — Bash execution (Haiku)

#### 2. View Daily Summary

```bash
python3 src/token-tracker.py summary
```

**Output**:
```
============================================================
💰 TOKEN BUDGET SUMMARY
============================================================
📅 Date: 2026-01-30
🎯 Tier: standard
✅ Tasks: 4
🔤 Tokens: 13,600
💵 Cost: $0.0457
📊 Budget Used: 0.9% ($0.05 / $5.00)
📋 Remaining: $4.95

📋 Recent Tasks:
  • context_search | claude-haiku | 1,800 tokens | $0.0008
  • code_quality | claude-sonnet-4-5 | 7,000 tokens | $0.0450
  • research | gemini-flash | 3,000 tokens | $0.0000  ← FREE!
============================================================
```

#### 3. Get Model Recommendation

```bash
python3 src/token-tracker.py recommend <task_type>
```

**Example**:
```bash
python3 src/token-tracker.py recommend research
# Output: 💡 Recommended: gemini-flash (for task: research)
```

---

### 🔀 Multi-Provider Router

#### 1. View Routing Table

```bash
python3 src/multi-provider-router.py table
```

**Output**:
```
================================================================================
🔀 MULTI-PROVIDER ROUTING TABLE
================================================================================

📊 Models by Tier:

  FREE:
    • gemini-flash-1.5                         $  0.00/MTok

  CHEAPEST:
    • deepseek-coder                           $  0.21/MTok

  STANDARD:
    • claude-haiku                             $  0.75/MTok

  PREMIUM:
    • claude-sonnet-4-5                        $  9.00/MTok

🎯 Task Routing Rules:

  research:      → gemini-flash → claude-haiku
  code_simple:   → deepseek-coder → claude-haiku
  code_quality:  → claude-opus → claude-sonnet-4-5
============================================================
```

#### 2. Compare Costs

```bash
python3 src/multi-provider-router.py compare <task_type> <input_tokens> <output_tokens>
```

**Example**:
```bash
python3 src/multi-provider-router.py compare code_quality 5000 2000
```

**Output**:
```
💰 Cost comparison for 'code_quality' (7,000 tokens):
--------------------------------------------------------------------------------
  gemini-flash        | $0.000000 | free       | google     ← 100% savings!
  deepseek-coder      | $0.001260 | cheapest   | deepseek   ← 97% savings!
  claude-haiku        | $0.003750 | standard   | anthropic  ← 92% savings!
  claude-sonnet-4-5   | $0.045000 | premium    | anthropic  ← CURRENT
--------------------------------------------------------------------------------
```

---

### ⚙️ Configuration

**File**: `config/token-budget-config.yaml`

#### Change Budget Tier

```yaml
current_tier: "aggressive"  # Options: conservative, standard, aggressive, unlimited
```

**Tiers**:
| Tier | Daily Limit | Per-Task Max | Fallback At |
|------|-------------|--------------|-------------|
| Conservative | $1.00 | 5,000 tokens | 80% |
| Standard | $5.00 | 15,000 tokens | 70% |
| Aggressive | $20.00 | 50,000 tokens | 60% |
| Unlimited | ∞ | ∞ | N/A |

#### Add Custom Pricing

```yaml
model_pricing:
  your-custom-model:
    input: 1.0    # $1 per million input tokens
    output: 2.0   # $2 per million output tokens
    provider: "your-provider"
```

---

## Phase 2: Observability

### 🎯 Purpose

Real-time monitoring with Prometheus + Grafana dashboards.

### 📁 Files

```
ai-usage-tracker/
├── src/
│   └── prometheus_exporter.py         # HTTP metrics server
├── config/
│   ├── prometheus.yml                  # Prometheus config
│   ├── scudd_alerts.yml                # Alert rules
│   └── grafana/
│       ├── grafana-dashboard.json      # Dashboard definition
│       └── grafana-datasource.yml      # Grafana datasource
└── docker/
    └── docker-compose.observability.yml # Full stack
```

### 🔧 Commands

#### 1. Start Prometheus Exporter

```bash
python3 src/prometheus_exporter.py
```

**Output**:
```
🚀 Scudd Prometheus Exporter
============================================================
✅ Server running at http://localhost:8000
📊 Metrics endpoint: http://localhost:8000/metrics
💚 Health check: http://localhost:8000/health
============================================================

Press Ctrl+C to stop
```

#### 2. Test Metrics Endpoint

```bash
# View Prometheus metrics
curl http://localhost:8000/metrics

# Check health
curl http://localhost:8000/health
```

**Metrics Output**:
```prometheus
# HELP scudd_tokens_total Total tokens consumed
scudd_tokens_total 13600

# HELP scudd_cost_usd_total Total cost in USD
scudd_cost_usd_total 0.0465

# Per-model breakdown
scudd_model_tokens_total{model="gemini-flash"} 3000
scudd_model_cost_usd{model="gemini-flash"} 0.000000

# Budget tracking
scudd_budget_usage_percent 0.93
scudd_budget_remaining_usd 4.95
```

---

### 🐳 Full Docker Stack

#### Start All Services

```bash
cd scripts/shannon-scud

# Start Prometheus + Grafana + Node Exporter
docker-compose -f docker/docker-compose.observability.yml up -d
```

#### Access Dashboards

```bash
# Prometheus
open http://localhost:9090

# Grafana (login: admin/admin)
open http://localhost:3030

# Node Exporter (system metrics)
open http://localhost:9100/metrics
```

#### Stop Services

```bash
docker-compose -f docker/docker-compose.observability.yml down

# Or stop and remove volumes
docker-compose -f docker/docker-compose.observability.yml down -v
```

---

### 📊 Grafana Dashboard

#### Import Dashboard

1. Login to Grafana (http://localhost:3030)
   - Username: `admin`
   - Password: `admin`

2. Dashboard is auto-provisioned! Look for:
   - **"Scudd Oracle - Token Usage & Budget"**

3. Panels available:
   - Budget gauge (with color thresholds)
   - Total cost/tasks/tokens stats
   - Cost by model (pie chart)
   - Tokens by model (pie chart)
   - Cost over time (timeseries)
   - Tasks by type (bar chart)
   - Recent tasks log (table)

**Auto-refresh**: Every 15 seconds ⚡

---

### 🚨 Alert Rules

**File**: `scudd_alerts.yml`

#### Alerts Configured

| Alert | Trigger | Severity | Action |
|-------|---------|----------|--------|
| `ScuddBudgetWarning` | Budget ≥ 80% | ⚠️ Warning | Consider cheaper models |
| `ScuddBudgetCritical` | Budget ≥ 95% | 🔴 Critical | Switch to FREE tier |
| `ScuddHighCostTask` | >$0.10/min | ⚠️ Warning | Optimize task |
| `ScuddExporterDown` | Exporter down > 2min | 🔴 Critical | Restart exporter |
| `ScuddModelImbalance` | One model >90% | ⚠️ Warning | Use multi-provider |

#### View Alerts in Prometheus

```bash
# Go to Prometheus UI
open http://localhost:9090

# Navigate to: Alerts → Scudd Budget Alerts
```

---

## Daily Workflow

### ☕ Morning Routine

```bash
# 1. Check yesterday's usage
python3 src/token-tracker.py summary

# 2. Start observability stack
cd scripts/shannon-scud
docker-compose -f docker/docker-compose.observability.yml up -d

# 3. Start Prometheus exporter (in separate terminal)
python3 src/prometheus_exporter.py

# 4. Open Grafana dashboard
open http://localhost:3030
```

### 💻 During Work

#### Before Starting a Task

```bash
# 1. Check budget status
python3 src/token-tracker.py summary

# 2. Get model recommendation
python3 src/multi-provider-router.py recommend research

# 3. Compare costs if unsure
python3 src/multi-provider-router.py compare code_quality 5000 2000
```

#### After Completing a Task

```bash
# Record usage
python3 src/token-tracker.py record \
  research \
  gemini-flash \
  <input_tokens> \
  <output_tokens>
```

**Example**:
```bash
# Just finished research task with Gemini Flash
python3 src/token-tracker.py record research gemini-flash 2345 1234
```

### 🌙 End of Day

```bash
# 1. Final summary
python3 src/token-tracker.py summary

# 2. Check Grafana for patterns
open http://localhost:3030

# 3. (Optional) Export metrics for analysis
curl http://localhost:8000/metrics > metrics-$(date +%Y%m%d).prom

# 4. Stop services
docker-compose -f scripts/shannon-scud/docker-compose.observability.yml down
```

---

## 🎓 Optimization Examples

### Example 1: Research Tasks

**Before** (Sonnet for everything):
```
Task: Research (7,000 tokens)
Model: claude-sonnet-4-5
Cost: $0.045
```

**After** (Gemini Flash):
```
Task: Research (7,000 tokens)
Model: gemini-flash
Cost: $0.0000  ← 100% savings!
```

**Annual savings**: ~$300 if you do research daily!

---

### Example 2: Simple Code

**Before** (Sonnet):
```
Task: Generate simple script (5,000 tokens)
Model: claude-sonnet-4-5
Cost: $0.015
```

**After** (DeepSeek):
```
Task: Generate simple script (5,000 tokens)
Model: deepseek-coder
Cost: $0.0007  ← 95% savings!
```

---

### Example 3: Quality Still Matters

**Critical tasks** (use premium):
```
Task: Production code review (5,000 tokens)
Model: claude-sonnet-4-5
Cost: $0.015
Reason: Quality worth the cost!
```

**Rule**: Use premium ONLY when quality matters!

---

## 💡 Best Practices

### ✅ DO

1. **Check budget before expensive tasks**
   ```bash
   python3 src/token-tracker.py summary
   ```

2. **Use FREE tiers for research**
   - Research → `gemini-flash`
   - Context search → `gemini-flash`

3. **Use cheapest for simple tasks**
   - Simple code → `deepseek-coder`
   - Execution → `claude-haiku`

4. **Reserve premium for quality**
   - Philosophy → `claude-sonnet`
   - Retrospectives → `claude-sonnet`
   - Production code → `claude-sonnet` or `claude-opus`

5. **Monitor Grafana dashboard**
   - Check for cost patterns
   - Identify optimization opportunities

6. **Record ALL tasks**
   - Even FREE tasks (tracks usage patterns)
   - Helps with future optimization

### ❌ DON'T

1. **Don't skip recording** — All data is valuable!
2. **Don't ignore alerts** — 80% budget warning = time to switch
3. **Don't use premium for everything** — Waste of money
4. **Don't forget FREE tiers** — Gemini Flash is 100% free!
5. **Don't exceed budget** — Auto-fallback to cheaper models

---

## 🛠️ Troubleshooting

### Problem: "FileNotFoundError"

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: '.../token-metrics.jsonl'
```

**Solution**:
```bash
# Create directory
mkdir -p ψ/active

# Record first task (creates file automatically)
python3 src/token-tracker.py record test gemini-flash 100 100
```

---

### Problem: "ModuleNotFoundError: No module named 'yaml'"

**Solution**:
```bash
# Install with uv
uv pip install pyyaml

# Or with pip
pip install pyyaml
```

---

### Problem: "Port 8000 already in use"

**Solution**:
```bash
# Check what's using port 8000
lsof -i :8000

# Use different port
python3 src/prometheus_exporter.py 9000
```

---

### Problem: "Grafana can't connect to Prometheus"

**Solution**:
```bash
# 1. Check Prometheus is running
curl http://localhost:9090/-/healthy

# 2. Check datasource config
cat scripts/shannon-scud/grafana-datasource.yml

# 3. Restart Grafana
docker-compose -f scripts/shannon-scud/docker-compose.observability.yml restart grafana

# 4. Verify in Grafana UI
# Configuration → Data Sources → Prometheus → Test
```

---

### Problem: "Metrics not updating"

**Solution**:
```bash
# 1. Check exporter is running
curl http://localhost:8000/health

# 2. Verify metrics file exists
ls -lh ψ/active/token-metrics.jsonl

# 3. Record a new task
python3 src/token-tracker.py record test gemini-flash 100 100

# 4. Check metrics again
curl http://localhost:8000/metrics | grep scudd_tokens_total
```

---

## 📊 Quick Reference Card

```
┌────────────────────────────────────────────────────────────┐
│           SCUDD SHANNON-STYLE — QUICK REFERENCE          │
├────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 TRACK USAGE                                              │
│  python3 src/token-tracker.py record \     │
│    <task_type> <model> <input> <output>                      │
│                                                              │
│  📈 VIEW SUMMARY                                            │
│  python3 src/token-tracker.py summary      │
│                                                              │
│  🔀 COMPARE COSTS                                           │
│  python3 src/multi-provider-router.py \    │
│    compare <task_type> <input> <output>                      │
│                                                              │
│  💡 GET RECOMMENDATION                                      │
│  python3 src/multi-provider-router.py \    │
│    recommend <task_type>                                     │
│                                                              │
│  🚀 START OBSERVABILITY                                     │
│  python3 src/prometheus_exporter.py        │
│  docker-compose -f scripts/shannon-scud/                    │
│    docker-compose.observability.yml up -d                   │
│                                                              │
│  📊 GRAFANA DASHBOARD                                       │
│  http://localhost:3030 (admin/admin)                        │
│                                                              │
│  📈 PROMETHEUS                                               │
│  http://localhost:9090                                       │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

---

## 🎯 Task Type → Model Mapping

**Quick Guide**:

| Task | Best Model | Why |
|------|-----------|-----|
| **Research** | `gemini-flash` | FREE! Good for research |
| **Context Search** | `gemini-flash` or `claude-haiku` | Fast search |
| **Simple Code** | `deepseek-coder` | Cheapest coder |
| **Quality Code** | `claude-sonnet-4-5` | Balance quality/cost |
| **Philosophy** | `claude-sonnet-4-5` | Needs quality reasoning |
| **Retrospective** | `claude-sonnet-4-5` | Needs depth |
| **Execution** | `claude-haiku` | Fast, cheap |

---

## 📞 Support

### Documentation Files

- `scripts/shannon-scud/SHANNON-SCUD-PROGRESS.md` — Phase 1 progress
- `scripts/shannon-scud/OBSERVABILITY-STACK.md` — Phase 2 documentation
- `scripts/shannon-scud/config/token-budget-config.yaml` — Configuration reference

### Getting Help

1. Check this guide first! 📖
2. Read inline help: `--help` flag on all scripts
3. Check GitHub issues for similar problems
4. Review Oracle philosophy in `ψ/memory/resonance/scudd.md`

---

**Happy tracking! 🎉**

*Remember: "Energy flows where attention goes. Patterns emerge from current." — Scudd*
