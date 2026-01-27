from datetime import date, timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.issues.models import Issue, StatusCategory
from apps.projects.models import Project
from apps.sprints.models import Sprint, SprintStatus


class SprintServiceError(Exception):
    pass


class SprintService:
    @staticmethod
    def get_sprints(
        project: Project,
        status: str | None = None,
    ) -> list[Sprint]:
        queryset = Sprint.objects.filter(project=project)
        if status:
            queryset = queryset.filter(status=status)
        return list(queryset.order_by("-start_date"))

    @staticmethod
    def get_sprint(sprint_id: UUID) -> Sprint:
        return Sprint.objects.get(id=sprint_id)

    @staticmethod
    def get_active_sprint(project: Project) -> Sprint | None:
        return Sprint.objects.filter(
            project=project,
            status=SprintStatus.ACTIVE,
        ).first()

    @staticmethod
    def _validate_dates(start_date: date, end_date: date) -> None:
        if start_date >= end_date:
            raise SprintServiceError("Дата начала должна быть раньше даты окончания")

    @staticmethod
    def _check_overlapping_active_sprint(
        project: Project,
        exclude_sprint_id: UUID | None = None,
    ) -> None:
        query = Sprint.objects.filter(
            project=project,
            status=SprintStatus.ACTIVE,
        )
        if exclude_sprint_id:
            query = query.exclude(id=exclude_sprint_id)
        if query.exists():
            raise SprintServiceError("В проекте уже есть активный спринт")

    @staticmethod
    @transaction.atomic
    def create_sprint(
        project: Project,
        name: str,
        start_date: date,
        end_date: date,
        goal: str = "",
    ) -> Sprint:
        SprintService._validate_dates(start_date, end_date)

        sprint = Sprint.objects.create(
            project=project,
            name=name,
            goal=goal,
            start_date=start_date,
            end_date=end_date,
            status=SprintStatus.PLANNED,
        )
        return sprint

    @staticmethod
    @transaction.atomic
    def update_sprint(
        sprint: Sprint,
        name: str | None = None,
        goal: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Sprint:
        if name is not None:
            sprint.name = name
        if goal is not None:
            sprint.goal = goal
        if start_date is not None:
            sprint.start_date = start_date
        if end_date is not None:
            sprint.end_date = end_date

        SprintService._validate_dates(sprint.start_date, sprint.end_date)
        sprint.save()
        return sprint

    @staticmethod
    def _calculate_story_points(sprint: Sprint) -> int:
        result = sprint.issues.aggregate(total=Sum("story_points"))
        return result["total"] or 0

    @staticmethod
    def _calculate_completed_story_points(sprint: Sprint) -> int:
        result = sprint.issues.filter(
            status__category=StatusCategory.DONE,
        ).aggregate(total=Sum("story_points"))
        return result["total"] or 0

    @staticmethod
    @transaction.atomic
    def start_sprint(sprint: Sprint) -> Sprint:
        if sprint.status != SprintStatus.PLANNED:
            raise SprintServiceError("Можно запустить только запланированный спринт")

        SprintService._check_overlapping_active_sprint(sprint.project)

        sprint.initial_story_points = SprintService._calculate_story_points(sprint)
        sprint.status = SprintStatus.ACTIVE
        sprint.save()
        return sprint

    @staticmethod
    @transaction.atomic
    def complete_sprint(
        sprint: Sprint,
        move_incomplete_to: UUID | str | None = None,
    ) -> Sprint:
        if sprint.status != SprintStatus.ACTIVE:
            raise SprintServiceError("Можно завершить только активный спринт")

        sprint.completed_story_points = SprintService._calculate_completed_story_points(
            sprint
        )
        sprint.status = SprintStatus.COMPLETED
        sprint.save()

        incomplete_issues = sprint.issues.exclude(
            status__category=StatusCategory.DONE,
        )

        if move_incomplete_to == "backlog" or move_incomplete_to is None:
            incomplete_issues.update(sprint=None)
        elif move_incomplete_to:
            target_sprint = Sprint.objects.get(id=move_incomplete_to)
            if target_sprint.status == SprintStatus.COMPLETED:
                raise SprintServiceError("Нельзя перенести задачи в завершённый спринт")
            incomplete_issues.update(sprint=target_sprint)

        return sprint

    @staticmethod
    @transaction.atomic
    def delete_sprint(sprint: Sprint) -> None:
        sprint.issues.update(sprint=None)
        sprint.delete()

    @staticmethod
    def get_sprint_issues(sprint: Sprint) -> list[Issue]:
        return list(sprint.issues.select_related("issue_type", "status", "assignee"))

    @staticmethod
    @transaction.atomic
    def add_issue_to_sprint(issue: Issue, sprint: Sprint) -> Issue:
        if sprint.status == SprintStatus.COMPLETED:
            raise SprintServiceError("Нельзя добавить задачу в завершённый спринт")
        issue.sprint = sprint
        issue.save()
        return issue

    @staticmethod
    @transaction.atomic
    def remove_issue_from_sprint(issue: Issue) -> Issue:
        issue.sprint = None
        issue.save()
        return issue

    @staticmethod
    def get_sprint_stats(sprint: Sprint) -> dict:
        total_sp = SprintService._calculate_story_points(sprint)
        completed_sp = SprintService._calculate_completed_story_points(sprint)
        total_issues = sprint.issues.count()
        completed_issues = sprint.issues.filter(
            status__category=StatusCategory.DONE,
        ).count()

        return {
            "total_story_points": total_sp,
            "completed_story_points": completed_sp,
            "remaining_story_points": total_sp - completed_sp,
            "total_issues": total_issues,
            "completed_issues": completed_issues,
            "remaining_issues": total_issues - completed_issues,
        }

    @staticmethod
    def get_velocity(project: Project, limit: int = 6) -> dict:
        """Get velocity metrics for completed sprints."""
        completed_sprints = Sprint.objects.filter(
            project=project,
            status=SprintStatus.COMPLETED,
        ).order_by("-end_date")[:limit]

        sprint_data = []
        total_velocity = 0

        for sprint in completed_sprints:
            velocity = sprint.completed_story_points or 0
            total_velocity += velocity
            sprint_data.append(
                {
                    "id": str(sprint.id),
                    "name": sprint.name,
                    "start_date": sprint.start_date.isoformat(),
                    "end_date": sprint.end_date.isoformat(),
                    "committed_story_points": sprint.initial_story_points or 0,
                    "completed_story_points": velocity,
                }
            )

        # Reverse to show oldest first (for charts)
        sprint_data.reverse()

        count = len(sprint_data)
        average_velocity = round(total_velocity / count, 1) if count > 0 else 0

        return {
            "sprints": sprint_data,
            "average_velocity": average_velocity,
            "total_sprints": count,
        }

    @staticmethod
    def get_burndown(sprint: Sprint) -> dict:
        """Get burndown chart data for a sprint."""
        # Get all issues that were in this sprint
        current_issues = list(sprint.issues.all())

        # Calculate sprint duration
        start = sprint.start_date
        end = sprint.end_date
        today = timezone.now().date()

        # For active sprints, cap at today
        if sprint.status == SprintStatus.ACTIVE and today < end:
            chart_end = today
        else:
            chart_end = end

        total_days = (end - start).days + 1
        elapsed_days = (chart_end - start).days + 1

        # Build initial story points (from sprint start or current if planned)
        if sprint.initial_story_points is not None:
            initial_sp = sprint.initial_story_points
        else:
            initial_sp = SprintService._calculate_story_points(sprint)

        # Calculate ideal burndown line
        ideal_data = []
        for day_offset in range(total_days + 1):
            current_date = start + timedelta(days=day_offset)
            ideal_remaining = initial_sp * (1 - day_offset / total_days)
            ideal_data.append(
                {
                    "date": current_date.isoformat(),
                    "value": round(ideal_remaining, 1),
                }
            )

        # Calculate actual burndown from issue history
        actual_data = []

        # Get historical status changes from issue history
        # We track when issues moved to 'done' status
        done_by_date: dict[date, int] = {}

        for issue in current_issues:
            # Skip issues without story points
            if not issue.story_points:
                continue

            # Check historical records for status changes to done
            try:
                history = (
                    issue.history.filter(
                        status__category=StatusCategory.DONE,
                    )
                    .order_by("history_date")
                    .first()
                )

                if history:
                    done_date = history.history_date.date()
                    if start <= done_date <= chart_end:
                        done_by_date[done_date] = (
                            done_by_date.get(done_date, 0) + issue.story_points
                        )
            except Exception:
                # If history not available, check current state
                if issue.status.category == StatusCategory.DONE:
                    # Assume it was completed on updated_at date
                    done_date = issue.updated_at.date()
                    if start <= done_date <= chart_end:
                        done_by_date[done_date] = (
                            done_by_date.get(done_date, 0) + issue.story_points
                        )

        # Build actual data
        remaining = initial_sp
        for day_offset in range(elapsed_days):
            current_date = start + timedelta(days=day_offset)
            completed_today = done_by_date.get(current_date, 0)
            remaining -= completed_today
            actual_data.append(
                {
                    "date": current_date.isoformat(),
                    "value": max(0, remaining),
                }
            )

        return {
            "sprint_id": str(sprint.id),
            "sprint_name": sprint.name,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "initial_story_points": initial_sp,
            "ideal": ideal_data,
            "actual": actual_data,
        }
