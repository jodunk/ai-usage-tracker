# Docker Debugging Commands Reference

**Purpose**: Quick reference for debugging Docker containerized services
**Context**: Grafana "No data" debugging session (2026-01-31)
**Scope**: Prometheus, Grafana, Exporter containers

---

## 🔍 Phase 1: Container Health Check

### Check Container Status
```bash
# List all containers with status
docker ps --filter "name=scudd" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Detailed status
docker ps -a | grep -E "prometheus|grafana|exporter"
```

**What it tells you**:
- Containers running? ✓
- Ports mapped correctly? ✓
- Health status? ✓

---

## 🌐 Phase 2: Network Connectivity

### Test Container-to-Container Communication
```bash
# From host - can you reach the service?
curl -s http://localhost:8000/metrics | head -5

# From Prometheus container - can it reach exporter?
docker exec scudd-prometheus wget -qO- http://scudd-exporter:8000/metrics | head -5

# From Grafana container - can it reach Prometheus?
docker exec scudd-grafana wget -qO- http://scudd-prometheus:9090/api/v1/status/config
```

**What it tells you**:
- Service responding on port? ✓
- DNS resolution working? ✓
- Container-to-container communication? ✓

**Common issues**:
- DNS fails → Check container network: `docker network inspect shannon-scud_scudd-network`
- Connection refused → Container not running or port wrong
- Timeout → Firewall or security group issue

---

## 📊 Phase 3: Service-Specific Checks

### Prometheus Target Health
```bash
# Check if Prometheus can scrape targets
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | grep -A 5 "health"

# Query specific metric
curl -s "http://localhost:9090/api/v1/query?query=scudd_tokens_total" | python3 -m json.tool

# Check last scrape time
curl -s http://localhost:9090/api/v1/targets | python3 -c "
import sys, json
targets = json.load(sys.stdin)['data']['activeTargets']
for t in targets:
    if 'scudd' in t['labels'].get('job', ''):
        print(f\"{t['labels']['job']}: {t['health']}, Last scrape: {t['lastScrape']}\")
"
```

**What it tells you**:
- Target up or down? ✓
- Last successful scrape time? ✓
- Error message if down? ✓

---

### Exporter Metrics Endpoint
```bash
# Get all metrics
curl -s http://localhost:8000/metrics

# Filter for specific metrics
curl -s http://localhost:8000/metrics | grep "^scudd_"

# Check specific metric
curl -s http://localhost:8000/metrics | grep "scudd_tokens_total"

# Count metrics
curl -s http://localhost:8000/metrics | grep "^scudd_" | wc -l
```

**What it tells you**:
- Metrics being exposed? ✓
- Which metrics exist? ✓
- Values (for gauges/counters)? ✓

---

### Grafana Datasource Health
```bash
# Test datasource connection
curl -s "http://localhost:3030/api/datasources" -u "admin:admin"

# Test query through datasource
curl -s "http://localhost:3030/api/datasources/proxy/1/api/v1/query?query=up" -u "admin:admin"
```

**What it tells you**:
- Datasource configured? ✓
- Prometheus reachable from Grafana? ✓
- Query working? ✓

---

## 📂 Phase 4: Volume Mount Verification

### Check Mounts Actually Exist
```bash
# Inspect container mounts
docker inspect scudd-exporter | python3 -c "
import sys, json
inspect = json.load(sys.stdin)
mounts = inspect[0]['Mounts']
for m in mounts:
    if 'psi' in m.get('Destination', ''):
        print(f\"Source: {m['Source']}\")
        print(f\"Destination: {m['Destination']}\")
        print(f\"Type: {m['Type']}\")
"

# Check if source directory exists on host
ls -la /Users/jodunk/Documents/Project/volt-oracle/ψ/active/ | head -5

# Check if mounted directory exists in container
docker exec scudd-exporter ls -la /app/psi/active/ | head -5
```

**What it tells you**:
- Mount configured correctly? ✓
- Source directory exists on host? ✓
- Files visible inside container? ✓

**Common issues**:
- **Empty directory in container** → Source path wrong (ψ vs psi, path doesn't exist)
- **Permission denied** → User ID mismatch, read-only mount
- **Mount not visible** → Container needs restart after mount change

---

## 🔧 Phase 5: Inside-Container Debugging

### File System Inspection
```bash
# List files in working directory
docker exec scudd-exporter ls -la /app/

# Check specific file
docker exec scudd-exporter cat /app/token-budget-config.yaml | head -20

# Check if file exists
docker exec scudd-exporter test -f /app/psi/active/token-metrics.jsonl && echo "EXISTS" || echo "NOT FOUND"

# Count lines in file
docker exec scudd-exporter wc -l /app/psi/active/token-metrics.jsonl
```

---

### Python Environment Check
```bash
# Python version
docker exec scudd-exporter python3 --version

# Python location
docker exec scudd-exporter which python3
docker exec scudd-exporter readlink -f /usr/local/bin/python3

# Python path
docker exec scudd-exporter python3 -c "import sys; print('\n'.join(sys.path))"

# Check installed packages
docker exec scudd-exporter pip list | grep -i yaml
```

**What it tells you**:
- Which Python interpreter? ✓
- Where is it located? ✓
- What's in sys.path? ✓
- Package installed? ✓

---

### Module Import Test
```bash
# Test import in isolation
docker exec scudd-exporter python3 -c "
import yaml
print('SUCCESS: yaml imported')
print(f'Version: {yaml.__version__}')
print(f'Location: {yaml.__file__}')
"

# Test with sys.path manipulation
docker exec scudd-exporter python3 -c "
import sys
sys.path.insert(0, '/app')
import yaml
print('SUCCESS with sys.path hack')
"

# Test loading actual module
docker exec scudd-exporter python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('test', '/app/prometheus_exporter.py')
module = importlib.util.module_from_spec(spec)
print(f'Module load: {module}')
"
```

**What it tells you**:
- Import works in isolation? ✓
- sys.path correct? ✓
- Module file loads? ✓

---

## 🐛 Phase 6: Runtime vs Import-Time Mystery

### Check Running Process
```bash
# Find process
docker exec scudd-exporter ps aux | grep python

# Check what's actually listening on port
docker exec scudd-exporter netstat -tlnp | grep 8000

# Test endpoint directly
curl -s http://localhost:8000/health

# Get metrics with debug info
curl -s http://localhost:8000/metrics | grep -B 2 -A 2 "Budget"
```

---

### Live Debugging (if possible)
```bash
# Check logs in real-time
docker logs -f scudd-exporter --tail 50

# Add debug print to code, then rebuild
# In prometheus_exporter.py:
import sys
print(f"DEBUG: sys.path = {sys.path}", file=sys.stderr)
print(f"DEBUG: yaml in sys.modules = {'yaml' in sys.modules}", file=sys.stderr)
```

---

## 🔨 Phase 7: Docker Build & Image

### Image Build Cycle
```bash
# Build image (no cache)
docker build --no-cache -f Dockerfile.exporter -t image:latest .

# Check image history
docker history shannon-scud-scudd-exporter:latest

# Inspect image
docker inspect shannon-scud-scudd-exporter:latest | grep -A 5 "Cmd"
```

### Container Restart Cycle
```bash
# Full cycle (rebuild + restart)
docker-compose -f scripts/shannon-scud/docker-compose.observability.yml build scudd-exporter
docker-compose -f scripts/shannon-scud/docker-compose.observability.yml up -d --force-recreate scudd-exporter

# Or manually:
docker stop scudd-exporter
docker rm scudd-exporter
docker run -d --name scudd-exporter [options] image:latest
```

**What it tells you**:
- Build succeeded? ✓
- Using latest code? ✓
- Container recreated (not restarted)? ✓

---

## 🎯 Phase 8: Query Testing

### Prometheus Queries
```bash
# Simple query
curl -s "http://localhost:9090/api/v1/query?query=up"

# Query with labels
curl -s "http://localhost:9090/api/v1/query?query=scudd_tokens_total"

# Range query
curl -s "http://localhost:9090/api/v1/query_range?query=scudd_tokens_total&start=2024-01-01T00:00:00Z&end=2024-01-31T23:59:59Z&step=1h"
```

### Grafana Query Workaround
```promql
# Daily Budget Usage (replaces scudd_budget_usage_percent)
(scudd_cost_usd_total / 5.0) * 100

# Budget Remaining (replaces scudd_budget_remaining_usd)
5.0 - scudd_cost_usd_total
```

---

## 📋 Quick Reference Card

### Health Check Commands
```bash
# All containers up?
docker ps --filter "name=scudd"

# Prometheus seeing exporter?
curl -s http://localhost:9090/api/v1/targets | grep scudd-oracle

# Exporter exposing metrics?
curl -s http://localhost:8000/metrics | grep scudd_tokens_total

# Volume mounted?
docker exec scudd-exporter ls /app/psi/active/token-metrics.jsonl

# PyYAML installed?
docker exec scudd-exporter python3 -c "import yaml; print(yaml.__version__)"
```

### Debugging Flow
```
1. Container status      → docker ps
2. Network connectivity  → docker exec wget/curl
3. Volume mounts        → docker exec ls -la /app/psi/active
4. Path calculation     → docker exec python3 -c "from pathlib import Path; ..."
5. Dependencies         → docker exec python3 -c "import yaml"
6. Runtime behavior     → curl http://localhost:8000/metrics
7. Workaround           → Grafana queries using existing metrics
```

---

## 💡 Pro Tips

### Fast Iteration
```bash
# Copy file to running container (no rebuild needed)
docker cp scripts/shannon-scud/prometheus_exporter.py scudd-exporter:/app/
docker restart scudd-exporter

# Or exec into container and edit
docker exec -it scudd-exporter bash
vi /app/prometheus_exporter.py
exit
docker restart scudd-exporter
```

### Clean Slate
```bash
# Remove all artifacts
docker stop container
docker rm container
docker rmi image
docker system prune -f

# Rebuild from scratch
docker-compose -f docker-compose.yml build --no-cache
docker-compose -f docker-compose.yml up -d
```

### Debug Commands Logging
```bash
# Log all commands to file for audit trail
set -x  # Enable command echo
script /tmp/debug-session.log
# ... run commands ...
exit
# View log
less /tmp/debug-session.log
```

---

## 📖 Related Documentation

### User Guides
- **[USER_GUIDE.md](USER_GUIDE.md)** - Token tracker commands, budget tiers, and usage
- **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)** - Complete Docker deployment guide with troubleshooting
- **[GRAFANA_PROVISIONING_GUIDE.md](GRAFANA_PROVISIONING_GUIDE.md)** - Dashboard setup, provisioning, and troubleshooting

### Session Documentation
- **[Retrospective: Grafana Budget Metrics Debug](../../ψ/memory/retrospectives/2026-01/31/12.07_grafana-budget-metrics-debug.md)** - Full debugging journey (26 min, 4 issues)
- **[Lesson Learned: Docker YAML Import Mystery](../../ψ/memory/learnings/2026-01-31_docker-yaml-import-mystery.md)** - Root cause analysis and patterns

### Quick Reference
- **[SHANNON-SCUD-PROGRESS.md](SHANNON-SCUD-PROGRESS.md)** - Implementation status by phase
- **[OBSERVABILITY-STACK.md](OBSERVABILITY-STACK.md)** - Architecture overview

---

**Last Updated**: 2026-01-31
**Session Context**: Grafana dashboard "No data" debugging
**Command Count**: 50+ commands across 8 debugging phases
