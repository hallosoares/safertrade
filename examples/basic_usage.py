#!/usr/bin/env python3
"""
SaferTrade Basic Usage Example

This example shows how to run a basic honeypot check on a token.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.honeypot_checker import HoneypotChecker


async def main():
    """Check if a token is a honeypot."""
    
    # Initialize the checker
    checker = HoneypotChecker()
    
    # Example: Check USDC on Ethereum
    token_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
    chain = "ethereum"
    
    print(f"Checking token: {token_address}")
    print(f"Chain: {chain}")
    print("-" * 50)
    
    result = await checker.analyze_token(token_address, chain)
    
    print(f"Is Honeypot: {result.get('is_honeypot', 'Unknown')}")
    print(f"Risk Score: {result.get('risk_score', 'N/A')}")
    print(f"Details: {result.get('details', {})}")


if __name__ == "__main__":
    asyncio.run(main())
