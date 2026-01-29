"""
Главный API модуль CTrack.

Здесь собираются все роутеры приложения.
"""

from ninja import NinjaAPI

from api.auth import router as auth_router
from api.boards import router as boards_router
from api.custom_fields import router as custom_fields_router
from api.feed import router as feed_router
from api.health import router as health_router
from api.issues import router as issues_router
from api.projects import router as projects_router
from api.reports import router as reports_router
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

# Issues endpoints
api.add_router("", issues_router, tags=["Issues"])

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
