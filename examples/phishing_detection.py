#!/usr/bin/env python3
"""
SaferTrade Phishing Detection Example

Check if an address is associated with known phishing campaigns.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.phishing_detector import PhishingDetector


def main():
    detector = PhishingDetector()
    
    # Example addresses to check
    addresses = [
        "0x742d35Cc6634C0532925a3b844Bc9e7595f35aBd",  # Example
    ]
    
    for addr in addresses:
        result = detector.check_address(addr)
        print(f"Address: {addr}")
        print(f"  Is Phishing: {result.get('is_phishing', False)}")
        print(f"  Confidence: {result.get('confidence', 0):.1%}")
        print()


if __name__ == "__main__":
    main()
