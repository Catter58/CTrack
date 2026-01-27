from datetime import date, timedelta

import pytest
from django.test import Client

from apps.issues.models import Issue, IssueType, Status, StatusCategory
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.sprints.models import Sprint, SprintStatus
from apps.users.models import User


@pytest.fixture
def project(db, user: User):
    project = Project.objects.create(
        name="Test Project",
        key="TEST",
        owner=user,
    )
    ProjectMembership.objects.create(
        project=project,
        user=user,
        role=ProjectRole.ADMIN,
    )
    return project


@pytest.fixture
def issue_type(db, project: Project):
    return IssueType.objects.create(
        project=project,
        name="Task",
        icon="task",
        color="#0066cc",
    )


@pytest.fixture
def status_todo(db, project: Project):
    return Status.objects.create(
        project=project,
        name="To Do",
        category=StatusCategory.TODO,
        color="#808080",
    )


@pytest.fixture
def planned_sprint(db, project: Project):
    return Sprint.objects.create(
        project=project,
        name="Sprint 1",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=14),
        status=SprintStatus.PLANNED,
    )


@pytest.fixture
def active_sprint(db, project: Project):
    return Sprint.objects.create(
        project=project,
        name="Active Sprint",
        start_date=date.today() - timedelta(days=7),
        end_date=date.today() + timedelta(days=7),
        status=SprintStatus.ACTIVE,
    )


@pytest.fixture
def backlog_issue(
    db, project: Project, issue_type: IssueType, status_todo: Status, user: User
):
    return Issue.objects.create(
        project=project,
        issue_type=issue_type,
        title="Backlog Task",
        status=status_todo,
        reporter=user,
        sprint=None,
    )


@pytest.fixture
def sprint_issue(
    db,
    project: Project,
    issue_type: IssueType,
    status_todo: Status,
    user: User,
    active_sprint: Sprint,
):
    return Issue.objects.create(
        project=project,
        issue_type=issue_type,
        title="Sprint Task",
        status=status_todo,
        reporter=user,
        sprint=active_sprint,
    )


@pytest.mark.django_db
class TestBacklogList:
    def test_get_backlog(
        self,
        api_client: Client,
        project: Project,
        backlog_issue: Issue,
        auth_headers: dict,
    ):
        response = api_client.get(
            f"/api/projects/{project.key}/backlog",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Backlog Task"

    def test_backlog_excludes_sprint_issues(
        self,
        api_client: Client,
        project: Project,
        backlog_issue: Issue,
        sprint_issue: Issue,
        auth_headers: dict,
    ):
        response = api_client.get(
            f"/api/projects/{project.key}/backlog",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["key"] == backlog_issue.key

    def test_backlog_includes_completed_sprint_issues(
        self,
        api_client: Client,
        project: Project,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
        auth_headers: dict,
    ):
        completed_sprint = Sprint.objects.create(
            project=project,
            name="Completed Sprint",
            start_date=date.today() - timedelta(days=28),
            end_date=date.today() - timedelta(days=14),
            status=SprintStatus.COMPLETED,
        )
        issue_in_completed = Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Task in completed sprint",
            status=status_todo,
            reporter=user,
            sprint=completed_sprint,
        )

        response = api_client.get(
            f"/api/projects/{project.key}/backlog",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        keys = [i["key"] for i in data]
        assert issue_in_completed.key in keys

    def test_backlog_pagination(
        self,
        api_client: Client,
        project: Project,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
        auth_headers: dict,
    ):
        for i in range(5):
            Issue.objects.create(
                project=project,
                issue_type=issue_type,
                title=f"Task {i}",
                status=status_todo,
                reporter=user,
            )

        response = api_client.get(
            f"/api/projects/{project.key}/backlog?limit=2&offset=1",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


@pytest.mark.django_db
class TestUpdateIssueSprint:
    def test_add_issue_to_sprint(
        self,
        api_client: Client,
        backlog_issue: Issue,
        planned_sprint: Sprint,
        auth_headers: dict,
    ):
        response = api_client.patch(
            f"/api/issues/{backlog_issue.key}/sprint?sprint_id={planned_sprint.id}",
            **auth_headers,
        )
        assert response.status_code == 200
        backlog_issue.refresh_from_db()
        assert backlog_issue.sprint == planned_sprint

    def test_remove_issue_from_sprint(
        self,
        api_client: Client,
        sprint_issue: Issue,
        auth_headers: dict,
    ):
        response = api_client.patch(
            f"/api/issues/{sprint_issue.key}/sprint",
            **auth_headers,
        )
        assert response.status_code == 200
        sprint_issue.refresh_from_db()
        assert sprint_issue.sprint is None

    def test_cannot_add_to_completed_sprint(
        self,
        api_client: Client,
        project: Project,
        backlog_issue: Issue,
        auth_headers: dict,
    ):
        completed_sprint = Sprint.objects.create(
            project=project,
            name="Completed Sprint",
            start_date=date.today() - timedelta(days=28),
            end_date=date.today() - timedelta(days=14),
            status=SprintStatus.COMPLETED,
        )
        response = api_client.patch(
            f"/api/issues/{backlog_issue.key}/sprint?sprint_id={completed_sprint.id}",
            **auth_headers,
        )
        assert response.status_code == 400
