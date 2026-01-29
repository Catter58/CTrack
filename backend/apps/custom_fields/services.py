from typing import Any
from uuid import UUID

from django.db import models
from django.db.models import QuerySet

from apps.users.models import User

from .models import CustomFieldDefinition, FieldType


class CustomFieldValidator:
    """Service for custom field validation."""

    @staticmethod
    def validate_field_value(
        definition: CustomFieldDefinition, value: Any
    ) -> tuple[bool, str | None]:
        """Validate a single field value against its definition."""
        if definition.is_required and value is None:
            return False, f"Field '{definition.name}' is required"

        if value is None:
            return True, None

        if definition.field_type == FieldType.TEXT:
            if not isinstance(value, str):
                return False, f"Field '{definition.name}' must be a string"

        elif definition.field_type == FieldType.TEXTAREA:
            if not isinstance(value, str):
                return False, f"Field '{definition.name}' must be a string"

        elif definition.field_type == FieldType.NUMBER:
            if not isinstance(value, int | float):
                return False, f"Field '{definition.name}' must be a number"

        elif definition.field_type == FieldType.DATE:
            pass

        elif definition.field_type == FieldType.DATETIME:
            pass

        elif definition.field_type == FieldType.CHECKBOX:
            if not isinstance(value, bool):
                return False, f"Field '{definition.name}' must be a boolean"

        elif definition.field_type == FieldType.SELECT:
            if value not in definition.options:
                return False, f"Invalid option for '{definition.name}'"

        elif definition.field_type == FieldType.MULTISELECT:
            if not isinstance(value, list):
                return False, f"Field '{definition.name}' must be a list"
            invalid = [v for v in value if v not in definition.options]
            if invalid:
                return False, f"Invalid options for '{definition.name}': {invalid}"

        elif definition.field_type == FieldType.USER:
            if not User.objects.filter(id=value).exists():
                return False, f"User not found for field '{definition.name}'"

        return True, None

    @staticmethod
    def validate_issue_custom_fields(
        issue_type_id: UUID | None,
        custom_fields: dict,
        project_id: UUID,
    ) -> tuple[bool, list[str]]:
        """Validate all custom fields for an issue."""
        definitions = CustomFieldDefinition.objects.filter(project_id=project_id)

        errors = []
        for definition in definitions:
            if definition.applicable_types and issue_type_id:
                if str(issue_type_id) not in [
                    str(t) for t in definition.applicable_types
                ]:
                    continue

            value = custom_fields.get(definition.field_key)
            is_valid, error = CustomFieldValidator.validate_field_value(
                definition, value
            )
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors

    @staticmethod
    def get_definitions_for_type(
        project_id: UUID, issue_type_id: UUID | None
    ) -> QuerySet[CustomFieldDefinition]:
        """Get custom field definitions applicable to an issue type."""
        definitions = CustomFieldDefinition.objects.filter(project_id=project_id)
        if issue_type_id:
            definitions = definitions.filter(
                models.Q(applicable_types=[])
                | models.Q(applicable_types__contains=[str(issue_type_id)])
            )
        return definitions.order_by("order")
