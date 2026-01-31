#!/usr/bin/env python3
"""
Token Budget Tracker - Shannon-Style Production Monitoring
Inspired by Kocoro-lab/Shannon framework

Tracks token usage, enforces budgets, and provides metrics
"""

import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
import logging

# ====== CONFIGURATION ======
# Paths relative to project root (git repository root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "token-budget-config.yaml"
USAGE_LOG = PROJECT_ROOT / "ψ" / "active" / "token-usage.log"
METRICS_FILE = PROJECT_ROOT / "ψ" / "active" / "token-metrics.jsonl"

# Ensure directories exist
USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)

# ====== LOGGING ======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(USAGE_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TokenTracker:
    """Track token usage and enforce budgets"""

    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self.config = self._load_config()
        self.daily_usage = self._load_daily_usage()

    def _load_config(self) -> Dict:
        """Load configuration from YAML"""
        if not self.config_path.exists():
            logger.warning(f"Config not found: {self.config_path}")
            return self._default_config()

        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "budget_tiers": {
                "standard": {
                    "daily_limit_usd": 5.00,
                    "per_task_max_tokens": 15000,
                    "fallback_trigger": 0.70
                }
            },
            "model_pricing": {
                "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
                "claude-haiku-4-20250919": {"input": 0.25, "output": 1.25},
            },
            "current_tier": "standard"
        }

    def _load_daily_usage(self) -> Dict:
        """Load today's usage from metrics file (returns latest record)"""
        today = datetime.now().strftime("%Y-%m-%d")

        if not METRICS_FILE.exists():
            return {"date": today, "tasks": [], "total_tokens": 0, "total_cost": 0.0}

        # Read today's usage (get LAST record for today)
        last_record = None
        with open(METRICS_FILE) as f:
            for line in f:
                record = json.loads(line)
                if record.get("date") == today:
                    last_record = record  # Keep updating to get the last one

        if last_record:
            return last_record

        # Reset if new day
        return {"date": today, "tasks": [], "total_tokens": 0, "total_cost": 0.0}

    def _save_daily_usage(self):
        """Append usage record to metrics file"""
        with open(METRICS_FILE, "a") as f:
            f.write(json.dumps(self.daily_usage) + "\n")

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model (with partial name matching)"""

        # Exact match first
        if model in self.config["model_pricing"]:
            return self.config["model_pricing"][model]

        # Partial match (e.g., "claude-sonnet-4-5" matches "claude-sonnet-4-5-20250929")
        for key in self.config["model_pricing"]:
            if model in key or key in model:
                return self.config["model_pricing"][key]

        # Default: free model
        logger.warning(f"No pricing found for {model}, assuming free")
        return {"input": 0.0, "output": 0.0}

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        pricing = self.get_model_pricing(model)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def record_usage(
        self,
        task_id: str,
        task_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        notes: str = "",
        estimated: bool = False
    ) -> Dict[str, Any]:
        """Record token usage for a task"""

        total_tokens = input_tokens + output_tokens
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        # Create usage record
        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "task_type": task_type,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost, 6),
            "estimated": estimated,
            "notes": notes
        }

        # Update daily usage
        self.daily_usage["tasks"].append(record)
        self.daily_usage["total_tokens"] += total_tokens
        self.daily_usage["total_cost"] += cost

        # Save
        self._save_daily_usage()

        # Log
        logger.info(
            f"Task {task_id} | {task_type} | {model} | "
            f"{total_tokens:,} tokens | ${cost:.4f}"
        )

        # Check budgets
        return self._check_budgets(record)

    def _check_budgets(self, record: Dict) -> Dict[str, Any]:
        """Check if budgets are exceeded"""

        tier = self.config["budget_tiers"][self.config["current_tier"]]
        daily_limit = tier.get("daily_limit_usd")
        task_limit = tier.get("per_task_max_tokens")

        alerts = []
        should_fallback = False

        # Check daily budget
        if daily_limit:
            daily_usage_pct = self.daily_usage["total_cost"] / daily_limit

            if daily_usage_pct >= 0.95:
                alerts.append("CRITICAL: Daily budget 95% used!")
            elif daily_usage_pct >= 0.80:
                alerts.append("WARNING: Daily budget 80% used")

            # Trigger fallback?
            if daily_usage_pct >= tier["fallback_trigger"]:
                should_fallback = True

        # Check task budget
        if task_limit and record["total_tokens"] > task_limit:
            alerts.append(
                f"WARNING: Task exceeded {task_limit:,} tokens "
                f"({record['total_tokens']:,} used)"
            )

        return {
            "alerts": alerts,
            "should_fallback": should_fallback,
            "daily_usage": {
                "cost": round(self.daily_usage["total_cost"], 4),
                "tokens": self.daily_usage["total_tokens"]
            }
        }

    def get_daily_summary(self) -> Dict:
        """Get today's usage summary (reload from file for latest data)"""
        # Reload to get latest state
        self.daily_usage = self._load_daily_usage()

        tier = self.config["budget_tiers"][self.config["current_tier"]]

        return {
            "date": self.daily_usage["date"],
            "tier": self.config["current_tier"],
            "tasks_completed": len(self.daily_usage["tasks"]),
            "total_tokens": self.daily_usage["total_tokens"],
            "total_cost": round(self.daily_usage["total_cost"], 4),
            "daily_limit": tier.get("daily_limit_usd"),
            "budget_used_pct": (
                round((self.daily_usage["total_cost"] / tier["daily_limit_usd"]) * 100, 1)
                if tier.get("daily_limit_usd")
                else None
            ),
            "recent_tasks": self.daily_usage["tasks"][-5:]  # Last 5
        }

    def recommend_model(self, task_type: str, current_model: str) -> str:
        """Recommend model based on budget and task"""

        tier = self.config["budget_tiers"][self.config["current_tier"]]
        daily_limit = tier.get("daily_limit_usd")

        # Check if we should fallback
        if daily_limit and self.daily_usage["total_cost"] >= (daily_limit * tier["fallback_trigger"]):
            # Use cheaper model
            routing = self.config["routing_rules"]["task_routing"].get(task_type, {})
            fallback = routing.get("fallback", "claude-haiku")

            logger.warning(
                f"Budget trigger reached! Recommending fallback: "
                f"{current_model} → {fallback}"
            )
            return fallback

        # Use preferred model
        routing = self.config["routing_rules"]["task_routing"].get(task_type, {})
        preferred = routing.get("preferred", [current_model])

        # Return first available preferred model
        for model in preferred:
            if model in self.config["model_pricing"]:
                return model

        return current_model

    def print_summary(self):
        """Print daily usage summary"""
        summary = self.get_daily_summary()

        print("\n" + "="*60)
        print("💰 TOKEN BUDGET SUMMARY")
        print("="*60)
        print(f"📅 Date: {summary['date']}")
        print(f"🎯 Tier: {summary['tier']}")
        print(f"✅ Tasks: {summary['tasks_completed']}")
        print(f"🔤 Tokens: {summary['total_tokens']:,}")
        print(f"💵 Cost: ${summary['total_cost']:.4f}")

        if summary['daily_limit']:
            print(f"📊 Budget Used: {summary['budget_used_pct']}% (${summary['total_cost']:.2f} / ${summary['daily_limit']:.2f})")

        print("\n📋 Recent Tasks:")
        for task in summary['recent_tasks']:
            print(
                f"  • {task['task_type']} | {task['model']} | "
                f"{task['total_tokens']:,} tokens | ${task['cost_usd']:.4f}"
            )

        print("="*60 + "\n")


# ====== CLI ======
def main():
    """CLI interface with argparse"""

    import argparse

    parser = argparse.ArgumentParser(
        description='Token Budget Tracker - Shannon-Style Production Monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show daily summary
  python token-tracker.py summary

  # Record token usage (from VSCode hook)
  python token-tracker.py record --task-type research --model claude-sonnet-4-5 --input-tokens 1000 --output-tokens 500

  # Record with estimation flag
  python token-tracker.py record --task-type general --model claude-haiku --input-tokens 500 --output-tokens 250 --estimated

  # Get model recommendation
  python token-tracker.py recommend --task-type research --current-model claude-sonnet-4-5
        """
    )

    parser.add_argument('command', nargs='?', default='summary',
                        choices=['summary', 'record', 'recommend'],
                        help='Command to run (default: summary)')

    # Record command arguments
    parser.add_argument('--task-type', type=str,
                        help='Task type (research, debugging, retrospective, code_quality, general)')
    parser.add_argument('--model', type=str,
                        help='Model name (e.g., claude-sonnet-4-5, claude-haiku-4-20250919)')
    parser.add_argument('--input-tokens', type=int,
                        help='Input tokens consumed')
    parser.add_argument('--output-tokens', type=int,
                        help='Output tokens consumed')
    parser.add_argument('--estimated', type=str, default='false',
                        help='Is this an estimated recording? (true/false)')
    parser.add_argument('--notes', type=str, default='',
                        help='Optional notes about this usage')
    parser.add_argument('--task-id', type=str,
                        help='Custom task ID (auto-generated if not provided)')

    # Recommend command arguments
    parser.add_argument('--current-model', type=str, default='claude-sonnet-4-5',
                        help='Current model for recommendation')

    args = parser.parse_args()

    tracker = TokenTracker()

    if args.command == 'summary':
        tracker.print_summary()

    elif args.command == 'record':
        # Validate required arguments
        if not all([args.task_type, args.model, args.input_tokens is not None, args.output_tokens is not None]):
            parser.error("--task-type, --model, --input-tokens, --output-tokens are required for 'record' command")

        # Generate task ID if not provided
        task_id = args.task_id or f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Parse estimated flag
        is_estimated = args.estimated.lower() in ('true', '1', 'yes', 'on')

        # Record usage
        result = tracker.record_usage(
            task_id=task_id,
            task_type=args.task_type,
            model=args.model,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            notes=args.notes,
            estimated=is_estimated
        )

        total_tokens = args.input_tokens + args.output_tokens
        est_marker = " (estimated)" if is_estimated else ""
        print(f"✅ Recorded: {total_tokens:,} tokens ({args.model}){est_marker}")

        if result["alerts"]:
            print("\n⚠️  Alerts:")
            for alert in result["alerts"]:
                print(f"  • {alert}")

    elif args.command == 'recommend':
        recommended = tracker.recommend_model(args.task_type or 'general', args.current_model)
        print(f"💡 Recommended: {recommended} (for task: {args.task_type or 'general'})")


if __name__ == "__main__":
    main()
