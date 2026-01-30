"""
Issue service layer.
"""

import re
from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.projects.models import Project, ProjectMembership
from apps.users.models import User
from apps.users.services import NotificationService

from .models import (
    ActivityAction,
    Issue,
    IssueActivity,
    IssueAttachment,
    IssueComment,
    IssueType,
    Status,
    StatusCategory,
    WorkflowTransition,
)


class ActivityService:
    @staticmethod
    def log(
        issue: Issue,
        user: User,
        action: str,
        field_name: str = "",
        old_value=None,
        new_value=None,
    ) -> IssueActivity:
        activity = IssueActivity.objects.create(
            issue=issue,
            user=user,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )

        # Publish real-time feed event
        from apps.core.events import publish_activity

        user_full_name = (
            " ".join(p for p in [user.first_name, user.last_name] if p).strip()
            or user.username
        )

        publish_activity(
            issue.project_id,
            {
                "id": str(activity.id),
                "action": action,
                "field_name": field_name,
                "old_value": old_value,
                "new_value": new_value,
                "created_at": activity.created_at.isoformat(),
                "issue": {
                    "key": issue.key,
                    "title": issue.title,
                    "project": {
                        "key": issue.project.key,
                        "name": issue.project.name,
                    },
                },
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user_full_name,
                    "avatar": user.avatar.url if user.avatar else None,
                },
            },
        )

        return activity

    @staticmethod
    def log_creation(issue: Issue, user: User) -> IssueActivity:
        return ActivityService.log(issue, user, ActivityAction.CREATED)

    @staticmethod
    def log_status_change(
        issue: Issue,
        user: User,
        old_status_name: str,
        new_status_name: str,
        old_status_category: str | None = None,
        new_status_category: str | None = None,
    ) -> IssueActivity:
        old_value = {"name": old_status_name}
        new_value = {"name": new_status_name}
        if old_status_category:
            old_value["category"] = old_status_category
        if new_status_category:
            new_value["category"] = new_status_category
        return ActivityService.log(
            issue,
            user,
            ActivityAction.STATUS_CHANGED,
            "status",
            old_value,
            new_value,
        )

    @staticmethod
    def log_assignment(
        issue: Issue, user: User, old_assignee: str | None, new_assignee: str | None
    ) -> IssueActivity:
        return ActivityService.log(
            issue,
            user,
            ActivityAction.ASSIGNED,
            "assignee",
            {"name": old_assignee} if old_assignee else None,
            {"name": new_assignee} if new_assignee else None,
        )

    @staticmethod
    def log_unassignment(issue: Issue, user: User, old_assignee: str) -> IssueActivity:
        return ActivityService.log(
            issue,
            user,
            ActivityAction.UNASSIGNED,
            "assignee",
            {"name": old_assignee},
            None,
        )

    @staticmethod
    def log_priority_change(
        issue: Issue, user: User, old_priority: str, new_priority: str
    ) -> IssueActivity:
        return ActivityService.log(
            issue,
            user,
            ActivityAction.PRIORITY_CHANGED,
            "priority",
            {"value": old_priority},
            {"value": new_priority},
        )

    @staticmethod
    def log_due_date_change(
        issue: Issue, user: User, old_date: str | None, new_date: str | None
    ) -> IssueActivity:
        return ActivityService.log(
            issue,
            user,
            ActivityAction.DUE_DATE_CHANGED,
            "due_date",
            {"value": old_date} if old_date else None,
            {"value": new_date} if new_date else None,
        )

    @staticmethod
    def log_story_points_change(
        issue: Issue, user: User, old_points: int | None, new_points: int | None
    ) -> IssueActivity:
        return ActivityService.log(
            issue,
            user,
            ActivityAction.STORY_POINTS_CHANGED,
            "story_points",
            {"value": old_points} if old_points is not None else None,
            {"value": new_points} if new_points is not None else None,
        )

    @staticmethod
    def log_attachment_added(issue: Issue, user: User, filename: str) -> IssueActivity:
        return ActivityService.log(
            issue,
            user,
            ActivityAction.ATTACHMENT_ADDED,
            "attachment",
            None,
            {"filename": filename},
        )

    @staticmethod
    def log_attachment_removed(
        issue: Issue, user: User, filename: str
    ) -> IssueActivity:
        return ActivityService.log(
            issue,
            user,
            ActivityAction.ATTACHMENT_REMOVED,
            "attachment",
            {"filename": filename},
            None,
        )

    @staticmethod
    def log_comment(issue: Issue, user: User) -> IssueActivity:
        return ActivityService.log(issue, user, ActivityAction.COMMENTED)

    @staticmethod
    def get_issue_activities(issue: Issue) -> QuerySet[IssueActivity]:
        return issue.activities.select_related("user").order_by("-created_at")

    @staticmethod
    def get_project_activities(
        project_id: UUID, limit: int = 50
    ) -> QuerySet[IssueActivity]:
        return (
            IssueActivity.objects.filter(issue__project_id=project_id)
            .select_related("user", "issue")
            .order_by("-created_at")[:limit]
        )


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
        epic_id: UUID | None = None,
        story_points: int | None = None,
        due_date=None,
        custom_fields: dict | None = None,
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

        # Get epic
        epic = None
        if epic_id:
            epic = Issue.objects.filter(
                id=epic_id, project=project, issue_type__is_epic=True
            ).first()

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
            epic=epic,
            story_points=story_points,
            due_date=due_date,
            custom_fields=custom_fields or {},
        )
        issue.save()

        # Log creation activity
        ActivityService.log_creation(issue, user)

        # Publish real-time event
        from apps.core.events import publish_issue_created

        publish_issue_created(
            issue.project_id,
            {
                "id": str(issue.id),
                "key": issue.key,
                "title": issue.title,
                "status_id": str(issue.status_id),
                "issue_type_id": str(issue.issue_type_id),
            },
        )

        return issue

    @staticmethod
    def get_issues(
        project: Project,
        status_id: UUID | None = None,
        issue_type_id: UUID | None = None,
        assignee_id: int | None = None,
        priority: str | None = None,
        epic_id: UUID | None = None,
        search: str | None = None,
    ) -> QuerySet[Issue]:
        """Get issues for project with optional filters."""
        from django.db.models import Q

        queryset = Issue.objects.filter(project=project).select_related(
            "issue_type", "status", "assignee", "reporter", "project", "sprint"
        )

        if status_id:
            queryset = queryset.filter(status_id=status_id)
        if issue_type_id:
            queryset = queryset.filter(issue_type_id=issue_type_id)
        if assignee_id is not None:
            if assignee_id == 0:
                queryset = queryset.filter(assignee__isnull=True)
            else:
                queryset = queryset.filter(assignee_id=assignee_id)
        if priority:
            queryset = queryset.filter(priority=priority)
        if epic_id:
            queryset = queryset.filter(epic_id=epic_id)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(key__icontains=search)
            )

        return queryset.order_by("-created_at")

    @staticmethod
    def get_backlog(
        project: Project,
        limit: int | None = None,
        offset: int = 0,
    ) -> QuerySet[Issue]:
        """Get backlog issues (not in any active/planned sprint)."""
        from apps.sprints.models import SprintStatus

        queryset = (
            Issue.objects.filter(project=project)
            .exclude(sprint__status__in=[SprintStatus.ACTIVE, SprintStatus.PLANNED])
            .select_related(
                "issue_type", "status", "assignee", "reporter", "project", "sprint"
            )
            .order_by("priority", "-created_at")
        )

        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]

        return queryset

    @staticmethod
    def get_backlog_count(project: Project) -> int:
        """Get count of backlog issues."""
        from apps.sprints.models import SprintStatus

        return (
            Issue.objects.filter(project=project)
            .exclude(sprint__status__in=[SprintStatus.ACTIVE, SprintStatus.PLANNED])
            .count()
        )

    @staticmethod
    @transaction.atomic
    def update_issue_sprint(
        issue: Issue,
        sprint_id: UUID | None,
    ) -> Issue:
        """Update issue sprint assignment."""
        from apps.sprints.models import Sprint, SprintStatus

        if sprint_id is None:
            issue.sprint = None
        else:
            sprint = Sprint.objects.get(id=sprint_id)
            if sprint.status == SprintStatus.COMPLETED:
                raise ValueError("Нельзя добавить задачу в завершённый спринт")
            if sprint.project_id != issue.project_id:
                raise ValueError("Спринт принадлежит другому проекту")
            issue.sprint = sprint

        issue.save()
        return issue

    @staticmethod
    def get_issue_by_key(key: str) -> Issue | None:
        """Get issue by key."""
        return (
            Issue.objects.filter(key=key.upper())
            .select_related(
                "issue_type",
                "status",
                "assignee",
                "reporter",
                "project",
                "sprint",
                "parent",
                "parent__status",
                "parent__assignee",
            )
            .first()
        )

    @staticmethod
    def get_issue_by_id(issue_id: UUID) -> Issue | None:
        """Get issue by ID."""
        return (
            Issue.objects.filter(id=issue_id)
            .select_related(
                "issue_type", "status", "assignee", "reporter", "project", "sprint"
            )
            .first()
        )

    @staticmethod
    @transaction.atomic
    def update_issue(issue: Issue, user: User | None = None, **kwargs) -> Issue:
        """Update issue fields with activity logging."""
        # Capture old values for activity logging
        old_status = issue.status
        old_assignee = issue.assignee
        old_priority = issue.priority
        old_due_date = issue.due_date
        old_story_points = issue.story_points

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
                elif field == "epic_id":
                    issue.epic_id = value
                else:
                    setattr(issue, field, value)

        issue.save()

        # Log activities if user is provided
        if user:
            # Reload related objects to get updated names
            issue.refresh_from_db()

            # Status change
            if "status_id" in kwargs and old_status.id != issue.status_id:
                ActivityService.log_status_change(
                    issue,
                    user,
                    old_status.name,
                    issue.status.name,
                    old_status.category,
                    issue.status.category,
                )

            # Assignee change
            if "assignee_id" in kwargs:
                old_name = old_assignee.get_full_name() if old_assignee else None
                new_name = issue.assignee.get_full_name() if issue.assignee else None

                if old_name != new_name:
                    if new_name is None and old_name:
                        # Unassigned
                        ActivityService.log_unassignment(issue, user, old_name)
                    else:
                        # Assigned or reassigned
                        ActivityService.log_assignment(issue, user, old_name, new_name)

            # Priority change
            if "priority" in kwargs and old_priority != issue.priority:
                ActivityService.log_priority_change(
                    issue, user, old_priority, issue.priority
                )

            # Due date change
            if "due_date" in kwargs:
                old_date_str = old_due_date.isoformat() if old_due_date else None
                new_date_str = issue.due_date.isoformat() if issue.due_date else None
                if old_date_str != new_date_str:
                    ActivityService.log_due_date_change(
                        issue, user, old_date_str, new_date_str
                    )

            # Story points change
            if "story_points" in kwargs and old_story_points != issue.story_points:
                ActivityService.log_story_points_change(
                    issue, user, old_story_points, issue.story_points
                )

            # Send email notifications (async via Celery in production)
            # Assignment notification
            if (
                "assignee_id" in kwargs
                and issue.assignee
                and issue.assignee != old_assignee
            ):
                NotificationService.send_assignment_notification(issue, issue.assignee)

            # Status change notification
            if "status_id" in kwargs and old_status.id != issue.status_id:
                NotificationService.send_status_change_notification(
                    issue, old_status.name, issue.status.name, user
                )

        # Publish real-time events
        from apps.core.events import publish_issue_moved, publish_issue_updated

        # Check if status changed (issue.moved event)
        if "status_id" in kwargs and old_status.id != issue.status_id:
            publish_issue_moved(
                issue.project_id,
                issue.key,
                old_status.name,
                issue.status.name,
            )
        else:
            # General update event
            publish_issue_updated(
                issue.project_id,
                {
                    "id": str(issue.id),
                    "key": issue.key,
                    "title": issue.title,
                    "status_id": str(issue.status_id),
                },
            )

        return issue

    @staticmethod
    def delete_issue(issue: Issue) -> None:
        """Delete an issue."""
        # Save data for event before deletion
        project_id = issue.project_id
        issue_key = issue.key

        issue.delete()

        # Publish real-time event
        from apps.core.events import publish_issue_deleted

        publish_issue_deleted(project_id, issue_key)

    @staticmethod
    def get_comments(issue: Issue) -> QuerySet[IssueComment]:
        """Get comments for issue."""
        return issue.comments.select_related("author").order_by("created_at")

    @staticmethod
    def add_comment(issue: Issue, user: User, content: str) -> IssueComment:
        comment = IssueComment.objects.create(issue=issue, author=user, content=content)
        ActivityService.log_comment(issue, user)

        # Publish real-time event
        from apps.core.events import publish_comment_added

        publish_comment_added(
            issue.project_id,
            issue.key,
            {
                "id": str(comment.id),
                "author_id": user.id,
                "author_name": user.get_full_name() or user.username,
            },
        )

        # Send email notifications
        # Notify reporter and assignee about new comment
        NotificationService.send_comment_notification(issue, comment)

        # Notify mentioned users
        mentioned_users = IssueService.get_mentioned_users(content)
        if mentioned_users.exists():
            NotificationService.send_mention_notification(
                issue, list(mentioned_users), user
            )

        return comment

    @staticmethod
    def update_comment(comment: IssueComment, content: str) -> IssueComment:
        comment.content = content
        comment.save(update_fields=["content", "updated_at"])
        return comment

    @staticmethod
    def delete_comment(comment: IssueComment) -> None:
        comment.delete()

    @staticmethod
    def get_comment_by_id(comment_id: UUID) -> IssueComment | None:
        return (
            IssueComment.objects.select_related("issue", "issue__project", "author")
            .filter(id=comment_id)
            .first()
        )

    @staticmethod
    def parse_mentions(content: str) -> list[str]:
        pattern = r"@(\w+)"
        return list(set(re.findall(pattern, content)))

    @staticmethod
    def get_mentioned_users(content: str) -> QuerySet[User]:
        usernames = IssueService.parse_mentions(content)
        if not usernames:
            return User.objects.none()
        return User.objects.filter(username__in=usernames)

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

    @staticmethod
    @transaction.atomic
    def bulk_update_story_points(
        project: "Project",
        updates: list[dict],
    ) -> tuple[int, list[str]]:
        """
        Bulk update story points for multiple issues.

        Args:
            project: Project to validate issue ownership
            updates: List of dicts with 'key' and 'story_points'

        Returns:
            Tuple of (updated_count, failed_keys)
        """
        updated = 0
        failed = []

        for item in updates:
            key = item.get("key")
            story_points = item.get("story_points")

            try:
                issue = Issue.objects.get(key=key, project=project)
                if story_points is not None and story_points < 0:
                    failed.append(key)
                    continue
                issue.story_points = story_points
                issue.save(update_fields=["story_points", "updated_at"])
                updated += 1
            except Issue.DoesNotExist:
                failed.append(key)

        return updated, failed

    @staticmethod
    def get_epics(project: Project) -> list[dict]:
        """
        Get all epics for a project with progress statistics.

        Returns list of dicts with epic data and computed progress.
        """
        from django.db.models import Q, Sum

        epics = Issue.objects.filter(
            project=project,
            issue_type__is_epic=True,
        ).select_related("issue_type", "status")

        result = []
        for epic in epics:
            # Get all issues linked to this epic
            epic_issues = Issue.objects.filter(epic=epic)

            # Calculate statistics
            total_issues = epic_issues.count()
            completed_issues = epic_issues.filter(
                status__category=StatusCategory.DONE
            ).count()

            sp_stats = epic_issues.aggregate(
                total_sp=Sum("story_points"),
                completed_sp=Sum(
                    "story_points",
                    filter=Q(status__category=StatusCategory.DONE),
                ),
            )

            result.append(
                {
                    "id": epic.id,
                    "key": epic.key,
                    "title": epic.title,
                    "description": epic.description,
                    "priority": epic.priority,
                    "status": epic.status,
                    "total_issues": total_issues,
                    "completed_issues": completed_issues,
                    "total_story_points": sp_stats["total_sp"] or 0,
                    "completed_story_points": sp_stats["completed_sp"] or 0,
                }
            )

        return result

    @staticmethod
    def get_epic(epic_id: UUID) -> Issue | None:
        """Get an epic by ID."""
        try:
            return Issue.objects.select_related("issue_type", "status").get(
                id=epic_id, issue_type__is_epic=True
            )
        except Issue.DoesNotExist:
            return None

    # Issue hierarchy methods

    @staticmethod
    def validate_parent(
        issue: Issue | None,
        parent_id: UUID,
        project: Project,
    ) -> tuple[bool, str | None]:
        """
        Validate parent assignment for an issue.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check parent exists and belongs to same project
        try:
            parent = Issue.objects.select_related("issue_type").get(
                id=parent_id, project=project
            )
        except Issue.DoesNotExist:
            return False, "Родительская задача не найдена"

        # Check parent is not the issue itself
        if issue and str(issue.id) == str(parent_id):
            return False, "Задача не может быть родителем самой себя"

        # Check for cycles (parent cannot be a descendant of issue)
        if issue:
            current = parent
            visited = {str(issue.id)}
            while current.parent_id:
                if str(current.parent_id) in visited:
                    return False, "Обнаружен цикл в иерархии задач"
                visited.add(str(current.parent_id))
                try:
                    current = Issue.objects.get(id=current.parent_id)
                except Issue.DoesNotExist:
                    break

        # Check allowed parent types (if defined)
        if issue and issue.issue_type.parent_types:
            allowed_types = issue.issue_type.parent_types
            if str(parent.issue_type_id) not in allowed_types:
                return (
                    False,
                    f"Тип '{parent.issue_type.name}' не может быть родителем для '{issue.issue_type.name}'",
                )

        return True, None

    @staticmethod
    def get_children(issue: Issue) -> QuerySet[Issue]:
        """Get direct children (subtasks) of an issue."""
        return (
            Issue.objects.filter(parent=issue)
            .select_related(
                "issue_type", "status", "assignee", "reporter", "project", "sprint"
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_children_stats(issue: Issue) -> dict:
        """Get children statistics for an issue."""
        children = Issue.objects.filter(parent=issue)
        total = children.count()
        completed = children.filter(status__category=StatusCategory.DONE).count()

        return {
            "children_count": total,
            "completed_children_count": completed,
        }

    # Workflow transition management

    @staticmethod
    def get_workflow_transition_by_id(
        transition_id: UUID,
    ) -> WorkflowTransition | None:
        """Get workflow transition by ID."""
        return (
            WorkflowTransition.objects.filter(id=transition_id)
            .select_related("project", "from_status", "to_status")
            .first()
        )

    @staticmethod
    def create_workflow_transition(
        project: Project,
        from_status_id: UUID,
        to_status_id: UUID,
        name: str = "",
        allowed_roles: list[str] | None = None,
    ) -> WorkflowTransition:
        """Create a new workflow transition."""
        from_status = Status.objects.get(id=from_status_id)
        to_status = Status.objects.get(id=to_status_id)

        return WorkflowTransition.objects.create(
            project=project,
            from_status=from_status,
            to_status=to_status,
            name=name,
            allowed_roles=allowed_roles or [],
        )

    @staticmethod
    def update_workflow_transition(
        transition: WorkflowTransition, **kwargs
    ) -> WorkflowTransition:
        """Update workflow transition fields."""
        for field, value in kwargs.items():
            if value is not None:
                setattr(transition, field, value)
        transition.save()
        return transition

    @staticmethod
    def delete_workflow_transition(transition: WorkflowTransition) -> None:
        """Delete a workflow transition."""
        transition.delete()

    @staticmethod
    @transaction.atomic
    def execute_transition(
        issue: Issue, transition: WorkflowTransition, user: User
    ) -> Issue:
        """Execute a workflow transition on an issue."""
        if issue.status_id != transition.from_status_id:
            raise ValueError("Текущий статус задачи не соответствует переходу")

        if issue.project_id != transition.project_id:
            raise ValueError("Переход не принадлежит проекту задачи")

        if transition.allowed_roles:
            membership = ProjectMembership.objects.filter(
                project=issue.project, user=user
            ).first()
            if not membership or membership.role not in transition.allowed_roles:
                raise ValueError("Недостаточно прав для выполнения перехода")

        issue.status = transition.to_status
        issue.save()
        return issue

    # Attachment methods

    @staticmethod
    def create_attachment(
        issue: Issue,
        user: User,
        file,
        filename: str,
        content_type: str,
    ) -> IssueAttachment:
        """Create a new attachment for an issue."""
        attachment = IssueAttachment.objects.create(
            issue=issue,
            uploaded_by=user,
            file=file,
            filename=filename,
            file_size=file.size,
            content_type=content_type,
        )
        ActivityService.log_attachment_added(issue, user, filename)
        return attachment

    @staticmethod
    def get_attachment_by_id(attachment_id: UUID) -> IssueAttachment | None:
        """Get attachment by ID."""
        return (
            IssueAttachment.objects.filter(id=attachment_id)
            .select_related("issue", "issue__project", "uploaded_by")
            .first()
        )

    @staticmethod
    def delete_attachment(
        attachment: IssueAttachment, user: User | None = None
    ) -> None:
        """Delete an attachment and its file."""
        if user:
            ActivityService.log_attachment_removed(
                attachment.issue, user, attachment.filename
            )
        attachment.file.delete(save=False)
        attachment.delete()

    @staticmethod
    def get_attachments(issue: Issue) -> QuerySet[IssueAttachment]:
        """Get all attachments for an issue."""
        return issue.attachments.select_related("uploaded_by").order_by("-created_at")

    @staticmethod
    def get_global_issues(
        user: User,
        project_id: UUID | None = None,
        status_id: UUID | None = None,
        assignee_id: int | None = None,
        reporter_id: int | None = None,
        priority: str | None = None,
        issue_type_id: UUID | None = None,
        sprint_id: UUID | None = None,
        due_date_from=None,
        due_date_to=None,
        created_from=None,
        created_to=None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> QuerySet[Issue]:
        """
        Get issues from all projects where user is a member.

        Supports filtering by various criteria and sorting.
        """
        # Get projects where user is a member
        user_project_ids = ProjectMembership.objects.filter(user=user).values_list(
            "project_id", flat=True
        )

        # Base queryset with select_related for performance
        queryset = Issue.objects.filter(project_id__in=user_project_ids).select_related(
            "issue_type",
            "status",
            "assignee",
            "reporter",
            "project",
            "sprint",
        )

        # Apply filters
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if status_id:
            queryset = queryset.filter(status_id=status_id)
        if assignee_id is not None:
            if assignee_id == 0:
                queryset = queryset.filter(assignee__isnull=True)
            else:
                queryset = queryset.filter(assignee_id=assignee_id)
        if reporter_id:
            queryset = queryset.filter(reporter_id=reporter_id)
        if priority:
            queryset = queryset.filter(priority=priority)
        if issue_type_id:
            queryset = queryset.filter(issue_type_id=issue_type_id)
        if sprint_id:
            queryset = queryset.filter(sprint_id=sprint_id)
        if due_date_from:
            queryset = queryset.filter(due_date__gte=due_date_from)
        if due_date_to:
            queryset = queryset.filter(due_date__lte=due_date_to)
        if created_from:
            queryset = queryset.filter(created_at__date__gte=created_from)
        if created_to:
            queryset = queryset.filter(created_at__date__lte=created_to)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(key__icontains=search)
            )

        # Apply sorting
        valid_sort_fields = {"created_at", "updated_at", "due_date", "priority"}
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"

        # For priority, use custom ordering
        if sort_by == "priority":
            from django.db.models import Case, IntegerField, Value, When

            priority_order = Case(
                When(priority="highest", then=Value(1)),
                When(priority="high", then=Value(2)),
                When(priority="medium", then=Value(3)),
                When(priority="low", then=Value(4)),
                When(priority="lowest", then=Value(5)),
                default=Value(3),
                output_field=IntegerField(),
            )
            if sort_order == "desc":
                queryset = queryset.annotate(priority_order=priority_order).order_by(
                    "-priority_order"
                )
            else:
                queryset = queryset.annotate(priority_order=priority_order).order_by(
                    "priority_order"
                )
        else:
            order_prefix = "-" if sort_order == "desc" else ""
            queryset = queryset.order_by(f"{order_prefix}{sort_by}")

        return queryset
