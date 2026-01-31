"""
Главный API модуль CTrack.

Здесь собираются все роутеры приложения.
"""

from ninja import NinjaAPI

from api.admin import router as admin_router
from api.auth import router as auth_router
from api.boards import router as boards_router
from api.custom_fields import router as custom_fields_router
from api.demo import router as demo_router
from api.events import router as events_router
from api.feed import router as feed_router
from api.health import router as health_router
from api.issues.activity import router as issues_activity_router
from api.issues.attachments import router as issues_attachments_router
from api.issues.backlog import router as issues_backlog_router
from api.issues.comments import router as issues_comments_router
from api.issues.editing import router as issues_editing_router
from api.issues.epics import router as issues_epics_router
from api.issues.issue_types import router as issues_issue_types_router
from api.issues.issues import router as issues_issues_router
from api.issues.statuses import router as issues_statuses_router
from api.issues.workflow import router as issues_workflow_router
from api.metrics import router as metrics_router
from api.projects import router as projects_router
from api.reports import router as reports_router
from api.search import router as search_router
from api.setup import router as setup_router
from api.sprints import router as sprints_router
from api.users import router as users_router

api = NinjaAPI(
    title="CTrack API",
    version="1.0.0",
    description="REST API для таск-трекера CTrack",
    docs_url="/docs",
)

# Health check endpoints
api.add_router("/health", health_router, tags=["Health"])

# Auth endpoints
api.add_router("/auth", auth_router, tags=["Auth"])

# Projects endpoints
api.add_router("/projects", projects_router, tags=["Projects"])

# Issues endpoints (domain-specific routers)
api.add_router("", issues_issue_types_router, tags=["Issues"])
api.add_router("", issues_statuses_router, tags=["Issues"])
api.add_router("", issues_issues_router, tags=["Issues"])
api.add_router("", issues_comments_router, tags=["Issues"])
api.add_router("", issues_activity_router, tags=["Issues"])
api.add_router("", issues_workflow_router, tags=["Issues"])
api.add_router("", issues_backlog_router, tags=["Issues"])
api.add_router("", issues_epics_router, tags=["Issues"])
api.add_router("", issues_attachments_router, tags=["Issues"])
api.add_router("", issues_editing_router, tags=["Issues"])

# Boards endpoints
api.add_router("", boards_router, tags=["Boards"])

# Setup Wizard endpoints
api.add_router("/setup", setup_router, tags=["Setup"])

# Users endpoints
api.add_router("/users", users_router, tags=["Users"])

# Sprints endpoints
api.add_router("", sprints_router, tags=["Sprints"])

# Reports endpoints
api.add_router("", reports_router, tags=["Reports"])

# Custom Fields endpoints
api.add_router("", custom_fields_router, tags=["Custom Fields"])

# Feed endpoints
api.add_router("", feed_router, tags=["Feed"])

# Events (SSE) endpoints
api.add_router("", events_router, tags=["Events"])

# Admin endpoints
api.add_router("", admin_router, tags=["Admin"])

# Search endpoints
api.add_router("", search_router, tags=["Search"])

# Metrics endpoints (Prometheus)
api.add_router("/metrics", metrics_router, tags=["Metrics"])

# Demo project endpoint
api.add_router("/demo", demo_router, tags=["Demo"])
