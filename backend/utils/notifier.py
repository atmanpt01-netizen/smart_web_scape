"""알림 서비스 — Slack, Email 알림 발송."""
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class NotificationService:
    """Slack Webhook 및 SMTP 이메일 알림."""

    async def send_alert(self, alert_data: dict[str, Any]) -> None:
        """알림 데이터를 기반으로 Slack 및/또는 Email 알림을 발송합니다."""
        from backend.config import get_settings
        settings = get_settings()

        tasks = []
        if settings.slack_webhook_url:
            tasks.append(self._send_slack(settings.slack_webhook_url, alert_data))
        if settings.smtp_host and settings.smtp_username:
            tasks.append(self._send_email(settings, alert_data))

        import asyncio
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_slack(self, webhook_url: str, alert_data: dict[str, Any]) -> None:
        """Slack Webhook으로 알림을 발송합니다."""
        try:
            from slack_sdk.webhook.async_client import AsyncWebhookClient

            client = AsyncWebhookClient(webhook_url)
            severity = alert_data.get("severity", "info")
            emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(severity, "ℹ️")

            await client.send(
                text=f"{emoji} *Smart Web Scraper 알림*",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"{emoji} *{alert_data.get('alert_type', '알림')}*\n"
                                f"{alert_data.get('message', '')}"
                            ),
                        },
                    }
                ],
            )
            logger.info("slack_notification_sent", severity=severity)
        except Exception as e:
            logger.error("slack_notification_failed", error=str(e))

    async def _send_email(self, settings: Any, alert_data: dict[str, Any]) -> None:
        """SMTP로 이메일 알림을 발송합니다."""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText

            msg = MIMEText(
                f"알림 유형: {alert_data.get('alert_type', '알림')}\n"
                f"내용: {alert_data.get('message', '')}\n"
                f"심각도: {alert_data.get('severity', 'info')}",
                "plain",
                "utf-8",
            )
            msg["Subject"] = f"[Smart Web Scraper] {alert_data.get('alert_type', '알림')}"
            msg["From"] = settings.smtp_from
            msg["To"] = settings.smtp_username

            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                start_tls=True,
            )
            logger.info("email_notification_sent")
        except Exception as e:
            logger.error("email_notification_failed", error=str(e))

    async def create_and_send_alert(
        self,
        session: Any,
        alert_type: str,
        message: str,
        severity: str = "warning",
        url_id: Any = None,
    ) -> None:
        """DB에 알림을 저장하고 외부 채널로 발송합니다."""
        from backend.db.models import Alert

        alert = Alert(
            url_id=url_id,
            severity=severity,
            alert_type=alert_type,
            message=message,
        )
        session.add(alert)
        await session.commit()

        await self.send_alert({
            "severity": severity,
            "alert_type": alert_type,
            "message": message,
            "url_id": str(url_id) if url_id else None,
        })
