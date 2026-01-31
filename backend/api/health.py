"""
Health check endpoints.
"""

import shutil
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest
from ninja import Router

DISK_WARNING_THRESHOLD_PERCENT = 10

router = Router()


def check_database() -> dict[str, str]:
    """Check database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_redis() -> dict[str, str]:
    """Check Redis cache connectivity."""
    try:
        cache.set("health_check", "ok", 1)
        if cache.get("health_check") == "ok":
            return {"status": "ok"}
        return {"status": "error", "message": "Cache read failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_disk() -> dict[str, Any]:
    """Check available disk space on storage volume."""
    try:
        path = getattr(settings, "MEDIA_ROOT", "/")
        usage = shutil.disk_usage(path)

        free_percent = (usage.free / usage.total) * 100

        result: dict[str, Any] = {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "free_percent": round(free_percent, 1),
        }

        if free_percent < DISK_WARNING_THRESHOLD_PERCENT:
            result["status"] = "warning"
            result["message"] = f"Low disk space: {free_percent:.1f}% free"
        else:
            result["status"] = "ok"

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("", auth=None)
def health_check(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """
    Проверка работоспособности сервиса.

    Возвращает статус базы данных и кэша.

    Public endpoint (auth=None) - intentionally accessible without authentication
    for monitoring systems, load balancers, and orchestration platforms.
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "disk": check_disk(),
    }

    all_ok = all(c["status"] in ("ok", "warning") for c in checks.values())
    status = "healthy" if all_ok else "unhealthy"
    http_status = 200 if status == "healthy" else 503

    return http_status, {
        "status": status,
        "checks": checks,
    }


@router.get("/ready", auth=None)
def readiness_check(request):
    """
    Kubernetes readiness probe.

    Public endpoint (auth=None) - intentionally accessible without authentication
    for Kubernetes readiness checks.
    """
    return {"ready": True}


@router.get("/live", auth=None)
def liveness_check(request):
    """
    Kubernetes liveness probe.

    Public endpoint (auth=None) - intentionally accessible without authentication
    for Kubernetes liveness checks.
    """
    return {"live": True}
