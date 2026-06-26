from __future__ import annotations

import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core.config import Settings


class EmailDeliveryError(RuntimeError):
    pass


def _require_smtp_setting(value: str | None, name: str) -> str:
    if value:
        return value
    raise EmailDeliveryError(f"{name} is required to send production magic links")


def build_magic_link(settings: Settings, token: str) -> str:
    base_url = settings.frontend_app_url.rstrip("/")
    return f"{base_url}/login?{urlencode({'token': token})}"


def send_magic_link_email(settings: Settings, recipient: str, token: str) -> None:
    host = _require_smtp_setting(settings.smtp_host, "SMTP_HOST")
    from_email = _require_smtp_setting(settings.smtp_from_email, "SMTP_FROM_EMAIL")
    link = build_magic_link(settings, token)

    message = EmailMessage()
    message["Subject"] = "Your VaaniEval sign-in link"
    message["From"] = from_email
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                "Use this link to sign in to VaaniEval:",
                "",
                link,
                "",
                "If the link does not open automatically, copy this token into the login page:",
                "",
                token,
                "",
                "This link expires soon. If you did not request it, you can ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username or settings.smtp_password:
                username = _require_smtp_setting(settings.smtp_username, "SMTP_USERNAME")
                password = _require_smtp_setting(settings.smtp_password, "SMTP_PASSWORD")
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Failed to send production magic link email") from exc
