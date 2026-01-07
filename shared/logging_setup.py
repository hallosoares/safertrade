import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def setup_logging(app_name: str, root_dir: Path):
    """
    Setup comprehensive logging with file and console output

    Args:
        app_name: Name of the application/component
        root_dir: Root directory for log file storage
    """
    # Create logs directory
    (root_dir / "logs").mkdir(exist_ok=True)
    log_file = root_dir / "logs" / f"{app_name}.log"

    # Define log format
    fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"

    # Setup handlers
    handlers = [logging.StreamHandler(sys.stdout)]

    try:
        # Add file handler
        handlers.append(logging.FileHandler(log_file))
    except Exception as e:
        print(f"Warning: Could not create log file {log_file}: {e}")
        pass

    # Configure logging
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers, force=True)


class ComprehensiveLogger:
    """
    Enhanced logging system with monitoring and alerting capabilities
    """

    def __init__(self, component_name: str, log_level: int = logging.INFO):
        """
        Initialize comprehensive logger

        Args:
            component_name: Name of the component being logged
            log_level: Logging level (default: INFO)
        """
        self.component_name = component_name
        self.logger = logging.getLogger(component_name)
        self.logger.setLevel(log_level)

        # Setup log file with timestamp
        self.log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Performance tracking
        self.performance_metrics = {}
        self.error_count = 0
        self.warning_count = 0

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """
        Log debug message with optional extra data

        Args:
            message: Debug message
            extra_data: Optional additional data to log
        """
        if extra_data:
            message = f"{message} | Extra: {json.dumps(extra_data, default=str)}"
        self.logger.debug(message)

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """
        Log info message with optional extra data

        Args:
            message: Info message
            extra_data: Optional additional data to log
        """
        if extra_data:
            message = f"{message} | Extra: {json.dumps(extra_data, default=str)}"
        self.logger.info(message)

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """
        Log warning message with optional extra data

        Args:
            message: Warning message
            extra_data: Optional additional data to log
        """
        self.warning_count += 1
        if extra_data:
            message = f"{message} | Extra: {json.dumps(extra_data, default=str)}"
        self.logger.warning(message)

    def error(
        self,
        message: str,
        exception: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Log error message with optional exception and extra data

        Args:
            message: Error message
            exception: Optional exception that caused the error
            extra_data: Optional additional data to log
        """
        self.error_count += 1

        if exception:
            message = f"{message} | Exception: {str(exception)}"
            # Add stack trace for debugging
            stack_trace = traceback.format_exc()
            message = f"{message} | StackTrace: {stack_trace}"

        if extra_data:
            message = f"{message} | Extra: {json.dumps(extra_data, default=str)}"

        self.logger.error(message)

    def critical(
        self,
        message: str,
        exception: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Log critical message with optional exception and extra data

        Args:
            message: Critical message
            exception: Optional exception that caused the critical error
            extra_data: Optional additional data to log
        """
        self.error_count += 1  # Critical errors also count as errors

        if exception:
            message = f"{message} | Exception: {str(exception)}"
            # Add stack trace for debugging
            stack_trace = traceback.format_exc()
            message = f"{message} | StackTrace: {stack_trace}"

        if extra_data:
            message = f"{message} | Extra: {json.dumps(extra_data, default=str)}"

        self.logger.critical(message)

        # Send immediate alert for critical errors
        self.send_alert("CRITICAL", message)

    def performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """
        Record a performance metric

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement (optional)
        """
        self.performance_metrics[metric_name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        }

        # Log performance metrics periodically
        if len(self.performance_metrics) % 10 == 0:  # Every 10 metrics
            self.info(
                "Performance metrics update",
                {"metrics_count": len(self.performance_metrics)},
            )

    def log_function_call(
        self, function_name: str, args: tuple = (), kwargs: dict = {}
    ):
        """
        Log function call for debugging and monitoring

        Args:
            function_name: Name of the function being called
            args: Function arguments
            kwargs: Function keyword arguments
        """
        self.debug(
            f"Function called: {function_name}",
            {
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()) if kwargs else [],
            },
        )

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """
        Log API call for monitoring

        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            request_size: Request size in bytes
            response_size: Response size in bytes
        """
        self.info(
            f"API Call: {method} {endpoint}",
            {
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "request_size_bytes": request_size,
                "response_size_bytes": response_size,
            },
        )

        # Track API performance metrics
        self.performance_metric(f"api_response_time_{endpoint}", response_time_ms, "ms")

        # Alert on slow responses or errors
        if response_time_ms > 5000:  # More than 5 seconds
            self.warning(
                f"Slow API response for {endpoint}",
                {"response_time_ms": response_time_ms},
            )

        if status_code >= 500:  # Server errors
            self.error(f"Server error {status_code} for {endpoint}")

    def log_database_query(
        self,
        query_type: str,
        table: str,
        execution_time_ms: float,
        rows_affected: int = 0,
        error: Optional[str] = None,
    ):
        """
        Log database query for monitoring

        Args:
            query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
            table: Database table
            execution_time_ms: Execution time in milliseconds
            rows_affected: Number of rows affected
            error: Error message if query failed
        """
        self.info(
            f"Database query: {query_type} on {table}",
            {
                "execution_time_ms": execution_time_ms,
                "rows_affected": rows_affected,
                "error": error,
            },
        )

        # Track database performance metrics
        self.performance_metric(f"db_query_time_{table}", execution_time_ms, "ms")

        # Alert on slow queries or errors
        if execution_time_ms > 1000:  # More than 1 second
            self.warning(
                f"Slow database query on {table}",
                {"execution_time_ms": execution_time_ms, "query_type": query_type},
            )

        if error:
            self.error(f"Database query error on {table}", {"error": error})

    def log_redis_operation(
        self,
        operation: str,
        key: str,
        execution_time_ms: float,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """
        Log Redis operation for monitoring

        Args:
            operation: Redis operation (GET, SET, DEL, etc.)
            key: Redis key
            execution_time_ms: Execution time in milliseconds
            success: Whether operation was successful
            error: Error message if operation failed
        """
        self.info(
            f"Redis operation: {operation} on {key}",
            {
                "execution_time_ms": execution_time_ms,
                "success": success,
                "error": error,
            },
        )

        # Track Redis performance metrics
        self.performance_metric(
            f"redis_operation_time_{operation}", execution_time_ms, "ms"
        )

        # Alert on slow operations or errors
        if execution_time_ms > 500:  # More than 500ms
            self.warning(
                f"Slow Redis operation: {operation}",
                {"execution_time_ms": execution_time_ms, "key": key},
            )

        if not success and error:
            self.error(f"Redis operation failed: {operation}", {"error": error})

    def send_alert(
        self,
        alert_level: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Send alert for critical issues

        Args:
            alert_level: Alert level (INFO, WARNING, ERROR, CRITICAL)
            message: Alert message
            additional_data: Optional additional data
        """
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "component": self.component_name,
            "level": alert_level,
            "message": message,
            "additional_data": additional_data or {},
        }

        # Log the alert
        self.logger.log(
            getattr(logging, alert_level, logging.ERROR),
            f"ALERT [{alert_level}]: {message}",
            extra={"alert_data": alert_data},
        )

        # In a real implementation, this would send to external alerting systems
        # like Slack, PagerDuty, email, etc.

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Get monitoring summary statistics

        Returns:
            Dictionary with monitoring summary
        """
        return {
            "component": self.component_name,
            "timestamp": datetime.now().isoformat(),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "performance_metrics": self.performance_metrics,
            "total_log_entries": len(logging.getLogger(self.component_name).handlers),
        }

    def reset_counters(self):
        """
        Reset error and warning counters
        """
        self.error_count = 0
        self.warning_count = 0
        self.performance_metrics.clear()


# Global logger instances
_logger_instances = {}


def get_logger(
    component_name: str, log_level: int = logging.INFO
) -> ComprehensiveLogger:
    """
    Get or create a comprehensive logger instance

    Args:
        component_name: Name of the component
        log_level: Logging level (default: INFO)

    Returns:
        ComprehensiveLogger instance
    """
    global _logger_instances

    if component_name not in _logger_instances:
        _logger_instances[component_name] = ComprehensiveLogger(
            component_name, log_level
        )

    return _logger_instances[component_name]


def setup_comprehensive_logging(
    app_name: str, root_dir: Path, log_level: int = logging.INFO
):
    """
    Setup comprehensive logging with monitoring capabilities

    Args:
        app_name: Name of the application/component
        root_dir: Root directory for log file storage
        log_level: Logging level (default: INFO)
    """
    # Setup basic logging first
    setup_logging(app_name, root_dir)

    # Create comprehensive logger
    comprehensive_logger = get_logger(app_name, log_level)

    # Log startup
    comprehensive_logger.info(f"Comprehensive logging initialized for {app_name}")

    return comprehensive_logger
