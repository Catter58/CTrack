"""
Search API endpoints.
"""

from uuid import UUID

from ninja import Query, Router, Schema

from apps.issues.schemas import IssueTypeSchema, StatusSchema
from apps.issues.search import SearchService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, UserSchema

router = Router(auth=AuthBearer(), tags=["Search"])


# Schemas for search results


class ProjectInfoSchema(Schema):
    """Minimal project info for search results."""

    id: UUID
    key: str
    name: str


class SearchIssueSchema(Schema):
    """Issue schema for search results."""

    id: UUID
    key: str
    title: str
    priority: str
    issue_type: IssueTypeSchema
    status: StatusSchema
    assignee: UserSchema | None
    project: ProjectInfoSchema
    headline_title: str | None = None
    headline_description: str | None = None


class SearchProjectSchema(Schema):
    """Project schema for search results."""

    id: UUID
    key: str
    name: str
    description: str


class GlobalSearchResponseSchema(Schema):
    """Response schema for global search."""

    query: str
    issues: list[SearchIssueSchema]
    projects: list[SearchProjectSchema]


class ProjectSearchResultSchema(Schema):
    """Single issue result with highlights."""

    id: UUID
    key: str
    title: str
    priority: str
    issue_type: IssueTypeSchema
    status: StatusSchema
    assignee: UserSchema | None
    headline_title: str | None = None
    headline_description: str | None = None


class ProjectSearchResponseSchema(Schema):
    """Response schema for project search."""

    query: str
    items: list[ProjectSearchResultSchema]
    total: int
    page: int
    page_size: int


# Helper functions


def format_issue_for_search(issue) -> dict:
    """Format issue object for search response."""
    return {
        "id": issue.id,
        "key": issue.key,
        "title": issue.title,
        "priority": issue.priority,
        "issue_type": issue.issue_type,
        "status": issue.status,
        "assignee": issue.assignee,
        "project": {
            "id": issue.project.id,
            "key": issue.project.key,
            "name": issue.project.name,
        },
        "headline_title": getattr(issue, "headline_title", None),
        "headline_description": getattr(issue, "headline_description", None),
    }


def format_project_for_search(project) -> dict:
    """Format project object for search response."""
    return {
        "id": project.id,
        "key": project.key,
        "name": project.name,
        "description": project.description,
    }


def format_issue_with_highlights(issue) -> dict:
    """Format issue object with search highlights."""
    return {
        "id": issue.id,
        "key": issue.key,
        "title": issue.title,
        "priority": issue.priority,
        "issue_type": issue.issue_type,
        "status": issue.status,
        "assignee": issue.assignee,
        "headline_title": getattr(issue, "headline_title", None),
        "headline_description": getattr(issue, "headline_description", None),
    }


# Endpoints


@router.get(
    "/search",
    response={200: GlobalSearchResponseSchema},
    summary="Global search",
    description="Search across all user's accessible projects",
)
def global_search(
    request,
    q: str = Query(..., min_length=2, description="Search query (min 2 characters)"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results per category"),
):
    """
    Global search across all user's accessible data.

    Searches for:
    - Issues (by title, description, or key)
    - Projects (by name)

    Returns results grouped by type.
    """
    result = SearchService.search_global(q, request.auth, limit)

    return 200, {
        "query": q,
        "issues": [format_issue_for_search(i) for i in result["issues"]],
        "projects": [format_project_for_search(p) for p in result["projects"]],
    }


@router.get(
    "/projects/{key}/search",
    response={
        200: ProjectSearchResponseSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
    summary="Project search",
    description="Search issues within a specific project",
)
def project_search(
    request,
    key: str,
    q: str = Query(..., min_length=2, description="Search query (min 2 characters)"),
    status_id: UUID = None,
    assignee_id: int = None,
    priority: str = None,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
):
    """
    Search issues within a specific project.

    Supports filtering by status, assignee, and priority.
    Returns paginated results with search highlights.
    """
    project = ProjectService.get_project_by_key(key)
    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    filters = {
        "status_id": status_id,
        "assignee_id": assignee_id,
        "priority": priority,
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    offset = (page - 1) * page_size
    result = SearchService.search_issues(
        q, request.auth, project.id, filters, page_size, offset
    )

    return 200, {
        "query": q,
        "items": [format_issue_with_highlights(i) for i in result["items"]],
        "total": result["total"],
        "page": page,
        "page_size": page_size,
    }
