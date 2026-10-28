"""
Servicio de Notificaciones Inmediatas vía Telegram Bot API y Email SMTP.
Alerta en tiempo real al propietario del negocio cuando ingresa una reseña crítica (1 o 2 estrellas).
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationService:
    """Gestiona el envío de alertas prioritarias a través de múltiples canales."""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

    async def send_telegram_alert(
        self,
        business_name: str,
        author_name: str,
        rating: int,
        text: str,
        urgency: str,
        suggested_response: str,
        source: str = "Google Maps"
    ) -> bool:
        """
        Envía un mensaje formateado a un chat o grupo de Telegram mediante la Bot API oficial.
        """
        if not settings.is_telegram_configured:
            logger.warning("Telegram no está configurado (TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID vacío).")
            return False

        star_emojis = "⭐" * rating + "☆" * (5 - rating)
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # Mensaje en formato Markdown / HTML
        message_html = (
            f"🚨 <b>ALERTA DE REPUTACIÓN: RESEÑA CRÍTICA</b> 🚨\n\n"
            f"🏪 <b>Negocio:</b> {business_name}\n"
            f"👤 <b>Cliente:</b> {author_name}\n"
            f"⭐ <b>Calificación:</b> {star_emojis} ({rating}/5)\n"
            f"⚡ <b>Urgencia:</b> {urgency.upper()}\n"
            f"🌐 <b>Origen:</b> {source}\n\n"
            f"💬 <b>Texto de la reseña:</b>\n"
            f"<i>\"{text}\"</i>\n\n"
            f"🤖 <b>Respuesta Diplomática Sugerida (IA):</b>\n"
            f"<blockquote>{suggested_response}</blockquote>\n\n"
            f"📲 <i>Accede a tu panel SaaS para aprobar, ajustar o publicar la respuesta.</i>"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if resp.status_code == 200 and data.get("ok"):
                    logger.info(f"Alerta Telegram enviada con éxito para la reseña de {author_name}.")
                    return True
                else:
                    logger.error(f"Fallo al enviar a Telegram: {data.get('description')}")
                    return False
        except Exception as e:
            logger.error(f"Error de conexión con la API de Telegram: {e}", exc_info=True)
            return False

    def send_email_alert(
        self,
        business_name: str,
        author_name: str,
        rating: int,
        text: str,
        urgency: str,
        suggested_response: str
    ) -> bool:
        """
        Envía un correo electrónico HTML de alerta crítica mediante SMTP.
        """
        if not settings.is_email_configured:
            logger.info("Notificaciones por email deshabilitadas o incompletas.")
            return False

        star_emojis = "★" * rating + "☆" * (5 - rating)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 [ALERTA] Nueva reseña de {rating} estrellas en {business_name}"
        msg["From"] = settings.SMTP_USER
        msg["To"] = settings.EMAIL_RECIPIENT

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 15px; margin-bottom: 20px;">
                <h2 style="color: #b91c1c; margin-top: 0;">Alerta de Reputación: Reseña Negativa</h2>
                <p>Se ha detectado una reseña de <strong>{rating} estrellas</strong> para <strong>{business_name}</strong> que requiere atención inmediata.</p>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold; width: 140px;">Cliente:</td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{author_name}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Calificación:</td><td style="padding: 8px; border-bottom: 1px solid #ddd; color: #e11d48; font-size: 16px;">{star_emojis} ({rating}/5)</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Urgencia:</td><td style="padding: 8px; border-bottom: 1px solid #ddd; color: #dc2626; font-weight: bold;">{urgency.upper()}</td></tr>
            </table>

            <h3 style="color: #1f2937;">Reseña Recibida:</h3>
            <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; font-style: italic; margin-bottom: 20px;">
                "{text}"
            </div>

            <h3 style="color: #1f2937;">Propuesta de Respuesta IA (Lista para publicar):</h3>
            <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; padding: 15px; border-radius: 6px; white-space: pre-wrap; margin-bottom: 20px;">
{suggested_response}
            </div>

            <p style="font-size: 12px; color: #6b7280;">Este es un mensaje automático generado por el Monitor Micro-SaaS de Reputación Local.</p>
        </body>
        </html>
        """

        part_html = MIMEText(html_body, "html")
        msg.attach(part_html)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10.0) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, [settings.EMAIL_RECIPIENT], msg.as_string())
            logger.info(f"Alerta de email enviada exitosamente a {settings.EMAIL_RECIPIENT}.")
            return True
        except Exception as e:
            logger.error(f"Error al enviar email SMTP de alerta: {e}", exc_info=True)
            return False

    async def dispatch_negative_alert(
        self,
        business_name: str,
        author_name: str,
        rating: int,
        text: str,
        urgency: str,
        suggested_response: str,
        source: str = "Google Maps"
    ) -> bool:
        """
        Orquesta el envío de alertas según los canales habilitados y el umbral de estrellas configurado.
        """
        if rating > settings.ALERT_ON_STARS_LEQ:
            return False

        telegram_sent = await self.send_telegram_alert(
            business_name=business_name,
            author_name=author_name,
            rating=rating,
            text=text,
            urgency=urgency,
            suggested_response=suggested_response,
            source=source
        )

        email_sent = self.send_email_alert(
            business_name=business_name,
            author_name=author_name,
            rating=rating,
            text=text,
            urgency=urgency,
            suggested_response=suggested_response
        )

        return telegram_sent or email_sent

    async def test_telegram_connection(self) -> Dict[str, Any]:
        """Prueba de diagnóstico para validar la integración de Telegram."""
        if not settings.is_telegram_configured:
            return {
                "success": False,
                "message": "Token de bot o Chat ID no configurados en el archivo .env"
            }

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        test_msg = (
            "✅ <b>¡Conexión Exitosa con el Bot de Telegram!</b>\n\n"
            "El sistema de monitoreo de reputación está listo para alertarte en tiempo real "
            "cuando un cliente deje una reseña de 1 o 2 estrellas."
        )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, json={
                    "chat_id": self.chat_id,
                    "text": test_msg,
                    "parse_mode": "HTML"
                })
                data = resp.json()
                if resp.status_code == 200 and data.get("ok"):
                    return {"success": True, "message": "Mensaje de prueba enviado con éxito a Telegram."}
                return {"success": False, "message": f"Telegram API Error: {data.get('description')}"}
        except Exception as e:
            return {"success": False, "message": f"Error de red al conectar con Telegram: {str(e)}"}


notification_service = NotificationService()

