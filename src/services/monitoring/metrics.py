"""Metrics collection and monitoring for the Fakelytics platform."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics to track."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Individual metric data point."""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Service for collecting and exposing system metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, list] = defaultdict(list)
        self._histograms: Dict[str, list] = defaultdict(list)
        self._request_count = 0
        self._error_count = 0
        self._start_time = datetime.utcnow()

    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Amount to increment by
            labels: Optional labels for the metric
        """
        key = self._make_key(name, labels)
        self._counters[key] += value
        logger.debug(f"Incremented counter {name}: {self._counters[key]}")

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric.
        
        Args:
            name: Gauge name
            value: Gauge value
            labels: Optional labels for the metric
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value
        logger.debug(f"Set gauge {name}: {value}")

    def record_timer(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timer metric.
        
        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            labels: Optional labels for the metric
        """
        key = self._make_key(name, labels)
        self._timers[key].append(duration_ms)
        logger.debug(f"Recorded timer {name}: {duration_ms}ms")

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a histogram metric.
        
        Args:
            name: Histogram name
            value: Value to record
            labels: Optional labels for the metric
        """
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        logger.debug(f"Recorded histogram {name}: {value}")

    def record_request(self, endpoint: str, method: str, status_code: int, duration_ms: float) -> None:
        """
        Record API request metrics.
        
        **Satisfies**: T-902 (Metrics: request count, latency, error rate)
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
        """
        self._request_count += 1
        
        # Track by endpoint
        self.increment_counter("http_requests_total", labels={"endpoint": endpoint, "method": method, "status": str(status_code)})
        self.record_timer("http_request_duration_ms", duration_ms, labels={"endpoint": endpoint, "method": method})
        
        # Track errors
        if status_code >= 400:
            self._error_count += 1
            self.increment_counter("http_errors_total", labels={"endpoint": endpoint, "status": str(status_code)})
        
        logger.debug(f"Recorded request: {method} {endpoint} {status_code} ({duration_ms}ms)")

    def record_pipeline_execution(self, pipeline_name: str, duration_ms: float, success: bool) -> None:
        """
        Record pipeline execution metrics.
        
        **Satisfies**: T-902 (Pipeline-specific metrics: latency per pipeline)
        
        Args:
            pipeline_name: Name of the pipeline (text, image, audio_video, spam)
            duration_ms: Execution duration in milliseconds
            success: Whether execution was successful
        """
        status = "success" if success else "failure"
        self.record_timer(f"pipeline_duration_ms", duration_ms, labels={"pipeline": pipeline_name, "status": status})
        self.increment_counter(f"pipeline_executions_total", labels={"pipeline": pipeline_name, "status": status})
        logger.debug(f"Recorded pipeline execution: {pipeline_name} {duration_ms}ms ({status})")

    def get_metrics_summary(self) -> Dict:
        """
        Get summary of all metrics.
        
        **Satisfies**: T-902 (Prometheus-compatible metrics endpoint)
        
        Returns:
            Dictionary with all metrics
        """
        uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
        error_rate = self._error_count / self._request_count if self._request_count > 0 else 0

        metrics_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime_seconds,
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate": error_rate,
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timers": {
                key: {
                    "count": len(values),
                    "mean": sum(values) / len(values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                } for key, values in self._timers.items()
            },
            "histograms": {
                key: {
                    "count": len(values),
                    "mean": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                } for key, values in self._histograms.items()
            },
        }
        
        return metrics_summary

    def to_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus format.
        
        **Satisfies**: T-902 (Prometheus-compatible metrics endpoint)
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        
        # Counters
        for key, value in self._counters.items():
            metric_name = key.replace(".", "_").replace("-", "_")
            lines.append(f"{metric_name} {value}")
        
        # Gauges
        for key, value in self._gauges.items():
            metric_name = key.replace(".", "_").replace("-", "_")
            lines.append(f"{metric_name} {value}")
        
        # Timers (as histograms)
        for key, values in self._timers.items():
            if values:
                metric_name = key.replace(".", "_").replace("-", "_")
                mean = sum(values) / len(values)
                lines.append(f"{metric_name}_mean {mean}")
                lines.append(f"{metric_name}_max {max(values)}")
                lines.append(f"{metric_name}_min {min(values)}")
        
        return "\n".join(lines)

    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()
        self._histograms.clear()
        self._request_count = 0
        self._error_count = 0
        self._start_time = datetime.utcnow()
        logger.info("Metrics reset")

    @staticmethod
    def _make_key(name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate metric key from name and labels."""
        if not labels:
            return name
        label_parts = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{name}:{{{','.join(label_parts)}}}"

    @staticmethod
    def _percentile(values: list, p: int) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int((p / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]


# Global instance
metrics_collector = MetricsCollector()
