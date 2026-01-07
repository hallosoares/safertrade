"""
Enhanced SaferTrade Metrics Collection
Comprehensive Prometheus metrics for all SaferTrade components
"""

import time

import redis
from prometheus_client import Counter, Gauge, Histogram

# Optional psutil import for system metrics
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# === REQUEST METRICS ===
# HTTP requests by endpoint, method, status
http_requests_total = Counter(
    "safertrade_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status", "component"],
)

http_request_duration_seconds = Histogram(
    "safertrade_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint", "component"],
)

# === TENANT USAGE METRICS ===
# Requests per tenant, rate limit hits
tenant_requests_total = Counter(
    "safertrade_tenant_requests_total",
    "Total requests per tenant",
    ["tenant_id", "component", "endpoint"],
)

tenant_rate_limit_hits_total = Counter(
    "safertrade_tenant_rate_limit_hits_total",
    "Rate limit hits per tenant",
    ["tenant_id", "component"],
)

tenant_active_sessions = Gauge(
    "safertrade_tenant_active_sessions", "Active sessions per tenant", ["tenant_id"]
)

# === PROCESSING METRICS ===
# Stream processing rate, latency, errors
stream_messages_processed_total = Counter(
    "safertrade_stream_messages_processed_total",
    "Total stream messages processed",
    ["stream", "consumer", "component"],
)

stream_processing_duration_seconds = Histogram(
    "safertrade_stream_processing_duration_seconds",
    "Stream message processing duration",
    ["stream", "consumer", "component"],
)

stream_processing_errors_total = Counter(
    "safertrade_stream_processing_errors_total",
    "Stream processing errors",
    ["stream", "consumer", "component", "error_type"],
)

stream_consumer_lag = Gauge(
    "safertrade_stream_consumer_lag",
    "Consumer lag behind stream",
    ["stream", "consumer_group", "consumer"],
)

# === BUSINESS LOGIC METRICS ===
# Signals generated, guards triggered, validations run
signals_generated_total = Counter(
    "safertrade_signals_generated_total",
    "Total signals generated",
    ["signal_type", "chain", "confidence_level"],
)

guards_triggered_total = Counter(
    "safertrade_guards_triggered_total",
    "Guards triggered",
    ["guard_type", "severity", "chain"],
)

validations_run_total = Counter(
    "safertrade_validations_run_total",
    "Validations executed",
    ["validation_type", "result", "chain"],
)

arbitrage_threats_detected = Counter(
    "safertrade_arbitrage_threats_detected_total",
    "Arbitrage threat detections (cross-chain risk monitoring)",
    ["pair", "exchange_a", "exchange_b", "risk_tier"],
)

# Backward compatibility alias
arbitrage_opportunities_detected = arbitrage_threats_detected

backtest_runs_total = Counter(
    "safertrade_backtest_runs_total",
    "Backtest executions",
    ["strategy", "timeframe", "result"],
)

# === INFRASTRUCTURE METRICS ===
# Redis connections, SQLite operations, memory usage
redis_operations_total = Counter(
    "safertrade_redis_operations_total",
    "Redis operations executed",
    ["operation", "database", "result"],
)

redis_connection_pool_size = Gauge(
    "safertrade_redis_connection_pool_size", "Redis connection pool size", ["database"]
)

sqlite_operations_total = Counter(
    "safertrade_sqlite_operations_total",
    "SQLite operations executed",
    ["operation", "database", "result"],
)

sqlite_connection_pool_size = Gauge(
    "safertrade_sqlite_connection_pool_size",
    "SQLite connection pool size",
    ["database"],
)

memory_usage_bytes = Gauge(
    "safertrade_memory_usage_bytes", "Memory usage by component", ["component", "type"]
)

cpu_usage_percent = Gauge(
    "safertrade_cpu_usage_percent", "CPU usage by component", ["component"]
)

# === EXISTING METRICS (from original metrics_exporter.py) ===
redis_stream_length = Gauge(
    "safertrade_redis_stream_length", "Redis stream length", ["stream"]
)
process_heartbeat = Gauge(
    "safertrade_process_heartbeat", "Process heartbeat timestamp", ["process_name"]
)
process_status = Gauge(
    "safertrade_process_status",
    "Process running status (1=running, 0=stopped)",
    ["process_name"],
)
detection_accept_rate = Gauge(
    "safertrade_detection_accept_rate",
    "Detection acceptance rate (detections/arbitrage)",
)
validation_pass_rate = Gauge(
    "safertrade_validation_pass_rate", "Validation pass rate (results/selected)"
)
guard_state = Gauge(
    "safertrade_guard_state", "Guard state (0=safe, 1=warning, 2=error)"
)
guard_budget = Gauge("safertrade_guard_budget", "Guard budget tracking")


class SaferTradeMetrics:
    """Centralized metrics collection for SaferTrade components"""

    def __init__(
        self, component_name: str, redis_url: str = "redis://localhost:6379/0"
    ):
        self.component_name = component_name
        self.redis_client = redis.from_url(redis_url)
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    # === REQUEST TRACKING ===
    def record_http_request(
        self, method: str, endpoint: str, status: int, duration: float
    ):
        """Record HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status),
            component=self.component_name,
        ).inc()

        http_request_duration_seconds.labels(
            method=method, endpoint=endpoint, component=self.component_name
        ).observe(duration)

    # === TENANT TRACKING ===
    def record_tenant_request(self, tenant_id: str, endpoint: str):
        """Record tenant request"""
        tenant_requests_total.labels(
            tenant_id=tenant_id, component=self.component_name, endpoint=endpoint
        ).inc()

    def record_rate_limit_hit(self, tenant_id: str):
        """Record rate limit hit"""
        tenant_rate_limit_hits_total.labels(
            tenant_id=tenant_id, component=self.component_name
        ).inc()

    def update_active_sessions(self, tenant_id: str, count: int):
        """Update active session count for tenant"""
        tenant_active_sessions.labels(tenant_id=tenant_id).set(count)

    # === STREAM PROCESSING ===
    def record_stream_message_processed(self, stream: str, consumer: str):
        """Record stream message processing"""
        stream_messages_processed_total.labels(
            stream=stream, consumer=consumer, component=self.component_name
        ).inc()

    def record_stream_processing_time(
        self, stream: str, consumer: str, duration: float
    ):
        """Record stream processing duration"""
        stream_processing_duration_seconds.labels(
            stream=stream, consumer=consumer, component=self.component_name
        ).observe(duration)

    def record_stream_error(self, stream: str, consumer: str, error_type: str):
        """Record stream processing error"""
        stream_processing_errors_total.labels(
            stream=stream,
            consumer=consumer,
            component=self.component_name,
            error_type=error_type,
        ).inc()

    # === BUSINESS LOGIC ===
    def record_signal_generated(self, signal_type: str, chain: str, confidence: str):
        """Record signal generation"""
        signals_generated_total.labels(
            signal_type=signal_type, chain=chain, confidence_level=confidence
        ).inc()

    def record_guard_triggered(self, guard_type: str, severity: str, chain: str):
        """Record guard trigger"""
        guards_triggered_total.labels(
            guard_type=guard_type, severity=severity, chain=chain
        ).inc()

    def record_validation_run(self, validation_type: str, result: str, chain: str):
        """Record validation execution"""
        validations_run_total.labels(
            validation_type=validation_type, result=result, chain=chain
        ).inc()

    def record_arbitrage_opportunity(
        self, pair: str, exchange_a: str, exchange_b: str, profit_tier: str
    ):
        """Record arbitrage opportunity detection"""
        arbitrage_opportunities_detected.labels(
            pair=pair,
            exchange_a=exchange_a,
            exchange_b=exchange_b,
            profit_tier=profit_tier,
        ).inc()

    def record_backtest_run(self, strategy: str, timeframe: str, result: str):
        """Record backtest execution"""
        backtest_runs_total.labels(
            strategy=strategy, timeframe=timeframe, result=result
        ).inc()

    # === INFRASTRUCTURE ===
    def record_redis_operation(self, operation: str, database: str, result: str):
        """Record Redis operation"""
        redis_operations_total.labels(
            operation=operation, database=database, result=result
        ).inc()

    def record_sqlite_operation(self, operation: str, database: str, result: str):
        """Record SQLite operation"""
        sqlite_operations_total.labels(
            operation=operation, database=database, result=result
        ).inc()

    def update_memory_usage(self):
        """Update memory usage metrics"""
        if not PSUTIL_AVAILABLE or not self.process:
            return

        try:
            memory_info = self.process.memory_info()
            memory_usage_bytes.labels(component=self.component_name, type="rss").set(
                memory_info.rss
            )

            memory_usage_bytes.labels(component=self.component_name, type="vms").set(
                memory_info.vms
            )
        except Exception:
            pass  # Ignore errors for optional metrics

    def update_cpu_usage(self):
        """Update CPU usage metrics"""
        if not PSUTIL_AVAILABLE or not self.process:
            return

        try:
            cpu_percent = self.process.cpu_percent()
            cpu_usage_percent.labels(component=self.component_name).set(cpu_percent)
        except Exception:
            pass  # Ignore errors for optional metrics

    # === CONTEXT MANAGERS FOR AUTOMATIC TRACKING ===
    def time_stream_processing(self, stream: str, consumer: str):
        """Context manager for timing stream processing"""

        class StreamTimer:
            def __init__(self, metrics, stream, consumer):
                self.metrics = metrics
                self.stream = stream
                self.consumer = consumer
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                self.metrics.record_stream_processing_time(
                    self.stream, self.consumer, duration
                )
                self.metrics.record_stream_message_processed(self.stream, self.consumer)

                if exc_type is not None:
                    error_type = exc_type.__name__ if exc_type else "unknown"
                    self.metrics.record_stream_error(
                        self.stream, self.consumer, error_type
                    )

        return StreamTimer(self, stream, consumer)

    def time_http_request(self, method: str, endpoint: str):
        """Context manager for timing HTTP requests"""

        class HTTPTimer:
            def __init__(self, metrics, method, endpoint):
                self.metrics = metrics
                self.method = method
                self.endpoint = endpoint
                self.start_time = None
                self.status = 200  # Default to success

            def __enter__(self):
                self.start_time = time.time()
                return self

            def set_status(self, status: int):
                self.status = status

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                if exc_type is not None:
                    self.status = 500  # Error status
                self.metrics.record_http_request(
                    self.method, self.endpoint, self.status, duration
                )

        return HTTPTimer(self, method, endpoint)


# Singleton instance for easy access
_metrics_instance = None


def get_metrics(
    component_name: str = None, redis_url: str = "redis://localhost:6379/0"
) -> SaferTradeMetrics:
    """Get or create metrics instance"""
    global _metrics_instance
    if _metrics_instance is None or (
        component_name and _metrics_instance.component_name != component_name
    ):
        _metrics_instance = SaferTradeMetrics(component_name or "unknown", redis_url)
    return _metrics_instance
