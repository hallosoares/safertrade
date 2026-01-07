#!/usr/bin/env python3
# SPDX-License-Identifier: BUSL-1.1
"""
OHLCV Data Feed - Creates candlestick data from price snapshots
Feeds the visual_price_pattern_engine with real OHLCV streams
"""

import os
import sys
import time
from typing import Dict, List

import redis
import json

# Ensure shared imports resolve when running directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.price_service import get_price_service


class OHLCVDataFeed:
    def __init__(self):
        redis_password = os.getenv("REDIS_PASSWORD", "your_redis_password")
        try:
            from shared.redis_client import get_redis_client
        except Exception:
            get_redis_client = None
        if get_redis_client:
            try:
                self.redis = get_redis_client()
            except Exception:
                self.redis = redis.Redis(
                    host="localhost",
                    port=6379,
                    password=redis_password,
                    decode_responses=True,
                )
        else:
            self.redis = redis.Redis(
                host="localhost",
                port=6379,
                password=redis_password,
                decode_responses=True,
            )
        self.price_service = get_price_service()

        # Candlestick builders for different timeframes
        self.candle_builders = {
            "1m": {},  # {asset: deque of prices in current minute}
            "5m": {},  # {asset: deque of prices in current 5min}
            "15m": {},  # {asset: deque of prices in current 15min}
        }

        # Track current candle start time
        self.current_candle_start = {"1m": None, "5m": None, "15m": None}

        # Assets to track
        self.assets = ["BTC", "ETH", "SOL", "LINK", "UNI"]
        self.chain = "ethereum"  # Default chain

    def get_current_prices(self) -> Dict[str, float]:
        """Fetch current prices using centralized price service"""
        try:
            prices = {}

            # Default volumes (estimate based on typical 24h volume)
            default_volumes = {
                "BTC": 25000000000,  # $25B daily volume
                "ETH": 12000000000,  # $12B
                "SOL": 2000000000,  # $2B
                "LINK": 500000000,  # $500M
                "UNI": 300000000,  # $300M
            }

            for symbol in self.assets:
                price = self.price_service.get_price(symbol)
                if price and price > 0:
                    prices[symbol] = {
                        "price": price,
                        "volume": default_volumes.get(symbol, 1000000000),
                    }

            return prices

        except Exception as e:
            print(f"❌ Error fetching prices: {e}")
            import traceback

            traceback.print_exc()
            return {}

    def get_timeframe_seconds(self, timeframe: str) -> int:
        """Get seconds for a timeframe"""
        timeframe_map = {"1m": 60, "5m": 300, "15m": 900}
        return timeframe_map.get(timeframe, 60)

    def should_close_candle(self, timeframe: str, current_time: int) -> bool:
        """Check if we should close the current candle"""
        if self.current_candle_start[timeframe] is None:
            return False

        elapsed = current_time - self.current_candle_start[timeframe]
        return elapsed >= self.get_timeframe_seconds(timeframe)

    from typing import Optional

    def build_candle(
        self,
        asset: str,
        timeframe: str,
        prices: List[float],
        volume: float,
        timestamp: int,
    ) -> Optional[Dict]:
        """Build OHLCV candle from price list"""
        if not prices:
            return None

        return {
            "timestamp": timestamp,
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],
            "volume": volume,
        }

    def publish_candle(self, asset: str, timeframe: str, candle: Dict):
        """Publish OHLCV candle to Redis stream"""
        stream_key = f"market:ohlcv:{asset}:{self.chain}:{timeframe}"

        try:
            # Add to stream
            self.redis.xadd(
                stream_key,
                {
                    "timestamp": str(candle["timestamp"]),
                    "open": str(candle["open"]),
                    "high": str(candle["high"]),
                    "low": str(candle["low"]),
                    "close": str(candle["close"]),
                    "volume": str(candle["volume"]),
                },
                maxlen=100,  # Keep last 100 candles
            )
            print(
                f"✅ {asset} {timeframe}: O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f}"
            )

        except Exception as e:
            print(f"❌ Error publishing candle: {e}")

    def run(self):
        """Main loop - fetch prices and build candles"""
        print("🕯️  OHLCV Data Feed starting...")
        print(f"   Assets: {', '.join(self.assets)}")
        print("   Timeframes: 1m, 5m, 15m")
        print(f"   Chain: {self.chain}")
        print("")

        # Initialize candle builders
        for timeframe in ["1m", "5m", "15m"]:
            for asset in self.assets:
                self.candle_builders[timeframe][asset] = []

        cycle = 0
        while True:
            try:
                cycle += 1
                current_time = int(time.time())

                # Fetch current prices
                prices = self.get_current_prices()

                if not prices:
                    print("⚠️  No prices fetched, retrying...")
                    time.sleep(10)
                    continue

                # Process each timeframe
                for timeframe in ["1m", "5m", "15m"]:
                    # Check if we need to close current candle
                    if self.should_close_candle(timeframe, current_time):
                        # Close all candles for this timeframe
                        for asset in self.assets:
                            price_list = self.candle_builders[timeframe].get(asset, [])
                            if price_list and asset in prices:
                                candle = self.build_candle(
                                    asset,
                                    timeframe,
                                    price_list,
                                    prices[asset]["volume"],
                                    self.current_candle_start[timeframe],
                                )
                                if candle:
                                    self.publish_candle(asset, timeframe, candle)

                        # Reset builders
                        for asset in self.assets:
                            self.candle_builders[timeframe][asset] = []

                        # Set new candle start time
                        self.current_candle_start[timeframe] = current_time

                    # Initialize candle start if needed
                    if self.current_candle_start[timeframe] is None:
                        self.current_candle_start[timeframe] = current_time

                    # Add current prices to builders
                    for asset in self.assets:
                        if asset in prices:
                            self.candle_builders[timeframe][asset].append(
                                prices[asset]["price"]
                            )

                # Sleep based on fastest timeframe (collect data every 5 seconds for 1m candles)
                time.sleep(5)

            except KeyboardInterrupt:
                print("\n👋 Shutting down OHLCV feed...")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(10)


if __name__ == "__main__":
    # Health check mode
    if len(sys.argv) > 1 and sys.argv[1] == "--health":
        try:
            # Only validate that price service construction works
            _ = get_price_service()
            print(json.dumps({"engine": "ohlcv_data_feed", "status": "healthy"}))
        except Exception as e:
            print(json.dumps({"engine": "ohlcv_data_feed", "status": "unhealthy", "error": str(e)}))
    else:
        feed = OHLCVDataFeed()
        feed.run()
