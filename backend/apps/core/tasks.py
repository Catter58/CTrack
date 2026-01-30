"""
Core Celery tasks for CTrack.

Provides async task implementations for:
- Email sending
- Webhook dispatch
- Report generation
- Bulk operations
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(
    self, to: str, subject: str, body: str, html_body: str | None = None
):
    """
    Send email asynchronously.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
    """
    from django.core.mail import send_mail

    logger.info("Sending email to %s: %s", to, subject)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,
            recipient_list=[to],
            html_message=html_body,
        )
        logger.info("Email sent successfully to %s", to)
    except Exception as exc:
        logger.exception("Failed to send email to %s", to)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, user_id: int):
    """
    Send welcome email to newly created user.

    Args:
        user_id: ID of the user to send welcome email to
    """
    from django.conf import settings
    from django.core.mail import send_mail

    from apps.users.models import User

    logger.info("Sending welcome email to user %d", user_id)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("User %d not found for welcome email", user_id)
        return

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    subject = "[CTrack] Добро пожаловать!"
    message = f"""
Здравствуйте, {user.get_full_name() or user.username}!

Для вас был создан аккаунт в системе CTrack.

Ваши данные для входа:
- Email: {user.email}
- Имя пользователя: {user.username}

Для входа в систему перейдите по ссылке:
{frontend_url}/auth/login

Если вы не запрашивали создание аккаунта, пожалуйста, свяжитесь с администратором.

С уважением,
Команда CTrack
"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[user.email],
        )
        logger.info("Welcome email sent successfully to user %d", user_id)
    except Exception as exc:
        logger.exception("Failed to send welcome email to user %d", user_id)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def dispatch_webhook_task(self, url: str, payload: dict, headers: dict | None = None):
    """
    Dispatch webhook to external URL.

    Args:
        url: Webhook endpoint URL
        payload: JSON payload to send
        headers: Optional HTTP headers
    """
    import httpx

    logger.info("Dispatching webhook to %s", url)

    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=request_headers)
            response.raise_for_status()

        logger.info(
            "Webhook dispatched successfully to %s (status: %d)",
            url,
            response.status_code,
        )
        return {"status": response.status_code, "url": url}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Webhook failed with status %d: %s", exc.response.status_code, url
        )
        raise self.retry(exc=exc) from exc
    except Exception as exc:
        logger.exception("Webhook dispatch error: %s", url)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True)
def generate_report_task(
    self, report_type: str, project_id: int, user_id: int, params: dict | None = None
):
    """
    Generate report asynchronously.

    Args:
        report_type: Type of report (velocity, burndown, etc.)
        project_id: Project ID for the report
        user_id: User ID requesting the report
        params: Optional report parameters
    """
    logger.info(
        "Generating %s report for project %d (user: %d)",
        report_type,
        project_id,
        user_id,
    )

    # Placeholder for report generation logic
    # In production, this would:
    # 1. Query project data
    # 2. Generate report (PDF, Excel, etc.)
    # 3. Store in media/reports/
    # 4. Notify user via WebSocket or email

    report_data = {
        "report_type": report_type,
        "project_id": project_id,
        "user_id": user_id,
        "params": params or {},
        "status": "completed",
    }

    logger.info("Report generation completed: %s", report_type)
    return report_data


@shared_task(bind=True)
def bulk_update_issues_task(self, issue_ids: list[int], updates: dict, user_id: int):
    """
    Perform bulk update on issues.

    Args:
        issue_ids: List of issue IDs to update
        updates: Dictionary of field updates
        user_id: User performing the update
    """
    from apps.issues.models import Issue

    logger.info("Bulk updating %d issues (user: %d)", len(issue_ids), user_id)

    updated_count = 0
    errors = []

    for issue_id in issue_ids:
        try:
            issue = Issue.objects.get(id=issue_id)

            for field, value in updates.items():
                if hasattr(issue, field):
                    setattr(issue, field, value)

            issue.save()
            updated_count += 1
        except Issue.DoesNotExist:
            errors.append({"issue_id": issue_id, "error": "Issue not found"})
        except Exception as exc:
            errors.append({"issue_id": issue_id, "error": str(exc)})

    result = {
        "total": len(issue_ids),
        "updated": updated_count,
        "errors": errors,
    }

    logger.info(
        "Bulk update completed: %d/%d issues updated", updated_count, len(issue_ids)
    )
    return result


@shared_task(bind=True)
def bulk_move_issues_task(
    self, issue_ids: list[int], target_status_id: int, user_id: int
):
    """
    Move multiple issues to a new status.

    Args:
        issue_ids: List of issue IDs to move
        target_status_id: Target status ID
        user_id: User performing the operation
    """
    from apps.issues.models import Issue, IssueStatus

    logger.info(
        "Bulk moving %d issues to status %d (user: %d)",
        len(issue_ids),
        target_status_id,
        user_id,
    )

    try:
        target_status = IssueStatus.objects.get(id=target_status_id)
    except IssueStatus.DoesNotExist:
        logger.error("Target status %d not found", target_status_id)
        return {"error": "Target status not found", "moved": 0}

    moved_count = 0
    errors = []

    for issue_id in issue_ids:
        try:
            issue = Issue.objects.get(id=issue_id)
            issue.status = target_status
            issue.save()
            moved_count += 1
        except Issue.DoesNotExist:
            errors.append({"issue_id": issue_id, "error": "Issue not found"})
        except Exception as exc:
            errors.append({"issue_id": issue_id, "error": str(exc)})

    result = {
        "total": len(issue_ids),
        "moved": moved_count,
        "target_status": target_status.name,
        "errors": errors,
    }

    logger.info("Bulk move completed: %d/%d issues moved", moved_count, len(issue_ids))
    return result
