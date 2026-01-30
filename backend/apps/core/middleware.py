"""
Middleware for CTrack API.

Includes:
- Request/Response logging with sensitive data masking
- ETag caching for conditional GET support
- Security headers (CSP, X-Frame-Options, etc.)
- Prometheus metrics collection
"""

import hashlib
import logging
import re
import time
import uuid
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("apps.core.middleware")

SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "x-csrf-token",
    }
)

SENSITIVE_BODY_KEYS = frozenset(
    {
        "password",
        "password1",
        "password2",
        "old_password",
        "new_password",
        "new_password1",
        "new_password2",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "secret_key",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
    }
)

MASKED_VALUE = "[MASKED]"


def mask_sensitive_value(key: str, value: Any) -> Any:
    """Mask sensitive values based on key name."""
    if key.lower() in SENSITIVE_BODY_KEYS:
        return MASKED_VALUE
    return value


def mask_headers(headers: dict[str, str]) -> dict[str, str]:
    """Mask sensitive headers."""
    return {
        key: MASKED_VALUE if key.lower() in SENSITIVE_HEADERS else value
        for key, value in headers.items()
    }


def mask_body(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask sensitive keys in request/response body."""
    if not isinstance(data, dict):
        return data

    masked = {}
    for key, value in data.items():
        if isinstance(value, dict):
            masked[key] = mask_body(value)
        elif isinstance(value, list):
            masked[key] = [
                mask_body(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            masked[key] = mask_sensitive_value(key, value)
    return masked


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def get_request_headers(request: HttpRequest) -> dict[str, str]:
    """Extract relevant headers from request."""
    headers = {}
    for key, value in request.META.items():
        if key.startswith("HTTP_"):
            header_name = key[5:].lower().replace("_", "-")
            headers[header_name] = value
    headers["content-type"] = request.content_type or ""
    return headers


class RequestLoggingMiddleware:
    """
    Middleware that logs incoming requests and outgoing responses.

    Logs include:
    - Request method, path, query params
    - Client IP address
    - Request/response timing
    - Response status code
    - User ID (if authenticated)

    Sensitive data (passwords, tokens, auth headers) is automatically masked.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._should_skip_logging(request):
            return self.get_response(request)

        request_id = str(uuid.uuid4())[:8]
        start_time = time.monotonic()

        self._log_request(request, request_id)

        response = self.get_response(request)

        duration_ms = (time.monotonic() - start_time) * 1000
        self._log_response(request, response, request_id, duration_ms)

        return response

    def _should_skip_logging(self, request: HttpRequest) -> bool:
        """Skip logging for health checks and static files."""
        skip_paths = ("/health", "/static/", "/media/", "/__debug__/")
        return any(request.path.startswith(path) for path in skip_paths)

    def _log_request(self, request: HttpRequest, request_id: str) -> None:
        """Log incoming request details."""
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = request.user.id

        log_data = {
            "request_id": request_id,
            "event": "request_started",
            "method": request.method,
            "path": request.path,
            "query_params": dict(request.GET) if request.GET else None,
            "client_ip": get_client_ip(request),
            "user_id": user_id,
            "headers": mask_headers(get_request_headers(request)),
        }

        logger.info("Request started", extra=log_data)

    def _log_response(
        self,
        request: HttpRequest,
        response: HttpResponse,
        request_id: str,
        duration_ms: float,
    ) -> None:
        """Log outgoing response details."""
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = request.user.id

        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING

        log_data = {
            "request_id": request_id,
            "event": "request_finished",
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "content_length": (
                len(response.content) if hasattr(response, "content") else 0
            ),
        }

        logger.log(log_level, "Request finished", extra=log_data)


# ETag Middleware Configuration

CACHEABLE_PATTERNS = [
    re.compile(r"^/api/projects/[^/]+/statuses/?$"),
    re.compile(r"^/api/projects/[^/]+/issue-types/?$"),
    re.compile(r"^/api/projects/[^/]+/members/?$"),
]


def is_cacheable_endpoint(path: str) -> bool:
    """Check if the request path matches a cacheable endpoint."""
    return any(pattern.match(path) for pattern in CACHEABLE_PATTERNS)


def generate_etag(content: bytes) -> str:
    """Generate ETag from response content using MD5 hash."""
    return f'"{hashlib.md5(content).hexdigest()}"'


class ETagMiddleware:
    """
    Middleware that adds ETag support for cacheable API endpoints.

    Features:
    - Generates ETags for response content on GET requests
    - Returns 304 Not Modified when If-None-Match header matches
    - Adds Cache-Control headers for appropriate endpoints
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only process GET requests for cacheable endpoints
        if request.method != "GET" or not is_cacheable_endpoint(request.path):
            return self.get_response(request)

        # Check If-None-Match header before processing
        if_none_match = request.META.get("HTTP_IF_NONE_MATCH")

        response = self.get_response(request)

        # Only add ETag for successful responses
        if response.status_code != 200:
            return response

        # Get response content
        content = response.content

        # Generate ETag
        etag = generate_etag(content)
        response["ETag"] = etag

        # Add Cache-Control header (private, must-revalidate)
        response["Cache-Control"] = "private, must-revalidate, max-age=0"

        # Check If-None-Match header
        if if_none_match:
            # Handle multiple ETags in If-None-Match
            etags = [e.strip() for e in if_none_match.split(",")]
            if etag in etags or "*" in etags:
                # Return 304 Not Modified
                return HttpResponse(status=304, headers={"ETag": etag})

        return response


# Security Headers Middleware


class SecurityHeadersMiddleware:
    """
    Middleware that adds security headers to responses.

    Headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Content-Security-Policy: Configured for SvelteKit + Carbon + EditorJS
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # X-Content-Type-Options - prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options - prevent clickjacking (backup for CSP frame-ancestors)
        response["X-Frame-Options"] = "DENY"

        # X-XSS-Protection - enable browser XSS filtering
        response["X-XSS-Protection"] = "1; mode=block"

        # Content-Security-Policy - restrict resource loading
        csp = self._build_csp()
        response["Content-Security-Policy"] = csp

        return response

    def _build_csp(self) -> str:
        """
        Build Content-Security-Policy header.

        Configured to allow:
        - SvelteKit inline scripts/styles (via 'unsafe-inline')
        - Carbon Components Svelte
        - EditorJS and its plugins
        - Local API and WebSocket connections
        """
        is_development = getattr(settings, "DEBUG", False)

        # Base sources
        self_src = "'self'"

        # Script sources
        # 'unsafe-inline' needed for SvelteKit hydration scripts
        # 'unsafe-eval' needed for EditorJS in development
        script_src_parts = [self_src, "'unsafe-inline'"]
        if is_development:
            script_src_parts.append("'unsafe-eval'")

        # Style sources
        # 'unsafe-inline' needed for Carbon components and SvelteKit style scoping
        style_src = f"{self_src} 'unsafe-inline'"

        # Image sources - allow data URIs for EditorJS
        img_src = f"{self_src} data: blob: https:"

        # Font sources
        font_src = f"{self_src} data:"

        # Connect sources - API and WebSocket connections
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        connect_src_parts = [
            self_src,
            "http://localhost:8000",
            "ws://localhost:8000",
            "http://127.0.0.1:8000",
            "ws://127.0.0.1:8000",
        ]

        # Add frontend URL for CORS
        if frontend_url:
            connect_src_parts.append(frontend_url)
            ws_url = frontend_url.replace("http://", "ws://").replace(
                "https://", "wss://"
            )
            connect_src_parts.append(ws_url)

        # Add production URLs if configured
        if not is_development:
            allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
            for host in allowed_hosts:
                if host and host != "*":
                    connect_src_parts.append(f"https://{host}")
                    connect_src_parts.append(f"wss://{host}")

        # Frame sources - deny all framing
        frame_ancestors = "'none'"

        # Object sources - deny plugins
        object_src = "'none'"

        # Base URI - restrict base tag
        base_uri = self_src

        # Form action - restrict form submissions
        form_action = self_src

        # Build CSP directives
        directives = [
            f"default-src {self_src}",
            f"script-src {' '.join(script_src_parts)}",
            f"style-src {style_src}",
            f"img-src {img_src}",
            f"font-src {font_src}",
            f"connect-src {' '.join(connect_src_parts)}",
            f"frame-ancestors {frame_ancestors}",
            f"object-src {object_src}",
            f"base-uri {base_uri}",
            f"form-action {form_action}",
        ]

        # Media sources for potential video/audio in issues
        directives.append(f"media-src {self_src} blob:")

        # Worker sources for service workers
        if is_development:
            directives.append(f"worker-src {self_src} blob:")

        return "; ".join(directives)


# Prometheus Metrics Middleware

# UUID pattern for normalizing paths
UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

# Numeric ID pattern
NUMERIC_ID_PATTERN = re.compile(r"/\d+(?=/|$)")


def normalize_endpoint(path: str) -> str:
    """
    Normalize endpoint path for metrics labeling.

    Replaces UUIDs and numeric IDs with placeholders to reduce cardinality.
    """
    path = UUID_PATTERN.sub("{uuid}", path)
    path = NUMERIC_ID_PATTERN.sub("/{id}", path)
    return path


class MetricsMiddleware:
    """
    Middleware for collecting Prometheus request metrics.

    Tracks request count, latency, and status codes.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip metrics for the metrics endpoint itself to avoid recursion
        if request.path.startswith("/api/metrics"):
            return self.get_response(request)

        start_time = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start_time

        self._record_metrics(request, response, duration)

        return response

    def _record_metrics(
        self, request: HttpRequest, response: HttpResponse, duration: float
    ) -> None:
        """Record request metrics to Prometheus collectors."""
        try:
            from api.metrics import REQUEST_COUNT, REQUEST_LATENCY
        except ImportError:
            return

        method = request.method
        endpoint = normalize_endpoint(request.path)
        status = str(response.status_code)

        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=status,
        ).inc()

        REQUEST_LATENCY.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)


class CacheMetricsMiddleware:
    """
    Middleware for tracking cache hit/miss metrics.

    Wraps cache operations to record statistics.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._patch_cache()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def _patch_cache(self) -> None:
        """Patch Django cache to track hit/miss metrics."""
        try:
            from django.core.cache import cache

            from api.metrics import CacheMetricsCollector

            original_get = cache.get

            def instrumented_get(key, default=None, version=None):
                result = original_get(key, default=default, version=version)
                if result is None or result == default:
                    CacheMetricsCollector.record_miss()
                else:
                    CacheMetricsCollector.record_hit()
                return result

            cache.get = instrumented_get
        except (ImportError, Exception):
            pass
