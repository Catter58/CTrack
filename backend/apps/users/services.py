from django.conf import settings
from django.core.mail import EmailMessage

from apps.core.email_backend import get_from_email, get_smtp_settings
from apps.issues.models import Issue, IssueComment

from .models import NotificationPreference, User


class NotificationService:
    @staticmethod
    def get_or_create_preferences(user: User) -> NotificationPreference:
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        return prefs

    @staticmethod
    def update_preferences(user: User, **kwargs) -> NotificationPreference:
        prefs = NotificationService.get_or_create_preferences(user)
        for key, value in kwargs.items():
            if value is not None and hasattr(prefs, key):
                setattr(prefs, key, value)
        prefs.save()
        return prefs

    @staticmethod
    def should_notify(user: User, notification_type: str) -> bool:
        try:
            prefs = user.notification_preferences
        except NotificationPreference.DoesNotExist:
            return True

        type_map = {
            "assign": prefs.notify_on_assign,
            "mention": prefs.notify_on_mention,
            "comment": prefs.notify_on_comment,
            "status_change": prefs.notify_on_status_change,
        }
        return type_map.get(notification_type, True)

    @staticmethod
    def send_assignment_notification(issue: Issue, assignee: User) -> bool:
        if not NotificationService.should_notify(assignee, "assign"):
            return False

        subject = f"[{issue.project.key}] Вам назначена задача: {issue.title}"
        message = f"""
Здравствуйте, {assignee.get_full_name() or assignee.username}!

Вам назначена задача {issue.key}: {issue.title}

Проект: {issue.project.name}
Приоритет: {issue.get_priority_display()}

Посмотреть задачу: {settings.FRONTEND_URL}/issues/{issue.key}
"""
        return NotificationService._send_email(assignee.email, subject, message)

    @staticmethod
    def send_mention_notification(
        issue: Issue, mentioned_users: list[User], comment_author: User
    ) -> int:
        sent = 0
        for user in mentioned_users:
            if user == comment_author:
                continue
            if not NotificationService.should_notify(user, "mention"):
                continue

            subject = f"[{issue.project.key}] Вас упомянули в {issue.key}"
            message = f"""
Здравствуйте, {user.get_full_name() or user.username}!

{comment_author.get_full_name() or comment_author.username} упомянул вас в комментарии к задаче {issue.key}: {issue.title}

Посмотреть задачу: {settings.FRONTEND_URL}/issues/{issue.key}
"""
            if NotificationService._send_email(user.email, subject, message):
                sent += 1
        return sent

    @staticmethod
    def send_comment_notification(issue: Issue, comment: IssueComment) -> int:
        sent = 0
        recipients = set()

        if issue.reporter and issue.reporter != comment.author:
            recipients.add(issue.reporter)
        if issue.assignee and issue.assignee != comment.author:
            recipients.add(issue.assignee)

        for user in recipients:
            if not NotificationService.should_notify(user, "comment"):
                continue

            subject = f"[{issue.project.key}] Новый комментарий в {issue.key}"
            message = f"""
Здравствуйте, {user.get_full_name() or user.username}!

{comment.author.get_full_name() or comment.author.username} добавил комментарий к задаче {issue.key}: {issue.title}

Комментарий:
{comment.content[:500]}{"..." if len(comment.content) > 500 else ""}

Посмотреть задачу: {settings.FRONTEND_URL}/issues/{issue.key}
"""
            if NotificationService._send_email(user.email, subject, message):
                sent += 1
        return sent

    @staticmethod
    def send_status_change_notification(
        issue: Issue, old_status: str, new_status: str, changed_by: User
    ) -> int:
        sent = 0
        recipients = set()

        if issue.reporter and issue.reporter != changed_by:
            recipients.add(issue.reporter)
        if issue.assignee and issue.assignee != changed_by:
            recipients.add(issue.assignee)

        for user in recipients:
            if not NotificationService.should_notify(user, "status_change"):
                continue

            subject = f"[{issue.project.key}] Статус {issue.key} изменён"
            message = f"""
Здравствуйте, {user.get_full_name() or user.username}!

Статус задачи {issue.key}: {issue.title} был изменён.

Старый статус: {old_status}
Новый статус: {new_status}
Изменил: {changed_by.get_full_name() or changed_by.username}

Посмотреть задачу: {settings.FRONTEND_URL}/issues/{issue.key}
"""
            if NotificationService._send_email(user.email, subject, message):
                sent += 1
        return sent

    @staticmethod
    def _send_email(to_email: str, subject: str, message: str) -> bool:
        # Check if SMTP is configured and enabled
        smtp_settings = get_smtp_settings()
        if smtp_settings is None:
            # SMTP not configured - skip sending
            return False

        try:
            from_email = get_from_email()

            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=[to_email],
            )
            # Use the custom database email backend
            email.send(fail_silently=True)
            return True
        except Exception:
            return False
