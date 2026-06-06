"""Standalone SMTP notifier for background workflow completion updates."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from loguru import logger

from easygs.config.schema import EmailOnlyNotifyConfig


class SmtpNotifier:
    """Send notification emails without depending on the email channel runtime."""

    def __init__(
        self,
        *,
        enabled: bool,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_use_tls: bool,
        smtp_use_ssl: bool,
        from_address: str,
        default_recipient: str = "",
    ):
        self.enabled = bool(enabled)
        self.smtp_host = smtp_host.strip()
        self.smtp_port = int(smtp_port)
        self.smtp_username = smtp_username.strip()
        self.smtp_password = smtp_password
        self.smtp_use_tls = bool(smtp_use_tls)
        self.smtp_use_ssl = bool(smtp_use_ssl)
        self.from_address = from_address.strip()
        self.default_recipient = default_recipient.strip().lower()

    @classmethod
    def from_notify_config(cls, config: EmailOnlyNotifyConfig) -> "SmtpNotifier":
        """Build a notifier from the standalone SMTP notification configuration."""
        return cls(
            enabled=config.enabled,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_username=config.smtp_username,
            smtp_password=config.smtp_password,
            smtp_use_tls=config.smtp_use_tls,
            smtp_use_ssl=config.smtp_use_ssl,
            from_address=config.from_address,
            default_recipient=config.to_address,
        )

    @property
    def is_configured(self) -> bool:
        """Whether the notifier has enough SMTP settings to send mail."""
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)

    def resolve_recipient(self, to_addr: str | None = None) -> str:
        """Resolve an explicit recipient or fall back to the configured default."""
        return (to_addr or self.default_recipient or "").strip().lower()

    async def send_workflow_completion(
        self,
        *,
        label: str,
        status: str,
        summary: str,
        workflow_id: str,
        to_addr: str | None = None,
    ) -> None:
        """Send a background workflow completion email."""
        if not self.enabled:
            logger.debug("Skip SMTP completion email: notifier is disabled")
            return

        recipient = self.resolve_recipient(to_addr)
        if not recipient:
            logger.debug("Skip SMTP completion email: no recipient configured")
            return

        if not self.is_configured:
            logger.warning("Skip SMTP completion email: SMTP notifier is not fully configured")
            return

        status_text = "completed successfully" if status == "succeeded" else "failed"
        subject = f"EasyGS workflow {status_text}: {label or workflow_id}"
        body = "\n".join(
            [
                summary.strip() or f"Background workflow {workflow_id} {status_text}.",
                "",
                f"Workflow ID: {workflow_id}",
                f"Name: {label or 'n/a'}",
                f"Status: {status}",
            ]
        )

        message = EmailMessage()
        message["From"] = self.from_address or self.smtp_username
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        await asyncio.to_thread(self._smtp_send, message)

    def _smtp_send(self, msg: EmailMessage) -> None:
        timeout = 30
        if self.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=timeout) as smtp:
                smtp.login(self.smtp_username, self.smtp_password)
                smtp.send_message(msg)
            return

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=timeout) as smtp:
            if self.smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(self.smtp_username, self.smtp_password)
            smtp.send_message(msg)
