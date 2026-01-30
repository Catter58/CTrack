"""
Custom email backend that reads SMTP settings from database.

Falls back to Django settings if database settings are not configured.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


def get_smtp_settings() -> dict | None:
    """
    Get SMTP settings from database.

    Returns None if not configured, allowing fallback to Django settings.
    """
    from apps.core.models import SystemSettings

    try:
        system_settings = SystemSettings.get_settings()
        smtp = system_settings.smtp_settings

        if not smtp or not smtp.get("enabled"):
            return None

        return smtp
    except Exception:
        return None


class DatabaseEmailBackend(BaseEmailBackend):
    """
    Email backend that reads SMTP settings from SystemSettings model.

    If database settings are not configured or disabled, falls back
    to Django's default SMTP settings.
    """

    def __init__(self, fail_silently: bool = False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self._connection = None
        self._smtp_settings = None

    def _get_backend(self) -> SMTPEmailBackend | None:
        """Get configured SMTP backend based on database or Django settings."""
        db_settings = get_smtp_settings()

        if db_settings:
            return SMTPEmailBackend(
                host=db_settings.get("host", "localhost"),
                port=db_settings.get("port", 587),
                username=db_settings.get("username", ""),
                password=db_settings.get("password", ""),
                use_tls=db_settings.get("use_tls", True),
                use_ssl=db_settings.get("use_ssl", False),
                timeout=db_settings.get("timeout", 30),
                fail_silently=self.fail_silently,
            )
        else:
            # Fallback to Django settings
            return SMTPEmailBackend(
                host=getattr(settings, "EMAIL_HOST", "localhost"),
                port=getattr(settings, "EMAIL_PORT", 587),
                username=getattr(settings, "EMAIL_HOST_USER", ""),
                password=getattr(settings, "EMAIL_HOST_PASSWORD", ""),
                use_tls=getattr(settings, "EMAIL_USE_TLS", True),
                use_ssl=getattr(settings, "EMAIL_USE_SSL", False),
                timeout=getattr(settings, "EMAIL_TIMEOUT", None),
                fail_silently=self.fail_silently,
            )

    def open(self) -> bool | None:
        """Open connection to SMTP server."""
        backend = self._get_backend()
        return backend.open() if backend else False

    def close(self) -> None:
        """Close connection to SMTP server."""
        pass

    def send_messages(self, email_messages) -> int:
        """
        Send one or more EmailMessage objects.

        Returns the number of messages sent.
        """
        backend = self._get_backend()
        if not backend:
            return 0

        return backend.send_messages(email_messages)


def get_from_email() -> str:
    """
    Get the 'from' email address from database settings or Django settings.

    Returns formatted 'Name <email>' if from_name is set.
    """
    db_settings = get_smtp_settings()

    if db_settings:
        from_email = db_settings.get("from_email", "")
        from_name = db_settings.get("from_name", "")

        if from_email:
            if from_name:
                return f"{from_name} <{from_email}>"
            return from_email

    return getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")


def test_smtp_connection(
    host: str,
    port: int,
    username: str = "",
    password: str = "",
    use_tls: bool = True,
    use_ssl: bool = False,
    from_email: str = "",
    test_recipient: str = "",
    timeout: int = 10,
) -> dict:
    """
    Test SMTP connection with provided settings.

    Args:
        host: SMTP server hostname
        port: SMTP server port
        username: SMTP username (optional)
        password: SMTP password (optional)
        use_tls: Use STARTTLS (default True)
        use_ssl: Use SSL/TLS (default False)
        from_email: From email address
        test_recipient: Email to send test message (optional)
        timeout: Connection timeout in seconds

    Returns:
        Dictionary with 'success' boolean and 'message' string
    """
    try:
        # Create SMTP connection
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)

        server.ehlo()

        # Use STARTTLS if configured
        if use_tls and not use_ssl:
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()

        # Authenticate if credentials provided
        if username and password:
            server.login(username, password)

        # Send test email if recipient provided
        if test_recipient and from_email:
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = test_recipient
            msg["Subject"] = "[CTrack] Тестовое сообщение SMTP"

            body = """
Это тестовое сообщение от CTrack.

Если вы получили это письмо, значит настройки SMTP работают корректно.
"""
            msg.attach(MIMEText(body, "plain", "utf-8"))

            server.sendmail(from_email, [test_recipient], msg.as_string())
            server.quit()
            return {
                "success": True,
                "message": f"Соединение успешно. Тестовое письмо отправлено на {test_recipient}",
            }

        server.quit()
        return {
            "success": True,
            "message": "Соединение с SMTP сервером успешно установлено",
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "Ошибка аутентификации. Проверьте имя пользователя и пароль",
        }
    except smtplib.SMTPConnectError:
        return {
            "success": False,
            "message": f"Не удалось подключиться к {host}:{port}",
        }
    except smtplib.SMTPServerDisconnected:
        return {
            "success": False,
            "message": "Сервер разорвал соединение",
        }
    except TimeoutError:
        return {
            "success": False,
            "message": f"Превышено время ожидания подключения к {host}:{port}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка: {str(e)}",
        }
