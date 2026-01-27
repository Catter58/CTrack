"""
Project service layer.
"""

from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from apps.users.models import User

from .models import Project, ProjectMembership, ProjectRole


class ProjectService:
    """Service for project operations."""

    @staticmethod
    @transaction.atomic
    def create_project(
        user: User,
        key: str,
        name: str,
        description: str = "",
        settings: dict[str, Any] | None = None,
    ) -> Project:
        """
        Create a new project.

        The creating user becomes owner and admin member.
        Default board and workflow transitions are created.
        """
        from apps.boards.models import Board
        from apps.issues.models import Status, WorkflowTransition

        project = Project.objects.create(
            key=key.upper(),
            name=name,
            description=description,
            owner=user,
            settings=settings or {},
        )

        # Add creator as admin member
        ProjectMembership.objects.create(
            project=project,
            user=user,
            role=ProjectRole.ADMIN,
        )

        # Create default Kanban board
        Board.create_default_board(project)

        # Create default workflow transitions
        statuses = list(Status.objects.filter(project__isnull=True).order_by("order"))
        if len(statuses) >= 4:
            todo, in_progress, review, done = statuses[:4]

            # К выполнению → В работе
            WorkflowTransition.objects.create(
                project=project,
                from_status=todo,
                to_status=in_progress,
                name="Взять в работу",
            )
            # В работе → На проверке
            WorkflowTransition.objects.create(
                project=project,
                from_status=in_progress,
                to_status=review,
                name="На проверку",
            )
            # В работе → К выполнению
            WorkflowTransition.objects.create(
                project=project,
                from_status=in_progress,
                to_status=todo,
                name="Вернуть",
            )
            # На проверке → Готово
            WorkflowTransition.objects.create(
                project=project,
                from_status=review,
                to_status=done,
                name="Завершить",
            )
            # На проверке → В работе
            WorkflowTransition.objects.create(
                project=project,
                from_status=review,
                to_status=in_progress,
                name="На доработку",
            )

        return project

    @staticmethod
    def get_user_projects(
        user: User, include_archived: bool = False
    ) -> QuerySet[Project]:
        """Get all projects where user is a member."""
        queryset = Project.objects.filter(memberships__user=user)

        if not include_archived:
            queryset = queryset.filter(is_archived=False)

        return queryset.distinct().order_by("-created_at")

    @staticmethod
    def get_project_by_key(key: str) -> Project | None:
        """Get project by key."""
        return Project.objects.filter(key=key.upper()).first()

    @staticmethod
    def get_project_by_id(project_id: UUID) -> Project | None:
        """Get project by ID."""
        return Project.objects.filter(id=project_id).first()

    @staticmethod
    def update_project(
        project: Project,
        name: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Project:
        """Update project details."""
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if settings is not None:
            project.settings = settings

        project.save()
        return project

    @staticmethod
    def archive_project(project: Project) -> Project:
        """Archive a project."""
        project.is_archived = True
        project.save()
        return project

    @staticmethod
    def unarchive_project(project: Project) -> Project:
        """Unarchive a project."""
        project.is_archived = False
        project.save()
        return project

    @staticmethod
    @transaction.atomic
    def delete_project_permanently(project: Project) -> bool:
        """Permanently delete a project and all related data."""
        project.delete()
        return True

    @staticmethod
    def get_user_membership(project: Project, user: User) -> ProjectMembership | None:
        """Get user's membership in project."""
        return ProjectMembership.objects.filter(project=project, user=user).first()

    @staticmethod
    def is_member(project: Project, user: User) -> bool:
        """Check if user is project member."""
        return ProjectMembership.objects.filter(project=project, user=user).exists()

    @staticmethod
    def get_members(project: Project) -> QuerySet[ProjectMembership]:
        """Get all project members."""
        return project.memberships.select_related("user").order_by("joined_at")

    @staticmethod
    def add_member(
        project: Project,
        user: User,
        role: str = ProjectRole.DEVELOPER,
    ) -> ProjectMembership:
        """Add a member to project."""
        membership, created = ProjectMembership.objects.get_or_create(
            project=project,
            user=user,
            defaults={"role": role},
        )

        if not created and membership.role != role:
            membership.role = role
            membership.save()

        return membership

    @staticmethod
    def remove_member(project: Project, user: User) -> bool:
        """Remove a member from project."""
        deleted, _ = ProjectMembership.objects.filter(
            project=project, user=user
        ).delete()
        return deleted > 0

    @staticmethod
    def change_member_role(
        project: Project,
        user: User,
        role: str,
    ) -> ProjectMembership | None:
        """Change member's role in project."""
        membership = ProjectMembership.objects.filter(
            project=project, user=user
        ).first()

        if membership:
            membership.role = role
            membership.save()

        return membership

    @staticmethod
    def can_manage_project(project: Project, user: User) -> bool:
        """Check if user can manage project settings."""
        membership = ProjectMembership.objects.filter(
            project=project, user=user
        ).first()
        return membership is not None and membership.can_manage

    @staticmethod
    def can_manage_members(project: Project, user: User) -> bool:
        """Check if user can manage project members."""
        membership = ProjectMembership.objects.filter(
            project=project, user=user
        ).first()
        return membership is not None and membership.is_admin
