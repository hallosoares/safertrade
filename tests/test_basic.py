"""
Basic tests for SaferTrade detection engines.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEngineImports:
    """Test that all public engines can be imported."""

    def test_import_honeypot_checker(self):
        from engines.honeypot_checker import HoneypotChecker
        assert HoneypotChecker is not None

    def test_import_gas_price_optimizer(self):
        from engines.gas_price_optimizer import GasPriceOptimizer
        assert GasPriceOptimizer is not None

    def test_import_health_check(self):
        from engines.health_check import SaferTradeHealthChecker
        assert SaferTradeHealthChecker is not None

    def test_import_pump_detector(self):
        from engines.pump_detector import PumpDetector
        assert PumpDetector is not None


class TestSharedImports:
    """Test that shared utilities can be imported."""

    def test_import_chains(self):
        from shared.chains import MultiChainManager, get_chain_manager
        assert MultiChainManager is not None
        assert get_chain_manager is not None

    def test_import_paths(self):
        from shared.paths import ROOT_DIR, DATA_DIR
        assert ROOT_DIR.exists()

    def test_import_logging(self):
        from shared.logging_setup import setup_logging
        assert setup_logging is not None


class TestChainConfig:
    """Test chain configuration."""

    def test_supported_chains(self):
        from shared.chains import get_chain_manager

        manager = get_chain_manager()
        chains = manager.get_supported_chains()

        # Should support at least these chains
        expected = ["ethereum", "polygon", "arbitrum", "optimism", "base"]
        for chain in expected:
            assert chain in chains, f"Missing chain: {chain}"

    def test_chain_ids(self):
        from shared.chains import get_chain_manager

        manager = get_chain_manager()

        # Verify chain IDs
        assert manager.get_chain_config("ethereum").chain_id == 1
        assert manager.get_chain_config("polygon").chain_id == 137
        assert manager.get_chain_config("arbitrum").chain_id == 42161
