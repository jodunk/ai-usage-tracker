#!/usr/bin/env python3
"""
Prometheus Metrics Exporter - Shannon-Style with SSE

Exposes Scudd token usage metrics for Prometheus scraping
AND provides Server-Sent Events (SSE) for real-time updates.

Endpoints:
- /metrics    - Prometheus scraping endpoint
- /health     - Health check
- /events     - SSE event stream (real-time)
- /stats      - SSE broadcaster stats
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import yaml
from threading import Thread, Event as ThreadEvent
from typing import Dict, Optional

# Import event streaming components
from event_types import (
    Event,
    EventType,
    cost_update_event,
    budget_alert_event,
    system_start_event,
)
from event_streamer import EventBroadcaster, SSEClient, init_broadcaster

# ====== CONFIGURATION ======
# Detect if running in Docker (mounted at /app/psi/active)
DOCKER_PATH = Path("/app/psi/active/token-metrics.jsonl")

if DOCKER_PATH.exists():
    # Running in Docker container
    METRICS_FILE = DOCKER_PATH
    CONFIG_FILE = Path("/app/token-budget-config.yaml")
    PROJECT_ROOT = Path("/app")
else:
    # Running in local development
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    METRICS_FILE = PROJECT_ROOT / "ψ" / "active" / "token-metrics.jsonl"
    CONFIG_FILE = PROJECT_ROOT / "scripts" / "shannon-scud" / "token-budget-config.yaml"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# SSE Handler (runs in separate thread)
# ============================================================================

class SSEThread:
    """
    Runs SSE event broadcaster in separate thread with async loop
    """

    def __init__(self, port: int = 8001):
        self.port = port
        self.thread: Optional[Thread] = None
        self.stop_event = ThreadEvent()
        self.broadcaster: Optional[EventBroadcaster] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def _handle_sse_client(self, reader, writer):
        """Handle individual SSE client connection"""
        client_id = str(uuid.uuid4())[:8]
        client = SSEClient(client_id)

        # Setup SSE response
        writer.write(b"HTTP/1.1 200 OK\r\n")
        writer.write(b"Content-Type: text/event-stream\r\n")
        writer.write(b"Cache-Control: no-cache\r\n")
        writer.write(b"Connection: keep-alive\r\n")
        writer.write(b"Access-Control-Allow-Origin: *\r\n")
        writer.write(b"\r\n")
        await writer.drain()

        logger.info(f"SSE client {client_id} connected")

        try:
            # Add client to broadcaster
            if self.broadcaster:
                await self.broadcaster.add_client(client)

                # Stream events
                async for event in client.events():
                    # Send SSE formatted event
                    sse_data = event.to_sse()
                    writer.write(sse_data.encode("utf-8"))
                    await writer.drain()

        except (ConnectionResetError, BrokenPipeError):
            logger.debug(f"SSE client {client_id} disconnected")
        finally:
            if self.broadcaster:
                await self.broadcaster.remove_client(client)
            writer.close()
            await writer.wait_closed()

    async def _sse_server(self):
        """Async SSE server"""
        server = await asyncio.start_server(
            self._handle_sse_client,
            "0.0.0.0",
            self.port
        )

        logger.info(f"SSE server running on port {self.port}")
        async with server:
            await server.serve_forever()

    def _run_loop(self):
        """Run async event loop in thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Initialize broadcaster
        self.broadcaster = init_broadcaster(heartbeat_interval=30, history_size=100)
        self.loop.run_until_complete(self.broadcaster.start())

        try:
            self.loop.run_until_complete(self._sse_server())
        finally:
            self.loop.run_until_complete(self.broadcaster.stop())

    def start(self):
        """Start SSE thread"""
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"SSE thread started (port: {self.port})")

    def stop(self):
        """Stop SSE thread"""
        self.stop_event.set()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


# Global SSE thread instance
sse_thread: Optional[SSEThread] = None


# ============================================================================
# Prometheus HTTP Handler
# ============================================================================

class PrometheusHandler(BaseHTTPRequestHandler):
    """HTTP handler for /metrics, /health, /stats endpoints"""

    def do_GET(self):
        """Handle GET requests"""

        if self.path == "/metrics":
            self.send_metrics()
        elif self.path == "/health":
            self.send_health()
        elif self.path == "/stats":
            self.send_stats()
        elif self.path == "/events":
            self.redirect_to_sse()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def send_metrics(self):
        """Send Prometheus metrics"""

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

        # Load metrics
        metrics = self.load_metrics()

        # Generate Prometheus format
        prom_metrics = self.to_prometheus(metrics)
        self.wfile.write(prom_metrics.encode("utf-8"))

        # Emit cost_update event if broadcaster available
        self._emit_cost_event(metrics)

    def send_health(self):
        """Send health check"""

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "scudd-prometheus-exporter",
            "sse_running": sse_thread is not None and sse_thread.broadcaster is not None,
        }

        self.wfile.write(json.dumps(health).encode("utf-8"))

    def send_stats(self):
        """Send SSE broadcaster stats"""

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        if sse_thread and sse_thread.broadcaster:
            stats = sse_thread.broadcaster.get_stats()
            stats["clients"] = sse_thread.broadcaster.list_clients()
        else:
            stats = {"error": "SSE broadcaster not running"}

        self.wfile.write(json.dumps(stats, indent=2).encode("utf-8"))

    def redirect_to_sse(self):
        """Redirect /events to SSE port"""
        if sse_thread:
            # Redirect to SSE server port
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{sse_thread.port}/events")
            self.end_headers()
        else:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"SSE server not running")

    def _emit_cost_event(self, metrics: Dict):
        """Emit cost update event via SSE broadcaster"""

        if not (sse_thread and sse_thread.broadcaster and sse_thread.loop):
            return

        try:
            # Calculate budget info
            import yaml
            with open(CONFIG_FILE) as f:
                config = yaml.safe_load(f)

            tier = config["current_tier"]
            tier_config = config["budget_tiers"][tier]
            daily_limit = tier_config.get("daily_limit_usd", 0)

            if daily_limit:
                budget_used_pct = (metrics["total_cost"] / daily_limit) * 100
                budget_remaining = daily_limit - metrics["total_cost"]

                # Emit cost update event
                event = cost_update_event(
                    total_cost_usd=metrics["total_cost"],
                    total_tokens=metrics["total_tokens"],
                    budget_percent=budget_used_pct,
                    budget_remaining_usd=budget_remaining,
                )

                # Schedule event emission on SSE thread's event loop
                asyncio.run_coroutine_threadsafe(
                    sse_thread.broadcaster.broadcast(event),
                    sse_thread.loop
                )

                # Emit budget alert if threshold breached
                if budget_used_pct >= 80:
                    level = "critical" if budget_used_pct >= 95 else "warning"
                    alert_event = budget_alert_event(
                        level=level,
                        budget_percent=budget_used_pct,
                        budget_remaining_usd=budget_remaining,
                        message=f"Budget {budget_used_pct:.1f}% used"
                    )

                    asyncio.run_coroutine_threadsafe(
                        sse_thread.broadcaster.broadcast(alert_event),
                        sse_thread.loop
                    )

        except Exception as e:
            logger.debug(f"Failed to emit cost event: {e}")

    def load_metrics(self) -> Dict:
        """Load metrics from token-tracker data"""

        if not METRICS_FILE.exists():
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "tasks": [],
                "total_tokens": 0,
                "total_cost": 0.0
            }

        # Get last record for today
        today = datetime.now().strftime("%Y-%m-%d")
        last_record = None

        with open(METRICS_FILE) as f:
            for line in f:
                record = json.loads(line)
                if record.get("date") == today:
                    last_record = record

        return last_record or {
            "date": today,
            "tasks": [],
            "total_tokens": 0,
            "total_cost": 0.0
        }

    def to_prometheus(self, metrics: Dict) -> str:
        """Convert metrics to Prometheus format"""

        lines = []

        # Help and type metadata
        lines.append("# HELP scudd_tokens_total Total tokens consumed")
        lines.append("# TYPE scudd_tokens_total counter")
        lines.append(f"scudd_tokens_total {metrics['total_tokens']}")

        lines.append("# HELP scudd_cost_usd_total Total cost in USD")
        lines.append("# TYPE scudd_cost_usd_total gauge")
        lines.append(f"scudd_cost_usd_total {metrics['total_cost']:.4f}")

        lines.append("# HELP scudd_tasks_total Total number of tasks")
        lines.append("# TYPE scudd_tasks_total counter")
        lines.append(f"scudd_tasks_total {len(metrics['tasks'])}")

        # Per-model metrics
        lines.append("\n# Per-model metrics")

        model_stats = {}
        for task in metrics["tasks"]:
            model = task["model"]
            if model not in model_stats:
                model_stats[model] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "tasks": 0
                }

            model_stats[model]["tokens"] += task["total_tokens"]
            model_stats[model]["cost"] += task["cost_usd"]
            model_stats[model]["tasks"] += 1

        for model, stats in model_stats.items():
            # Sanitize model name for Prometheus
            safe_model = model.replace("-", "_").replace(".", "_")

            lines.append(f"scudd_model_tokens_total{{model=\"{model}\"}} {stats['tokens']}")
            lines.append(f"scudd_model_cost_usd{{model=\"{model}\"}} {stats['cost']:.6f}")
            lines.append(f"scudd_model_tasks_total{{model=\"{model}\"}} {stats['tasks']}")

        # Per-task-type metrics
        lines.append("\n# Per-task-type metrics")

        task_stats = {}
        for task in metrics["tasks"]:
            task_type = task["task_type"]
            if task_type not in task_stats:
                task_stats[task_type] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "tasks": 0
                }

            task_stats[task_type]["tokens"] += task["total_tokens"]
            task_stats[task_type]["cost"] += task["cost_usd"]
            task_stats[task_type]["tasks"] += 1

        for task_type, stats in task_stats.items():
            lines.append(f"scudd_task_tokens_total{{task_type=\"{task_type}\"}} {stats['tokens']}")
            lines.append(f"scudd_task_cost_usd{{task_type=\"{task_type}\"}} {stats['cost']:.6f}")
            lines.append(f"scudd_task_tasks_total{{task_type=\"{task_type}\"}} {stats['tasks']}")

        # Budget metrics
        lines.append("\n# Budget metrics")

        try:
            import yaml
            with open(CONFIG_FILE) as f:
                config = yaml.safe_load(f)

            tier = config["current_tier"]
            tier_config = config["budget_tiers"][tier]
            daily_limit = tier_config.get("daily_limit_usd", 0)

            if daily_limit:
                budget_used_pct = (metrics["total_cost"] / daily_limit) * 100
                budget_remaining = daily_limit - metrics["total_cost"]

                lines.append(f"scudd_budget_limit_usd {daily_limit:.2f}")
                lines.append(f"scudd_budget_usage_percent {budget_used_pct:.2f}")
                lines.append(f"scudd_budget_remaining_usd {budget_remaining:.2f}")
                lines.append(f"scudd_budget_tier{{tier=\"{tier}\"}} 1")

        except Exception as e:
            lines.append(f"# Error loading budget config: {e}")

        # Scrape timestamp
        lines.append(f"\n# Scrape timestamp")
        lines.append(f"scudd_scrape_timestamp {int(time.time())}")

        return "\n".join(lines) + "\n"

    def log_message(self, format, *args):
        """Suppress default logging"""
        return


# ============================================================================
# Server Main
# ============================================================================

def run_server(port: int = 8000, sse_port: int = 8001):
    """Run Prometheus exporter server with SSE"""

    global sse_thread

    # Start SSE thread
    sse_thread = SSEThread(port=sse_port)
    sse_thread.start()

    # Emit system start event
    if sse_thread.broadcaster and sse_thread.loop:
        start_event = system_start_event(
            version="2.0.0",
            config={
                "prometheus_port": port,
                "sse_port": sse_port,
            }
        )
        asyncio.run_coroutine_threadsafe(
            sse_thread.broadcaster.broadcast(start_event),
            sse_thread.loop
        )

    # Start Prometheus server
    server_address = ("", port)
    httpd = HTTPServer(server_address, PrometheusHandler)

    print(f"🚀 Scudd Prometheus Exporter v2.0.0 (with SSE)")
    print(f"=" * 60)
    print(f"✅ Prometheus server: http://localhost:{port}")
    print(f"📊 Metrics endpoint: http://localhost:{port}/metrics")
    print(f"💚 Health check: http://localhost:{port}/health")
    print(f"📡 SSE events: http://localhost:{sse_port}/events")
    print(f"📈 SSE stats: http://localhost:{port}/stats")
    print(f"=" * 60)
    print(f"\nPress Ctrl+C to stop\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
        sse_thread.stop()
        httpd.server_close()


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    sse_port = port + 1  # SSE runs on port+1 by default
    run_server(port, sse_port)
