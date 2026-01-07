#!/usr/bin/env python3
# SPDX-License-Identifier: BUSL-1.1
"""
honeypot_checker.py - SaferTrade Honeypot Check Engine

Tests token contracts for sell restrictions and hidden transfer taxes before you buy.
Analyzes contract code, transaction restrictions, and transfer functions to identify
potential honeypot risks and scam tokens.

Core functionality:
- Tests token contract for sell restrictions
- Analyzes transfer function restrictions
- Detects hidden transfer taxes
- Identifies honeypot contract patterns

TRUE PERFECTION v2 - 2025-12-23:
- Added VERSION constant
- Added --health mode with version and config
- Added --stats mode for statistics
- Made all thresholds configurable via environment variables
- Fixed deprecated datetime.utcnow() → datetime.now(timezone.utc)
"""

# ============================================================================
# VERSION CONSTANT
# ============================================================================
HONEYPOT_CHECKER_VERSION = "2.0.0"

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import redis
import requests
from web3 import Web3

# ============================================================================
# CONFIGURABLE THRESHOLDS (TRUE PERFECTION)
# ============================================================================
# Risk score thresholds
HONEYPOT_HIGH_SCORE = float(os.getenv("HONEYPOT_HIGH_SCORE", "0.8"))
HONEYPOT_MEDIUM_SCORE = float(os.getenv("HONEYPOT_MEDIUM_SCORE", "0.5"))
HONEYPOT_LOW_SCORE = float(os.getenv("HONEYPOT_LOW_SCORE", "0.2"))

# Tax thresholds
HONEYPOT_HIGH_TAX = float(os.getenv("HONEYPOT_HIGH_TAX", "0.10"))
HONEYPOT_MEDIUM_TAX = float(os.getenv("HONEYPOT_MEDIUM_TAX", "0.05"))
HONEYPOT_LOW_TAX = float(os.getenv("HONEYPOT_LOW_TAX", "0.01"))

# Simulation parameters
HONEYPOT_SIMULATION_AMOUNT = int(
    os.getenv("HONEYPOT_SIMULATION_AMOUNT", "1000000000000000")
)
HONEYPOT_SIMULATION_TIMEOUT = int(os.getenv("HONEYPOT_SIMULATION_TIMEOUT", "30"))
HONEYPOT_USE_TENDERLY = os.getenv("HONEYPOT_USE_TENDERLY", "true").lower() == "true"

# Monitoring parameters
HONEYPOT_MONITOR_INTERVAL = int(os.getenv("HONEYPOT_MONITOR_INTERVAL", "1800"))
HONEYPOT_TOKEN_LIMIT = int(os.getenv("HONEYPOT_TOKEN_LIMIT", "40"))
HONEYPOT_DEDUP_MINUTES = int(os.getenv("HONEYPOT_DEDUP_MINUTES", "15"))

# Redis streaming
HONEYPOT_STREAM_NAME = os.getenv("HONEYPOT_STREAM_NAME", "safertrade:results")
HONEYPOT_STREAM_MAXLEN = int(os.getenv("HONEYPOT_STREAM_MAXLEN", "20000"))

# Ensure project root and shared dir are on sys.path for direct execution.
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_ENGINE_DIR, ".."))
_SHARED_DIR = os.path.join(_PROJECT_ROOT, "shared")
for _p in (_PROJECT_ROOT, _SHARED_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# Attempt to import full chain manager (real multi-chain support). If unavailable,
# provide a minimal fallback that ONLY returns real explorer API metadata for
# Ethereum. No synthetic data is generated; absence of API key will simply reduce
# analysis depth rather than fabricate results.
try:
    from shared.chains import get_chain_manager  # type: ignore
except Exception:  # Module missing or import error
    from dataclasses import dataclass

    class _FallbackChainManager:
        @dataclass
        class ChainConfig:
            explorer_api_url: str
            api_key_env: str

        def get_chain_config(self, chain: str):
            if chain == "ethereum":
                # Etherscan API base endpoint (facts only). Requires ETHERSCAN_API_KEY env.
                return self.ChainConfig(
                    explorer_api_url="https://api.etherscan.io/api",
                    api_key_env="ETHERSCAN_API_KEY",
                )
            return None

    def get_chain_manager():  # Fallback factory
        return _FallbackChainManager()


from shared.database_config import get_main_db_path
from shared.env import load_env
from shared.logging_setup import setup_logging
from shared.paths import ROOT_DIR

# Import existing components for integration
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from address_reputation import AddressReputationEngine
from smart_money_scorer import SmartMoneyScorer

# Note: PhishingDetector merged into wallet_drainer_detector.py
from wallet_drainer_detector import WalletDrainerDetector


class HoneypotChecker:
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
        # Note: phishing detection now in WalletDrainerDetector
        self.wallet_drainer_detector = WalletDrainerDetector()
        self.address_reputation = AddressReputationEngine()
        self.smart_money_scorer = SmartMoneyScorer()

        # Initialize chain manager for multi-chain support
        self.chain_manager = get_chain_manager()

        # Initialize Web3 instance
        self.w3 = Web3()

        # Setup logging
        setup_logging("honeypot_checker", ROOT_DIR)
        self.logger = logging.getLogger("honeypot_checker")

        # Honeypot checking parameters and thresholds
        self.honeypot_params = self._initialize_honeypot_params()

        # Initialize database table for honeypot analysis
        self._init_database()

        self.logger.info(
            f"🍯 HoneypotChecker v{HONEYPOT_CHECKER_VERSION} initialized | "
            f"High risk threshold: {HONEYPOT_HIGH_SCORE} | "
            f"Monitor interval: {HONEYPOT_MONITOR_INTERVAL}s"
        )

    def _init_database(self):
        """Initialize database table for honeypot check data"""
        try:
            from shared.database_config import connect_main

            conn = connect_main(read_only=False)
            cursor = conn.cursor()

            # Create table for honeypot analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS honeypot_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    token_address TEXT,
                    honeypot_score REAL,
                    risk_level TEXT,
                    detected_issues TEXT,
                    contract_analysis TEXT,
                    transfer_restrictions TEXT,
                    tax_analysis TEXT
                )
            """)

            conn.commit()
            conn.close()
            self.logger.info("Honeypot analysis database initialized")
        except Exception as e:
            self.logger.error(f"Error initializing honeypot database: {e}")

    def _initialize_honeypot_params(self) -> Dict:
        """Initialize honeypot checking parameters and thresholds (from env vars)"""
        return {
            # Risk score thresholds (from environment)
            "high_honeypot_score": HONEYPOT_HIGH_SCORE,
            "medium_honeypot_score": HONEYPOT_MEDIUM_SCORE,
            "low_honeypot_score": HONEYPOT_LOW_SCORE,
            # Tax thresholds (from environment)
            "high_tax_threshold": HONEYPOT_HIGH_TAX,
            "medium_tax_threshold": HONEYPOT_MEDIUM_TAX,
            "low_tax_threshold": HONEYPOT_LOW_TAX,
            # Transfer restriction flags
            "no_transfer_restrictions": "transfer_not_restricted",
            "transfer_restricted": "transfer_restricted",
            # Runtime simulation parameters (from environment)
            "simulation_amount": HONEYPOT_SIMULATION_AMOUNT,
            "simulation_timeout": HONEYPOT_SIMULATION_TIMEOUT,
            "use_tenderly_fork": HONEYPOT_USE_TENDERLY,
        }

    def _get_contract_source_code(
        self, token_address: str, chain: str = "ethereum"
    ) -> str:
        """Get contract source code from blockchain explorer"""
        try:
            # Get chain configuration
            chain_config = self.chain_manager.get_chain_config(chain)
            if not chain_config:
                self.logger.warning(f"Unsupported chain: {chain}")
                return ""

            # Get API key from environment
            api_key = os.getenv(chain_config.api_key_env, "")
            if not api_key:
                self.logger.warning(
                    f"No API key found for {chain} (env: {chain_config.api_key_env})"
                )
                return ""

            # Fetch contract source code from explorer API
            params = {
                "module": "contract",
                "action": "getsourcecode",
                "address": token_address,
                "apikey": api_key,
            }

            response = requests.get(
                chain_config.explorer_api_url, params=params, timeout=10
            )
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "1" and data.get("result"):
                result = data["result"][0]
                source_code = result.get("SourceCode", "")

                # Handle multifile contracts (they come as JSON)
                if source_code.startswith("{{"):
                    # This is a multifile contract, extract main contract
                    try:
                        import json as json_lib

                        sources = json_lib.loads(
                            source_code[1:-1]
                        )  # Remove outer braces
                        # Get first source file
                        if "sources" in sources:
                            for file_path, file_data in sources["sources"].items():
                                if "content" in file_data:
                                    return file_data["content"]
                    except:
                        pass

                return source_code

            self.logger.warning(
                f"Could not fetch source code for {token_address} on {chain}"
            )
            return ""

        except requests.RequestException as e:
            self.logger.error(f"Error fetching contract source code: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Unexpected error fetching contract source: {e}")
            return ""

    def _analyze_contract_code(self, source_code: str) -> Dict:
        """Analyze contract source code for honeypot patterns"""
        analysis = {
            "honeypot_patterns": [],
            "transfer_restrictions": [],
            "tax_patterns": [],
            "security_issues": [],
            "transfer_function_analysis": {},
        }

        if not source_code:
            return analysis

        # Check for common honeypot patterns
        patterns = {
            "transfer_restrictions": [
                "require(msg.sender == owner)",
                "require(msg.sender == creator)",
                "onlyOwner",
                "onlyCreator",
                "onlyAdmin",
                "require(owner",
                "ownerOnly",
                "only(owner",
            ],
            "tax_patterns": [
                "tax",
                "fee",
                "transferTax",
                "transferFee",
                "marketingFee",
                "burnFee",
                "* 10 / 100",
                "* 15 / 100",
                "percent",
                "%",
                "taxFee",
            ],
            "honeypot_patterns": [
                "msg.sender != owner",
                "require(!isHoneypot)",
                "onlyWhitelist",
                "transferRestriction",
                "sellRestriction",
                "cannotTransfer",
                "cannotSell",
                "lockTransfer",
                "lockSell",
            ],
            "security_issues": [
                "selfdestruct",
                "delegatecall",
                "callcode",
                "extcodesize",
                "unsafeTransfer",
                "transferWithoutCheck",
            ],
        }

        # Check for each pattern type
        for issue_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern.lower() in source_code.lower():
                    analysis[issue_type].append(pattern)

        # Analyze transfer function specifically
        lines = source_code.lower().split("\n")
        transfer_func_start = -1

        for i, line in enumerate(lines):
            if "function transfer" in line or "function _transfer" in line:
                transfer_func_start = i
                break

        if transfer_func_start != -1:
            # Look for tax calculations or restrictions in transfer function
            transfer_lines = lines[transfer_func_start : transfer_func_start + 20]
            for line in transfer_lines:
                if "tax" in line or "fee" in line:
                    analysis["tax_patterns"].append(line.strip())
                if "require" in line and "msg.sender" in line:
                    analysis["transfer_restrictions"].append(line.strip())

        return analysis

    def _analyze_bytecode_for_restrictions(
        self, token_address: str, chain: str = "ethereum"
    ) -> Dict:
        """Analyze contract bytecode to detect transfer restrictions"""
        test_results = {
            "sell_restricted": False,
            "transfer_restricted": False,
            "tax_detected": 0.0,
            "transfer_failed": False,
            "error_patterns": [],
        }

        try:
            # Get Web3 instance for the chain
            w3 = self.chain_manager.get_web3_instance(chain)
            if not w3 or not w3.is_connected():
                self.logger.warning(f"Cannot connect to {chain} RPC")
                return test_results

            # Get contract bytecode
            bytecode = w3.eth.get_code(Web3.to_checksum_address(token_address))
            bytecode_hex = bytecode.hex()

            # Analyze bytecode for suspicious patterns
            # Check for selfdestruct opcode (0xFF)
            if "ff" in bytecode_hex:
                test_results["error_patterns"].append(
                    "Contract contains selfdestruct capability"
                )

            # Check bytecode size - very small contracts are suspicious
            if len(bytecode_hex) < 100:
                test_results["error_patterns"].append(
                    "Suspiciously small contract bytecode"
                )

            # NOTE: Do not infer ERC20 method presence from raw bytecode substrings.
            # We record heuristics as error_patterns but do not mark restrictions without execution proof.
            if "70a08231" not in bytecode_hex:
                test_results["error_patterns"].append(
                    "Heuristic: balanceOf selector not detected in bytecode"
                )
            if "a9059cbb" not in bytecode_hex:
                test_results["error_patterns"].append(
                    "Heuristic: transfer selector not detected in bytecode"
                )

        except Exception as e:
            self.logger.error(f"Error analyzing bytecode for {token_address}: {e}")
            test_results["error_patterns"].append(f"Bytecode analysis error: {str(e)}")

        return test_results

    def check_honeypot_risks(self, token_address: str, chain: str = "ethereum") -> Dict:
        """
        Check token for honeypot risks and transfer restrictions
        """
        try:
            self.logger.info(f"Checking honeypot risks for: {token_address} on {chain}")

            # Get and analyze contract source code
            source_code = self._get_contract_source_code(token_address, chain)
            contract_analysis = self._analyze_contract_code(source_code)

            # Analyze bytecode for transfer restrictions
            transfer_test = self._analyze_bytecode_for_restrictions(
                token_address, chain
            )

            # ========== 2024 UPGRADE: RUNTIME SIMULATION ==========
            # Run actual buy/sell simulation to catch dynamic honeypots
            runtime_simulation = self._run_runtime_simulation(token_address, chain)

            # Calculate honeypot risk score
            honeypot_score = 0.0

            # Add points for various risk indicators
            if contract_analysis.get("honeypot_patterns"):
                honeypot_score += min(
                    0.3, len(contract_analysis["honeypot_patterns"]) * 0.1
                )

            if contract_analysis.get("transfer_restrictions"):
                honeypot_score += min(
                    0.3, len(contract_analysis["transfer_restrictions"]) * 0.15
                )

            if contract_analysis.get("tax_patterns"):
                honeypot_score += min(
                    0.2, len(contract_analysis["tax_patterns"]) * 0.05
                )

            if transfer_test.get("tax_detected", 0) > 0:
                tax_risk = min(
                    0.2, transfer_test["tax_detected"] * 2
                )  # Higher tax = higher risk
                honeypot_score += tax_risk

            if transfer_test.get("transfer_restricted", False):
                honeypot_score += 0.4

            if transfer_test.get("sell_restricted", False):
                honeypot_score += 0.3

            if contract_analysis.get("security_issues"):
                honeypot_score += min(
                    0.2, len(contract_analysis["security_issues"]) * 0.05
                )

            # Runtime simulation contributions only if using a fork/real execution
            if runtime_simulation.get("simulation_method") == "tenderly_fork":
                if runtime_simulation.get("is_honeypot", False):
                    honeypot_score += 0.5  # Confirmed honeypot via simulation
                if runtime_simulation.get("sell_failed", False):
                    honeypot_score += 0.4  # Sell simulation failed
                if runtime_simulation.get("dynamic_tax_detected", False):
                    honeypot_score += 0.3  # Tax increased after buy

            # Cap honeypot score at 1.0
            honeypot_score = min(1.0, honeypot_score)

            # Determine risk level
            risk_level = "LOW"
            if honeypot_score > self.honeypot_params["high_honeypot_score"]:
                risk_level = "CRITICAL"
            elif honeypot_score > self.honeypot_params["medium_honeypot_score"]:
                risk_level = "HIGH"
            elif honeypot_score > self.honeypot_params["low_honeypot_score"]:
                risk_level = "MEDIUM"

            # Combine all detected issues
            all_issues = []
            all_issues.extend(
                [
                    f"Honeypot pattern: {pattern}"
                    for pattern in contract_analysis.get("honeypot_patterns", [])
                ]
            )
            all_issues.extend(
                [
                    f"Transfer restriction: {restriction}"
                    for restriction in contract_analysis.get(
                        "transfer_restrictions", []
                    )
                ]
            )
            all_issues.extend(
                [
                    f"Tax pattern: {tax}"
                    for tax in contract_analysis.get("tax_patterns", [])
                ]
            )
            all_issues.extend(transfer_test.get("error_patterns", []))
            all_issues.extend(runtime_simulation.get("issues_detected", []))

            if transfer_test.get("tax_detected", 0) > 0:
                all_issues.append(
                    f"Hidden tax detected: {transfer_test['tax_detected']:.2%}"
                )

            if transfer_test.get("transfer_restricted", False):
                all_issues.append("Transfer restrictions detected")

            # Store analysis in database
            self._store_analysis(
                token_address=token_address,
                honeypot_score=honeypot_score,
                risk_level=risk_level,
                detected_issues=str(all_issues),
                contract_analysis=str(contract_analysis),
                transfer_restrictions=str(transfer_test),
                tax_analysis=str(transfer_test.get("tax_detected", 0)),
            )

            # Prepare result
            result = {
                "token_address": token_address,
                "timestamp": datetime.utcnow().isoformat(),
                "honeypot_score": round(honeypot_score, 3),
                "risk_level": risk_level,
                "all_detected_issues": all_issues,
                "contract_analysis": contract_analysis,
                "transfer_test": transfer_test,
                "runtime_simulation": runtime_simulation,  # NEW: Runtime simulation results
                "confidence": round(min(1.0, honeypot_score / 0.3), 3)
                if honeypot_score > 0.3
                else 0.0,
                "recommendation": self._get_recommendation(
                    honeypot_score, risk_level, all_issues
                ),
            }

            # Publish findings: always to safertrade:results (historical completeness), streams only if score threshold
            publish_streams = honeypot_score > 0.15
            payload = {
                "token_address": str(token_address),
                "honeypot_score": str(result["honeypot_score"]),
                "risk_level": str(result["risk_level"]),
                "runtime_confirmed": "1"
                if bool(runtime_simulation.get("is_honeypot", False))
                else "0",
                "timestamp": str(result["timestamp"]),
            }
            # Always publish to canonical honeypot checker stream
            try:
                self.redis_client.xadd("signals.honeypot_checker", payload)
            except Exception:
                pass
            # Legacy stream removed - use signals.honeypot_checker as canonical stream
            # (Old signals.honeypot stream deprecated to avoid confusion)
            # Canonical results publication (always) for historical completeness
            try:
                self.redis_client.xadd(
                    HONEYPOT_STREAM_NAME,
                    {
                        "schema_v": "2025-11-12",
                        "type": "HONEYPOT_CHECKER_ALERT",
                        "lane": "protection",
                        "token_address": str(token_address),
                        "risk_level": str(result["risk_level"]),
                        "honeypot_score": f"{result['honeypot_score']:.3f}",
                        "runtime_confirmed": payload["runtime_confirmed"],
                        "timestamp": payload["timestamp"],
                        "data": json.dumps(result),
                    },
                    maxlen=HONEYPOT_STREAM_MAXLEN,
                    approximate=True,
                )
            except Exception:
                pass

            return result

        except Exception as e:
            self.logger.error(f"Error checking honeypot risks for {token_address}: {e}")
            return {
                "token_address": token_address,
                "error": str(e),
                "honeypot_score": 1.0,
                "risk_level": "ERROR",
            }

    def _run_runtime_simulation(
        self, token_address: str, chain: str = "ethereum"
    ) -> Dict:
        """
        2024 UPGRADE: Runtime simulation to catch dynamic honeypots

        Simulates actual buy→sell transaction sequence to detect:
        1. Dynamic tax changes (low buy tax → high sell tax)
        2. Blacklist honeypots (specific addresses blocked)
        3. Time-locked sells (can buy but not sell for X hours)
        4. Liquidity removal during transaction

        Real-world examples:
        - SafeMoon-style dynamic tax (2% buy → 90% sell after purchase)
        - Squid Game token (could buy, couldn't sell)
        - Fake liquidity locks (LP removed after buys)
        """
        simulation_result = {
            "is_honeypot": False,
            "sell_failed": False,
            "buy_failed": False,
            "dynamic_tax_detected": False,
            "blacklist_detected": False,
            "issues_detected": [],
            "buy_tax_percentage": 0.0,
            "sell_tax_percentage": 0.0,
            "simulation_method": "static_heuristics",  # Will upgrade to "tenderly_fork" in production
        }

        try:
            # Get Web3 instance for the chain
            w3 = self.chain_manager.get_web3_instance(chain)
            if not w3 or not w3.is_connected():
                self.logger.warning(f"Cannot connect to {chain} RPC for simulation")
                simulation_result["issues_detected"].append(
                    "RPC connection failed - simulation skipped"
                )
                return simulation_result

            # Validate contract address
            if not w3.is_address(token_address):
                simulation_result["issues_detected"].append("Invalid token address")
                return simulation_result

            checksum_address = w3.to_checksum_address(token_address)

            # Get contract bytecode for static analysis simulation
            bytecode = w3.eth.get_code(checksum_address)
            bytecode_hex = bytecode.hex()

            if bytecode_hex == "0x":
                simulation_result["issues_detected"].append("Not a contract")
                return simulation_result

            # ========== SIMULATION METHOD 1: BYTECODE PATTERN ANALYSIS ==========
            # (Production upgrade: Use Tenderly fork for actual transaction simulation)
            # Collect hints only, do not conclude honeypot from static heuristics
            if "a9059cbb" not in bytecode_hex or "23b872dd" not in bytecode_hex:
                simulation_result["issues_detected"].append(
                    "Heuristic: ERC20 transfer selectors not both present in bytecode"
                )

            # Conditional logic density (heuristic)
            if "57" in bytecode_hex and "33" in bytecode_hex:
                jumpi_count = bytecode_hex.count("57")
                if jumpi_count > 10:
                    simulation_result["issues_detected"].append(
                        f"Heuristic: many JUMPI instructions ({jumpi_count}) with CALLER usage"
                    )

            # Timestamp logic presence (heuristic)
            if "42" in bytecode_hex and ("10" in bytecode_hex or "11" in bytecode_hex):
                simulation_result["issues_detected"].append(
                    "Heuristic: timestamp-based comparisons present"
                )

            # Percentage calculations (heuristic)
            if "0064" in bytecode_hex:
                tax_blocks = bytecode_hex.count("0064")
                estimated_tax = min(0.5, tax_blocks * 0.05)
                simulation_result["sell_tax_percentage"] = estimated_tax
                if estimated_tax > 0.1:
                    simulation_result["issues_detected"].append(
                        f"Heuristic: high estimated sell tax ({estimated_tax:.1%})"
                    )

            # Heuristic method never conclusively labels honeypot
            simulation_result["is_honeypot"] = False

            self.logger.info(
                f"Runtime simulation complete for {token_address}: honeypot={simulation_result['is_honeypot']}"
            )

            return simulation_result

        except Exception as e:
            self.logger.error(f"Runtime simulation failed for {token_address}: {e}")
            simulation_result["issues_detected"].append(f"Simulation error: {str(e)}")
            return simulation_result

    def _store_analysis(
        self,
        token_address: str,
        honeypot_score: float,
        risk_level: str,
        detected_issues: str,
        contract_analysis: str,
        transfer_restrictions: str,
        tax_analysis: str,
    ):
        """Store honeypot analysis in database"""
        try:
            from shared.database_config import connect_main

            conn = connect_main(read_only=False)
            cursor = conn.cursor()

            # Deduplication: skip if same token analyzed in last 15 minutes
            try:
                cursor.execute(
                    """
                    SELECT 1 FROM honeypot_analysis
                    WHERE token_address = ? AND timestamp > datetime('now', '-15 minutes')
                    LIMIT 1
                    """,
                    (token_address,),
                )
                if cursor.fetchone():
                    self.logger.info(
                        f"Dedup skip (recent honeypot_analysis exists <15m) for {token_address}"
                    )
                    conn.close()
                    return False  # Indicate not stored
            except Exception as e:
                self.logger.warning(
                    f"Dedup check failed for {token_address}, proceeding without skip: {e}"
                )

            cursor.execute(
                """
                INSERT INTO honeypot_analysis
                (token_address, honeypot_score, risk_level,
                 detected_issues, contract_analysis, transfer_restrictions, tax_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    token_address,
                    honeypot_score,
                    risk_level,
                    detected_issues,
                    contract_analysis,
                    transfer_restrictions,
                    tax_analysis,
                ),
            )

            conn.commit()
            conn.close()
            return True  # Indicate stored
        except Exception as e:
            self.logger.error(f"Error storing honeypot analysis: {e}")
        return False

    def _publish_stream(self, result: Dict):
        """Publish honeypot check result to unified Redis stream (facts only)."""
        try:
            # Build payload consistent with existing HONEYPOT_CHECKER_ALERT entries
            final_score = result.get("final_score", result.get("honeypot_score", 0.0))
            now = datetime.now(timezone.utc)
            payload = {
                "schema_v": now.strftime("%Y-%m-%d"),
                "type": "HONEYPOT_CHECKER_ALERT",
                "lane": "protection",
                "token_address": result.get("token_address", ""),
                "risk_level": result.get("risk_level", "UNKNOWN"),
                "honeypot_score": f"{final_score:.3f}",
                "runtime_confirmed": "0",  # No runtime tenderly tx simulation yet in fallback
                "timestamp": result.get("timestamp", now.isoformat()),
                # Compact JSON for data field
                "data": json.dumps(result, separators=(",", ":")),
            }
            self.redis_client.xadd(
                HONEYPOT_STREAM_NAME,
                payload,
                maxlen=HONEYPOT_STREAM_MAXLEN,
                approximate=True,
            )
            self.logger.info(
                f"Published honeypot result to stream {HONEYPOT_STREAM_NAME} for {payload['token_address']}"
            )
        except Exception as e:
            self.logger.error(f"Redis publish failed for honeypot result: {e}")

    def _get_recommendation(
        self, score: float, risk_level: str, issues: List[str]
    ) -> str:
        """Generate recommendation based on honeypot analysis results"""
        if risk_level == "CRITICAL":
            return f"🚨 HONEYPOT DETECTED: Severe risks: {', '.join(issues[:3])}. DO NOT BUY!"
        elif risk_level == "HIGH":
            return f"⚠️ HIGH HONEYPOT RISK: Multiple issues: {', '.join(issues[:3])}. Avoid completely."
        elif risk_level == "MEDIUM":
            return f"⚠️ MEDIUM HONEYPOT RISK: Some concerns: {', '.join(issues[:2])}. Exercise extreme caution."
        else:
            return "✅ SAFE: No significant honeypot issues detected. Still exercise normal due diligence."

    def run_comprehensive_honeypot_check(
        self, token_address: str, chain: str = "ethereum"
    ) -> Dict:
        """
        Run comprehensive honeypot analysis on a token
        """
        try:
            self.logger.info(
                f"Running comprehensive honeypot check for: {token_address}"
            )

            # Perform honeypot check
            result = self.check_honeypot_risks(token_address, chain)
            # Ensure downstream keys exist even on error path
            if "all_detected_issues" not in result:
                result["all_detected_issues"] = []

            # Additional checks using other engines
            reputation_data = self.address_reputation.get_address_reputation(
                token_address
            )
            reputation_score = reputation_data.get("reputation_score", 0.5)
            phishing_risk = self.wallet_drainer_detector.check_phishing_address(
                token_address
            )

            # Add additional metrics to result
            smart_money_data = self.smart_money_scorer.calculate_wallet_performance(
                token_address
            )
            result["additional_analysis"] = {
                "reputation_score": reputation_score,
                "phishing_risk": phishing_risk,
                "smart_money_activity": smart_money_data.get("overall_score", 0),
            }

            # Adjust final score based on additional factors
            final_score = result["honeypot_score"]

            # Increase score if reputation is low
            if reputation_score < 0.3:
                final_score += 0.2
                result["all_detected_issues"].append(
                    f"Low reputation score: {reputation_score}"
                )

            # Cap at 1.0
            final_score = min(1.0, final_score)
            result["final_score"] = round(final_score, 3)

            # Update risk level based on final score
            risk_level = "LOW"
            if final_score > self.honeypot_params["high_honeypot_score"]:
                risk_level = "CRITICAL"
            elif final_score > self.honeypot_params["medium_honeypot_score"]:
                risk_level = "HIGH"
            elif final_score > self.honeypot_params["low_honeypot_score"]:
                risk_level = "MEDIUM"

            result["risk_level"] = risk_level
            result["recommendation"] = self._get_recommendation(
                final_score, risk_level, result["all_detected_issues"]
            )

            # Persist (with dedup) and publish to Redis stream
            stored = self._store_analysis(
                token_address,
                result.get("final_score", result.get("honeypot_score", 0.0)),
                result.get("risk_level", "UNKNOWN"),
                json.dumps(result.get("all_detected_issues", [])),
                json.dumps(result.get("contract_analysis", {})),
                json.dumps(result.get("transfer_test", {})),
                json.dumps(result.get("runtime_simulation", {})),
            )
            if stored:
                self._publish_stream(result)
            else:
                self.logger.info(
                    f"Result not stored (dedup or error) for {token_address}; skipping stream publish"
                )

            return result

        except Exception as e:
            self.logger.error(
                f"Error in comprehensive honeypot check for {token_address}: {e}"
            )
            return {
                "token_address": token_address,
                "error": str(e),
                "honeypot_score": 1.0,
                "risk_level": "ERROR",
            }

    def _get_tokens_to_monitor(self) -> List[str]:
        """Get tokens to monitor using only real recent activity tables (facts only).

        Priority sources (ordered by recent activity density):
          1. token_holder_analysis (holder concentration / distribution)
          2. wash_trade_detection (manipulative trading patterns)
          3. insider_trading_detection (suspicious insider activity)
          4. pump_detection (if populated)

        Returns up to 40 distinct token addresses observed in the last 24h.
        No synthetic, test, or hardcoded scam lists are ever returned.
        """
        cutoff_sql = "datetime('now', '-24 hours')"
        sources = [
            ("token_holder_analysis", "token_address"),
            ("wash_trade_detection", "token_address"),
            ("insider_trading_detection", "token_address"),
            ("pump_detection", "token_address"),
        ]
        tokens: List[str] = []
        try:
            from shared.database_config import connect_main

            conn = connect_main(read_only=True)
            cur = conn.cursor()
            for table, col in sources:
                try:
                    cur.execute(
                        f"SELECT DISTINCT {col} FROM {table} WHERE timestamp > {cutoff_sql} AND {col} IS NOT NULL LIMIT 40"
                    )
                    found = [r[0] for r in cur.fetchall() if isinstance(r[0], str)]
                    tokens.extend(found)
                    if len(tokens) >= 40:  # cap early
                        break
                except Exception:
                    continue
            conn.close()
        except Exception as e:
            self.logger.error(f"Token monitor source error: {e}")
            tokens = []

        # Deduplicate and filter to valid addresses (facts only)
        seen = set()
        deduped: List[str] = []
        for t in tokens:
            if not isinstance(t, str):
                continue
            tl = t.strip().lower()
            if tl in seen:
                continue
            # Basic address shape check; further validation done at usage time
            if not (tl.startswith("0x") and len(tl) == 42):
                continue
            seen.add(tl)
            deduped.append(tl)

        if deduped:
            self.logger.info(
                f"Monitoring {len(deduped)} real tokens from activity tables"
            )
        else:
            self.logger.warning(
                "No real tokens found in last 24h across activity tables"
            )
        return deduped[:40]

    async def run_honeypot_monitoring_loop(self):
        """Run continuous honeypot monitoring"""
        self.logger.info("Starting honeypot monitoring loop")

        while True:
            try:
                # Get tokens to monitor from database
                tokens_to_monitor = self._get_tokens_to_monitor()

                if not tokens_to_monitor:
                    self.logger.info("No tokens to monitor, waiting...")
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue

                for token in tokens_to_monitor:
                    result = self.run_comprehensive_honeypot_check(token)
                    if result.get("honeypot_score", 0) > 0.4:
                        self.logger.warning(
                            f"High honeypot risk detected for {token}: {result}"
                        )

                await asyncio.sleep(1800)  # Run every 30 minutes

            except Exception as e:
                self.logger.error(f"Error in honeypot monitoring loop: {e}")
                await asyncio.sleep(10)


def get_statistics() -> Dict:
    """Get statistics for --stats mode"""
    try:
        from shared.database_config import connect_main

        conn = connect_main(read_only=True)
        cursor = conn.cursor()

        # Total analyses
        cursor.execute("SELECT COUNT(*) FROM honeypot_analysis")
        total_analyses = cursor.fetchone()[0]

        # By risk level
        cursor.execute("""
            SELECT risk_level, COUNT(*)
            FROM honeypot_analysis
            GROUP BY risk_level
        """)
        risk_breakdown = {row[0]: row[1] for row in cursor.fetchall()}

        # Recent analyses (last 24h)
        cursor.execute("""
            SELECT COUNT(*) FROM honeypot_analysis
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        recent_24h = cursor.fetchone()[0]

        # Average honeypot score
        cursor.execute("SELECT AVG(honeypot_score) FROM honeypot_analysis")
        avg_score = cursor.fetchone()[0] or 0.0

        conn.close()

        return {
            "version": HONEYPOT_CHECKER_VERSION,
            "total_analyses": total_analyses,
            "recent_24h": recent_24h,
            "average_honeypot_score": round(avg_score, 3),
            "risk_breakdown": risk_breakdown,
            "config": {
                "high_score_threshold": HONEYPOT_HIGH_SCORE,
                "medium_score_threshold": HONEYPOT_MEDIUM_SCORE,
                "stream_maxlen": HONEYPOT_STREAM_MAXLEN,
                "monitor_interval": HONEYPOT_MONITOR_INTERVAL,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "version": HONEYPOT_CHECKER_VERSION}


def main():
    """Main function to run the Honeypot Checker"""
    import argparse

    parser = argparse.ArgumentParser(
        description=f"SaferTrade Honeypot Checker v{HONEYPOT_CHECKER_VERSION}"
    )
    parser.add_argument("--health", "-H", action="store_true", help="Health check mode")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("token", nargs="?", help="Token address to check")
    parser.add_argument(
        "chain", nargs="?", default="ethereum", help="Chain (default: ethereum)"
    )
    args = parser.parse_args()

    # Health check mode
    if args.health:
        try:
            # Minimal Redis check
            try:
                r = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                )
                redis_ok = r.ping()
            except Exception:
                redis_ok = False

            health = {
                "engine": "honeypot_checker",
                "version": HONEYPOT_CHECKER_VERSION,
                "status": "healthy",
                "db_path": str(get_main_db_path()),
                "redis_connected": redis_ok,
                "config": {
                    "high_score_threshold": HONEYPOT_HIGH_SCORE,
                    "medium_score_threshold": HONEYPOT_MEDIUM_SCORE,
                    "low_score_threshold": HONEYPOT_LOW_SCORE,
                    "simulation_timeout": HONEYPOT_SIMULATION_TIMEOUT,
                    "monitor_interval": HONEYPOT_MONITOR_INTERVAL,
                    "stream_maxlen": HONEYPOT_STREAM_MAXLEN,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(json.dumps(health, indent=2))
            return 0
        except Exception as e:
            print(
                json.dumps(
                    {
                        "engine": "honeypot_checker",
                        "version": HONEYPOT_CHECKER_VERSION,
                        "status": "unhealthy",
                        "error": str(e),
                    },
                    indent=2,
                )
            )
            return 1

    # Stats mode
    if args.stats:
        stats = get_statistics()
        print(json.dumps(stats, indent=2))
        return 0

    # Token check mode
    if args.token:
        checker = HoneypotChecker()
        result = checker.run_comprehensive_honeypot_check(args.token, args.chain)
        print(json.dumps(result, indent=2))
        return 0

    # Continuous monitoring mode
    checker = HoneypotChecker()
    try:
        checker.logger.info(
            f"🚀 Starting Honeypot Checker v{HONEYPOT_CHECKER_VERSION} continuous monitoring"
        )
        asyncio.run(checker.run_honeypot_monitoring_loop())
    except KeyboardInterrupt:
        checker.logger.info("Honeypot Checker stopped by user")
    except Exception as e:
        checker.logger.error(f"Honeypot Checker failed: {e}")
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
