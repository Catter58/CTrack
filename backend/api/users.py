"""
Users API endpoints.
"""

import io
import uuid

from django.contrib.auth.hashers import check_password
from django.core.files.uploadedfile import InMemoryUploadedFile
from ninja import Router, Schema
from ninja.files import UploadedFile
from PIL import Image

from apps.users.auth import AuthBearer
from apps.users.models import User
from apps.users.schemas import ErrorSchema, MessageSchema, UserSchema
from apps.users.services import NotificationService

router = Router(auth=AuthBearer())

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_OUTPUT_SIZE = (256, 256)


class UserUpdateSchema(Schema):
    """Schema for updating user profile."""

    first_name: str | None = None
    last_name: str | None = None


class PasswordChangeSchema(Schema):
    """Schema for changing password."""

    current_password: str
    new_password: str


class UserListSchema(Schema):
    """Schema for user list item."""

    id: int
    username: str
    email: str
    first_name: str | None
    last_name: str | None
    full_name: str
    avatar: str | None
    is_active: bool

    @staticmethod
    def resolve_first_name(obj: User) -> str | None:
        return obj.first_name or None

    @staticmethod
    def resolve_last_name(obj: User) -> str | None:
        return obj.last_name or None

    @staticmethod
    def resolve_full_name(obj: User) -> str:
        full = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full if full else obj.username

    @staticmethod
    def resolve_avatar(obj: User) -> str | None:
        return obj.avatar.url if obj.avatar else None


@router.get("", response=list[UserListSchema])
def list_users(request, search: str = None, limit: int = 50, offset: int = 0):
    """Get list of users with optional search."""
    queryset = User.objects.filter(is_active=True)

    if search:
        from django.db.models import Q

        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    return list(queryset.distinct()[offset : offset + limit])


@router.get("/{user_id}", response={200: UserSchema, 404: ErrorSchema})
def get_user(request, user_id: int):
    """Get user by ID."""
    user = User.objects.filter(id=user_id, is_active=True).first()

    if not user:
        return 404, {"detail": "Пользователь не найден"}

    return 200, user


@router.patch(
    "/{user_id}", response={200: UserSchema, 403: ErrorSchema, 404: ErrorSchema}
)
def update_user(request, user_id: int, data: UserUpdateSchema):
    """Update user profile."""
    # Users can only update their own profile
    if request.auth.id != user_id and not request.auth.is_superuser:
        return 403, {"detail": "Можно редактировать только свой профиль"}

    user = User.objects.filter(id=user_id).first()

    if not user:
        return 404, {"detail": "Пользователь не найден"}

    # Update fields
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name

    user.save()

    return 200, user


class AvatarUploadResponse(Schema):
    """Response schema for avatar upload."""

    avatar_url: str


@router.post(
    "/{user_id}/avatar",
    response={
        200: AvatarUploadResponse,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def upload_avatar(request, user_id: int, file: UploadedFile):
    """
    Upload and process user avatar.

    Accepts an image file (JPEG, PNG, GIF, WebP) up to 5MB.
    The image is resized to 256x256 and converted to JPEG.
    Supports cropping coordinates from the frontend.
    """
    # Users can only update their own avatar
    if request.auth.id != user_id and not request.auth.is_superuser:
        return 403, {"detail": "Можно изменить только свой аватар"}

    user = User.objects.filter(id=user_id).first()
    if not user:
        return 404, {"detail": "Пользователь не найден"}

    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return 400, {"detail": "Допустимые форматы: JPEG, PNG, GIF, WebP"}

    # Validate file size
    if file.size > MAX_AVATAR_SIZE:
        return 400, {"detail": "Максимальный размер файла: 5 МБ"}

    try:
        # Open image with Pillow
        image = Image.open(file.file)

        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Crop to square (center crop)
        width, height = image.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        image = image.crop((left, top, right, bottom))

        # Resize to target size
        image = image.resize(AVATAR_OUTPUT_SIZE, Image.Resampling.LANCZOS)

        # Save to buffer
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)

        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.jpg"

        # Delete old avatar if exists
        if user.avatar:
            user.avatar.delete(save=False)

        # Save new avatar
        user.avatar.save(
            filename,
            InMemoryUploadedFile(
                buffer,
                field_name="avatar",
                name=filename,
                content_type="image/jpeg",
                size=buffer.getbuffer().nbytes,
                charset=None,
            ),
            save=True,
        )

        return 200, {"avatar_url": user.avatar.url}

    except Exception as e:
        return 400, {"detail": f"Ошибка обработки изображения: {str(e)}"}


@router.delete(
    "/{user_id}/avatar",
    response={200: MessageSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_avatar(request, user_id: int):
    """Delete user avatar."""
    # Users can only delete their own avatar
    if request.auth.id != user_id and not request.auth.is_superuser:
        return 403, {"detail": "Можно удалить только свой аватар"}

    user = User.objects.filter(id=user_id).first()
    if not user:
        return 404, {"detail": "Пользователь не найден"}

    if user.avatar:
        user.avatar.delete(save=True)

    return 200, {"message": "Аватар удалён"}


@router.patch(
    "/{user_id}/password",
    response={200: MessageSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def change_password(request, user_id: int, data: PasswordChangeSchema):
    """Change user password."""
    # Users can only change their own password
    if request.auth.id != user_id:
        return 403, {"detail": "Можно изменить только свой пароль"}

    user = User.objects.filter(id=user_id).first()

    if not user:
        return 404, {"detail": "Пользователь не найден"}

    # Verify current password
    if not check_password(data.current_password, user.password):
        return 400, {"detail": "Неверный текущий пароль"}

    # Validate new password
    if len(data.new_password) < 8:
        return 400, {"detail": "Пароль должен содержать минимум 8 символов"}

    # Set new password
    user.set_password(data.new_password)
    user.save()

    return 200, {"message": "Пароль успешно изменён"}


class NotificationPreferencesSchema(Schema):
    notify_on_assign: bool
    notify_on_mention: bool
    notify_on_comment: bool
    notify_on_status_change: bool
    email_frequency: str


class NotificationPreferencesUpdateSchema(Schema):
    notify_on_assign: bool | None = None
    notify_on_mention: bool | None = None
    notify_on_comment: bool | None = None
    notify_on_status_change: bool | None = None
    email_frequency: str | None = None


@router.get("/me/notification-preferences", response=NotificationPreferencesSchema)
def get_notification_preferences(request):
    prefs = NotificationService.get_or_create_preferences(request.auth)
    return prefs


@router.patch("/me/notification-preferences", response=NotificationPreferencesSchema)
def update_notification_preferences(request, data: NotificationPreferencesUpdateSchema):
    prefs = NotificationService.update_preferences(
        request.auth,
        notify_on_assign=data.notify_on_assign,
        notify_on_mention=data.notify_on_mention,
        notify_on_comment=data.notify_on_comment,
        notify_on_status_change=data.notify_on_status_change,
        email_frequency=data.email_frequency,
    )
    return prefs
