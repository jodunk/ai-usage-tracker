"""
Event Types Definition for Scudd Oracle SSE Streaming

Defines all event types that can be streamed to clients via /events endpoint.
Each event has a type, timestamp, and structured data.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from enum import Enum
import json


class EventType(str, Enum):
    """All event types that can be streamed"""

    # Token & Cost Events
    TOKEN_USAGE = "token_usage"  # When tokens are used
    COST_UPDATE = "cost_update"  # When cost is calculated
    BUDGET_ALERT = "budget_alert"  # When budget threshold is breached

    # Task Events
    TASK_START = "task_start"  # When a task begins
    TASK_COMPLETE = "task_complete"  # When a task finishes
    TASK_ERROR = "task_error"  # When a task fails

    # Model Events
    MODEL_SWITCH = "model_switch"  # When switching between models
    MODEL_FALLBACK = "model_fallback"  # When falling back to cheaper model

    # System Events
    SYSTEM_START = "system_start"  # When exporter starts
    HEARTBEAT = "heartbeat"  # Periodic heartbeat (every 30s)


@dataclass
class Event:
    """
    Base event structure

    All events follow this format:
    {
      "type": "event_type",
      "timestamp": "2026-01-30T15:45:00.123456Z",
      "data": {...}
    }
    """

    type: EventType
    data: Dict[str, Any]
    timestamp: str = None

    def __post_init__(self):
        """Set timestamp to current UTC time if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_sse(self) -> str:
        """
        Convert to Server-Sent Events format

        SSE format:
        event: event_type
        data: {...json...}

        Returns:
            str: SSE-formatted string
        """
        event_line = f"event: {self.type.value}"
        data_line = f"data: {json.dumps(asdict(self))}"
        return f"{event_line}\n{data_line}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }


# ============================================================================
# Event Constructors
# ============================================================================

def token_usage_event(
    model: str,
    tokens: int,
    cost_usd: float,
    task_id: Optional[str] = None,
    task_type: Optional[str] = None,
) -> Event:
    """
    Token usage event

    Emitted when tokens are consumed

    Args:
        model: Model name (e.g., "claude-3-5-sonnet")
        tokens: Number of tokens used
        cost_usd: Cost in USD
        task_id: Optional task ID
        task_type: Optional task type

    Example:
        >>> token_usage_event("claude-3-5-sonnet", 1000, 0.003, "task-123")
        Event(type='token_usage', data={...})
    """
    return Event(
        type=EventType.TOKEN_USAGE,
        data={
            "model": model,
            "tokens": tokens,
            "cost_usd": round(cost_usd, 6),
            "task_id": task_id,
            "task_type": task_type,
        },
    )


def cost_update_event(
    total_cost_usd: float,
    total_tokens: int,
    budget_percent: float,
    budget_remaining_usd: float,
) -> Event:
    """
    Cost update event

    Emitted when total cost is recalculated

    Args:
        total_cost_usd: Total cost today
        total_tokens: Total tokens used
        budget_percent: Budget usage percentage (0-100)
        budget_remaining_usd: Remaining budget in USD
    """
    return Event(
        type=EventType.COST_UPDATE,
        data={
            "total_cost_usd": round(total_cost_usd, 4),
            "total_tokens": total_tokens,
            "budget_percent": round(budget_percent, 2),
            "budget_remaining_usd": round(budget_remaining_usd, 2),
        },
    )


def budget_alert_event(
    level: str,  # "warning", "critical"
    budget_percent: float,
    budget_remaining_usd: float,
    message: str,
) -> Event:
    """
    Budget alert event

    Emitted when budget threshold is breached

    Args:
        level: Alert level ("warning" or "critical")
        budget_percent: Current budget usage percentage
        budget_remaining_usd: Remaining budget
        message: Alert message

    Example:
        >>> budget_alert_event("warning", 85.5, 1.45, "Budget 85% used")
        Event(type='budget_alert', data={...})
    """
    return Event(
        type=EventType.BUDGET_ALERT,
        data={
            "level": level,
            "budget_percent": round(budget_percent, 2),
            "budget_remaining_usd": round(budget_remaining_usd, 2),
            "message": message,
        },
    )


def task_start_event(
    task_id: str,
    task_type: str,
    model: str,
    estimated_tokens: Optional[int] = None,
) -> Event:
    """
    Task start event

    Emitted when a task begins execution

    Args:
        task_id: Unique task identifier
        task_type: Type of task
        model: Model being used
        estimated_tokens: Optional estimated token count
    """
    return Event(
        type=EventType.TASK_START,
        data={
            "task_id": task_id,
            "task_type": task_type,
            "model": model,
            "estimated_tokens": estimated_tokens,
        },
    )


def task_complete_event(
    task_id: str,
    task_type: str,
    model: str,
    tokens_used: int,
    cost_usd: float,
    duration_ms: int,
) -> Event:
    """
    Task complete event

    Emitted when a task finishes successfully

    Args:
        task_id: Unique task identifier
        task_type: Type of task
        model: Model that was used
        tokens_used: Total tokens consumed
        cost_usd: Cost in USD
        duration_ms: Duration in milliseconds
    """
    return Event(
        type=EventType.TASK_COMPLETE,
        data={
            "task_id": task_id,
            "task_type": task_type,
            "model": model,
            "tokens_used": tokens_used,
            "cost_usd": round(cost_usd, 6),
            "duration_ms": duration_ms,
        },
    )


def task_error_event(
    task_id: str,
    task_type: str,
    model: str,
    error_message: str,
    tokens_used: Optional[int] = None,
) -> Event:
    """
    Task error event

    Emitted when a task fails

    Args:
        task_id: Unique task identifier
        task_type: Type of task
        model: Model that was being used
        error_message: Error description
        tokens_used: Optional tokens used before failure
    """
    return Event(
        type=EventType.TASK_ERROR,
        data={
            "task_id": task_id,
            "task_type": task_type,
            "model": model,
            "error_message": error_message,
            "tokens_used": tokens_used,
        },
    )


def model_switch_event(
    from_model: str,
    to_model: str,
    reason: str,
) -> Event:
    """
    Model switch event

    Emitted when switching between models

    Args:
        from_model: Previous model name
        to_model: New model name
        reason: Reason for switch (e.g., "budget_exceeded", "api_error")

    Example:
        >>> model_switch_event("claude-3-5-sonnet", "gpt-4o-mini", "cost_optimization")
        Event(type='model_switch', data={...})
    """
    return Event(
        type=EventType.MODEL_SWITCH,
        data={
            "from_model": from_model,
            "to_model": to_model,
            "reason": reason,
        },
    )


def model_fallback_event(
    primary_model: str,
    fallback_model: str,
    reason: str,
) -> Event:
    """
    Model fallback event

    Emitted when falling back to cheaper/backup model

    Args:
        primary_model: Model that failed
        fallback_model: Model falling back to
        reason: Reason for fallback
    """
    return Event(
        type=EventType.MODEL_FALLBACK,
        data={
            "primary_model": primary_model,
            "fallback_model": fallback_model,
            "reason": reason,
        },
    )


def system_start_event(
    version: str,
    config: Dict[str, Any],
) -> Event:
    """
    System start event

    Emitted when the exporter starts up

    Args:
        version: Exporter version
        config: Configuration snapshot
    """
    return Event(
        type=EventType.SYSTEM_START,
        data={
            "version": version,
            "config": config,
        },
    )


def heartbeat_event(
    uptime_seconds: int,
    total_tasks: int,
    total_cost_usd: float,
) -> Event:
    """
    Heartbeat event

    Emitted periodically (every 30s) to show system is alive

    Args:
        uptime_seconds: Uptime in seconds
        total_tasks: Total tasks completed
        total_cost_usd: Total cost since start
    """
    return Event(
        type=EventType.HEARTBEAT,
        data={
            "uptime_seconds": uptime_seconds,
            "total_tasks": total_tasks,
            "total_cost_usd": round(total_cost_usd, 4),
        },
    )


# ============================================================================
# Event Utilities
# ============================================================================

def parse_event(json_str: str) -> Optional[Event]:
    """
    Parse event from JSON string

    Args:
        json_str: JSON string representation of event

    Returns:
        Event object or None if parsing fails
    """
    try:
        data = json.loads(json_str)
        return Event(
            type=EventType(data["type"]),
            timestamp=data.get("timestamp"),
            data=data["data"],
        )
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def validate_event(event: Event) -> bool:
    """
    Validate event structure

    Args:
        event: Event to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(event, Event):
        return False

    if not isinstance(event.type, EventType):
        return False

    if not isinstance(event.data, dict):
        return False

    if not event.timestamp:
        return False

    return True
