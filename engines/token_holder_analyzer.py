#!/usr/bin/env python3
# SPDX-License-Identifier: BUSL-1.1
"""
token_holder_analyzer.py - SaferTrade Token Holder Analysis Engine

Maps token holder distribution to detect concentrated ownership and dump risks.
Analyzes holder concentration, wallet clustering, and distribution patterns to
identify potential manipulation and liquidity risks.

Core functionality:
- Maps token holder distribution and concentration
- Analyzes wallet clustering and address relationships
- Identifies concentrated ownership and dump risks
- Detects potential manipulation through holder patterns
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Canonical token address -> symbol mapping used by this engine.
# The addresses and labels below are present in this repository (see comments in
# this file and token maps in other engines), thus do not rely on assumptions.
# Lookup is performed case-insensitively.
TOKEN_ADDRESS_TO_SYMBOL: Dict[str, str] = {
    # USDC (Ethereum legacy address) – referenced with label in this file
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
    # WETH (Ethereum) – mapping appears in real_bridge_arbitrage
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
    # WBTC (Ethereum) – mapping appears in real_bridge_arbitrage
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "WBTC",
    # UNI (Ethereum) – referenced with label in this file
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984": "UNI",
}

import numpy as np
import redis
import requests
from web3 import Web3

# Ensure project root is on sys.path so 'shared' resolves to this repo
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from shared.database_config import connect_main, get_main_db_path
from shared.env import load_env
from shared.logging_setup import setup_logging
from shared.paths import ROOT_DIR

# Import existing components for integration
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from address_reputation import AddressReputationEngine
from institutional_flow_tracker import InstitutionalFlowTracker
from smart_money_scorer import SmartMoneyScorer
from whale_tracker import WhaleTracker


class TokenHolderAnalyzer:
    def __init__(self):
        # Initialize Redis connection for real-time data streaming
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )

        # Initialize database connection
        self.db_path = get_main_db_path()

        # Initialize supporting engines
        self.whale_tracker = WhaleTracker()
        self.institutional_tracker = InstitutionalFlowTracker()
        self.smart_money_scorer = SmartMoneyScorer()
        self.address_reputation = AddressReputationEngine()

        # Initialize Web3 instance
        self.w3 = Web3()

        # Setup logging
        setup_logging("token_holder_analyzer", ROOT_DIR)
        self.logger = logging.getLogger("token_holder_analyzer")

        # Holder analysis parameters and thresholds
        self.holder_params = self._initialize_holder_params()

        # Initialize database table for holder analysis
        self._init_database()

        self.logger.info("Token Holder Analyzer initialized")

    # -----------------------------
    # Safe helper shims to reduce noise when optional methods differ across engines
    # -----------------------------
    def _get_reputation_score(self, address: str) -> float:
        """Return a 0-1 reputation risk score for an address.

        Prefers AddressReputationEngine.get_reputation_score if present.
        Falls back to get_address_reputation and normalizes reputation_score (0-100)
        to 0-1 range. If neither exists, returns 0.0.
        """
        try:
            if hasattr(self.address_reputation, "get_reputation_score"):
                return float(self.address_reputation.get_reputation_score(address))
            if hasattr(self.address_reputation, "get_address_reputation"):
                rep = self.address_reputation.get_address_reputation(address) or {}
                raw = rep.get("reputation_score", 0)
                try:
                    return float(raw) / 100.0
                except Exception:
                    return 0.0
        except Exception:
            return 0.0

        return 0.0

    def _get_smart_money_score(self, address: str) -> float:
        """Return smart money score for wallet if available; else 0.0.

        Prefers SmartMoneyScorer.calculate_wallet_score. If missing,
        uses calculate_wallet_performance()['smart_money_score'] when available.
        """
        try:
            scorer = self.smart_money_scorer
            if hasattr(scorer, "calculate_wallet_score"):
                return float(scorer.calculate_wallet_score(address))
            if hasattr(scorer, "calculate_wallet_performance"):
                perf = scorer.calculate_wallet_performance(address) or {}
                return float(perf.get("smart_money_score", 0.0))
        except Exception:
            return 0.0
        return 0.0

    def _init_database(self):
        """Initialize database table for token holder analysis data"""
        try:
            conn = connect_main(timeout=30.0, read_only=False)
            cursor = conn.cursor()

            # Create table for token holder analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_holder_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    token_address TEXT,
                    holder_concentration_score REAL,
                    risk_level TEXT,
                    concentration_metrics TEXT,
                    top_holders TEXT,
                    smart_money_ratio REAL,
                    institutional_ratio REAL,
                    distribution_analysis TEXT
                )
            """)

            conn.commit()
            conn.close()
            self.logger.info("Token holder analysis database initialized")
        except Exception as e:
            self.logger.error(f"Error initializing token holder database: {e}")

    def _initialize_holder_params(self) -> Dict:
        """Initialize token holder analysis parameters and thresholds"""
        return {
            # Concentration thresholds
            "high_concentration_threshold": 0.5,  # 50%+ held by top holders
            "medium_concentration_threshold": 0.3,  # 30%+ held by top holders
            "low_concentration_threshold": 0.1,  # 10%+ held by top holders
            # Top holder counts
            "top_1_threshold": 0.3,  # 30%+ held by single holder
            "top_5_threshold": 0.5,  # 50%+ held by top 5 holders
            "top_10_threshold": 0.7,  # 70%+ held by top 10 holders
            # Smart money ratio thresholds
            "high_smart_money_ratio": 0.4,  # 40%+ smart money
            "medium_smart_money_ratio": 0.2,  # 20%+ smart money
            "low_smart_money_ratio": 0.1,  # 10%+ smart money
            # Institutional ratio thresholds
            "high_institutional_ratio": 0.3,  # 30%+ institutional
            "medium_institutional_ratio": 0.15,  # 15%+ institutional
            "low_institutional_ratio": 0.05,  # 5%+ institutional
        }

    def analyze_holder_concentration(
        self, token_address: str, holder_data: List[Dict]
    ) -> Dict:
        """
        Analyze token holder concentration patterns
        """
        try:
            analysis = {
                "concentration_detected": False,
                "concentration_score": 0.0,
                "top_holders": [],
                "concentration_metrics": {},
                "risk_level": "LOW",
                "concentration_patterns": [],
            }

            if not holder_data or len(holder_data) < 5:
                return analysis

            # Calculate holder concentration metrics
            total_supply = sum(holder.get("balance", 0) for holder in holder_data)
            if total_supply <= 0:
                return analysis

            # Sort holders by balance (descending)
            sorted_holders = sorted(
                holder_data, key=lambda x: x.get("balance", 0), reverse=True
            )

            # Calculate concentration for top holders
            top_1_balance = sorted_holders[0].get("balance", 0) if sorted_holders else 0
            top_5_balance = sum(
                holder.get("balance", 0) for holder in sorted_holders[:5]
            )
            top_10_balance = sum(
                holder.get("balance", 0) for holder in sorted_holders[:10]
            )

            # Calculate concentration ratios
            top_1_concentration = (
                top_1_balance / total_supply if total_supply > 0 else 0
            )
            top_5_concentration = (
                top_5_balance / total_supply if total_supply > 0 else 0
            )
            top_10_concentration = (
                top_10_balance / total_supply if total_supply > 0 else 0
            )

            # Calculate Gini coefficient as measure of inequality
            balances = [holder.get("balance", 0) for holder in sorted_holders]
            if balances and len(balances) > 1:
                sorted_balances = sorted(balances, reverse=True)
                n = len(sorted_balances)
                gini = (
                    (2 * sum((i + 1) * val for i, val in enumerate(sorted_balances)))
                    - n
                    - 1
                )
                gini = gini / n if n > 1 else 0
            else:
                gini = 0

            # Calculate concentration score (0-1, higher = more concentrated)
            concentration_score = 0.0

            # Add concentration metrics
            if top_1_concentration > self.holder_params["top_1_threshold"]:
                concentration_score += min(0.4, top_1_concentration * 0.8)
                analysis["concentration_patterns"].append(
                    f"Single holder controls {top_1_concentration:.1%}"
                )

            if top_5_concentration > self.holder_params["top_5_threshold"]:
                concentration_score += min(
                    0.3,
                    (top_5_concentration - self.holder_params["top_5_threshold"]) * 0.5,
                )
                analysis["concentration_patterns"].append(
                    f"Top 5 holders control {top_5_concentration:.1%}"
                )

            if top_10_concentration > self.holder_params["top_10_threshold"]:
                concentration_score += min(
                    0.2,
                    (top_10_concentration - self.holder_params["top_10_threshold"])
                    * 0.3,
                )
                analysis["concentration_patterns"].append(
                    f"Top 10 holders control {top_10_concentration:.1%}"
                )

            # Add Gini component (higher Gini = more concentration)
            concentration_score += gini * 0.1

            # Cap concentration score at 1.0
            concentration_score = min(1.0, concentration_score)

            # Determine if concentration detected
            analysis["concentration_detected"] = concentration_score > 0.2

            # Determine risk level
            risk_level = "LOW"
            if concentration_score > 0.7:
                risk_level = "CRITICAL"
            elif concentration_score > 0.4:
                risk_level = "HIGH"
            elif concentration_score > 0.2:
                risk_level = "MEDIUM"

            # Get top holders
            top_holders = []
            for i, holder in enumerate(sorted_holders[:10]):
                address = holder.get("address", "")
                balance = holder.get("balance", 0)
                percentage = balance / total_supply if total_supply > 0 else 0

                top_holders.append(
                    {
                        "rank": i + 1,
                        "address": address,
                        "balance": balance,
                        "percentage": percentage,
                    }
                )

            analysis["concentration_score"] = concentration_score
            analysis["risk_level"] = risk_level
            analysis["top_holders"] = top_holders
            analysis["concentration_metrics"] = {
                "top_1_concentration": top_1_concentration,
                "top_5_concentration": top_5_concentration,
                "top_10_concentration": top_10_concentration,
                "gini_coefficient": gini,
                "total_holders": len(holder_data),
                "total_supply": total_supply,
            }

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing holder concentration: {e}")
            return {
                "concentration_detected": False,
                "concentration_score": 0.0,
                "top_holders": [],
                "concentration_metrics": {},
                "risk_level": "ERROR",
                "concentration_patterns": [],
            }

    def analyze_wallet_clustering(self, holder_data: List[Dict]) -> Dict:
        """
        Analyze wallet clustering patterns to detect related addresses
        """
        try:
            analysis = {
                "clustering_detected": False,
                "clustering_score": 0.0,
                "cluster_groups": [],
                "cluster_metrics": {},
                "clustering_patterns": [],
                "risk_level": "LOW",
            }

            if not holder_data or len(holder_data) < 3:
                return analysis

            # Analyze real holder data for clustering patterns
            # Group holders by balance similarity (potential clustering)
            balance_groups = {}
            for holder in holder_data[:20]:  # Check top 20 holders
                balance = holder.get("balance", 0)
                address = holder.get("address", "")

                # Group by balance ranges (rough clustering)
                balance_range = int(balance // 100000)  # Group by 100K increments
                if balance_range not in balance_groups:
                    balance_groups[balance_range] = []
                balance_groups[balance_range].append(
                    {"address": address, "balance": balance}
                )

            # Identify potential clusters (groups with multiple addresses)
            clusters = []
            for balance_range, holders in balance_groups.items():
                if len(holders) >= 3:  # At least 3 addresses with similar balances
                    cluster = {
                        "balance_range": balance_range,
                        "holder_count": len(holders),
                        "total_balance": sum(h["balance"] for h in holders),
                        "holders": holders,
                    }
                    clusters.append(cluster)

            # Calculate clustering score
            clustering_score = 0.0
            if clusters:
                total_clustered_holders = sum(c["holder_count"] for c in clusters)
                clustering_score = min(
                    1.0, total_clustered_holders / len(holder_data[:20]) * 0.5
                )
                analysis["clustering_detected"] = True
                analysis["cluster_groups"] = clusters[:5]  # Limit to top 5 clusters
                analysis["clustering_patterns"].append(
                    f"{len(clusters)} potential address clusters detected"
                )

            # Determine risk level based on clustering
            risk_level = "LOW"
            if clustering_score > 0.7:
                risk_level = "CRITICAL"
            elif clustering_score > 0.4:
                risk_level = "HIGH"
            elif clustering_score > 0.2:
                risk_level = "MEDIUM"

            analysis["clustering_score"] = clustering_score
            analysis["risk_level"] = risk_level
            analysis["cluster_metrics"] = {
                "total_clusters": len(clusters),
                "clustered_holders": sum(c["holder_count"] for c in clusters),
                "clustering_ratio": clustering_score,
            }

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing wallet clustering: {e}")
            return {
                "clustering_detected": False,
                "clustering_score": 0.0,
                "cluster_groups": [],
                "cluster_metrics": {},
                "clustering_patterns": [],
                "risk_level": "ERROR",
            }

    def analyze_holder_relationships(
        self, token_address: str, holder_data: List[Dict]
    ) -> Dict:
        """
        Analyze relationships between token holders
        """
        try:
            analysis = {
                "relationships_detected": False,
                "relationship_score": 0.0,
                "related_addresses": [],
                "relationship_patterns": [],
                "risk_level": "LOW",
            }

            if not holder_data or len(holder_data) < 5:
                return analysis

            # Check for related addresses using real reputation scores
            related_addresses = []
            for holder in holder_data[:10]:  # Check top 10 holders
                address = holder.get("address", "")
                reputation = self._get_reputation_score(address)

                # Addresses with low reputation might be related to other low-reputation addresses
                if reputation < 0.3:
                    related_addresses.append(
                        {
                            "address": address,
                            "reputation": reputation,
                            "potential_relationships": [],
                        }
                    )

            # Calculate relationship score
            relationship_score = 0.0
            if related_addresses:
                relationship_score = min(1.0, len(related_addresses) * 0.1)
                analysis["relationships_detected"] = True
                analysis["related_addresses"] = related_addresses[:5]
                analysis["relationship_patterns"].append(
                    f"{len(related_addresses)} low-reputation holders"
                )

            # Determine risk level
            risk_level = "LOW"
            if relationship_score > 0.7:
                risk_level = "CRITICAL"
            elif relationship_score > 0.4:
                risk_level = "HIGH"
            elif relationship_score > 0.2:
                risk_level = "MEDIUM"

            analysis["relationship_score"] = relationship_score
            analysis["risk_level"] = risk_level

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing holder relationships: {e}")
            return {
                "relationships_detected": False,
                "relationship_score": 0.0,
                "related_addresses": [],
                "relationship_patterns": [],
                "risk_level": "ERROR",
            }

    def analyze_smart_money_distribution(
        self, token_address: str, holder_data: List[Dict]
    ) -> Dict:
        """
        Analyze smart money distribution in token holders
        """
        try:
            analysis = {
                "smart_money_detected": False,
                "smart_money_ratio": 0.0,
                "smart_money_holders": [],
                "smart_money_patterns": [],
                "risk_level": "LOW",
            }

            if not holder_data:
                return analysis

            # Use smart money scorer to identify smart money holders
            smart_money_holders = []
            total_smart_money_balance = 0.0
            total_supply = sum(holder.get("balance", 0) for holder in holder_data)

            for holder in holder_data[:20]:  # Check top 20 holders
                address = holder.get("address", "")
                balance = holder.get("balance", 0)

                # Get smart money score for the address
                smart_money_score = self._get_smart_money_score(address)

                if smart_money_score > 0.7:  # High smart money score
                    smart_money_holders.append(
                        {
                            "address": address,
                            "balance": balance,
                            "smart_money_score": smart_money_score,
                            "percentage_of_supply": balance / total_supply
                            if total_supply > 0
                            else 0,
                        }
                    )
                    total_smart_money_balance += balance

            # Calculate smart money ratio
            smart_money_ratio = (
                total_smart_money_balance / total_supply if total_supply > 0 else 0
            )

            # Determine if smart money detected
            analysis["smart_money_detected"] = len(smart_money_holders) > 0
            analysis["smart_money_ratio"] = smart_money_ratio
            analysis["smart_money_holders"] = smart_money_holders[:10]

            # Identify patterns
            if smart_money_ratio > self.holder_params["high_smart_money_ratio"]:
                analysis["smart_money_patterns"].append(
                    f"High smart money concentration: {smart_money_ratio:.1%}"
                )
            elif smart_money_ratio > self.holder_params["medium_smart_money_ratio"]:
                analysis["smart_money_patterns"].append(
                    f"Medium smart money presence: {smart_money_ratio:.1%}"
                )
            elif smart_money_ratio > self.holder_params["low_smart_money_ratio"]:
                analysis["smart_money_patterns"].append(
                    f"Low smart money presence: {smart_money_ratio:.1%}"
                )

            # Determine risk level (inverse - more smart money = lower risk)
            risk_level = "LOW"
            if smart_money_ratio < 0.05:  # Very little smart money
                risk_level = "HIGH"
                analysis["smart_money_patterns"].append(
                    "Low smart money presence - potential dump risk"
                )
            elif smart_money_ratio < 0.1:  # Little smart money
                risk_level = "MEDIUM"
                analysis["smart_money_patterns"].append("Moderate smart money presence")

            analysis["risk_level"] = risk_level

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing smart money distribution: {e}")
            return {
                "smart_money_detected": False,
                "smart_money_ratio": 0.0,
                "smart_money_holders": [],
                "smart_money_patterns": [],
                "risk_level": "ERROR",
            }

    def analyze_institutional_distribution(
        self, token_address: str, holder_data: List[Dict]
    ) -> Dict:
        """
        Analyze institutional distribution in token holders
        """
        try:
            analysis = {
                "institutional_detected": False,
                "institutional_ratio": 0.0,
                "institutional_holders": [],
                "institutional_patterns": [],
                "risk_level": "LOW",
            }

            if not holder_data:
                return analysis

            # Use institutional flow tracker to identify institutional holders
            institutional_holders = []
            total_institutional_balance = 0.0
            total_supply = sum(holder.get("balance", 0) for holder in holder_data)

            for holder in holder_data[:20]:  # Check top 20 holders
                address = holder.get("address", "")
                balance = holder.get("balance", 0)

                # Get institutional score for the address (with fallback if method missing)
                try:
                    if hasattr(self.institutional_tracker, "get_wallet_score"):
                        institutional_score = (
                            self.institutional_tracker.get_wallet_score(address)
                        )
                    else:
                        # Fallback: basic heuristic based on balance
                        institutional_score = {
                            "is_institutional": balance > 10000000,  # $10M+ threshold
                            "score": min(balance / 100000000, 1.0),  # Normalize to 0-1
                        }
                except Exception as e:
                    self.logger.debug(
                        f"Could not get institutional score for {address}: {e}"
                    )
                    institutional_score = {"is_institutional": False, "score": 0}

                if institutional_score.get("is_institutional", False):
                    institutional_holders.append(
                        {
                            "address": address,
                            "balance": balance,
                            "institutional_score": institutional_score.get("score", 0),
                            "percentage_of_supply": balance / total_supply
                            if total_supply > 0
                            else 0,
                        }
                    )
                    total_institutional_balance += balance

            # Calculate institutional ratio
            institutional_ratio = (
                total_institutional_balance / total_supply if total_supply > 0 else 0
            )

            # Determine if institutional detected
            analysis["institutional_detected"] = len(institutional_holders) > 0
            analysis["institutional_ratio"] = institutional_ratio
            analysis["institutional_holders"] = institutional_holders[:10]

            # Identify patterns
            if institutional_ratio > self.holder_params["high_institutional_ratio"]:
                analysis["institutional_patterns"].append(
                    f"High institutional concentration: {institutional_ratio:.1%}"
                )
            elif institutional_ratio > self.holder_params["medium_institutional_ratio"]:
                analysis["institutional_patterns"].append(
                    f"Medium institutional presence: {institutional_ratio:.1%}"
                )
            elif institutional_ratio > self.holder_params["low_institutional_ratio"]:
                analysis["institutional_patterns"].append(
                    f"Low institutional presence: {institutional_ratio:.1%}"
                )

            # Determine risk level (inverse - more institutional = lower risk)
            risk_level = "LOW"
            if institutional_ratio < 0.05:  # Very little institutional presence
                risk_level = "HIGH"
                analysis["institutional_patterns"].append(
                    "Low institutional presence - potential volatility"
                )
            elif institutional_ratio < 0.1:  # Little institutional presence
                risk_level = "MEDIUM"
                analysis["institutional_patterns"].append(
                    "Moderate institutional presence"
                )

            analysis["risk_level"] = risk_level

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing institutional distribution: {e}")
            return {
                "institutional_detected": False,
                "institutional_ratio": 0.0,
                "institutional_holders": [],
                "institutional_patterns": [],
                "risk_level": "ERROR",
            }

    def _get_token_holders(self, token_address: str) -> List[Dict]:
        """Get token holders from database (whale movements and known addresses)"""
        try:
            # Use hardened connection (WAL + busy timeout)
            conn = connect_main(timeout=30.0, read_only=False)
            cursor = conn.cursor()

            # IMPORTANT: whale_movements schema uses whale_address (not wallet_address)
            # and token_symbol, not token_address. We only have token_address input here;
            # attempt to derive a symbol match by joining on addresses if available.
            # For now, we look up flows for this token via heuristic: match rows whose
            # transaction hash recent and token_symbol unknown mapping is not trivial.
            # If direct token_address column missing, skip holder extraction.
            cols = [
                c[1]
                for c in cursor.execute(
                    "PRAGMA table_info('whale_movements')"
                ).fetchall()
            ]
            if "whale_address" not in cols:
                self.logger.error(
                    "whale_movements table missing whale_address column; cannot extract holders"
                )
                conn.close()
                return []

            # Prefer token_symbol mapping if token_address appears in addresses table
            token_symbol = None
            if "token_symbol" in cols:
                # Attempt heuristic: find top symbol associated to this token_address from addresses mapping if exists
                try:
                    cursor.execute(
                        "SELECT category FROM addresses WHERE address = ? LIMIT 1",
                        (token_address,),
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        # category sometimes stores a descriptor; ignore if looks like JSON
                        token_symbol = row[0] if len(row[0]) < 15 else None
                except Exception:
                    token_symbol = None
            # Prefer explicit address->symbol mapping (facts from this repo)
            token_symbol = (
                TOKEN_ADDRESS_TO_SYMBOL.get(token_address.lower())
                if "token_symbol" in cols
                else None
            )

            # If we cannot map to symbol, fallback to raw token_address flow rows if column exists.
            holders = []
            rows = []
            try:
                if "token_address" in cols:
                    cursor.execute(
                        """
                        SELECT whale_address as address,
                               SUM(amount_usd) as total_volume,
                               COUNT(*) as tx_count
                        FROM whale_movements
                        WHERE token_address = ?
                          AND timestamp > datetime('now', '-30 days')
                        GROUP BY whale_address
                        ORDER BY total_volume DESC
                        LIMIT 100
                        """,
                        (token_address,),
                    )
                    rows = cursor.fetchall()
                elif token_symbol:
                    cursor.execute(
                        """
                        SELECT whale_address as address,
                               SUM(amount_usd) as total_volume,
                               COUNT(*) as tx_count
                        FROM whale_movements
                        WHERE token_symbol = ?
                          AND timestamp > datetime('now', '-30 days')
                        GROUP BY whale_address
                        ORDER BY total_volume DESC
                        LIMIT 100
                        """,
                        (token_symbol,),
                    )
                    rows = cursor.fetchall()
                else:
                    self.logger.warning(
                        f"No token_address column and no symbol mapping for {token_address}; holder extraction skipped"
                    )
            except Exception as e:
                self.logger.error(f"Holder query failed: {e}")
            finally:
                conn.close()

            if not rows:
                self.logger.warning(f"No holder data found for {token_address}")
                return []

            # Calculate total volume for percentage calculation
            total_volume = sum(row[1] for row in rows if row[1])

            for row in rows:
                address = row[0]
                balance = float(row[1]) if row[1] else 0.0
                percentage = (balance / total_volume * 100) if total_volume > 0 else 0.0

                holders.append(
                    {
                        "address": address,
                        "balance": balance,
                        "percentage": percentage,
                        "tx_count": row[2],
                    }
                )

            return holders

        except Exception as e:
            self.logger.error(f"Error fetching token holders: {e}")
            return []

    def analyze_token_holder_distribution(self, token_address: str) -> Dict:
        """
        Main function to analyze token holder distribution comprehensively
        """
        try:
            self.logger.info(
                f"Analyzing token holder distribution for: {token_address}"
            )

            # Get token holder data
            holder_data = self._get_token_holders(token_address)

            # Perform comprehensive holder analysis
            concentration_analysis = self.analyze_holder_concentration(
                token_address, holder_data
            )
            clustering_analysis = self.analyze_wallet_clustering(holder_data)
            relationship_analysis = self.analyze_holder_relationships(
                token_address, holder_data
            )
            smart_money_analysis = self.analyze_smart_money_distribution(
                token_address, holder_data
            )
            institutional_analysis = self.analyze_institutional_distribution(
                token_address, holder_data
            )

            # Calculate overall holder risk score
            holder_risk_score = (
                concentration_analysis.get("concentration_score", 0) * 0.4
                + clustering_analysis.get("clustering_score", 0) * 0.2
                + relationship_analysis.get("relationship_score", 0) * 0.15
                + (1 - smart_money_analysis.get("smart_money_ratio", 0))
                * 0.15  # Inverse (less smart money = higher risk)
                + (1 - institutional_analysis.get("institutional_ratio", 0))
                * 0.1  # Inverse (less institutional = higher risk)
            )

            # Identify all detected patterns
            all_patterns = (
                concentration_analysis.get("concentration_patterns", [])
                + clustering_analysis.get("clustering_patterns", [])
                + relationship_analysis.get("relationship_patterns", [])
                + smart_money_analysis.get("smart_money_patterns", [])
                + institutional_analysis.get("institutional_patterns", [])
            )

            # Determine overall risk level
            risk_level = "LOW"
            if holder_risk_score > 0.7:
                risk_level = "CRITICAL"
            elif holder_risk_score > 0.4:
                risk_level = "HIGH"
            elif holder_risk_score > 0.2:
                risk_level = "MEDIUM"

            # Store analysis in database
            self._store_analysis(
                token_address=token_address,
                holder_concentration_score=holder_risk_score,
                risk_level=risk_level,
                concentration_metrics=str(
                    concentration_analysis.get("concentration_metrics", {})
                ),
                top_holders=str(concentration_analysis.get("top_holders", [])[:5]),
                smart_money_ratio=smart_money_analysis.get("smart_money_ratio", 0),
                institutional_ratio=institutional_analysis.get(
                    "institutional_ratio", 0
                ),
                distribution_analysis=str(
                    {
                        "concentration": concentration_analysis,
                        "clustering": clustering_analysis,
                        "relationships": relationship_analysis,
                        "smart_money": smart_money_analysis,
                        "institutional": institutional_analysis,
                    }
                ),
            )

            # Prepare comprehensive result
            result = {
                "token_address": token_address,
                "timestamp": datetime.utcnow().isoformat(),
                "holder_risk_score": round(holder_risk_score, 3),
                "risk_level": risk_level,
                "all_detected_patterns": all_patterns,
                "concentration_analysis": concentration_analysis,
                "clustering_analysis": clustering_analysis,
                "relationship_analysis": relationship_analysis,
                "smart_money_analysis": smart_money_analysis,
                "institutional_analysis": institutional_analysis,
                "top_holders": concentration_analysis.get("top_holders", [])[:10],
                "confidence": round(min(1.0, holder_risk_score / 0.3), 3)
                if holder_risk_score > 0.3
                else 0.0,
                "recommendation": self._get_recommendation(
                    holder_risk_score, risk_level, all_patterns
                ),
            }

            # Publish significant findings to Redis
            if holder_risk_score > 0.3:
                self.redis_client.xadd(
                    "signals.token_holder",
                    {
                        "token_address": token_address,
                        "holder_risk_score": result["holder_risk_score"],
                        "risk_level": result["risk_level"],
                        "timestamp": result["timestamp"],
                    },
                )

            return result

        except Exception as e:
            self.logger.error(
                f"Error analyzing token holder distribution for {token_address}: {e}"
            )
            return {
                "token_address": token_address,
                "error": str(e),
                "holder_risk_score": 1.0,
                "risk_level": "ERROR",
            }

    def _store_analysis(
        self,
        token_address: str,
        holder_concentration_score: float,
        risk_level: str,
        concentration_metrics: str,
        top_holders: str,
        smart_money_ratio: float,
        institutional_ratio: float,
        distribution_analysis: str,
    ):
        """Store token holder analysis in database"""
        try:
            conn = connect_main(timeout=30.0, read_only=False)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO token_holder_analysis
                (token_address, holder_concentration_score, risk_level,
                 concentration_metrics, top_holders, smart_money_ratio,
                 institutional_ratio, distribution_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    token_address,
                    holder_concentration_score,
                    risk_level,
                    concentration_metrics,
                    top_holders,
                    smart_money_ratio,
                    institutional_ratio,
                    distribution_analysis,
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error storing token holder analysis: {e}")

    def _get_recommendation(
        self, score: float, risk_level: str, patterns: List[str]
    ) -> str:
        """Generate recommendation based on holder analysis results"""
        if risk_level == "CRITICAL":
            return f"🚨 HOLDER DISTRIBUTION CRITICAL: Severe concentration issues: {', '.join(patterns[:3])}. Do not invest."
        elif risk_level == "HIGH":
            return f"⚠️ HIGH HOLDER RISK: Multiple concerning patterns: {', '.join(patterns[:3])}. Avoid completely."
        elif risk_level == "MEDIUM":
            return f"⚠️ MEDIUM HOLDER RISK: Some concerning patterns: {', '.join(patterns[:2])}. Exercise extreme caution."
        else:
            return "✅ HEALTHY HOLDER DISTRIBUTION: No significant concentration or clustering issues detected."

    def monitor_token_holder_risks(self, token_address: str) -> Dict:
        """
        Monitor a specific token for holder distribution risks
        """
        try:
            self.logger.info(f"Monitoring holder risks for token: {token_address}")

            # Perform comprehensive holder analysis
            return self.analyze_token_holder_distribution(token_address)

        except Exception as e:
            self.logger.error(f"Error monitoring holder risks for {token_address}: {e}")
            return {
                "token_address": token_address,
                "error": str(e),
                "holder_risk_score": 1.0,
                "risk_level": "ERROR",
            }

    async def run_holder_monitoring_loop(self):
        """Run continuous token holder monitoring"""
        self.logger.info("Starting token holder monitoring loop")

        # Tokens to monitor (in practice would come from watchlist)
        tokens_to_monitor = [
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
            "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
            "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",  # UNI
        ]

        while True:
            try:
                for token in tokens_to_monitor:
                    # Run CPU-intensive analysis in a separate thread to avoid blocking the asyncio event loop
                    result = await asyncio.to_thread(
                        self.monitor_token_holder_risks, token
                    )
                    if result.get("holder_risk_score", 0) > 0.4:
                        self.logger.warning(
                            f"High holder risk detected for {token}: {result}"
                        )

                await asyncio.sleep(1800)  # Run every 30 minutes

            except Exception as e:
                self.logger.error(f"Error in holder monitoring loop: {e}")
                await asyncio.sleep(10)


def main():
    """Main function to run the Token Holder Analyzer"""
    # Lightweight health path: avoid heavy initialization when --health is passed
    if len(sys.argv) > 1 and sys.argv[1] in {"--health", "-H"}:
        try:
            print(
                json.dumps(
                    {
                        "engine": "token_holder_analyzer",
                        "status": "healthy",
                        "db_path": str(get_main_db_path()),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )
            return
        except Exception as e:
            print(
                json.dumps(
                    {
                        "engine": "token_holder_analyzer",
                        "status": "error",
                        "error": str(e),
                    }
                )
            )
            return

    analyzer = TokenHolderAnalyzer()

    if len(sys.argv) > 1:
        token_addr = sys.argv[1]
        result = analyzer.analyze_token_holder_distribution(token_addr)
        print(json.dumps(result, indent=2))
    else:
        try:
            analyzer.logger.info(
                "🚀 Starting Token Holder Analyzer continuous monitoring"
            )
            asyncio.run(analyzer.run_holder_monitoring_loop())
        except KeyboardInterrupt:
            analyzer.logger.info("Token Holder Analyzer stopped by user")
        except Exception as e:
            analyzer.logger.error(f"Token Holder Analyzer failed: {e}")
            raise


if __name__ == "__main__":
    main()
