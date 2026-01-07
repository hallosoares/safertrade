"""
SaferTrade Engines Module Initialization
Configures common settings for all detection engines
"""

import sys

# Increase recursion limit to prevent ZipFile recursion errors
# This fixes warnings in whale_tracker and institutional_flow_tracker
sys.setrecursionlimit(5000)  # Default is 1000, increase to 5000
