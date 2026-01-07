#!/usr/bin/env python3
# SPDX-License-Identifier: BUSL-1.1
"""
gas_price_optimizer.py - SaferTrade Gas Price Optimization Engine

Analyzes gas patterns to optimize transaction timing and reduce costs.
Monitors network congestion, gas price dynamics, and transaction prioritization
to recommend optimal gas prices for minimal costs and maximal execution success.

Core functionality:
- Monitors network congestion and gas price dynamics
- Optimizes transaction timing to reduce gas costs
- Analyzes gas price correlation with transaction success
- Provides gas price recommendations for minimal costs

TRUE PERFECTION v2 - 2025-12-23:
- Added configurable environment variables for all thresholds
- Added AccuracyTracker integration for prediction validation
- Added maxlen to Redis stream publishing
- Made all database timeouts configurable

TRUE PERFECTION v3 - 2025-12-23:
- Added VERSION constant for tracking
"""

# Version constant for tracking
GAS_PRICE_OPTIMIZER_VERSION = "2.0.0"

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import redis
import requests
from web3 import Web3

# Add project root to path for proper imports
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from shared.chains import get_chain_manager
from shared.database_config import get_main_db_path
from shared.env import load_env
from shared.logging_setup import setup_logging
from shared.paths import ROOT_DIR

# Load environment variables
load_env(ROOT_DIR)

# Setup logging early
setup_logging("gas_price_optimizer", ROOT_DIR)
logger = logging.getLogger("gas_price_optimizer")

# ============================================================================
# CONFIGURABLE ENVIRONMENT VARIABLES
# All thresholds and parameters are configurable via environment
# ============================================================================

# Gas price thresholds (in gwei)
GAS_LOW_THRESHOLD = int(os.getenv("GAS_LOW_THRESHOLD", "20"))
GAS_MEDIUM_THRESHOLD = int(os.getenv("GAS_MEDIUM_THRESHOLD", "50"))
GAS_HIGH_THRESHOLD = int(os.getenv("GAS_HIGH_THRESHOLD", "100"))
GAS_EXTREME_THRESHOLD = int(os.getenv("GAS_EXTREME_THRESHOLD", "200"))

# Network congestion thresholds
GAS_CONGESTION_LOW = float(os.getenv("GAS_CONGESTION_LOW", "0.3"))
GAS_CONGESTION_MEDIUM = float(os.getenv("GAS_CONGESTION_MEDIUM", "0.6"))
GAS_CONGESTION_HIGH = float(os.getenv("GAS_CONGESTION_HIGH", "0.8"))
GAS_CONGESTION_EXTREME = float(os.getenv("GAS_CONGESTION_EXTREME", "0.95"))

# MEV activity impact thresholds
GAS_MEV_LOW_IMPACT = float(os.getenv("GAS_MEV_LOW_IMPACT", "0.2"))
GAS_MEV_MEDIUM_IMPACT = float(os.getenv("GAS_MEV_MEDIUM_IMPACT", "0.5"))
GAS_MEV_HIGH_IMPACT = float(os.getenv("GAS_MEV_HIGH_IMPACT", "0.8"))

# MEV gas premiums (in gwei)
GAS_MEV_PREMIUM_HIGH = int(os.getenv("GAS_MEV_PREMIUM_HIGH", "20"))
GAS_MEV_PREMIUM_MEDIUM = int(os.getenv("GAS_MEV_PREMIUM_MEDIUM", "10"))
GAS_MEV_PREMIUM_LOW = int(os.getenv("GAS_MEV_PREMIUM_LOW", "5"))

# Bot competition premiums (in gwei)
GAS_BOT_PREMIUM_HIGH = int(os.getenv("GAS_BOT_PREMIUM_HIGH", "15"))
GAS_BOT_PREMIUM_MEDIUM = int(os.getenv("GAS_BOT_PREMIUM_MEDIUM", "5"))

# Time-based optimization windows (in minutes)
GAS_OPTIMAL_TIME_WINDOW = int(os.getenv("GAS_OPTIMAL_TIME_WINDOW", "30"))
GAS_SAFE_BUFFER_PERIOD = int(os.getenv("GAS_SAFE_BUFFER_PERIOD", "10"))

# Priority multipliers
GAS_PRIORITY_HIGH_MULT = float(os.getenv("GAS_PRIORITY_HIGH_MULT", "1.2"))
GAS_PRIORITY_LOW_MULT = float(os.getenv("GAS_PRIORITY_LOW_MULT", "0.8"))

# Database and Redis configuration
GAS_DB_TIMEOUT = float(os.getenv("GAS_DB_TIMEOUT", "30.0"))
GAS_REDIS_STREAM_MAXLEN = int(os.getenv("GAS_REDIS_STREAM_MAXLEN", "10000"))
GAS_SIGNIFICANT_DIFF_GWEI = int(os.getenv("GAS_SIGNIFICANT_DIFF_GWEI", "10"))

# Monitoring configuration
GAS_MONITOR_INTERVAL_SECONDS = int(os.getenv("GAS_MONITOR_INTERVAL_SECONDS", "300"))
GAS_ERROR_RETRY_SECONDS = int(os.getenv("GAS_ERROR_RETRY_SECONDS", "10"))

# AccuracyTracker lazy initialization
_accuracy_tracker = None


def get_accuracy_tracker():
    """Lazy initialization of AccuracyTracker to avoid circular imports"""
    global _accuracy_tracker
    if _accuracy_tracker is None:
        try:
            from engines.accuracy_tracker import AccuracyTracker

            _accuracy_tracker = AccuracyTracker()
            logger.info("AccuracyTracker initialized for gas_price_optimizer")
        except Exception as e:
            logger.warning(f"Could not initialize AccuracyTracker: {e}")
            _accuracy_tracker = False  # Mark as unavailable
    return _accuracy_tracker if _accuracy_tracker else None


# NOTE: Avoid importing heavy engine modules at import time. We'll import them lazily
# inside the class initializer so that `--health` can run fast without side effects.
# Engine imports need engines directory in path
_engines_dir = Path(__file__).resolve().parent
if str(_engines_dir) not in sys.path:
    sys.path.insert(0, str(_engines_dir))


class GasPriceOptimizer:
    def __init__(self):
        # Lazy imports to avoid heavy side-effects during health checks
        from protocol_health_monitor import ProtocolHealthMonitor  # noqa: WPS433
        from real_mev_analyzer import RealMEVAnalyzer  # noqa: WPS433
        from transaction_analyzer import TransactionAnalyzer  # noqa: WPS433

        # Initialize Redis connection for real-time data streaming
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )

        # Initialize database connection
        self.db_path = get_main_db_path()

        # Initialize supporting engines
        self.protocol_monitor = ProtocolHealthMonitor()
        self.mev_analyzer = RealMEVAnalyzer()
        self.transaction_analyzer = TransactionAnalyzer()

        # Initialize chain manager for multi-chain support
        self.chain_manager = get_chain_manager()

        # Initialize Web3 instance
        self.w3 = Web3()

        # Setup logging
        setup_logging("gas_price_optimizer", ROOT_DIR)
        self.logger = logging.getLogger("gas_price_optimizer")

        # Gas optimization parameters
        self.gas_params = self._initialize_gas_params()

        # Initialize database table for gas price optimization
        self._init_database()

        self.logger.info("Gas Price Optimizer initialized")

    def _init_database(self):
        """Initialize database table for gas price optimization data"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=GAS_DB_TIMEOUT)
            cursor = conn.cursor()

            # Create table for gas price optimization
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gas_price_optimization (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    chain TEXT,
                    current_gas_price REAL,
                    optimized_gas_price REAL,
                    network_congestion REAL,
                    mev_activity REAL,
                    transaction_success_rate REAL,
                    cost_savings_usd REAL,
                    optimization_score REAL,
                    risk_level TEXT
                )
            """)

            conn.commit()
            conn.close()
            self.logger.info("Gas price optimization database initialized")
        except Exception as e:
            self.logger.error(
                f"Error initializing gas price optimization database: {e}"
            )

    def _initialize_gas_params(self) -> Dict:
        """Initialize gas optimization parameters and thresholds from config"""
        return {
            # Gas price thresholds (in gwei)
            "low_gas_threshold": GAS_LOW_THRESHOLD,
            "medium_gas_threshold": GAS_MEDIUM_THRESHOLD,
            "high_gas_threshold": GAS_HIGH_THRESHOLD,
            "extreme_gas_threshold": GAS_EXTREME_THRESHOLD,
            # Network congestion levels
            "low_congestion_threshold": GAS_CONGESTION_LOW,
            "medium_congestion_threshold": GAS_CONGESTION_MEDIUM,
            "high_congestion_threshold": GAS_CONGESTION_HIGH,
            "extreme_congestion_threshold": GAS_CONGESTION_EXTREME,
            # MEV activity impact
            "low_mev_impact": GAS_MEV_LOW_IMPACT,
            "medium_mev_impact": GAS_MEV_MEDIUM_IMPACT,
            "high_mev_impact": GAS_MEV_HIGH_IMPACT,
            # Time-based optimization windows
            "optimal_time_window": GAS_OPTIMAL_TIME_WINDOW,
            "safe_buffer_period": GAS_SAFE_BUFFER_PERIOD,
        }

    def analyze_network_congestion(self, chain: str = "ethereum") -> Dict:
        """
        Analyze current network congestion levels
        """
        try:
            analysis = {
                "network_congestion": 0.0,
                "gas_price_trend": "STABLE",
                "congestion_level": "LOW",
                "recommended_timing": "NOW",
                "congestion_score": 0.0,
            }

            # Get current gas price
            current_gas_price = self._get_current_gas_price(chain)

            # Get network utilization data (with fallback if method not available)
            try:
                if hasattr(self.protocol_monitor, "get_network_utilization"):
                    network_utilization = self.protocol_monitor.get_network_utilization(
                        chain
                    )
                else:
                    # Estimate from gas price if method not available
                    network_utilization = (
                        min(
                            1.0,
                            current_gas_price
                            / self.gas_params["extreme_gas_threshold"],
                        )
                        if current_gas_price
                        else 0.5
                    )
            except Exception as e:
                self.logger.debug(
                    f"Network utilization not available, using gas-based estimate: {e}"
                )
                network_utilization = 0.5

            # Calculate congestion metrics
            congestion_score = 0.0

            # Base congestion on gas price
            if current_gas_price > self.gas_params["extreme_gas_threshold"]:
                congestion_score += 0.4
                analysis["gas_price_trend"] = "EXTREME"
                analysis["congestion_level"] = "EXTREME"
                analysis["recommended_timing"] = (
                    "AVOID"  # Avoid during extreme congestion
                )
            elif current_gas_price > self.gas_params["high_gas_threshold"]:
                congestion_score += 0.3
                analysis["gas_price_trend"] = "HIGH"
                analysis["congestion_level"] = "HIGH"
                analysis["recommended_timing"] = "LATER"  # Wait for lower gas
            elif current_gas_price > self.gas_params["medium_gas_threshold"]:
                congestion_score += 0.2
                analysis["gas_price_trend"] = "MEDIUM"
                analysis["congestion_level"] = "MEDIUM"
                analysis["recommended_timing"] = "SOON"  # Good timing
            elif current_gas_price > self.gas_params["low_gas_threshold"]:
                congestion_score += 0.1
                analysis["gas_price_trend"] = "LOW"
                analysis["congestion_level"] = "LOW"
                analysis["recommended_timing"] = "NOW"  # Optimal timing
            else:
                analysis["gas_price_trend"] = "VERY_LOW"
                analysis["congestion_level"] = "LOW"
                analysis["recommended_timing"] = "NOW"  # Best timing

            # Adjust based on network utilization
            if network_utilization > self.gas_params["extreme_congestion_threshold"]:
                congestion_score += 0.3
                if analysis["congestion_level"] != "EXTREME":
                    analysis["congestion_level"] = "HIGH"
                    analysis["recommended_timing"] = "LATER"
            elif network_utilization > self.gas_params["high_congestion_threshold"]:
                congestion_score += 0.2
                if analysis["congestion_level"] == "LOW":
                    analysis["congestion_level"] = "MEDIUM"
                    analysis["recommended_timing"] = "SOON"
            elif network_utilization > self.gas_params["medium_congestion_threshold"]:
                congestion_score += 0.1
                if analysis["congestion_level"] == "LOW":
                    analysis["congestion_level"] = "MEDIUM"

            analysis["network_congestion"] = min(1.0, congestion_score)
            analysis["congestion_score"] = min(1.0, congestion_score)

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing network congestion: {e}")
            return {
                "network_congestion": 0.0,
                "gas_price_trend": "STABLE",
                "congestion_level": "LOW",
                "recommended_timing": "NOW",
                "congestion_score": 0.0,
            }

    def analyze_mev_impact_on_gas(self, chain: str = "ethereum") -> Dict:
        """
        Analyze MEV activity impact on gas prices
        """
        try:
            analysis = {
                "mev_activity": 0.0,
                "mev_gas_premium": 0.0,
                "mev_impact_level": "LOW",
                "mev_risk_adjustment": 0.0,
                "mev_recommendations": [],
            }

            # Get MEV activity data (with fallback if method not available)
            try:
                if hasattr(self.mev_analyzer, "get_recent_mev_activity"):
                    mev_data = self.mev_analyzer.get_recent_mev_activity(chain)
                else:
                    # Use default empty data if method not available
                    mev_data = {
                        "recent_detections": [],
                        "sandwich_count": 0,
                        "liquidation_count": 0,
                    }
            except Exception as e:
                self.logger.debug(f"MEV activity data not available: {e}")
                mev_data = {
                    "recent_detections": [],
                    "sandwich_count": 0,
                    "liquidation_count": 0,
                }

            # Calculate MEV impact metrics
            mev_activity_score = 0.0
            mev_gas_premium = 0.0

            # Base MEV activity on recent detections
            recent_mev_count = len(mev_data.get("recent_detections", []))
            if recent_mev_count > 10:
                mev_activity_score += 0.4
                mev_gas_premium += GAS_MEV_PREMIUM_HIGH
                analysis["mev_impact_level"] = "HIGH"
                analysis["mev_recommendations"].append(
                    "High MEV activity - consider using private mempool"
                )
            elif recent_mev_count > 5:
                mev_activity_score += 0.3
                mev_gas_premium += GAS_MEV_PREMIUM_MEDIUM
                analysis["mev_impact_level"] = "MEDIUM"
                analysis["mev_recommendations"].append(
                    "Moderate MEV activity - add gas buffer"
                )
            elif recent_mev_count > 0:
                mev_activity_score += 0.2
                mev_gas_premium += GAS_MEV_PREMIUM_LOW
                analysis["mev_impact_level"] = "LOW"
                analysis["mev_recommendations"].append(
                    "Low MEV activity - standard gas pricing"
                )

            # Check for MEV bot competition
            bot_competition = mev_data.get("bot_competition", 0.0)
            if bot_competition > 0.7:
                mev_activity_score += 0.2
                mev_gas_premium += GAS_BOT_PREMIUM_HIGH
                analysis["mev_recommendations"].append(
                    "High bot competition - significant gas premium needed"
                )
            elif bot_competition > 0.4:
                mev_activity_score += 0.1
                mev_gas_premium += GAS_BOT_PREMIUM_MEDIUM
                analysis["mev_recommendations"].append(
                    "Moderate bot competition - slight gas premium needed"
                )

            analysis["mev_activity"] = min(1.0, mev_activity_score)
            analysis["mev_gas_premium"] = mev_gas_premium
            analysis["mev_risk_adjustment"] = (
                mev_gas_premium * 0.1
            )  # 10% of premium as risk adjustment

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing MEV impact on gas: {e}")
            return {
                "mev_activity": 0.0,
                "mev_gas_premium": 0.0,
                "mev_impact_level": "LOW",
                "mev_risk_adjustment": 0.0,
                "mev_recommendations": [],
            }

    def analyze_transaction_success_correlation(self, chain: str = "ethereum") -> Dict:
        """
        Analyze correlation between gas prices and transaction success rates
        """
        try:
            analysis = {
                "success_rate_correlation": 0.0,
                "optimal_gas_range": {},
                "failure_patterns": [],
                "success_recommendations": [],
                "transaction_success_score": 0.0,
            }

            # Get transaction data
            try:
                transaction_data = self.transaction_analyzer.get_recent_transactions(
                    chain
                )
            except NotImplementedError:
                # Method requires real chain API integration - gracefully degrade
                self.logger.debug(
                    "get_recent_transactions requires chain API integration"
                )
                return analysis

            # Calculate success rate correlation with gas prices
            successful_txs = [tx for tx in transaction_data if tx.get("status") == 1]
            failed_txs = [tx for tx in transaction_data if tx.get("status") == 0]

            if not transaction_data:
                return analysis

            # Calculate success rate
            success_rate = (
                len(successful_txs) / len(transaction_data) if transaction_data else 0.0
            )

            # Analyze gas prices for successful vs failed transactions
            successful_gas_prices = [
                tx.get("gas_price_gwei", 0) for tx in successful_txs
            ]
            failed_gas_prices = [tx.get("gas_price_gwei", 0) for tx in failed_txs]

            avg_successful_gas = (
                sum(successful_gas_prices) / len(successful_gas_prices)
                if successful_gas_prices
                else 0
            )
            avg_failed_gas = (
                sum(failed_gas_prices) / len(failed_gas_prices)
                if failed_gas_prices
                else 0
            )

            # Calculate correlation (simplified)
            correlation_score = 0.0
            if avg_successful_gas > 0 and avg_failed_gas > 0:
                # Higher successful gas prices generally indicate better success rates
                gas_difference = avg_successful_gas - avg_failed_gas
                correlation_score = min(
                    1.0, abs(gas_difference) / 50
                )  # Normalize by 50 gwei range

            # Determine optimal gas range
            optimal_min = (
                max(1, avg_successful_gas * 0.8) if avg_successful_gas > 0 else 20
            )
            optimal_max = avg_successful_gas * 1.2 if avg_successful_gas > 0 else 100

            analysis["success_rate_correlation"] = correlation_score
            analysis["optimal_gas_range"] = {
                "min_gas_gwei": round(optimal_min, 1),
                "max_gas_gwei": round(optimal_max, 1),
                "recommended_gas_gwei": round((optimal_min + optimal_max) / 2, 1),
            }

            # Identify failure patterns
            if failed_txs:
                low_gas_failures = [
                    tx for tx in failed_txs if tx.get("gas_price_gwei", 100) < 20
                ]
                if len(low_gas_failures) / len(failed_txs) > 0.5:
                    analysis["failure_patterns"].append(
                        "Low gas price failures (>50% of failures)"
                    )
                    analysis["success_recommendations"].append(
                        "Avoid gas prices <20 gwei for critical transactions"
                    )

            # Calculate transaction success score
            success_score = success_rate * 0.7 + correlation_score * 0.3
            analysis["transaction_success_score"] = min(1.0, success_score)

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing transaction success correlation: {e}")
            return {
                "success_rate_correlation": 0.0,
                "optimal_gas_range": {},
                "failure_patterns": [],
                "success_recommendations": [],
                "transaction_success_score": 0.0,
            }

    def calculate_optimized_gas_price(
        self, chain: str = "ethereum", transaction_priority: str = "medium"
    ) -> Dict:
        """
        Calculate optimized gas price based on all factors
        """
        try:
            self.logger.info(
                f"Calculating optimized gas price for {chain} with priority: {transaction_priority}"
            )

            # Get current gas price
            current_gas_price = self._get_current_gas_price(chain)

            # Analyze network congestion
            congestion_analysis = self.analyze_network_congestion(chain)

            # Analyze MEV impact
            mev_analysis = self.analyze_mev_impact_on_gas(chain)

            # Analyze transaction success correlation
            success_analysis = self.analyze_transaction_success_correlation(chain)

            # Calculate base optimized gas price
            base_gas_price = current_gas_price

            # Adjust for network congestion
            congestion_multiplier = 1.0
            if congestion_analysis["congestion_level"] == "EXTREME":
                congestion_multiplier = 0.7  # Reduce during extreme congestion (wait)
            elif congestion_analysis["congestion_level"] == "HIGH":
                congestion_multiplier = 0.8  # Slightly reduce during high congestion
            elif congestion_analysis["congestion_level"] == "LOW":
                congestion_multiplier = (
                    1.1  # Slightly increase during low congestion (faster execution)
                )

            # Adjust for MEV activity
            mev_gas_premium = mev_analysis.get("mev_gas_premium", 0.0)

            # Adjust for transaction priority
            priority_multiplier = 1.0
            if transaction_priority == "high":
                priority_multiplier = GAS_PRIORITY_HIGH_MULT
            elif transaction_priority == "low":
                priority_multiplier = GAS_PRIORITY_LOW_MULT

            # Calculate optimized gas price
            optimized_gas_price = (
                base_gas_price * congestion_multiplier
                + mev_gas_premium
                + (base_gas_price * (priority_multiplier - 1.0))
            )

            # Apply optimal range constraints
            optimal_range = success_analysis.get("optimal_gas_range", {})
            if optimal_range:
                min_gas = optimal_range.get("min_gas_gwei", 20)
                max_gas = optimal_range.get("max_gas_gwei", 200)
                optimized_gas_price = max(min_gas, min(max_gas, optimized_gas_price))

            # Calculate cost savings potential
            cost_savings_usd = (
                abs(current_gas_price - optimized_gas_price) * 0.01
            )  # Approximate savings per transaction

            # Determine optimization score (0-1, higher is better optimization)
            optimization_score = 0.0
            if current_gas_price > 0:
                # Savings potential contributes to score
                savings_ratio = (
                    abs(current_gas_price - optimized_gas_price) / current_gas_price
                )
                optimization_score += min(
                    0.5, savings_ratio * 2
                )  # Up to 50% of score from savings

                # Success rate improvement contributes to score
                optimization_score += (
                    success_analysis.get("transaction_success_score", 0.0) * 0.3
                )

                # Congestion avoidance contributes to score
                optimization_score += (
                    1 - congestion_analysis.get("congestion_score", 0.0)
                ) * 0.2

            optimization_score = min(1.0, optimization_score)

            # Determine risk level
            risk_level = "LOW"
            if optimization_score > 0.7:
                risk_level = "CRITICAL"
            elif optimization_score > 0.4:
                risk_level = "HIGH"
            elif optimization_score > 0.2:
                risk_level = "MEDIUM"

            # Store calculation in database
            self._store_calculation(
                chain=chain,
                current_gas_price=current_gas_price,
                optimized_gas_price=optimized_gas_price,
                network_congestion=congestion_analysis.get("network_congestion", 0.0),
                mev_activity=mev_analysis.get("mev_activity", 0.0),
                transaction_success_rate=success_analysis.get(
                    "transaction_success_score", 0.0
                ),
                cost_savings_usd=cost_savings_usd,
                optimization_score=optimization_score,
                risk_level=risk_level,
            )

            # Prepare comprehensive result
            result = {
                "chain": chain,
                "timestamp": datetime.utcnow().isoformat(),
                "current_gas_price_gwei": round(current_gas_price, 1),
                "optimized_gas_price_gwei": round(optimized_gas_price, 1),
                "gas_savings_potential_usd": round(cost_savings_usd, 2),
                "optimization_score": round(optimization_score, 3),
                "risk_level": risk_level,
                "network_congestion_analysis": congestion_analysis,
                "mev_impact_analysis": mev_analysis,
                "transaction_success_analysis": success_analysis,
                "priority_setting": transaction_priority,
                "recommended_action": self._get_recommendation(
                    optimized_gas_price,
                    current_gas_price,
                    risk_level,
                    congestion_analysis,
                    mev_analysis,
                ),
                "confidence": round(min(1.0, optimization_score / 0.3), 3)
                if optimization_score > 0.3
                else 0.0,
            }

            # Publish significant findings to Redis
            if abs(current_gas_price - optimized_gas_price) > GAS_SIGNIFICANT_DIFF_GWEI:
                self.redis_client.xadd(
                    "signals.gas_optimizer",
                    {
                        "chain": chain,
                        "current_gas_price": result["current_gas_price_gwei"],
                        "optimized_gas_price": result["optimized_gas_price_gwei"],
                        "gas_savings_potential": result["gas_savings_potential_usd"],
                        "optimization_score": result["optimization_score"],
                        "risk_level": result["risk_level"],
                        "timestamp": result["timestamp"],
                    },
                    maxlen=GAS_REDIS_STREAM_MAXLEN,
                )

                # Record prediction with AccuracyTracker for validation
                tracker = get_accuracy_tracker()
                if tracker:
                    try:
                        tracker.record_prediction(
                            engine_name="gas_price_optimizer",
                            prediction_type="gas_optimization",
                            predicted_value=result["optimized_gas_price_gwei"],
                            confidence=result["confidence"],
                            metadata={
                                "chain": chain,
                                "current_gas_price": result["current_gas_price_gwei"],
                                "optimization_score": result["optimization_score"],
                                "risk_level": result["risk_level"],
                            },
                        )
                    except Exception as e:
                        self.logger.debug(f"AccuracyTracker recording failed: {e}")

            return result

        except Exception as e:
            self.logger.error(f"Error calculating optimized gas price for {chain}: {e}")
            return {
                "chain": chain,
                "error": str(e),
                "current_gas_price_gwei": 0,
                "optimized_gas_price_gwei": 0,
                "gas_savings_potential_usd": 0,
                "optimization_score": 0,
                "risk_level": "ERROR",
            }

    def _get_current_gas_price(self, chain: str = "ethereum") -> float:
        """Get current gas price for specified chain from blockchain"""
        try:
            # Get Web3 instance for the chain
            w3 = self.chain_manager.get_web3_instance(chain)

            if not w3 or not w3.is_connected():
                self.logger.warning(f"Cannot connect to {chain} RPC, using default")
                return 50.0

            # Get current gas price from chain
            gas_price_wei = w3.eth.gas_price
            gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")

            self.logger.debug(f"Current gas price on {chain}: {gas_price_gwei} gwei")
            return float(gas_price_gwei)

        except Exception as e:
            self.logger.error(f"Error getting current gas price for {chain}: {e}")
            # Return reasonable default based on chain
            defaults = {
                "ethereum": 50.0,
                "arbitrum": 0.1,
                "optimism": 0.001,
                "polygon": 50.0,
                "base": 0.001,
            }
            return defaults.get(chain.lower(), 50.0)

    def _store_calculation(
        self,
        chain: str,
        current_gas_price: float,
        optimized_gas_price: float,
        network_congestion: float,
        mev_activity: float,
        transaction_success_rate: float,
        cost_savings_usd: float,
        optimization_score: float,
        risk_level: str,
    ):
        """Store gas price optimization calculation in database"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=GAS_DB_TIMEOUT)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO gas_price_optimization
                (chain, current_gas_price, optimized_gas_price, network_congestion,
                 mev_activity, transaction_success_rate, cost_savings_usd,
                 optimization_score, risk_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    chain,
                    current_gas_price,
                    optimized_gas_price,
                    network_congestion,
                    mev_activity,
                    transaction_success_rate,
                    cost_savings_usd,
                    optimization_score,
                    risk_level,
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error storing gas price optimization calculation: {e}")

    def _get_recommendation(
        self,
        optimized_gas: float,
        current_gas: float,
        risk_level: str,
        congestion_analysis: Dict,
        mev_analysis: Dict,
    ) -> str:
        """Generate recommendation based on gas optimization results"""
        if risk_level == "CRITICAL":
            return f"🚨 CRITICAL GAS RISK: Extreme network congestion. Current: {current_gas}gwei, Recommended: {optimized_gas}gwei. Avoid non-critical transactions."
        elif risk_level == "HIGH":
            return f"⚠️ HIGH GAS RISK: Network congestion detected. Current: {current_gas}gwei, Recommended: {optimized_gas}gwei. Add significant gas buffer."
        elif risk_level == "MEDIUM":
            return f"⚠️ MEDIUM GAS RISK: Moderate congestion. Current: {current_gas}gwei, Recommended: {optimized_gas}gwei. Consider timing optimization."
        else:
            savings = abs(current_gas - optimized_gas)
            if savings > 20:
                return f"✅ SIGNIFICANT SAVINGS: Save ~{savings:.1f}gwei per transaction. Current: {current_gas}gwei, Recommended: {optimized_gas}gwei."
            elif savings > 5:
                return f"✅ MODERATE SAVINGS: Save ~{savings:.1f}gwei per transaction. Current: {current_gas}gwei, Recommended: {optimized_gas}gwei."
            else:
                return f"✅ OPTIMAL PRICING: Minimal gas optimization needed. Current: {current_gas}gwei, Recommended: {optimized_gas}gwei."

    def get_statistics(self) -> Dict:
        """Get gas optimizer statistics for dashboard integration"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=GAS_DB_TIMEOUT)
            cursor = conn.cursor()

            # Get total optimizations count
            cursor.execute("SELECT COUNT(*) FROM gas_price_optimization")
            total_optimizations = cursor.fetchone()[0]

            # Get optimizations by chain
            cursor.execute("""
                SELECT chain, COUNT(*) as count
                FROM gas_price_optimization
                GROUP BY chain
            """)
            by_chain = {row[0]: row[1] for row in cursor.fetchall()}

            # Get risk level distribution
            cursor.execute("""
                SELECT risk_level, COUNT(*) as count
                FROM gas_price_optimization
                GROUP BY risk_level
            """)
            risk_distribution = {row[0]: row[1] for row in cursor.fetchall()}

            # Get average optimization score
            cursor.execute("SELECT AVG(optimization_score) FROM gas_price_optimization")
            avg_optimization_score = cursor.fetchone()[0] or 0.0

            # Get total cost savings
            cursor.execute("SELECT SUM(cost_savings_usd) FROM gas_price_optimization")
            total_savings_usd = cursor.fetchone()[0] or 0.0

            # Get recent optimizations (last 24h)
            cursor.execute("""
                SELECT COUNT(*) FROM gas_price_optimization
                WHERE timestamp > datetime('now', '-24 hours')
            """)
            optimizations_24h = cursor.fetchone()[0]

            conn.close()

            return {
                "total_optimizations": total_optimizations,
                "optimizations_24h": optimizations_24h,
                "by_chain": by_chain,
                "risk_distribution": risk_distribution,
                "avg_optimization_score": round(avg_optimization_score, 3),
                "total_savings_usd": round(total_savings_usd, 2),
                "config": {
                    "gas_low_threshold": GAS_LOW_THRESHOLD,
                    "gas_extreme_threshold": GAS_EXTREME_THRESHOLD,
                    "monitor_interval_seconds": GAS_MONITOR_INTERVAL_SECONDS,
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}

    def get_gas_history(self, chain: str = "ethereum", limit: int = 100) -> List[Dict]:
        """Get historical gas optimization data for a chain"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=GAS_DB_TIMEOUT)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT timestamp, current_gas_price, optimized_gas_price,
                       network_congestion, mev_activity, optimization_score, risk_level
                FROM gas_price_optimization
                WHERE chain = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (chain, limit),
            )

            history = []
            for row in cursor.fetchall():
                history.append(
                    {
                        "timestamp": row[0],
                        "current_gas_price": row[1],
                        "optimized_gas_price": row[2],
                        "network_congestion": row[3],
                        "mev_activity": row[4],
                        "optimization_score": row[5],
                        "risk_level": row[6],
                    }
                )

            conn.close()
            return history

        except Exception as e:
            self.logger.error(f"Error getting gas history: {e}")
            return []

    def optimize_gas_for_transaction(
        self,
        chain: str = "ethereum",
        transaction_type: str = "standard",
        transaction_size_eth: float = 0.1,
    ) -> Dict:
        """
        Optimize gas for a specific transaction type and size
        """
        try:
            self.logger.info(
                f"Optimizing gas for {transaction_type} transaction on {chain}"
            )

            # Determine transaction priority based on type and size
            transaction_priority = "medium"
            if transaction_type == "critical" or transaction_size_eth > 1.0:
                transaction_priority = "high"
            elif transaction_type == "batch" or transaction_size_eth < 0.01:
                transaction_priority = "low"

            # Calculate optimized gas price
            optimization_result = self.calculate_optimized_gas_price(
                chain, transaction_priority
            )

            # Calculate transaction cost
            current_cost_eth = (
                (optimization_result["current_gas_price_gwei"] * 21000)
                / 1e9
                * transaction_size_eth
            )
            optimized_cost_eth = (
                (optimization_result["optimized_gas_price_gwei"] * 21000)
                / 1e9
                * transaction_size_eth
            )
            cost_savings_eth = current_cost_eth - optimized_cost_eth

            # Add transaction-specific recommendations
            transaction_recommendations = []
            if transaction_type == "swap":
                transaction_recommendations.append(
                    "Use optimized gas for better swap execution"
                )
            elif transaction_type == "transfer":
                transaction_recommendations.append(
                    "Standard gas optimization sufficient for transfers"
                )
            elif transaction_type == "contract_deployment":
                transaction_recommendations.append(
                    "Consider higher gas limit for contract deployment"
                )

            # Update result with transaction-specific info
            optimization_result["transaction_type"] = transaction_type
            optimization_result["transaction_size_eth"] = transaction_size_eth
            optimization_result["current_transaction_cost_eth"] = round(
                current_cost_eth, 6
            )
            optimization_result["optimized_transaction_cost_eth"] = round(
                optimized_cost_eth, 6
            )
            optimization_result["transaction_cost_savings_eth"] = round(
                cost_savings_eth, 6
            )
            optimization_result["transaction_specific_recommendations"] = (
                transaction_recommendations
            )

            return optimization_result

        except Exception as e:
            self.logger.error(f"Error optimizing gas for transaction on {chain}: {e}")
            return {
                "chain": chain,
                "transaction_type": transaction_type,
                "error": str(e),
                "current_gas_price_gwei": 0,
                "optimized_gas_price_gwei": 0,
                "gas_savings_potential_usd": 0,
                "optimization_score": 0,
                "risk_level": "ERROR",
            }

    async def run_gas_optimization_loop(self):
        """Run continuous gas price optimization monitoring"""
        self.logger.info("Starting gas price optimization monitoring loop")

        # Chains to monitor
        chains_to_monitor = ["ethereum", "arbitrum", "polygon", "bsc", "optimism"]

        while True:
            try:
                for chain in chains_to_monitor:
                    # Optimize gas for different transaction types
                    result = self.calculate_optimized_gas_price(chain, "medium")
                    if result.get("optimization_score", 0) > 0.3:
                        self.logger.info(f"Gas optimization for {chain}: {result}")

                await asyncio.sleep(GAS_MONITOR_INTERVAL_SECONDS)

            except Exception as e:
                self.logger.error(f"Error in gas optimization loop: {e}")
                await asyncio.sleep(GAS_ERROR_RETRY_SECONDS)


def main():
    """Main function to run the Gas Price Optimizer"""
    # Lightweight health check that avoids heavy engine initialization
    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        try:
            # Minimal checks that don't require importing heavy engines
            db_path = get_main_db_path()
            chain_mgr = get_chain_manager()
            w3_ok = bool(Web3())

            # Check Redis connection
            try:
                r = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                )
                redis_ok = r.ping()
            except Exception:
                redis_ok = False

            health = {
                "engine": "gas_price_optimizer",
                "version": GAS_PRICE_OPTIMIZER_VERSION,
                "status": "healthy",
                "db_path": db_path,
                "chain_manager_available": chain_mgr is not None,
                "web3_available": w3_ok,
                "redis_connected": redis_ok,
                "config": {
                    "gas_thresholds": {
                        "low": GAS_LOW_THRESHOLD,
                        "medium": GAS_MEDIUM_THRESHOLD,
                        "high": GAS_HIGH_THRESHOLD,
                        "extreme": GAS_EXTREME_THRESHOLD,
                    },
                    "monitor_interval_seconds": GAS_MONITOR_INTERVAL_SECONDS,
                    "redis_stream_maxlen": GAS_REDIS_STREAM_MAXLEN,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            print(json.dumps(health))
            return
        except Exception as e:  # pragma: no cover - defensive
            print(
                json.dumps(
                    {
                        "engine": "gas_price_optimizer",
                        "version": GAS_PRICE_OPTIMIZER_VERSION,
                        "status": "unhealthy",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )
            return

    # Stats mode - show statistics without starting optimizer
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        try:
            optimizer = GasPriceOptimizer()
            stats = optimizer.get_statistics()
            stats["version"] = GAS_PRICE_OPTIMIZER_VERSION
            print(json.dumps(stats, indent=2))
        except Exception as e:
            print(json.dumps({"error": str(e), "version": GAS_PRICE_OPTIMIZER_VERSION}))
        return

    optimizer = GasPriceOptimizer()

    # Check for command line arguments for one-off calculations
    if len(sys.argv) > 1:
        chain = sys.argv[1]
        priority = sys.argv[2] if len(sys.argv) > 2 else "medium"
        result = optimizer.calculate_optimized_gas_price(chain, priority)
        print(json.dumps(result, indent=2))
    else:
        # Run continuous gas optimization monitoring
        try:
            optimizer.logger.info(
                "🚀 Starting Gas Price Optimizer continuous monitoring"
            )
            asyncio.run(optimizer.run_gas_optimization_loop())
        except KeyboardInterrupt:
            optimizer.logger.info("Gas Price Optimizer stopped by user")
        except Exception as e:
            optimizer.logger.error(f"Gas Price Optimizer failed: {e}")
            raise


if __name__ == "__main__":
    main()
