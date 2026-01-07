"""
Example: Honeypot Detection
Detect tokens that prevent selling (honeypot contracts)
"""

from engines.honeypot_checker.engine import HoneypotChecker
from shared.redis_client import get_redis_client


def check_token_safety(token_address: str):
    """
    Check if a token is a honeypot.
    
    Honeypots are malicious contracts that allow buying but prevent selling,
    trapping investors' funds.
    """
    redis = get_redis_client()
    checker = HoneypotChecker(redis)
    
    result = checker.check_token(token_address)
    
    print(f"Token: {token_address}")
    print(f"Is Honeypot: {result.is_honeypot}")
    print(f"Risk Score: {result.risk_score}/100")
    
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    return result


if __name__ == "__main__":
    # Example: Check a suspicious token
    # Replace with actual token address
    TOKEN = "0x..."
    check_token_safety(TOKEN)
