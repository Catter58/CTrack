"""
Issue service layer.
"""

from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.projects.models import Project, ProjectMembership
from apps.users.models import User

from .models import Issue, IssueComment, IssueType, Status, WorkflowTransition


class IssueService:
    """Service for issue operations."""

    @staticmethod
    def get_issue_types(project: Project) -> QuerySet[IssueType]:
        """Get issue types for project (including global)."""
        return IssueType.objects.filter(
            Q(project=project) | Q(project__isnull=True)
        ).order_by("order")

    @staticmethod
    def get_statuses(project: Project) -> QuerySet[Status]:
        """Get statuses for project (including global)."""
        return Status.objects.filter(
            Q(project=project) | Q(project__isnull=True)
        ).order_by("order")

    @staticmethod
    def get_default_status(project: Project) -> Status | None:
        """Get default (first TODO) status for project."""
        return (
            Status.objects.filter(
                Q(project=project) | Q(project__isnull=True),
                category="todo",
            )
            .order_by("order")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def create_issue(
        project: Project,
        user: User,
        title: str,
        issue_type_id: UUID,
        description: str = "",
        status_id: UUID | None = None,
        priority: str = "medium",
        assignee_id: int | None = None,
        parent_id: UUID | None = None,
        story_points: int | None = None,
        due_date=None,
    ) -> Issue:
        """Create a new issue."""
        # Get issue type
        issue_type = IssueType.objects.get(id=issue_type_id)

        # Get status (default if not specified)
        if status_id:
            status = Status.objects.get(id=status_id)
        else:
            status = IssueService.get_default_status(project)

        # Get assignee
        assignee = None
        if assignee_id:
            assignee = User.objects.filter(id=assignee_id).first()

        # Get parent
        parent = None
        if parent_id:
            parent = Issue.objects.filter(id=parent_id, project=project).first()

        issue = Issue(
            project=project,
            issue_type=issue_type,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee=assignee,
            reporter=user,
            parent=parent,
            story_points=story_points,
            due_date=due_date,
        )
        issue.save()

        return issue

    @staticmethod
    def get_issues(
        project: Project,
        status_id: UUID | None = None,
        issue_type_id: UUID | None = None,
        assignee_id: int | None = None,
        priority: str | None = None,
    ) -> QuerySet[Issue]:
        """Get issues for project with optional filters."""
        queryset = Issue.objects.filter(project=project).select_related(
            "issue_type", "status", "assignee", "reporter"
        )

        if status_id:
            queryset = queryset.filter(status_id=status_id)
        if issue_type_id:
            queryset = queryset.filter(issue_type_id=issue_type_id)
        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)
        if priority:
            queryset = queryset.filter(priority=priority)

        return queryset.order_by("-created_at")

    @staticmethod
    def get_issue_by_key(key: str) -> Issue | None:
        """Get issue by key."""
        return (
            Issue.objects.filter(key=key.upper())
            .select_related("issue_type", "status", "assignee", "reporter", "project")
            .first()
        )

    @staticmethod
    def get_issue_by_id(issue_id: UUID) -> Issue | None:
        """Get issue by ID."""
        return (
            Issue.objects.filter(id=issue_id)
            .select_related("issue_type", "status", "assignee", "reporter", "project")
            .first()
        )

    @staticmethod
    def update_issue(issue: Issue, **kwargs) -> Issue:
        """Update issue fields."""
        for field, value in kwargs.items():
            if value is not None:
                if field == "issue_type_id":
                    issue.issue_type_id = value
                elif field == "status_id":
                    issue.status_id = value
                elif field == "assignee_id":
                    issue.assignee_id = value
                elif field == "parent_id":
                    issue.parent_id = value
                else:
                    setattr(issue, field, value)

        issue.save()
        return issue

    @staticmethod
    def delete_issue(issue: Issue) -> None:
        """Delete an issue."""
        issue.delete()

    @staticmethod
    def get_comments(issue: Issue) -> QuerySet[IssueComment]:
        """Get comments for issue."""
        return issue.comments.select_related("author").order_by("created_at")

    @staticmethod
    def add_comment(issue: Issue, user: User, content: str) -> IssueComment:
        """Add comment to issue."""
        return IssueComment.objects.create(issue=issue, author=user, content=content)

    @staticmethod
    def get_available_transitions(
        issue: Issue, user: User
    ) -> QuerySet[WorkflowTransition]:
        """Get available status transitions for issue."""
        project = issue.project
        current_status = issue.status

        # Get user's role in project
        membership = ProjectMembership.objects.filter(
            project=project, user=user
        ).first()
        user_role = membership.role if membership else None

        transitions = WorkflowTransition.objects.filter(
            project=project, from_status=current_status
        ).select_related("from_status", "to_status")

        # Filter by role if specified
        result = []
        for transition in transitions:
            if not transition.allowed_roles or user_role in transition.allowed_roles:
                result.append(transition)

        return result

    @staticmethod
    def can_transition(issue: Issue, to_status_id: UUID, user: User) -> bool:
        """Check if user can transition issue to given status."""
        project = issue.project

        # Check if workflow is defined
        has_workflow = WorkflowTransition.objects.filter(project=project).exists()

        if not has_workflow:
            # No workflow defined - allow any transition
            return True

        # Check if transition exists
        transition = WorkflowTransition.objects.filter(
            project=project,
            from_status=issue.status,
            to_status_id=to_status_id,
        ).first()

        if not transition:
            return False

        # Check role restriction
        if transition.allowed_roles:
            membership = ProjectMembership.objects.filter(
                project=project, user=user
            ).first()
            if not membership or membership.role not in transition.allowed_roles:
                return False

        return True

    # Issue Type management

    @staticmethod
    def get_issue_type(issue_type_id: UUID) -> IssueType | None:
        """Get issue type by ID."""
        return IssueType.objects.filter(id=issue_type_id).first()

    @staticmethod
    def create_issue_type(
        project: Project | None,
        name: str,
        icon: str = "checkmark",
        color: str = "#1192e8",
        is_subtask: bool = False,
        parent_types: list[str] | None = None,
        order: int = 1,
    ) -> IssueType:
        """Create a new issue type."""
        return IssueType.objects.create(
            project=project,
            name=name,
            icon=icon,
            color=color,
            is_subtask=is_subtask,
            parent_types=parent_types or [],
            order=order,
        )

    @staticmethod
    def update_issue_type(issue_type: IssueType, **kwargs) -> IssueType:
        """Update issue type fields."""
        for field, value in kwargs.items():
            if value is not None:
                setattr(issue_type, field, value)
        issue_type.save()
        return issue_type

    @staticmethod
    def delete_issue_type(issue_type: IssueType) -> None:
        """Delete an issue type."""
        issue_type.delete()

    # Status management

    @staticmethod
    def get_status(status_id: UUID) -> Status | None:
        """Get status by ID."""
        return Status.objects.filter(id=status_id).first()

    @staticmethod
    def create_status(
        project: Project | None,
        name: str,
        category: str = "todo",
        color: str = "#6f6f6f",
        order: int = 1,
    ) -> Status:
        """Create a new status."""
        return Status.objects.create(
            project=project,
            name=name,
            category=category,
            color=color,
            order=order,
        )

    @staticmethod
    def update_status(status: Status, **kwargs) -> Status:
        """Update status fields."""
        for field, value in kwargs.items():
            if value is not None:
                setattr(status, field, value)
        status.save()
        return status

    @staticmethod
    def delete_status(status: Status) -> None:
        """Delete a status."""
        status.delete()
