"""
Health check endpoints.
"""

from django.core.cache import cache
from django.db import connection
from ninja import Router, Schema

router = Router()


class HealthResponse(Schema):
    status: str
    database: str
    cache: str
    version: str


@router.get("", response=HealthResponse, auth=None)
def health_check(request):
    """
    Проверка работоспособности сервиса.

    Возвращает статус базы данных и кэша.
    """
    db_status = "ok"
    cache_status = "ok"

    # Проверка базы данных
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_status = "error"

    # Проверка Redis
    try:
        cache.set("health_check", "ok", 10)
        if cache.get("health_check") != "ok":
            cache_status = "error"
    except Exception:
        cache_status = "error"

    overall_status = "ok" if db_status == "ok" and cache_status == "ok" else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        cache=cache_status,
        version="1.0.0",
    )


@router.get("/ready", auth=None)
def readiness_check(request):
    """Kubernetes readiness probe."""
    return {"ready": True}


@router.get("/live", auth=None)
def liveness_check(request):
    """Kubernetes liveness probe."""
    return {"live": True}
