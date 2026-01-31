#!/usr/bin/env python3
"""
Multi-Provider Router - Shannon-Style
Inspired by Kocoro-lab/Shannon framework

Routes requests to appropriate AI providers based on:
- Task type
- Budget constraints
- Model availability
- Cost optimization
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

# ====== CONFIGURATION ======
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "token-budget-config.yaml"


class Provider(Enum):
    """AI Providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"
    LOCAL = "local"


class ModelTier(Enum):
    """Model Tiers by Cost"""
    FREE = "free"
    CHEAPEST = "cheapest"
    STANDARD = "standard"
    PREMIUM = "premium"


class MultiProviderRouter:
    """Route requests to appropriate AI providers"""

    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration"""
        if not self.config_path.exists():
            return self._default_config()

        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "model_pricing": {
                "claude-haiku": {"input": 0.25, "output": 1.25, "provider": "anthropic"},
                "claude-sonnet-4-5": {"input": 3.0, "output": 15.0, "provider": "anthropic"},
                "gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "openai"},
                "deepseek-chat": {"input": 0.14, "output": 0.28, "provider": "deepseek"},
                "gemini-flash": {"input": 0.0, "output": 0.0, "provider": "google"},
            },
            "routing_rules": {
                "task_routing": {
                    "research": {"preferred": ["gemini-flash"], "fallback": "claude-haiku"},
                    "code_simple": {"preferred": ["deepseek-coder"], "fallback": "claude-haiku"},
                    "code_quality": {"preferred": ["claude-opus"], "fallback": "claude-sonnet-4-5"},
                }
            }
        }

    def get_models_by_tier(self, tier: ModelTier) -> List[str]:
        """Get models by cost tier"""

        pricing = self.config["model_pricing"]
        models = []

        for model, costs in pricing.items():
            avg_cost = (costs["input"] + costs["output"]) / 2

            if tier == ModelTier.FREE and avg_cost == 0:
                models.append(model)
            elif tier == ModelTier.CHEAPEST and 0 < avg_cost <= 0.5:
                models.append(model)
            elif tier == ModelTier.STANDARD and 0.5 < avg_cost <= 5:
                models.append(model)
            elif tier == ModelTier.PREMIUM and avg_cost > 5:
                models.append(model)

        return sorted(models, key=lambda m: pricing[m]["input"])

    def recommend_model(
        self,
        task_type: str,
        current_budget_pct: float = 0.0,
        current_model: Optional[str] = None,
        preferred_tier: Optional[ModelTier] = None
    ) -> Dict[str, Any]:
        """Recommend model for task"""

        # Get routing rules for task type
        routing = self.config.get("routing_rules", {}).get("task_routing", {}).get(task_type, {})

        # Budget-aware routing
        tier_config = self.config["budget_tiers"][self.config["current_tier"]]
        fallback_trigger = tier_config.get("fallback_trigger", 0.80)

        # If budget is tight, use cheaper tier
        if current_budget_pct >= fallback_trigger:
            preferred_tier = ModelTier.CHEAPEST
        elif preferred_tier is None:
            preferred_tier = ModelTier.STANDARD

        # Get preferred models
        if routing.get("preferred"):
            candidates = routing["preferred"]
        else:
            # Get models by tier
            candidates = self.get_models_by_tier(preferred_tier)

        # Filter by availability
        available = [m for m in candidates if m in self.config["model_pricing"]]

        if not available:
            # Use fallback
            fallback = routing.get("fallback")
            if fallback:
                return {
                    "model": fallback,
                    "reason": f"fallback for {task_type}",
                    "tier": self._get_model_tier(fallback)
                }

            # Use cheapest available
            return {
                "model": self.get_models_by_tier(ModelTier.CHEAPEST)[0],
                "reason": "cheapest available",
                "tier": ModelTier.CHEAPEST
            }

        # Return first available
        model = available[0]
        return {
            "model": model,
            "reason": f"preferred for {task_type}",
            "tier": self._get_model_tier(model)
        }

    def _get_model_tier(self, model: str) -> ModelTier:
        """Get tier for a model"""

        if model not in self.config["model_pricing"]:
            return ModelTier.STANDARD

        avg_cost = (self.config["model_pricing"][model]["input"] +
                   self.config["model_pricing"][model]["output"]) / 2

        if avg_cost == 0:
            return ModelTier.FREE
        elif avg_cost <= 0.5:
            return ModelTier.CHEAPEST
        elif avg_cost <= 5:
            return ModelTier.STANDARD
        else:
            return ModelTier.PREMIUM

    def compare_models(self, task_type: str, input_tokens: int, output_tokens: int) -> List[Dict]:
        """Compare cost across models for a task"""

        results = []

        for model, pricing in self.config["model_pricing"].items():
            input_cost = (input_tokens / 1_000_000) * pricing["input"]
            output_cost = (output_tokens / 1_000_000) * pricing["output"]
            total_cost = input_cost + output_cost

            results.append({
                "model": model,
                "provider": pricing.get("provider", "unknown"),
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
                "total_cost": round(total_cost, 6),
                "tier": self._get_model_tier(model).value
            })

        # Sort by cost
        return sorted(results, key=lambda x: x["total_cost"])

    def print_routing_table(self):
        """Print routing rules"""

        print("\n" + "="*80)
        print("🔀 MULTI-PROVIDER ROUTING TABLE")
        print("="*80)

        print("\n📊 Models by Tier:")
        for tier in [ModelTier.FREE, ModelTier.CHEAPEST, ModelTier.STANDARD, ModelTier.PREMIUM]:
            models = self.get_models_by_tier(tier)
            if models:
                print(f"\n  {tier.value.upper()}:")
                for model in models:
                    pricing = self.config["model_pricing"][model]
                    avg = (pricing["input"] + pricing["output"]) / 2
                    print(f"    • {model:40s} ${avg:6.2f}/MTok")

        print("\n🎯 Task Routing Rules:")
        routing = self.config.get("routing_rules", {}).get("task_routing", {})
        for task_type, rules in routing.items():
            print(f"\n  {task_type}:")
            print(f"    Preferred: {', '.join(rules.get('preferred', ['N/A']))}")
            print(f"    Fallback: {rules.get('fallback', 'N/A')}")

        print("\n" + "="*80 + "\n")


# ====== CLI ======
def main():
    """CLI interface"""

    router = MultiProviderRouter()

    import sys

    if len(sys.argv) < 2:
        router.print_routing_table()
        return

    command = sys.argv[1]

    if command == "recommend":
        task_type = sys.argv[2] if len(sys.argv) > 2 else "general"
        budget_pct = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

        recommendation = router.recommend_model(task_type, budget_pct)

        print(f"\n💡 Recommendation for '{task_type}':")
        print(f"  Model: {recommendation['model']}")
        print(f"  Tier: {recommendation['tier'].value}")
        print(f"  Reason: {recommendation['reason']}")

    elif command == "compare":
        task_type = sys.argv[2] if len(sys.argv) > 2 else "general"
        input_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
        output_tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 2000

        print(f"\n💰 Cost comparison for '{task_type}' ({input_tokens + output_tokens:,} tokens):")
        print("-" * 80)

        results = router.compare_models(task_type, input_tokens, output_tokens)

        for r in results:
            print(
                f"  {r['model']:35s} | ${r['total_cost']:8.6f} | "
                f"{r['tier']:10s} | {r['provider']}"
            )

    elif command == "table":
        router.print_routing_table()

    else:
        print(f"Unknown command: {command}")
        print("Available: recommend, compare, table")


if __name__ == "__main__":
    main()
