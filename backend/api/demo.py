"""
Demo project API endpoint.
"""

from datetime import date, timedelta
from random import choice

from django.db import transaction
from ninja import Router

from apps.issues.models import Issue, IssueType, Status
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.sprints.models import Sprint, SprintStatus
from apps.users.auth import AuthBearer
from apps.users.models import User
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())


class DemoProjectResponseSchema:
    """Response schema for demo project creation."""

    project_key: str
    message: str


@router.post(
    "/create-demo",
    response={201: dict, 400: ErrorSchema},
    summary="Создать демо-проект",
)
@transaction.atomic
def create_demo_project(request):
    """
    Create a demo project with sample data.

    Creates:
    - Project with key "DEMO"
    - 2 sprints (one active, one planned)
    - 2 epics with progress
    - 10+ issues (stories, tasks, bugs)
    - Subtasks for some issues
    """
    user = request.auth

    # Check if demo project already exists
    if Project.objects.filter(key="DEMO").exists():
        return 400, {"detail": "Демо-проект уже существует"}

    # Create demo project
    project = _create_demo_project(user)

    return 201, {
        "project_key": project.key,
        "message": "Демо-проект успешно создан",
    }


def _create_demo_project(user: User) -> Project:
    """Create demo project with all sample data."""
    from apps.boards.models import Board

    # Create project
    project = Project.objects.create(
        key="DEMO",
        name="Демо-проект CTrack",
        description="Пример проекта для демонстрации возможностей CTrack. "
        "Содержит эпики, задачи, подзадачи, спринты и примеры workflow.",
        owner=user,
        settings={},
    )

    # Add user as admin
    ProjectMembership.objects.create(
        project=project,
        user=user,
        role=ProjectRole.ADMIN,
    )

    # Create default board
    Board.create_default_board(project)

    # Create workflow transitions
    _create_demo_workflow(project)

    # Create sprints
    sprints = _create_demo_sprints(project)

    # Get issue types and statuses
    epic_type = IssueType.objects.filter(is_epic=True, project__isnull=True).first()
    story_type = IssueType.objects.filter(name="История", project__isnull=True).first()
    task_type = IssueType.objects.filter(name="Задача", project__isnull=True).first()
    bug_type = IssueType.objects.filter(name="Баг", project__isnull=True).first()
    subtask_type = IssueType.objects.filter(
        is_subtask=True, project__isnull=True
    ).first()

    statuses = {
        s.category: s
        for s in Status.objects.filter(project__isnull=True).order_by("order")
    }
    todo = statuses.get("todo")
    in_progress = list(
        Status.objects.filter(project__isnull=True, category="in_progress")
    )
    done = statuses.get("done")

    # Create epics
    epics = _create_demo_epics(project, user, epic_type, todo, done)

    # Create issues
    _create_demo_issues(
        project=project,
        user=user,
        epics=epics,
        sprints=sprints,
        story_type=story_type,
        task_type=task_type,
        bug_type=bug_type,
        subtask_type=subtask_type,
        todo=todo,
        in_progress=in_progress,
        done=done,
    )

    return project


def _create_demo_workflow(project: Project) -> None:
    """Create demo workflow transitions."""
    from apps.issues.models import WorkflowTransition

    statuses = list(Status.objects.filter(project__isnull=True).order_by("order"))
    if len(statuses) >= 4:
        todo, in_progress, review, done = statuses[:4]

        transitions = [
            (todo, in_progress, "Взять в работу"),
            (in_progress, review, "На проверку"),
            (in_progress, todo, "Вернуть"),
            (review, done, "Завершить"),
            (review, in_progress, "На доработку"),
        ]

        for from_status, to_status, name in transitions:
            WorkflowTransition.objects.create(
                project=project,
                from_status=from_status,
                to_status=to_status,
                name=name,
            )


def _create_demo_sprints(project: Project) -> dict:
    """Create demo sprints."""
    today = date.today()

    # Active sprint (current 2 weeks)
    active_sprint = Sprint.objects.create(
        project=project,
        name="Спринт 1 - MVP",
        goal="Реализовать базовый функционал приложения",
        start_date=today - timedelta(days=7),
        end_date=today + timedelta(days=7),
        status=SprintStatus.ACTIVE,
        initial_story_points=21,
        completed_story_points=8,
    )

    # Planned sprint (next 2 weeks)
    planned_sprint = Sprint.objects.create(
        project=project,
        name="Спринт 2 - Улучшения",
        goal="Добавить дополнительные функции и исправить баги",
        start_date=today + timedelta(days=8),
        end_date=today + timedelta(days=22),
        status=SprintStatus.PLANNED,
    )

    return {
        "active": active_sprint,
        "planned": planned_sprint,
    }


def _create_demo_epics(
    project: Project,
    user: User,
    epic_type: IssueType,
    todo: Status,
    done: Status,
) -> list:
    """Create demo epics."""
    if not epic_type:
        return []

    epics = []

    # Epic 1: User management
    epic1 = Issue.objects.create(
        project=project,
        issue_type=epic_type,
        title="Управление пользователями",
        description='{"blocks":[{"type":"paragraph","data":{"text":"Система авторизации и управления профилями пользователей"}}]}',
        status=todo,
        priority="high",
        reporter=user,
    )
    epics.append(epic1)

    # Epic 2: Task management
    epic2 = Issue.objects.create(
        project=project,
        issue_type=epic_type,
        title="Управление задачами",
        description='{"blocks":[{"type":"paragraph","data":{"text":"Создание, редактирование и отслеживание задач"}}]}',
        status=todo,
        priority="highest",
        reporter=user,
    )
    epics.append(epic2)

    return epics


def _create_demo_issues(
    project: Project,
    user: User,
    epics: list,
    sprints: dict,
    story_type: IssueType,
    task_type: IssueType,
    bug_type: IssueType,
    subtask_type: IssueType,
    todo: Status,
    in_progress: list,
    done: Status,
) -> None:
    """Create demo issues with various states."""
    active_sprint = sprints.get("active")
    planned_sprint = sprints.get("planned")

    # Helper to get random in_progress status
    def random_in_progress():
        return choice(in_progress) if in_progress else todo

    # Stories in active sprint
    if story_type and active_sprint:
        epic = epics[1] if len(epics) > 1 else None

        # Done story
        Issue.objects.create(
            project=project,
            issue_type=story_type,
            title="Создание задачи через форму",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Как пользователь, я хочу создавать задачи через удобную форму"}}]}',
            status=done,
            priority="high",
            reporter=user,
            assignee=user,
            sprint=active_sprint,
            epic=epic,
            story_points=5,
        )

        # In progress story
        Issue.objects.create(
            project=project,
            issue_type=story_type,
            title="Drag & drop на Kanban-доске",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Как пользователь, я хочу перетаскивать задачи между колонками"}}]}',
            status=random_in_progress(),
            priority="high",
            reporter=user,
            assignee=user,
            sprint=active_sprint,
            epic=epic,
            story_points=8,
        )

        # Todo story
        Issue.objects.create(
            project=project,
            issue_type=story_type,
            title="Фильтрация задач по исполнителю",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Как пользователь, я хочу фильтровать задачи по назначенному исполнителю"}}]}',
            status=todo,
            priority="medium",
            reporter=user,
            sprint=active_sprint,
            epic=epic,
            story_points=3,
        )

    # Tasks
    if task_type:
        epic = epics[0] if epics else None

        # Done task
        Issue.objects.create(
            project=project,
            issue_type=task_type,
            title="Настроить JWT авторизацию",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Реализовать JWT токены для API"}}]}',
            status=done,
            priority="highest",
            reporter=user,
            assignee=user,
            sprint=active_sprint,
            epic=epic,
            story_points=3,
        )

        # In progress task with subtasks
        task2 = Issue.objects.create(
            project=project,
            issue_type=task_type,
            title="Разработать API для проектов",
            description='{"blocks":[{"type":"paragraph","data":{"text":"REST API для CRUD операций с проектами"}}]}',
            status=random_in_progress(),
            priority="high",
            reporter=user,
            assignee=user,
            sprint=active_sprint,
            epic=epic,
            story_points=5,
        )

        # Create subtasks for task2
        if subtask_type:
            Issue.objects.create(
                project=project,
                issue_type=subtask_type,
                title="Создать модель Project",
                status=done,
                priority="medium",
                reporter=user,
                assignee=user,
                parent=task2,
            )
            Issue.objects.create(
                project=project,
                issue_type=subtask_type,
                title="Написать сериализаторы",
                status=done,
                priority="medium",
                reporter=user,
                assignee=user,
                parent=task2,
            )
            Issue.objects.create(
                project=project,
                issue_type=subtask_type,
                title="Добавить тесты API",
                status=todo,
                priority="low",
                reporter=user,
                parent=task2,
            )

        # Backlog task (no sprint)
        Issue.objects.create(
            project=project,
            issue_type=task_type,
            title="Добавить экспорт в CSV",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Возможность экспортировать список задач в CSV файл"}}]}',
            status=todo,
            priority="low",
            reporter=user,
            epic=epic,
            story_points=2,
        )

        # Task in planned sprint
        Issue.objects.create(
            project=project,
            issue_type=task_type,
            title="Реализовать уведомления",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Email и push уведомления о изменениях в задачах"}}]}',
            status=todo,
            priority="medium",
            reporter=user,
            sprint=planned_sprint,
            story_points=5,
        )

    # Bugs
    if bug_type:
        # Critical bug in progress
        Issue.objects.create(
            project=project,
            issue_type=bug_type,
            title="Ошибка при сохранении задачи с пустым описанием",
            description='{"blocks":[{"type":"paragraph","data":{"text":"При сохранении задачи без описания возникает ошибка 500"}},{"type":"paragraph","data":{"text":"Шаги воспроизведения:\\n1. Открыть форму создания задачи\\n2. Заполнить только название\\n3. Нажать Сохранить"}}]}',
            status=random_in_progress(),
            priority="highest",
            reporter=user,
            assignee=user,
            sprint=active_sprint,
            story_points=2,
        )

        # Medium bug in backlog
        Issue.objects.create(
            project=project,
            issue_type=bug_type,
            title="Неправильное отображение даты в Safari",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Дата отображается в неверном формате в браузере Safari"}}]}',
            status=todo,
            priority="medium",
            reporter=user,
            story_points=1,
        )

        # Fixed bug
        Issue.objects.create(
            project=project,
            issue_type=bug_type,
            title="Утечка памяти при длительной работе",
            description='{"blocks":[{"type":"paragraph","data":{"text":"Исправлена утечка памяти в компоненте списка задач"}}]}',
            status=done,
            priority="high",
            reporter=user,
            assignee=user,
            sprint=active_sprint,
            story_points=3,
        )
