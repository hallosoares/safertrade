#!/usr/bin/env python3
"""
Unified stream configuration for SaferTrade
"""

import os

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://:your_redis_password@localhost:6379/0")

# Stream names
STREAMS = {
    # Raw signal sources
    "bridge_arbitrage": "bridge.arbitrage",
    "gaps_ready": "gaps.ready",
    "gaps_ethereum": "gaps.ethereum",
    "gaps_arbitrum": "gaps.arbitrum",
    "mevshare_raw": "mevshare.raw",
    # Processed detection streams
    "safertrade_detections": "safertrade.detections",
    "safertrade_selected": "safertrade.selected",
    "safertrade_results": "safertrade.results",
    "safertrade_guard_state": "safertrade.guard_state",
    "safertrade_intents": "safertrade.intents",
    "intel_visual_patterns": "intel:visual:patterns",
    "intel_arb_forecast": "intel:arb_forecast",
    "intel_ensemble_votes": "intel:ensemble:votes",
    "intel_preposition": "intel:preposition",
    "strategy_evolution_proposals": "strategy:evolution:proposals",
    # Validation and capsule streams
    "validation_capsules": "validation:capsules",
    "execution_commands": "execution:commands",
}

# Consumer groups
CONSUMER_GROUPS = {
    # SaferTrade Selection Engine
    "safertrade_selection": "g:st_select",
    # SaferTrade Validation
    "safertrade_validation": "g:st_validate",
    "safertrade_real_validation": "g:st_real_validate",
    # SaferTrade Guard/Execution
    "safertrade_guard": "g:st_guard",
    "safertrade_execution": "g:st_exec",
    # Specialized consumers
    "gap_finder": "g:gap_finder",
    "arbitrage_bridge": "g:bridge_arb",
}

# Default start positions
DEFAULT_START = os.getenv("START_FROM", "$")

# Validation thresholds
VALIDATION_THRESHOLDS = {
    "min_profit_bps": int(os.getenv("MIN_PROFIT_BPS", "300")),  # 3%
    "min_confidence": int(os.getenv("MIN_CONFIDENCE", "60")),
    "min_pool_usd": int(os.getenv("MIN_POOL_USD", "250000")),
    "max_gas_gwei": int(os.getenv("MAX_GAS_GWEI", "80")),
    "target_min_edge_bps": int(os.getenv("TARGET_MIN_EDGE_BPS", "6")),
}

# Guard settings
GUARD_SETTINGS = {
    "error_rate_threshold": float(os.getenv("GUARD_ERROR_THRESHOLD", "0.15")),  # 15%
    "min_edge_bps": int(os.getenv("GUARD_MIN_EDGE_BPS", "300")),
    "min_validation_score": int(os.getenv("GUARD_MIN_SCORE", "60")),
    "window_size": int(os.getenv("GUARD_WINDOW_SIZE", "20")),
}


def get_redis_client():
    """Get configured Redis client (delegates to centralized client)."""
    try:
        from shared.redis_client import get_redis_client as _get

        return _get()
    except Exception:
        import redis

        return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def get_stream_name(key):
    """Get stream name by key"""
    return STREAMS.get(key, key)


def get_consumer_group(key):
    """Get consumer group by key"""
    return CONSUMER_GROUPS.get(key, f"g:{key}")
