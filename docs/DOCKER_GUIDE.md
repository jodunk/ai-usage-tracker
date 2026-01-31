# Docker Deployment Guide - Scudd Oracle Observability Stack

## อะไรใหม่ใน Docker?

**ก่อนหน้านี้**: รัน exporter บน host machine (port 8000, 8001)
**ตอนนี้**: รันทั้งหมดใน Docker containers!

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │  scudd-exporter  │  │    Prometheus    │  │  Grafana   │ │
│  │  :8000 (metrics) │──│ :9090 (scrape)   │──│ :3030     │ │
│  │  :8001 (SSE)     │  │                  │  │           │ │
│  └──────────────────┘  └──────────────────┘  └───────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Build & Start All Services

```bash
cd scripts/shannon-scud

# Build images & start containers
docker-compose -f docker/docker-compose.observability.yml up -d --build
```

**Output:**
```
✅ Successfully built scudd-exporter
✅ Created scudd-prometheus
✅ Created scudd-grafana
✅ Created scudd-exporter
```

### 2. Verify Services

```bash
# Check all containers running
docker-compose -f docker/docker-compose.observability.yml ps

# Check exporter health
curl http://localhost:8000/health

# Check Prometheus targets
curl -s localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

**Expected:**
```json
{"job": "prometheus", "health": "up"}
{"job": "scudd-oracle", "health": "up"}
```

### 3. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana Dashboard** | http://localhost:3030 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Exporter Metrics** | http://localhost:8000/metrics | - |
| **SSE Events** | http://localhost:8001/events | - |
| **Exporter Stats** | http://localhost:8000/stats | - |

## 📂 File Structure

```
volt-oracle/
├── Dockerfile.exporter                    # Exporter container image
├── scripts/shannon-scud/
│   ├── docker-compose.observability.yml  # Orchestrates everything
│   ├── prometheus.yml                     # Scrape config (updated)
│   ├── grafana-dashboard.json
│   ├── grafana-datasource.yml
│   ├── grafana-dashboard-provisioning.yml
│   ├── config/token-budget-config.yaml
│   ├── prometheus_exporter.py
│   ├── event_types.py
│   ├── event_streamer.py
│   └── sse-client.html
└── ψ/active/
    ├── token-usage.log                    # Tracked by token-tracker
    └── token-metrics.jsonl                # Read by exporter
```

## 🔧 Container Details

### scudd-exporter

**Image**: Built from `Dockerfile.exporter`
**Base**: `python:3.14-slim`

**Ports:**
- `8000` - Prometheus metrics endpoint
- `8001` - SSE event stream

**Volumes:**
- `./config/token-budget-config.yaml:/app/config/token-budget-config.yaml:ro` - Budget config
- `../../psi/active:/app/psi/active:rw` - Metrics storage

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Environment Variables:**
- `PYTHONUNBUFFERED=1` - Real-time logs

### Prometheus

**Image**: `prom/prometheus:v2.50.0`

**Configuration:**
- Scrape interval: 15s
- Targets:
  - `scudd-exporter:8000` (within Docker network)
  - `prometheus:9090` (self-monitoring)

### Grafana

**Image**: `grafana/grafana:10.3.0`

**Credentials:**
- User: `admin`
- Password: `admin`

**Provisioning:**
- Dashboard: Auto-loaded from `grafana-dashboard.json`
- Datasource: Auto-configured to Prometheus

## 🛠️ Common Commands

### Start Services

```bash
# Start all services
docker-compose -f docker/docker-compose.observability.yml up -d

# Start specific service
docker-compose -f docker/docker-compose.observability.yml up scudd-exporter
```

### Stop Services

```bash
# Stop all services
docker-compose -f docker/docker-compose.observability.yml down

# Stop & remove volumes (⚠️ deletes data!)
docker-compose -f docker/docker-compose.observability.yml down -v
```

### View Logs

```bash
# All services
docker-compose -f docker/docker-compose.observability.yml logs -f

# Specific service
docker-compose -f docker/docker-compose.observability.yml logs -f scudd-exporter
docker logs scudd-exporter -f
```

### Restart Services

```bash
# Restart all
docker-compose -f docker/docker-compose.observability.yml restart

# Restart exporter
docker-compose -f docker/docker-compose.observability.yml restart scudd-exporter
docker restart scudd-exporter
```

### Rebuild After Changes

```bash
# Rebuild exporter image
docker-compose -f docker/docker-compose.observability.yml up -d --build scudd-exporter
```

## 🐛 Troubleshooting

**🔗 Quick Debug Commands**: See [DOCKER_DEBUG_COMMANDS.md](DOCKER_DEBUG_COMMANDS.md) for comprehensive debugging reference (50+ commands across 8 phases)

### Container Not Starting

**Check logs:**
```bash
docker logs scudd-exporter
```

**Common issues:**

1. **Port 8000/8001 already in use**
   ```bash
   lsof -ti:8000 | xargs kill -9
   lsof -ti:8001 | xargs kill -9
   ```

2. **Permission denied on ψ/active**
   ```bash
   chmod 755 ψ/active
   ```

3. **Config file not found**
   ```bash
   # Verify paths in docker-compose.yml
   ls -la scripts/shannon-scud/config/token-budget-config.yaml
   ls -la ψ/active
   ```

### Prometheus Can't Scrape Exporter

**Symptom**: Target shows `health: down`

**Debug:**
```bash
# Check exporter is accessible from Prometheus container
docker exec scudd-prometheus wget -O- http://scudd-exporter:8000/health

# Check network
docker network inspect volt-oracle_scudd-network
```

**Fix:** Ensure both containers use `scudd-network`

### Grafana Shows "No Data"

1. **Check datasource connection**
   - Go to http://localhost:3030/datasources
   - Click "Prometheus" → "Test"
   - Should show: ✅ "Data source is working"

2. **Check Prometheus has data**
   ```bash
   curl -s 'http://localhost:9090/api/v1/query?query=scudd_tokens_total' | jq
   ```

3. **Check dashboard time range**
   - Click time picker (top right)
   - Select "Last 15 minutes"

## 📊 Testing SSE Stream in Docker

### Option 1: Terminal (curl)

```bash
curl -N http://localhost:8001/events
```

**Expected output:**
```
event: heartbeat
data: {"type":"heartbeat","data":{"uptime_seconds":1234,...}}

event: cost_update
data: {"type":"cost_update","data":{"total_cost_usd":0.0123,...}}
```

### Option 2: Browser (HTML Client)

1. Open in browser:
   ```
   file:///Users/jodunk/Documents/Project/volt-oracle/scripts/shannon-scud/sse-client.html
   ```

2. Click "🔌 Connect"

3. Should see live events streaming!

## 🔄 Updating Exporter Code

After modifying Python files (`prometheus_exporter.py`, `event_types.py`, etc.):

```bash
# Rebuild & restart
cd scripts/shannon-scud
docker-compose -f docker/docker-compose.observability.yml up -d --build scudd-exporter
```

## 💾 Data Persistence

**Prometheus data**: Stored in Docker volume `prometheus-data`
**Grafana data**: Stored in Docker volume `grafana-data`
**Token metrics**: Stored in `ψ/active/` (mounted from host)

To backup:
```bash
# Backup volumes
docker run --rm -v volt-oracle_prometheus-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup.tar.gz -C /data .

docker run --rm -v volt-oracle_grafana-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/grafana-backup.tar.gz -C /data .

# Backup metrics
cp ψ/active/token-metrics.jsonl ψ/active/token-metrics.jsonl.backup
```

## 🚢 Production Tips

### Resource Limits

Add to `docker-compose.observability.yml`:

```yaml
services:
  scudd-exporter:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Logging

Configure log rotation:

```yaml
services:
  scudd-exporter:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Restart Policy

Already configured: `restart: unless-stopped`

Container will auto-restart on failure, but not after manual stop.

## ✅ Success Checklist

- [ ] All containers running (`docker ps`)
- [ ] Exporter health check passing (`curl http://localhost:8000/health`)
- [ ] Prometheus scraping exporter (targets show "up")
- [ ] Grafana dashboard loaded (accessible at http://localhost:3030)
- [ ] SSE events streaming (`curl http://localhost:8001/events`)
- [ ] Metrics visible in Grafana panels

---

## 🔗 Related Resources

### Debugging & Troubleshooting
- **[DOCKER_DEBUG_COMMANDS.md](DOCKER_DEBUG_COMMANDS.md)** - Quick reference: 50+ debugging commands organized by phase
- **[GRAFANA_PROVISIONING_GUIDE.md](GRAFANA_PROVISIONING_GUIDE.md)** - Dashboard setup, auto-provisioning, and troubleshooting

### Session Documentation
- **[Retrospective: Grafana Budget Metrics Debug](../../ψ/memory/retrospectives/2026-01/31/12.07_grafana-budget-metrics-debug.md)** - Full debugging journey (26 min)
- **[Lesson Learned: Docker YAML Import Mystery](../../ψ/memory/learnings/2026-01-31_docker-yaml-import-mystery.md)** - Root cause analysis and workarounds

### Architecture & Status
- **[SHANNON-SCUD-PROGRESS.md](SHANNON-SCUD-PROGRESS.md)** - Implementation progress tracking
- **[OBSERVABILITY-STACK.md](OBSERVABILITY-STACK.md)** - System architecture and data flow
- **[USER_GUIDE.md](USER_GUIDE.md)** - Token tracker commands and usage examples

---

**Happy Observabling! 📊**
