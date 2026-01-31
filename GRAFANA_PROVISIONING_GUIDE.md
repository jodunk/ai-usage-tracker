# Grafana Dashboard Auto-Provisioning Guide

> **Target Audience**: DevOps Engineers, Flow Architects, Data Engineers
> **Reading Time**: 10 minutes
> **Difficulty**: Intermediate

## 👥 Who Should Read This Guide

| Role | What You'll Learn |
|------|-------------------|
| **Flow Architect** | How to structure auto-provisioned observability stacks |
| **DevOps Engineer** | Step-by-step deployment + troubleshooting patterns |
| **Data Engineer** | How to version-control Grafana dashboards like code |
| **Platform Engineer** | Container orchestration patterns for monitoring |

**Prerequisites:**
- Basic Docker Compose knowledge
- Understanding of JSON/YAML formats
- Familiarity with Prometheus metrics concepts

## 📋 TL;DR (60-Second Overview)

**What**: Automatically deploy Grafana dashboards without manual import
**Why**: Consistent, version-controlled, repeatable deployments
**How**: Mount JSON configs + enable provisioning environment variable

```
┌─────────────────────────────────────────────────────────────┐
│                    PROVISIONING FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Create Dashboard JSON                    │
│     (Direct format - NO wrapper!)                              │
│           ↓                                                  │
│  2. Mount to Container (/etc/grafana/provisioning/)          │
│           ↓                                                  │
│  3. Set ENV: GF_PROVISIONING_ENABLED=true                    │
│           ↓                                                  │
│  4. Start Container → Dashboard Auto-Loaded! ✅              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Overview

การใช้ Grafana auto-provisioning ช่วยให้ dashboard ถูกสร้างอัตโนมัติเมื่อเริ่ม container โดยไม่ต้อง import เอง

## ⚠️ Critical Issue: Dashboard JSON Format

```
┌──────────────────────────────────────────────────────────────┐
│            ⚠️  #1 ERROR: "Dashboard title cannot be empty"   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  This error is MISLEADING! The title exists, but Grafana    │
│  can't find it because you used the WRONG JSON format.     │
│                                                              │
│  Quick Check: Does your JSON have a "dashboard" key at      │
│  the root level? If YES → This is your problem!             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### The Problem

Grafana มี 2 รูปแบบของ dashboard JSON:

```
┌──────────────────────────┬──────────────────────────────────┐
│   API Wrapper Format     │      Direct Format               │
│   (HTTP API only)        │      (File provisioning)         │
├──────────────────────────┼──────────────────────────────────┤
│                          │                                  │
│  {                       │  {                               │
│    "dashboard": {  ❌    │    "id": null,          ✅       │
│      "id": null,         │    "title": "...",      ✅       │
│      "title": "..."      │    "panels": [...]      ✅       │
│    }                     │  }                               │
│  }                       │                                  │
│                          │                                  │
│  ❌ FAILS with files     │  ✅ WORKS with files             │
└──────────────────────────┴──────────────────────────────────┘
```

**หลายคนใช้รูปแบบที่ 1 แล้ว dashboard ไม่โหลด พร้อม error นี้:**
```
failed to load dashboard from " error="Dashboard title cannot be empty"
```

### The Solution

**❌ WRONG** (API wrapper format):
```json
{
  "dashboard": {           // ❌ REMOVE THIS WRAPPER
    "id": null,
    "title": "My Dashboard",
    "panels": [...]
  },
  "overwrite": true        // ❌ REMOVE THIS TOO
}
```

**✅ CORRECT** (Direct format for file provisioning):
```json
{
  "id": null,              // ✅ Keep at root level
  "title": "My Dashboard", // ✅ Keep at root level
  "panels": [...]          // ✅ Keep at root level
}
```

**Quick Checklist:**
- [ ] ❌ ไม่มี `"dashboard"` wrapper
- [ ] ❌ ไม่มี `"overwrite": true` key
- [ ] ✅ ใส่ dashboard fields โดยตรงที่ root level
- [ ] ✅ `"id": null` (เพื่อให้ Grafana สร้าง ID ใหม่)

## Directory Structure

```
scripts/shannon-scud/
├── docker-compose.observability.yml          # ⚙️  Container orchestration
├── grafana-dashboard.json                    # 📊 Dashboard definition (direct format!)
├── grafana-dashboard-provisioning.yml        # 📁 Dashboard provider config
├── grafana-datasource.yml                    # 🔌 Datasource config
├── prometheus.yml                            # 📈 Prometheus scrape targets
└── scudd_alerts.yml                          # 🚨 Alert rules
```

**Key Files Explained:**

| File | Purpose | Format | Critical Setting |
|------|---------|--------|------------------|
| `grafana-dashboard.json` | Dashboard panels, layout, queries | JSON (Direct format!) | `"id": null` |
| `grafana-dashboard-provisioning.yml` | Tells Grafana where to find dashboards | YAML | `folder: /etc/grafana/provisioning/dashboards` |
| `grafana-datasource.yml` | Connects Grafana to Prometheus | YAML | `url: http://prometheus:9090` |
| `docker-compose.observability.yml` | Mounts files + sets ENV vars | YAML | `GF_PROVISIONING_ENABLED=true` |

## File 1: Dashboard JSON (`grafana-dashboard.json`)

**CRITICAL**: Use direct format (no wrapper)

```json
{
  "id": null,
  "title": "Scudd Oracle - Token Usage & Budget",
  "tags": ["scudd", "oracle", "tokens"],
  "timezone": "browser",
  "schemaVersion": 38,
  "version": 0,
  "refresh": "15s",
  "panels": [
    {
      "id": 1,
      "title": "My Panel",
      "type": "stat",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
      "targets": [
        {
          "expr": "up"
        }
      ]
    }
  ]
}
```

### Required Fields
- `"id": null` - Let Grafana generate ID
- `"title"` - Dashboard name (THIS is what the error refers to!)
- `"schemaVersion"` - Grafana version (typically 38 for v10+)
- `"panels"` - Array of panel objects

## File 2: Dashboard Provider (`grafana-dashboard-provisioning.yml`)

```yaml
apiVersion: 1

providers:
  - name: 'Grafana'
    orgId: 1
    folder: ''          # Empty = root folder
    type: file
    disableDeletion: false
    editable: true
    options:
      folder: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: false
```

**Key Settings:**
- `folder: ''` - Dashboard จะอยู่ที่ root folder (ไม่อยู่ใน subfolder)
- `foldersFromFilesStructure: false` - ไม่ใช้โครงสร้าง directory
- `disableDeletion: false` - อนุญาตให้ลบ dashboard ผ่าน UI

## File 3: Datasource Config (`grafana-datasource.yml`)

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090    # Docker network name
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: "POST"
```

**Note**: `url` ใช้ Docker service name (`prometheus:9090`) ไม่ใช่ `localhost`

## File 4: Docker Compose (`docker-compose.observability.yml`)

```yaml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:v2.50.0
    container_name: scudd-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./scudd_alerts.yml:/etc/prometheus/scudd_alerts.yml:ro
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.enable-lifecycle"
    restart: unless-stopped
    networks:
      - scudd-network

  grafana:
    image: grafana/grafana:10.3.0
    container_name: scudd-grafana
    ports:
      - "3030:3000"        # Host:Container
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=http://localhost:3030
      - GF_PROVISIONING_ENABLED=true           # ← CRITICAL
      - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
    volumes:
      - grafana-data:/var/lib/grafana
      # ↓ Mount dashboard JSON
      - ./grafana-dashboard.json:/etc/grafana/provisioning/dashboards/scudd-dashboard.json:ro
      # ↓ Mount dashboard provider config
      - ./grafana-dashboard-provisioning.yml:/etc/grafana/provisioning/dashboards/scudd-dashboard-provisioning.yml:ro
      # ↓ Mount datasource config
      - ./grafana-datasource.yml:/etc/grafana/provisioning/datasources/prometheus.yml:ro
    restart: unless-stopped
    networks:
      - scudd-network
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:

networks:
  scudd-network:
    driver: bridge
```

### Critical Environment Variables
```yaml
GF_PROVISIONING_ENABLED=true                          # Enable provisioning
GF_PATHS_PROVISIONING=/etc/grafana/provisioning      # Path to provisioning configs
```

### Volume Mounts Explained
```yaml
# Host file → Container path
./grafana-dashboard.json:/etc/grafana/provisioning/dashboards/scudd-dashboard.json:ro
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                          Fixed path in Grafana container
```

## File 5: Prometheus Config (`prometheus.yml`)

### Docker Networking Considerations

**ถ้า scrape จาก host machine**:
```yaml
scrape_configs:
  - job_name: "scudd-oracle"
    static_configs:
      - targets:
          - "host.docker.internal:8000"   # ← Docker Desktop Mac/Windows
```

**ถ้า scrape จาก container อื่น**:
```yaml
scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets:
          - "localhost:9090"   # ← Container-to-container
```

## Deployment Steps

### ✅ Pre-Flight Checklist

```
┌─────────────────────────────────────────────────────────────┐
│                    BEFORE YOU START                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [ ] Dashboard JSON uses DIRECT format (no wrapper)        │
│  [ ] JSON is valid (test with json.tool or jq)             │
│  [ ] docker-compose.yml has correct volume mount paths     │
│  [ ] GF_PROVISIONING_ENABLED=true in environment vars      │
│  [ ] Prometheus URL uses Docker network name               │
│  [ ] Files are in correct directory                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Start the Stack

```bash
cd /path/to/scripts/shannon-scud
docker-compose -f docker-compose.observability.yml up -d
```

**What happens:**
1. Creates Docker network `scudd-network`
2. Starts Prometheus on port 9090
3. Starts Grafana on port 3030 (mapped to container port 3000)
4. Mounts config files into containers
5. Grafana auto-loads dashboards on startup

### Step 2: Check Logs

```bash
# Grafana logs - Look for provisioning messages
docker logs scudd-grafana -f | grep -i "provision\|dashboard"

# Prometheus logs - Look for scrape targets
docker logs scudd-prometheus -f
```

**Expected Grafana log output:**
```
INFO Provisioning: Loaded config file         # ✅ Good!
INFO Provisioning: Loaded dashboards from /etc/grafana/provisioning/dashboards
INFO Provisioning: provisioned dashboard named "Scudd Oracle"
```

**Error logs:**
```
ERRO Failed to load dashboard                # ❌ Problem!
ERRO Dashboard title cannot be empty         # ❌ Wrong JSON format!
```

### Step 3: Verify Dashboard Provisioning

```bash
curl -s "admin:admin@localhost:3030/api/search?query=Scudd" | jq
```

**Expected output (Success ✅):**
```json
[
  {
    "id": 1,
    "title": "Scudd Oracle - Token Usage & Budget",
    "uri": "db/scudd-oracle-token-usage-budget",
    "url": "/d/abc123def456/scudd-oracle-token-usage-budget",
    "type": "dash-db"
  }
]
```

**Empty output (`[]`):**
- Dashboard not loaded → Check logs
- Wrong title in query → Check dashboard JSON title field

### Step 4: Verify Prometheus Targets

```bash
curl -s localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

**Expected (All up ✅):**
```json
{"job": "prometheus", "health": "up"}
{"job": "scudd-oracle", "health": "up"}
```

**If health is "down":**
- Check if exporter is running on host: `curl http://localhost:8000/metrics`
- Check network connectivity (see Troubleshooting below)

## Troubleshooting

### 🔍 Decision Tree: Dashboard Not Appearing

```
                    Dashboard Not Visible?
                            │
                            ├─→ Can you access Grafana UI?
                            │   │
                            │   ├─→ NO → Check: docker ps | grep grafana
                            │   │         └─→ Container not running?
                            │   │              └─→ docker-compose up -d
                            │   │
                            │   └─→ YES → Continue below
                            │
                            ├─→ Check Logs:
                            │   docker logs scudd-grafana | grep -i dashboard
                            │
                            ├── ERROR: "Dashboard title cannot be empty"
                            │   │
                            │   └─→ CAUSE: Wrong JSON format!
                            │        FIX: Remove "dashboard" wrapper
                            │
                            ├── ERROR: "failed to read dashboard"
                            │   │
                            │   └─→ CAUSE: Invalid JSON syntax
                            │        FIX: python3 -m json.tool grafana-dashboard.json
                            │
                            └── ERROR: "no such file or directory"
                                │
                                └─→ CAUSE: Volume mount path wrong
                                     FIX: Check docker-compose.yml paths
```

### Common Error Patterns

**Error**: `Dashboard title cannot be empty`
```
┌────────────────────────────────────────────────────────────┐
│  DIAGNOSIS: You used API wrapper format                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Your JSON looks like:                                     │
│  {                                                        │
│    "dashboard": {   ← ❌ REMOVE THIS                      │
│      ...                                                │
│    }                                                     │
│  }                                                       │
│                                                            │
│  FIX: Extract contents of "dashboard" to root level       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Error**: `failed to read dashboard`
```
┌────────────────────────────────────────────────────────────┐
│  DIAGNOSIS: JSON syntax error                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Test your JSON:                                           │
│  $ python3 -m json.tool grafana-dashboard.json            │
│  $ cat grafana-dashboard.json | jq .                      │
│                                                            │
│  Common issues:                                            │
│  - Missing comma after array item                         │
│  - Trailing comma (last item can't have comma)           │
│  - Single quotes instead of double quotes                 │
│  - Missing closing brace } or bracket ]                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Error**: `no such file or directory`
```
┌────────────────────────────────────────────────────────────┐
│  DIAGNOSIS: Volume mount path mismatch                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Check:                                                    │
│  1. File exists on host?                                  │
│     $ ls -la grafana-dashboard.json                       │
│                                                            │
│  2. Path in docker-compose.yml matches actual file?      │
│     volumes:                                              │
│       - ./grafana-dashboard.json:/etc/grafana/...         │
│         ^^^^^^^^^^^^^^^^^^^^^^^                          │
│         Must exist relative to docker-compose.yml!       │
│                                                            │
│  3. Check container mount:                                │
│     $ docker exec scudd-grafana ls -la /etc/grafana/provisioning/dashboards/ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Prometheus Can't Scrape Exporter

**Symptom**: Target shows `health: down`

```
┌────────────────────────────────────────────────────────────┐
│              TARGET HEALTH CHECK                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. Test from HOST machine:                               │
│     $ curl http://localhost:8000/metrics                  │
│     → Works? Problem is Docker networking                │
│     → Fails? Exporter not running                         │
│                                                            │
│  2. Test from CONTAINER:                                  │
│     $ docker exec scudd-prometheus wget -O- http://host.docker.internal:8000/metrics │
│     → Works? Prometheus config wrong                      │
│     → Fails? Network issue (see table below)              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

| Issue | Cause | Fix |
|-------|-------|-----|
| `localhost:8000` doesn't work from container | Container isolation | Use `host.docker.internal:8000` |
| `host.docker.internal` doesn't work | Linux host (not Mac/Windows) | Use `172.17.0.1:8000` (docker0 bridge IP) |
| Connection timeout | Firewall blocking | `sudo ufw allow 8000` |
| Target shows `up` but no data | Wrong metrics endpoint | Check exporter `/metrics` path |

### Grafana Shows "No Data"

```
┌────────────────────────────────────────────────────────────┐
│              NO DATA DEBUGGING                             │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. DATASOURCE CONNECTION:                                │
│     → http://localhost:3030/datasources                   │
│     → Click Prometheus → "Test"                           │
│     → Should show: ✅ "Data source is working"            │
│                                                            │
│  2. PROMETHEUS HAS DATA:                                  │
│     $ curl -s 'http://localhost:9090/api/v1/query?query=up' | jq │
│     → Should return metric data (not empty result)       │
│                                                            │
│  3. TIME RANGE:                                           │
│     → Dashboard time picker (top right)                   │
│     → Select "Last 5 minutes" or wider                    │
│     → Refresh interval too long? Set to "15s"             │
│                                                            │
│  4. QUERY SYNTAX:                                         │
│     → Click panel title → "Edit"                          │
│     → Test query manually                                 │
│     → Check metric name exists in Prometheus              │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Quick Reference

### 🔄 Convert API format → Provisioning format

**Before (API)**:
```json
{
  "dashboard": {           // ❌ Remove this wrapper
    "id": null,
    "title": "My Dashboard",
    ...
  },
  "overwrite": true,       // ❌ Remove this
  "message": "Updated"     // ❌ Remove this
}
```

**After (Provisioning)**:
```json
{
  "id": null,
  "title": "My Dashboard",
  ...
}
```

### ✅ Test dashboard JSON validity
```bash
python3 -m json.tool grafana-dashboard.json > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"
```

### 🔄 Restart services after changes
```bash
# Restart Grafana only (after dashboard edits)
docker-compose -f docker-compose.observability.yml restart grafana

# Restart Prometheus only (after config changes)
docker-compose -f docker-compose.observability.yml restart prometheus

# Restart all
docker-compose -f docker-compose.observability.yml restart
```

### 🔍 View dashboard UID
```bash
curl -s "admin:admin@localhost:3030/api/search" | jq -r '.[] | select(.title == "Scudd Oracle - Token Usage & Budget") | .uid'
```

### 📊 Quick Health Check (One-Liner)
```bash
echo "=== Grafana Dashboards ===" && \
curl -s "admin:admin@localhost:3030/api/search" | jq -r '.[] | .title' && \
echo -e "\n=== Prometheus Targets ===" && \
curl -s localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HOST MACHINE                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Docker Compose (orchestrates everything)                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│           │                          │                             │
│           │ Mount files               │ Mount files                │
│           ▼                          ▼                             │
│  ┌──────────────────┐      ┌──────────────────┐                   │
│  │  grafana-dashboard│      │ prometheus.yml   │                   │
│  │  .json           │      │ scudd_alerts.yml │                   │
│  └──────────────────┘      └──────────────────┘                   │
│           │                          │                             │
│           ▼                          ▼                             │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    Docker Network                          │   │
│  │                   (scudd-network)                          │   │
│  │                                                              │   │
│  │   ┌─────────────────────┐     ┌──────────────────────┐     │   │
│  │   │   Grafana Container  │     │ Prometheus Container │     │   │
│  │   │   :3030 → :3000     │────▶│      :9090           │     │   │
│  │   │                     │     │                      │     │   │
│  │   │  /etc/grafana/      │     │  /etc/prometheus/    │     │   │
│  │   │  provisioning/      │     │                      │     │   │
│  │   │  └── dashboards/    │     │  Scrapes:            │     │   │
│  │   │      └── *.json     │     │  - localhost:9090    │     │   │
│  │   │                     │     │  - host.docker.      │     │   │
│  │   │  Auto-loads on      │     │    internal:8000     │     │   │
│  │   │  startup! ✅        │     │                      │     │   │
│  │   └─────────────────────┘     └──────────────────────┘     │   │
│  │                                           │                 │   │
│  └───────────────────────────────────────────┼─────────────────┘   │
│                                              │                     │
│                                              ▼                     │
│                                    ┌──────────────────┐            │
│                                    │  Scudd Oracle    │            │
│                                    │  Exporter        │            │
│                                    │  :8000/metrics   │            │
│                                    └──────────────────┘            │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

Key Data Flows:
  ① Dashboard JSON mounted into Grafana container at startup
  ② Grafana reads + auto-loads dashboard from /etc/grafana/provisioning/
  ③ Prometheus scrapes metrics from Scudd Oracle exporter
  ④ Grafana queries Prometheus for dashboard data
```

## Best Practices

### 1. Version Control Dashboard JSON
```bash
git add grafana-dashboard.json
git commit -m "feat: Add cost overview panel"
```

### 2. Use Descriptive Panel IDs
Don't rely on auto-generated IDs. Set meaningful ones:
```json
{
  "id": 100,  // High number to avoid conflicts
  "title": "Budget Usage",
  ...
}
```

### 3. Group Panels by Grid Position
```json
{
  "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
}
```

- `h`: Height (rows)
- `w`: Width (columns, max 24)
- `x`: X position
- `y`: Y position

### 4. Set Refresh Intervals Wisely
```json
{
  "refresh": "15s"  // For real-time metrics
  // or
  "refresh": "1m"   // For slower changing data
}
```

### 5. Use Variables for Flexibility
```json
{
  "templating": {
    "list": [
      {
        "name": "model",
        "type": "query",
        "query": "label_values(scudd_model_tokens_total, model)"
      }
    ]
  }
}
```

## Advanced: Multiple Dashboards

### Directory Structure
```
dashboards/
├── overview.json
├── performance.json
└── cost-analysis.json
```

### Docker Compose
```yaml
volumes:
  - ./dashboards/overview.json:/etc/grafana/provisioning/dashboards/overview.json:ro
  - ./dashboards/performance.json:/etc/grafana/provisioning/dashboards/performance.json:ro
  - ./dashboards/cost-analysis.json:/etc/grafana/provisioning/dashboards/cost-analysis.json:ro
```

### Provider Config
```yaml
providers:
  - name: 'Dashboards'
    folder: ''
    type: file
    options:
      folder: /etc/grafana/provisioning/dashboards
```

All JSON files in the mounted folder will be auto-provisioned!

## Conclusion

### 🎯 Key Takeaways

```
┌─────────────────────────────────────────────────────────────┐
│              THE 5 GOLDEN RULES                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1️⃣  Use DIRECT JSON format (no "dashboard" wrapper)      │
│  2️⃣  Set GF_PROVISIONING_ENABLED=true                      │
│  3️⃣  Mount files to /etc/grafana/provisioning/dashboards/ │
│  4️⃣  Use host.docker.internal for Mac/Windows networking   │
│  5️⃣  Always check logs if dashboard doesn't appear        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ✅ Success Checklist

- [ ] Dashboard JSON validated (no syntax errors)
- [ ] Direct format used (no `"dashboard"` wrapper)
- [ ] docker-compose.yml volume mounts correct
- [ ] Environment variables set in compose file
- [ ] Prometheus datasource configured with Docker network URL
- [ ] Containers running (`docker ps`)
- [ ] Dashboard appears in Grafana UI
- [ ] Data visible in panels (not "No Data")

### 🚀 Next Steps

1. **Customize Dashboard**: Edit `grafana-dashboard.json` and restart
2. **Add Alerts**: Configure `scudd_alerts.yml` for Prometheus alerts
3. **Version Control**: Commit all config files to Git
4. **CI/CD Integration**: Add provisioning to deployment pipeline

**Happy Dashboarding! 📊**

---

## 📌 Printable Cheat Sheet

```
╔═══════════════════════════════════════════════════════════════╗
║          GRAFANA PROVISIONING CHEAT SHEET                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  FILE LOCATIONS (relative to docker-compose.yml):            ║
║  ├── grafana-dashboard.json                    (Dashboard)  ║
║  ├── grafana-dashboard-provisioning.yml        (Provider)   ║
║  ├── grafana-datasource.yml                    (Datasource) ║
║  └── docker-compose.observability.yml          (Orchestrate)║
║                                                               ║
║  CRITICAL ENV VARS:                                          ║
║  GF_PROVISIONING_ENABLED=true                                ║
║  GF_PATHS_PROVISIONING=/etc/grafana/provisioning             ║
║                                                               ║
║  VOLUME MOUNTS:                                              ║
║  ./grafana-dashboard.json:/etc/grafana/provisioning/...      ║
║                                                               ║
║  JSON FORMAT CHECK:                                          ║
║  $ cat file.json | python3 -m json.tool                      ║
║                                                               ║
║  RESTART GRAFANA:                                            ║
║  $ docker-compose restart grafana                            ║
║                                                               ║
║  CHECK LOGS:                                                 ║
║  $ docker logs scudd-grafana | grep -i dashboard             ║
║                                                               ║
║  COMMON ERRORS:                                              ║
║  - "Dashboard title cannot be empty" → Wrong JSON format     ║
║  - "no such file" → Volume mount path wrong                  ║
║  - "No Data" → Time range or query issue                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 📚 References

### Official Documentation
- [Grafana Provisioning Docs](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [Prometheus Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)
- [Grafana Dashboard JSON Schema](https://grafana.com/docs/grafana/latest/dashboard/json-model/)

### Project Documentation
- **[DOCKER_DEBUG_COMMANDS.md](DOCKER_DEBUG_COMMANDS.md)** - Quick reference for debugging Docker issues
- **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)** - Complete Docker deployment and troubleshooting
- **[USER_GUIDE.md](USER_GUIDE.md)** - Token tracker usage and commands

### Session Documentation
- **[Retrospective: Grafana Budget Metrics Debug](../../ψ/memory/retrospectives/2026-01/31/12.07_grafana-budget-metrics-debug.md)** - Full debugging session notes
- **[Lesson Learned: Docker YAML Import Mystery](../../ψ/memory/learnings/2026-01-31_docker-yaml-import-mystery.md)** - Technical analysis and workarounds
