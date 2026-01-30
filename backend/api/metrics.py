"""
Prometheus metrics endpoint for CTrack.

Provides system metrics for monitoring and alerting.
"""

import os
import time

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse
from ninja import Router
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

from apps.users.models import User

router = Router()

# Check if running in multiprocess mode (gunicorn with multiple workers)
MULTIPROCESS_MODE = "PROMETHEUS_MULTIPROC_DIR" in os.environ

# Use appropriate registry based on deployment mode
if MULTIPROCESS_MODE:
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
else:
    registry = REGISTRY


# Request metrics
REQUEST_COUNT = Counter(
    "ctrack_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "ctrack_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Database metrics
DB_QUERY_TIME = Histogram(
    "ctrack_db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_CONNECTIONS = Gauge(
    "ctrack_db_connections_active",
    "Number of active database connections",
)

# Cache metrics
CACHE_OPERATIONS = Counter(
    "ctrack_cache_operations_total",
    "Cache operations",
    ["operation", "result"],
)

CACHE_HIT_RATE = Gauge(
    "ctrack_cache_hit_rate",
    "Cache hit rate (0.0 to 1.0)",
)

# User metrics
ACTIVE_USERS = Gauge(
    "ctrack_users_active_total",
    "Total number of active users",
)

TOTAL_USERS = Gauge(
    "ctrack_users_total",
    "Total number of users",
)

# Application metrics
APP_INFO = Gauge(
    "ctrack_app_info",
    "Application information",
    ["version"],
)


class CacheMetricsCollector:
    """Collector for Redis cache metrics."""

    _hits = 0
    _misses = 0

    @classmethod
    def record_hit(cls) -> None:
        cls._hits += 1
        CACHE_OPERATIONS.labels(operation="get", result="hit").inc()

    @classmethod
    def record_miss(cls) -> None:
        cls._misses += 1
        CACHE_OPERATIONS.labels(operation="get", result="miss").inc()

    @classmethod
    def get_hit_rate(cls) -> float:
        total = cls._hits + cls._misses
        if total == 0:
            return 0.0
        return cls._hits / total


def collect_user_metrics() -> None:
    """Collect user-related metrics."""
    total = User.objects.count()
    active = User.objects.filter(is_active=True).count()

    TOTAL_USERS.set(total)
    ACTIVE_USERS.set(active)


def collect_db_metrics() -> None:
    """Collect database connection metrics."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
            )
            row = cursor.fetchone()
            if row:
                DB_CONNECTIONS.set(row[0])
    except Exception:
        pass


def measure_db_query_time() -> float:
    """Measure a simple database query time."""
    start = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        duration = time.perf_counter() - start
        DB_QUERY_TIME.labels(query_type="health_check").observe(duration)
        return duration
    except Exception:
        return 0.0


def collect_cache_metrics() -> None:
    """Collect Redis cache metrics."""
    hit_rate = CacheMetricsCollector.get_hit_rate()
    CACHE_HIT_RATE.set(hit_rate)

    # Try to get Redis INFO stats if available
    try:
        client = cache.client.get_client()
        info = client.info("stats")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total > 0:
            CACHE_HIT_RATE.set(hits / total)
    except (AttributeError, Exception):
        pass


@router.get("", auth=None)
def metrics_endpoint(request: HttpRequest) -> HttpResponse:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.

    Public endpoint (auth=None) - intentionally accessible without authentication
    for Prometheus monitoring systems to scrape metrics.
    """
    # Collect current metrics
    collect_user_metrics()
    collect_db_metrics()
    collect_cache_metrics()
    measure_db_query_time()

    # Set app info
    APP_INFO.labels(version="1.0.0").set(1)

    # Generate Prometheus format output
    output = generate_latest(registry)

    return HttpResponse(output, content_type=CONTENT_TYPE_LATEST)


@router.get("/health", auth=None)
def metrics_health(request: HttpRequest) -> dict:
    """
    Health check for metrics endpoint.

    Public endpoint (auth=None) - intentionally accessible without authentication
    for monitoring systems to verify metrics service availability.
    """
    return {"status": "ok", "metrics_enabled": True}
