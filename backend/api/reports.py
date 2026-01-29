"""Project reports API endpoints."""

from datetime import date, datetime, timedelta
from statistics import median
from uuid import UUID

from django.db.models import Count, F
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from ninja import Router

from api.schemas.reports import (
    AssigneeStatsSchema,
    CreatedVsResolvedItemSchema,
    CreatedVsResolvedSchema,
    CycleTimeGroupSchema,
    CycleTimeSchema,
    PeriodType,
    PriorityStatsSchema,
    ReportSummarySchema,
    StatusStatsSchema,
    TypeStatsSchema,
)
from apps.issues.models import Issue, IssueActivity
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())


@router.get(
    "/projects/{key}/reports/summary",
    response={200: ReportSummarySchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_report_summary(request, key: str):
    """Get summary report: issues count by status, type, and assignee."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    issues = Issue.objects.filter(project=project)

    by_status = (
        issues.values(
            sid=F("status__id"),
            status_name=F("status__name"),
            category=F("status__category"),
            status_color=F("status__color"),
        )
        .annotate(count=Count("id"))
        .order_by("status__order")
    )

    by_type = (
        issues.values(
            tid=F("issue_type__id"),
            type_name=F("issue_type__name"),
        )
        .annotate(count=Count("id"))
        .order_by("issue_type__order")
    )

    by_assignee_raw = (
        issues.values("assignee__id", "assignee__first_name", "assignee__last_name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    by_assignee = []
    for item in by_assignee_raw:
        if item["assignee__id"]:
            name = (
                f"{item['assignee__first_name']} {item['assignee__last_name']}".strip()
            )
            if not name:
                name = f"User #{item['assignee__id']}"
        else:
            name = "Не назначено"

        by_assignee.append(
            AssigneeStatsSchema(
                assignee_id=item["assignee__id"],
                assignee_name=name,
                count=item["count"],
            )
        )

    # Priority order for sorting
    priority_order = {"highest": 0, "high": 1, "medium": 2, "low": 3, "lowest": 4}
    by_priority_raw = (
        issues.values("priority").annotate(count=Count("id")).order_by("priority")
    )
    by_priority = sorted(
        [
            PriorityStatsSchema(priority=p["priority"], count=p["count"])
            for p in by_priority_raw
            if p["priority"]
        ],
        key=lambda x: priority_order.get(x.priority, 99),
    )

    return 200, ReportSummarySchema(
        total_issues=issues.count(),
        by_status=[
            StatusStatsSchema(
                status_id=s["sid"],
                status_name=s["status_name"],
                category=s["category"],
                status_color=s["status_color"],
                count=s["count"],
            )
            for s in by_status
        ],
        by_type=[
            TypeStatsSchema(
                type_id=t["tid"],
                type_name=t["type_name"],
                count=t["count"],
            )
            for t in by_type
        ],
        by_assignee=by_assignee,
        by_priority=by_priority,
    )


@router.get(
    "/projects/{key}/reports/created-vs-resolved",
    response={
        200: CreatedVsResolvedSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def get_created_vs_resolved(
    request,
    key: str,
    period: PeriodType = PeriodType.WEEK,
    date_from: date = None,
    date_to: date = None,
):
    """Get created vs resolved issues report for given period."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    if date_to is None:
        date_to = date.today()
    if date_from is None:
        if period == PeriodType.DAY:
            date_from = date_to - timedelta(days=30)
        elif period == PeriodType.WEEK:
            date_from = date_to - timedelta(weeks=12)
        else:
            date_from = date_to - timedelta(days=365)

    if date_from > date_to:
        return 400, {"detail": "date_from должен быть раньше date_to"}

    trunc_func = {
        PeriodType.DAY: TruncDay,
        PeriodType.WEEK: TruncWeek,
        PeriodType.MONTH: TruncMonth,
    }[period]

    datetime_from = datetime.combine(date_from, datetime.min.time())
    datetime_to = datetime.combine(date_to, datetime.max.time())

    created_qs = (
        Issue.objects.filter(
            project=project,
            created_at__gte=datetime_from,
            created_at__lte=datetime_to,
        )
        .annotate(period_date=trunc_func("created_at"))
        .values("period_date")
        .annotate(count=Count("id"))
    )

    # Query activities where status was changed to a "done" category
    # The new_value JSONField should contain {"name": "...", "category": "done"}
    resolved_qs = (
        IssueActivity.objects.filter(
            issue__project=project,
            action="status_changed",
            created_at__gte=datetime_from,
            created_at__lte=datetime_to,
            new_value__category="done",
        )
        .annotate(period_date=trunc_func("created_at"))
        .values("period_date")
        .annotate(count=Count("id"))
    )

    created_map = {item["period_date"].date(): item["count"] for item in created_qs}
    resolved_map = {item["period_date"].date(): item["count"] for item in resolved_qs}

    all_dates = set(created_map.keys()) | set(resolved_map.keys())
    all_dates = sorted(all_dates)

    data = [
        CreatedVsResolvedItemSchema(
            date=d,
            created=created_map.get(d, 0),
            resolved=resolved_map.get(d, 0),
        )
        for d in all_dates
    ]

    return 200, CreatedVsResolvedSchema(
        period=period.value,
        date_from=date_from,
        date_to=date_to,
        data=data,
    )


@router.get(
    "/projects/{key}/reports/cycle-time",
    response={200: CycleTimeSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_cycle_time(request, key: str):
    """Get cycle time report: average time from created to done status."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    # Query activities where status was changed to a "done" category
    done_activities = IssueActivity.objects.filter(
        issue__project=project,
        action="status_changed",
        new_value__category="done",
    ).select_related("issue", "issue__issue_type")

    cycle_times = []
    type_times: dict[UUID, list[float]] = {}
    priority_times: dict[str, list[float]] = {}

    for activity in done_activities:
        issue = activity.issue
        created = issue.created_at
        resolved = activity.created_at

        hours = (resolved - created).total_seconds() / 3600

        cycle_times.append(hours)

        type_id = issue.issue_type_id
        if type_id not in type_times:
            type_times[type_id] = []
        type_times[type_id].append(hours)

        priority = issue.priority
        if priority not in priority_times:
            priority_times[priority] = []
        priority_times[priority].append(hours)

    overall_avg = sum(cycle_times) / len(cycle_times) if cycle_times else None
    overall_median = median(cycle_times) if cycle_times else None

    from apps.issues.models import IssueType, Priority

    type_objs = {t.id: t for t in IssueType.objects.filter(id__in=type_times.keys())}
    by_type = []
    for type_id, times in type_times.items():
        type_obj = type_objs.get(type_id)
        by_type.append(
            CycleTimeGroupSchema(
                group_name=type_obj.name if type_obj else "Unknown",
                group_id=type_id,
                avg_hours=sum(times) / len(times) if times else None,
                median_hours=median(times) if times else None,
                count=len(times),
            )
        )

    priority_names = {p.value: p.label for p in Priority}
    priority_order = [p.value for p in Priority]

    by_priority = []
    for priority in priority_order:
        times = priority_times.get(priority, [])
        if times:
            by_priority.append(
                CycleTimeGroupSchema(
                    group_name=priority_names.get(priority, priority),
                    group_id=None,
                    avg_hours=sum(times) / len(times),
                    median_hours=median(times),
                    count=len(times),
                )
            )

    return 200, CycleTimeSchema(
        overall_avg_hours=overall_avg,
        overall_median_hours=overall_median,
        total_completed=len(cycle_times),
        by_type=by_type,
        by_priority=by_priority,
    )
