from uuid import UUID

from ninja import Router

from apps.custom_fields.models import CustomFieldDefinition
from apps.custom_fields.schemas import (
    CustomFieldDefinitionCreateSchema,
    CustomFieldDefinitionSchema,
    CustomFieldDefinitionUpdateSchema,
)
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())


def generate_field_key(project_id: UUID | None) -> str:
    prefix = "cf"
    count = CustomFieldDefinition.objects.filter(project_id=project_id).count()
    return f"{prefix}_{count + 1}"


@router.get(
    "/projects/{project_key}/custom-fields",
    response={
        200: list[CustomFieldDefinitionSchema],
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def list_custom_fields(request, project_key: str):
    project = ProjectService.get_project_by_key(project_key)
    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    fields = CustomFieldDefinition.objects.filter(project=project).order_by(
        "order", "name"
    )
    return 200, list(fields)


@router.post(
    "/projects/{project_key}/custom-fields",
    response={
        201: CustomFieldDefinitionSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def create_custom_field(
    request, project_key: str, data: CustomFieldDefinitionCreateSchema
):
    project = ProjectService.get_project_by_key(project_key)
    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_admin(project, request.auth):
        return 403, {"detail": "Только администратор может создавать поля"}

    if data.field_type in ("select", "multiselect") and not data.options:
        return 400, {"detail": "Необходимо указать варианты для поля выбора"}

    field_key = generate_field_key(project.id)

    field = CustomFieldDefinition.objects.create(
        project=project,
        name=data.name,
        field_key=field_key,
        field_type=data.field_type,
        options=data.options,
        is_required=data.is_required,
        default_value=data.default_value,
        description=data.description,
        applicable_types=[str(t) for t in data.applicable_types],
    )
    return 201, field


@router.get(
    "/custom-fields/{field_id}",
    response={200: CustomFieldDefinitionSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_custom_field(request, field_id: UUID):
    field = (
        CustomFieldDefinition.objects.filter(id=field_id)
        .select_related("project")
        .first()
    )
    if not field:
        return 404, {"detail": "Поле не найдено"}

    if field.project and not ProjectService.is_member(field.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    return 200, field


@router.patch(
    "/custom-fields/{field_id}",
    response={
        200: CustomFieldDefinitionSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def update_custom_field(
    request, field_id: UUID, data: CustomFieldDefinitionUpdateSchema
):
    field = (
        CustomFieldDefinition.objects.filter(id=field_id)
        .select_related("project")
        .first()
    )
    if not field:
        return 404, {"detail": "Поле не найдено"}

    if field.project and not ProjectService.is_admin(field.project, request.auth):
        return 403, {"detail": "Только администратор может редактировать поля"}

    update_data = data.dict(exclude_unset=True)
    if (
        "applicable_types" in update_data
        and update_data["applicable_types"] is not None
    ):
        update_data["applicable_types"] = [
            str(t) for t in update_data["applicable_types"]
        ]

    for key, value in update_data.items():
        if value is not None:
            setattr(field, key, value)

    field.save()
    return 200, field


@router.delete(
    "/custom-fields/{field_id}",
    response={204: None, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_custom_field(request, field_id: UUID):
    field = (
        CustomFieldDefinition.objects.filter(id=field_id)
        .select_related("project")
        .first()
    )
    if not field:
        return 404, {"detail": "Поле не найдено"}

    if field.project and not ProjectService.is_admin(field.project, request.auth):
        return 403, {"detail": "Только администратор может удалять поля"}

    field.delete()
    return 204, None


@router.get(
    "/projects/{project_key}/custom-fields/for-type/{type_id}",
    response={
        200: list[CustomFieldDefinitionSchema],
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def get_custom_fields_for_type(request, project_key: str, type_id: UUID):
    project = ProjectService.get_project_by_key(project_key)
    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    from apps.custom_fields.services import CustomFieldValidator

    fields = CustomFieldValidator.get_definitions_for_type(project.id, type_id)
    return 200, list(fields)
