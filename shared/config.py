"""
SaferTrade Configuration Manager
Handles environment-specific configuration loading and management
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


class RateLimitTier:
    """Rate limit tier definitions for API access"""

    FREE = "free"
    STARTUP = "startup"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


@dataclass
class DatabaseConfig:
    """Database configuration"""

    url: str
    pool_size: int


@dataclass
class RedisConfig:
    """Redis configuration"""

    host: str
    port: int
    url: str


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""

    storage: str  # 'redis' or 'memory'
    free_tier_limit: int
    starter_tier_limit: int
    pro_tier_limit: int
    enterprise_tier_limit: int  # 0 means unlimited


@dataclass
class AlertConfig:
    """Alert system configuration"""

    discord_bot_token: str
    discord_client_id: str
    discord_permissions: str
    discord_channel_free: str
    discord_channel_premium: str
    discord_channel_critical: str
    telegram_api_id: str
    telegram_api_hash: str
    telegram_bot_token: str
    telegram_free_chat_id: str
    telegram_premium_chat_id: str


@dataclass
class BlockchainConfig:
    """Blockchain API configuration"""

    alchemy_api_key: str
    ethereum_rpc_url: str
    arbitrum_rpc_url: str
    infura_api_key: str
    infura_gas_api_key: str
    infura_https: str
    etherscan_api_key: str
    arbiscan_api_key: str
    optimism_api_key: str
    bscscan_api_key: str
    snowscan_api_key: str
    dune_api_key: str


@dataclass
class PriceAPIConfig:
    """Price API configuration"""

    coingecko_api_key: str
    coinmarketcap_api_key: str
    coinlayer_api_key: str
    cryptocompare_api_key: str
    livecoinwatch_api_key: str
    messari_api_key: str


@dataclass
class AppConfig:
    """Main application configuration"""

    environment: str  # 'production', 'staging', 'development'
    debug: bool
    production_mode: bool
    port: int
    host: str
    log_level: str
    max_workers: int

    database: DatabaseConfig
    redis: RedisConfig
    rate_limit: RateLimitConfig
    alerts: AlertConfig
    blockchain: BlockchainConfig
    price_apis: PriceAPIConfig


class ConfigManager:
    """Configuration manager for loading environment-specific settings"""

    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._load_environment_config()

    def _load_environment_config(self):
        """Load configuration based on environment"""
        # Determine environment from ENVIRONMENT variable, default to 'development'
        env = os.getenv("ENVIRONMENT", "development")

        # Load appropriate .env file
        if env == "production":
            env_file = "configs/production.env"
        elif env == "staging":
            env_file = "configs/staging.env"
        else:  # development
            env_file = ".env"  # Use the existing .env file

        # Load the environment file
        if os.path.exists(env_file):
            load_dotenv(env_file, override=False)

        # Create configuration objects
        self._config = AppConfig(
            environment=env,
            debug=os.getenv("DEBUG", "False").lower() == "true",
            production_mode=os.getenv("PRODUCTION_MODE", "false").lower() == "true",
            port=int(os.getenv("PORT", "8000")),
            host=os.getenv("HOST", "127.0.0.1"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///safertrade.db"),
                pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
            ),
            redis=RedisConfig(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                url=os.getenv("REDIS_URL", "redis://:your_redis_password@localhost:6379"),
            ),
            rate_limit=RateLimitConfig(
                storage=os.getenv("RATE_LIMIT_STORAGE", "redis"),
                free_tier_limit=int(os.getenv("FREE_TIER_LIMIT", "100")),
                starter_tier_limit=int(os.getenv("STARTER_TIER_LIMIT", "10000")),
                pro_tier_limit=int(os.getenv("PRO_TIER_LIMIT", "100000")),
                enterprise_tier_limit=int(os.getenv("ENTERPRISE_TIER_LIMIT", "0")),
            ),
            alerts=AlertConfig(
                discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
                discord_client_id=os.getenv("DISCORD_CLIENT_ID", ""),
                discord_permissions=os.getenv("DISCORD_PERMISSIONS", ""),
                discord_channel_free=os.getenv("DISCORD_CHANNEL_FREE", ""),
                discord_channel_premium=os.getenv("DISCORD_CHANNEL_PREMIUM", ""),
                discord_channel_critical=os.getenv("DISCORD_CHANNEL_CRITICAL", ""),
                telegram_api_id=os.getenv("TELEGRAM_API_ID", ""),
                telegram_api_hash=os.getenv("TELEGRAM_API_HASH", ""),
                telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
                telegram_free_chat_id=os.getenv("TELEGRAM_FREE_CHAT_ID", ""),
                telegram_premium_chat_id=os.getenv("TELEGRAM_PREMIUM_CHAT_ID", ""),
            ),
            blockchain=BlockchainConfig(
                alchemy_api_key=os.getenv("ALCHEMY_API_KEY", ""),
                ethereum_rpc_url=os.getenv("ETHEREUM_RPC_URL", ""),
                arbitrum_rpc_url=os.getenv("ARBITRUM_RPC_URL", ""),
                infura_api_key=os.getenv("INFURA_API_KEY", ""),
                infura_gas_api_key=os.getenv("INFURA_GAS_API_KEY", ""),
                infura_https=os.getenv("INFURA_HTTPS", ""),
                etherscan_api_key=os.getenv("ETHERSCAN_API_KEY", ""),
                arbiscan_api_key=os.getenv("ARBISCAN_API_KEY", ""),
                optimism_api_key=os.getenv("OPTIMISM_API_KEY", ""),
                bscscan_api_key=os.getenv("BSCSCAN_API_KEY", ""),
                snowscan_api_key=os.getenv("SNOWSCAN_API_KEY", ""),
                dune_api_key=os.getenv("DUNE_API_KEY", ""),
            ),
            price_apis=PriceAPIConfig(
                coingecko_api_key=os.getenv("COINGECKO_API_KEY", ""),
                coinmarketcap_api_key=os.getenv("COINMARKETCAP_API_KEY", ""),
                coinlayer_api_key=os.getenv("COINLAYER_API_KEY", ""),
                cryptocompare_api_key=os.getenv("CRYPTOCOMPARE_API_KEY", ""),
                livecoinwatch_api_key=os.getenv("LIVECOINWATCH_API_KEY", ""),
                messari_api_key=os.getenv("MESSARI_API_KEY", ""),
            ),
        )

    def get_config(self) -> AppConfig:
        """Get the current application configuration"""
        if self._config is None:
            self._load_environment_config()
        return self._config

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return self.get_config().database

    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return self.get_config().redis

    def get_rate_limit_config(self) -> RateLimitConfig:
        """Get rate limiting configuration"""
        return self.get_config().rate_limit

    def get_alert_config(self) -> AlertConfig:
        """Get alert system configuration"""
        return self.get_config().alerts

    def get_blockchain_config(self) -> BlockchainConfig:
        """Get blockchain configuration"""
        return self.get_config().blockchain

    def get_price_api_config(self) -> PriceAPIConfig:
        """Get price API configuration"""
        return self.get_config().price_apis

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.get_config().environment == "production"

    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.get_config().environment == "staging"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.get_config().environment == "development"


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get the current application configuration"""
    return get_config_manager().get_config()
