"""
SaferTrade Centralized Redis Client
Provides a single, shared Redis client instance to avoid connection pool bloat
"""

import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import redis

# Import shared modules directly
try:
    from env import load_env
    from paths import ROOT_DIR
except ImportError:
    # Try absolute imports if running from different context
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from env import load_env
    from paths import ROOT_DIR

# Load environment variables
load_env(ROOT_DIR)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def _attempt_connection(
    host: str, port: int, db: int, password: Optional[str], username: str, ssl: bool
) -> Optional[redis.Redis]:
    """Attempt to create a Redis client; return None on failure."""
    try:
        kwargs = {
            "host": host,
            "port": port,
            "db": db,
            "decode_responses": True,
            "socket_connect_timeout": 3,
            "socket_timeout": 3,
            "socket_keepalive": True,
            "health_check_interval": 30,
            "retry_on_timeout": True,
            "max_connections": 25,
            "encoding": "utf-8",
            "ssl": ssl,
            "ssl_cert_reqs": None,
        }
        if password:
            kwargs["password"] = password
        if username:
            kwargs["username"] = username
        client = redis.Redis(**kwargs)
        client.ping()  # raise if not reachable / auth failure
        return client
    except Exception as e:
        # AUTH failure when password supplied but server has no password => retry without password outside
        if "ERR AUTH" in str(e) or "no password is set" in str(e):
            try:
                kwargs.pop("password", None)
                client = redis.Redis(**kwargs)
                client.ping()
                return client
            except Exception:
                return None
        return None


def get_redis_client() -> redis.Redis:
    """Get or create the global Redis client instance with smart auto-detection.

    Resolution order:
    1. Explicit REDIS_URL (if provided) -> parse & connect
    2. Explicit REDIS_HOST/PORT/PASSWORD vars
    3. Probe production (6380 with password) then dev (6379 no password)
    4. Raise RuntimeError if all attempts fail.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL")
    redis_password_env = os.getenv("REDIS_PASSWORD", "your_redis_password")
    username = os.getenv("REDIS_USERNAME", "")
    ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
    db = int(os.getenv("REDIS_DB", "0"))

    # 1. REDIS_URL direct
    if redis_url:
        try:
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None  # fall through

    # 2. Explicit host/port
    host = os.getenv("REDIS_HOST")
    port_env = os.getenv("REDIS_PORT")
    if host and port_env:
        client = _attempt_connection(
            host, int(port_env), db, redis_password_env, username, ssl
        )
        if client:
            _redis_client = client
            return _redis_client

    # 3. Probing sequence
    probe_matrix = [
        ("localhost", 6380, redis_password_env),  # production mapping
        ("127.0.0.1", 6380, redis_password_env),
        (
            "localhost",
            6379,
            redis_password_env,
        ),  # attempt with password (may downgrade)
        ("localhost", 6379, None),  # dev no password
    ]
    for h, p, pw in probe_matrix:
        client = _attempt_connection(h, p, db, pw, username, ssl)
        if client:
            # Persist discovered config into env for downstream processes for this session
            os.environ.setdefault("REDIS_HOST", h)
            os.environ.setdefault("REDIS_PORT", str(p))
            if pw:
                os.environ.setdefault("REDIS_PASSWORD", pw)
            _redis_client = client
            break

    if _redis_client is None:
        raise RuntimeError("Failed to establish Redis connection after probe attempts")

    return _redis_client


def get_redis_url() -> str:
    """Return an assembled Redis URL matching current detected settings."""
    # Ensure client initialized (auto-detect may set env vars)
    try:
        if _redis_client is None:
            get_redis_client()
    except Exception:
        pass
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_password = os.getenv("REDIS_PASSWORD")
    if redis_password:
        return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    return f"redis://{redis_host}:{redis_port}/{redis_db}"


def get_secure_redis_connection() -> redis.Redis:
    """Get a Redis connection with all security features enabled"""
    # Use environment variables for configuration
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_password = os.getenv("REDIS_PASSWORD", "your_redis_password")
    redis_username = os.getenv("REDIS_USERNAME", "")
    redis_ssl = os.getenv("REDIS_SSL", "false").lower() == "true"

    # Create connection with enhanced security
    connection_params = {
        "host": redis_host,
        "port": redis_port,
        "db": redis_db,
        "password": redis_password,
        "decode_responses": True,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
        "socket_keepalive": True,
        "health_check_interval": 30,
        "retry_on_timeout": True,
        "max_connections": 20,  # Limit connections from this client
        "encoding": "utf-8",
        "ssl": redis_ssl,
        "ssl_cert_reqs": None,  # Don't verify SSL certificates by default
    }

    # Add username if specified (for Redis 6+ ACL)
    if redis_username:
        connection_params["username"] = redis_username

    return redis.Redis(**connection_params)


def test_redis_connection() -> Dict[str, Any]:
    """Test Redis connection and return status"""
    try:
        r = get_secure_redis_connection()
        start_time = time.time()

        # Test basic operations
        test_key = f"health_check_test_{int(time.time())}"
        test_value = "connection_test"

        # Set and get test value
        r.set(test_key, test_value, ex=60)
        retrieved_value = r.get(test_key)

        if retrieved_value != test_value:
            return {
                "healthy": False,
                "error": "Set/get test failed",
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
            }

        # Test Redis info
        info = r.info()

        # Test with security monitoring
        from .redis_security_monitor import get_redis_security_monitor

        security_monitor = get_redis_security_monitor()
        security_status = security_monitor.get_security_metrics()

        return {
            "healthy": True,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "uptime_hours": info.get("uptime_in_seconds", 0) / 3600,
            "security_status": security_status.get(
                "overall_security_healthy", "unknown"
            ),
            "security_issues": len(security_status.get("issues", [])),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def get_redis_health_metrics() -> Dict[str, Any]:
    """Get comprehensive Redis health metrics"""
    try:
        r = get_secure_redis_connection()
        info = r.info()

        # Basic metrics
        metrics = {
            "server": {
                "redis_version": info.get("redis_version"),
                "uptime_hours": info.get("uptime_in_seconds", 0) / 3600,
                "connected_clients": info.get("connected_clients", 0),
                "blocked_clients": info.get("blocked_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "total_net_input_bytes": info.get("total_net_input_bytes", 0),
                "total_net_output_bytes": info.get("total_net_output_bytes", 0),
                "role": info.get("role", "unknown"),
            },
            "memory": {
                "maxmemory": info.get("maxmemory", 0),
                "maxmemory_human": info.get("maxmemory_human", "0B"),
                "maxmemory_policy": info.get("maxmemory_policy", "noeviction"),
                "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0.0),
                "mem_allocator": info.get("mem_allocator", "jemalloc"),
            },
            "persistence": {
                "loading": info.get("loading", False),
                "rdb_changes_since_last_save": info.get(
                    "rdb_changes_since_last_save", 0
                ),
                "rdb_bgsave_in_progress": info.get("rdb_bgsave_in_progress", False),
                "rdb_last_save_time": info.get("rdb_last_save_time", 0),
                "aof_enabled": info.get("aof_enabled", False),
            },
            "stats": {
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "latest_fork_usec": info.get("latest_fork_usec", 0),
            },
        }

        # Calculate derived metrics
        hits = metrics["stats"]["keyspace_hits"]
        misses = metrics["stats"]["keyspace_misses"]
        total_accesses = hits + misses

        if total_accesses > 0:
            metrics["calculated"] = {
                "hit_rate": round((hits / total_accesses) * 100, 2),
                "miss_rate": round((misses / total_accesses) * 100, 2),
            }

        # Add memory usage percentage
        maxmemory = int(info.get("maxmemory", 1))
        if maxmemory > 0:
            metrics["calculated"]["memory_usage_percentage"] = round(
                (info.get("used_memory", 0) / maxmemory) * 100, 2
            )

        # Add timestamp
        metrics["timestamp"] = datetime.utcnow().isoformat()

        return metrics
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


def run_redis_security_scan() -> Dict[str, Any]:
    """Run a comprehensive Redis security scan"""
    try:
        from .redis_security_monitor import get_redis_security_monitor

        security_monitor = get_redis_security_monitor()
        return security_monitor.run_security_scan()
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


def reset_redis_client():
    """Reset the global Redis client (useful for testing)"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
    _redis_client = None


def ping_redis() -> bool:
    """Test Redis connectivity by pinging the server"""
    try:
        client = get_redis_client()
        response = client.ping()
        return bool(response)
    except Exception:
        return False


def get_redis_metrics():
    """Get Redis server metrics using the monitoring module if available"""
    try:
        from .redis_monitoring import RedisMetricsMonitor

        monitor = RedisMetricsMonitor()
        return monitor.get_health_status()
    except ImportError:
        # Fallback to basic ping only if monitoring module not available
        return {
            "healthy": ping_redis(),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
