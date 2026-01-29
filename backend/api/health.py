"""
Health check endpoints.
"""

from typing import Any

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest
from ninja import Router

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


@router.get("", auth=None)
def health_check(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """
    Проверка работоспособности сервиса.

    Возвращает статус базы данных и кэша.
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
    }

    status = (
        "healthy" if all(c["status"] == "ok" for c in checks.values()) else "unhealthy"
    )
    http_status = 200 if status == "healthy" else 503

    return http_status, {
        "status": status,
        "checks": checks,
    }


@router.get("/ready", auth=None)
def readiness_check(request):
    """Kubernetes readiness probe."""
    return {"ready": True}


@router.get("/live", auth=None)
def liveness_check(request):
    """Kubernetes liveness probe."""
    return {"live": True}
