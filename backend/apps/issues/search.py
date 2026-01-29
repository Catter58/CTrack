"""
Full-text search service for CTrack issues.

Uses PostgreSQL tsvector with:
- Russian language config for title/description
- Simple config for key (exact match)
- Weights: A for title/key, B for description
"""

from uuid import UUID

from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank

from apps.issues.models import Issue
from apps.projects.models import Project, ProjectMembership
from apps.users.models import User


class SearchService:
    """Service for full-text search operations."""

    @staticmethod
    def search_issues(
        query: str,
        user: User,
        project_id: UUID | None = None,
        filters: dict | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """
        Search issues with full-text search.

        Args:
            query: Search query string
            user: User performing the search
            project_id: Optional project UUID to limit search scope
            filters: Optional dict with status_id, assignee_id, priority
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            dict with 'items', 'total' keys
        """
        # Get user's accessible projects
        if project_id:
            project_ids = [project_id]
        else:
            project_ids = list(
                ProjectMembership.objects.filter(user=user).values_list(
                    "project_id", flat=True
                )
            )

        if not project_ids:
            return {"items": [], "total": 0}

        # Check if query looks like issue key (e.g., PROJ-123)
        is_key_search = "-" in query and query.split("-")[0].isalpha()

        if is_key_search:
            # Exact match on key
            qs = Issue.objects.filter(
                project_id__in=project_ids, key__icontains=query
            ).order_by("-created_at")
        else:
            # Full-text search with Russian config
            search_query = SearchQuery(query, config="russian")
            qs = (
                Issue.objects.annotate(
                    rank=SearchRank("search_vector", search_query),
                    headline_title=SearchHeadline(
                        "title",
                        search_query,
                        start_sel="<mark>",
                        stop_sel="</mark>",
                        config="russian",
                    ),
                    headline_description=SearchHeadline(
                        "description",
                        search_query,
                        start_sel="<mark>",
                        stop_sel="</mark>",
                        config="russian",
                        max_words=30,
                        min_words=15,
                    ),
                )
                .filter(project_id__in=project_ids, search_vector=search_query)
                .order_by("-rank", "-created_at")
            )

        # Apply additional filters
        if filters:
            if filters.get("status_id"):
                qs = qs.filter(status_id=filters["status_id"])
            if filters.get("assignee_id"):
                qs = qs.filter(assignee_id=filters["assignee_id"])
            if filters.get("priority"):
                qs = qs.filter(priority=filters["priority"])

        total = qs.count()
        items = qs.select_related(
            "project", "status", "assignee", "issue_type", "reporter"
        )[offset : offset + limit]

        return {
            "items": list(items),
            "total": total,
        }

    @staticmethod
    def search_global(query: str, user: User, limit: int = 10) -> dict:
        """
        Global search across all user's projects.

        Returns issues and projects grouped.

        Args:
            query: Search query string
            user: User performing the search
            limit: Maximum number of results per category

        Returns:
            dict with 'issues' and 'projects' keys
        """
        project_ids = list(
            ProjectMembership.objects.filter(user=user).values_list(
                "project_id", flat=True
            )
        )

        if not project_ids:
            return {"issues": [], "projects": []}

        # Check if query looks like issue key
        is_key_search = "-" in query and query.split("-")[0].isalpha()

        if is_key_search:
            # Search by key
            issues = (
                Issue.objects.filter(project_id__in=project_ids, key__icontains=query)
                .select_related("project", "status", "issue_type", "assignee")
                .order_by("-created_at")[:limit]
            )
        else:
            # Full-text search
            search_query = SearchQuery(query, config="russian")
            issues = (
                Issue.objects.annotate(rank=SearchRank("search_vector", search_query))
                .filter(project_id__in=project_ids, search_vector=search_query)
                .select_related("project", "status", "issue_type", "assignee")
                .order_by("-rank", "-created_at")[:limit]
            )

        # Search projects by name
        projects = Project.objects.filter(
            id__in=project_ids, name__icontains=query
        ).order_by("-created_at")[:limit]

        return {
            "issues": list(issues),
            "projects": list(projects),
        }
