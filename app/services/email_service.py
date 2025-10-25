"""
Email Service - Servicio de envío de correos electrónicos

Soporta múltiples proveedores:
- SMTP (Gmail, Outlook, Custom)
- SendGrid API
- Fallback entre proveedores

Características:
- Multi-tenant con configuración por empresa
- Templates HTML
- Attachments
- Retry con backoff
- Logging y auditoría
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Configuración de email por empresa"""
    company_id: str
    from_email: str
    from_name: str

    # SMTP Config (optional)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True

    # SendGrid Config (optional)
    sendgrid_api_key: Optional[str] = None

    # Mailgun Config (optional)
    mailgun_api_key: Optional[str] = None
    mailgun_domain: Optional[str] = None

    # Settings
    max_retries: int = 3
    retry_delay: int = 2  # seconds


class EmailService:
    """
    Servicio de envío de emails multi-tenant.

    Ejemplo de uso:
        # Configurar servicio
        config = EmailConfig(
            company_id="benova",
            from_email="contact@benova.com",
            from_name="Benova Clínica Estética",
            smtp_host=os.getenv('SMTP_HOST'),
            smtp_port=587,
            smtp_username=os.getenv('SMTP_USERNAME'),
            smtp_password=os.getenv('SMTP_PASSWORD')
        )

        email_service = EmailService(config)

        # Enviar email
        result = email_service.send_email(
            to_email="patient@example.com",
            subject="Confirmación de Cita",
            body_html="<h1>Su cita ha sido confirmada</h1>",
            body_text="Su cita ha sido confirmada"
        )
    """

    def __init__(self, config: EmailConfig):
        """
        Inicializar servicio de email.

        Args:
            config: Configuración de email
        """
        self.config = config
        self.company_id = config.company_id

        # Determinar proveedor disponible
        self.provider = self._detect_provider()

        logger.info(
            f"✅ EmailService initialized for {self.company_id} "
            f"(provider: {self.provider}, from: {config.from_email})"
        )

    def _detect_provider(self) -> str:
        """Detectar proveedor de email disponible"""
        if self.config.sendgrid_api_key:
            return "sendgrid"
        elif self.config.mailgun_api_key:
            return "mailgun"
        elif self.config.smtp_host:
            return "smtp"
        else:
            return "none"

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar un email.

        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            body_html: Cuerpo en HTML (opcional)
            body_text: Cuerpo en texto plano (opcional)
            cc: Lista de emails en copia (opcional)
            bcc: Lista de emails en copia oculta (opcional)
            attachments: Lista de adjuntos (opcional)
            reply_to: Email para responder (opcional)

        Returns:
            Dict con resultado:
            {
                "success": bool,
                "message_id": str,  # Si disponible
                "provider": str,
                "error": str  # Si falló
            }
        """
        # Validar inputs
        if not to_email or not subject:
            return {
                "success": False,
                "error": "to_email and subject are required"
            }

        if not body_html and not body_text:
            return {
                "success": False,
                "error": "Either body_html or body_text is required"
            }

        logger.info(
            f"📧 [{self.company_id}] Sending email to {to_email}: {subject}"
        )

        # Intentar envío con reintentos
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                if attempt > 0:
                    logger.info(
                        f"   Retry attempt {attempt}/{self.config.max_retries - 1}"
                    )
                    time.sleep(self.config.retry_delay * attempt)

                # Enviar según proveedor
                if self.provider == "smtp":
                    result = self._send_via_smtp(
                        to_email, subject, body_html, body_text,
                        cc, bcc, attachments, reply_to
                    )
                elif self.provider == "sendgrid":
                    result = self._send_via_sendgrid(
                        to_email, subject, body_html, body_text,
                        cc, bcc, attachments, reply_to
                    )
                elif self.provider == "mailgun":
                    result = self._send_via_mailgun(
                        to_email, subject, body_html, body_text,
                        cc, bcc, attachments, reply_to
                    )
                else:
                    return {
                        "success": False,
                        "error": "No email provider configured"
                    }

                if result["success"]:
                    logger.info(
                        f"✅ [{self.company_id}] Email sent successfully to {to_email}"
                    )
                    return result

                last_error = result.get("error", "Unknown error")

            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"❌ [{self.company_id}] Email send attempt {attempt + 1} failed: {e}"
                )

        # Todos los intentos fallaron
        logger.error(
            f"💥 [{self.company_id}] Email send failed after {self.config.max_retries} attempts: {last_error}"
        )

        return {
            "success": False,
            "error": last_error,
            "provider": self.provider
        }

    def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        body_html: Optional[str],
        body_text: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
        attachments: Optional[List[Dict[str, Any]]],
        reply_to: Optional[str]
    ) -> Dict[str, Any]:
        """Enviar email vía SMTP"""
        if not self.config.smtp_host:
            return {"success": False, "error": "SMTP not configured"}

        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = to_email

        if cc:
            msg['Cc'] = ', '.join(cc)

        if reply_to:
            msg['Reply-To'] = reply_to

        # Agregar cuerpo
        if body_text:
            part_text = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(part_text)

        if body_html:
            part_html = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(part_html)

        # Agregar adjuntos
        if attachments:
            for attachment in attachments:
                filename = attachment.get('filename')
                content = attachment.get('content')
                mime_type = attachment.get('mime_type', 'application/octet-stream')

                if filename and content:
                    part = MIMEBase(*mime_type.split('/'))
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)

        # Conectar y enviar
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.smtp_use_tls:
                    server.starttls()

                if self.config.smtp_username and self.config.smtp_password:
                    server.login(
                        self.config.smtp_username,
                        self.config.smtp_password
                    )

                # Preparar destinatarios
                recipients = [to_email]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)

                server.sendmail(
                    self.config.from_email,
                    recipients,
                    msg.as_string()
                )

            return {
                "success": True,
                "provider": "smtp",
                "to": to_email
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"SMTP error: {str(e)}",
                "provider": "smtp"
            }

    def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        body_html: Optional[str],
        body_text: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
        attachments: Optional[List[Dict[str, Any]]],
        reply_to: Optional[str]
    ) -> Dict[str, Any]:
        """Enviar email vía SendGrid API"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            # Crear mensaje
            message = Mail(
                from_email=Email(self.config.from_email, self.config.from_name),
                to_emails=To(to_email),
                subject=subject
            )

            if body_text:
                message.content = Content("text/plain", body_text)

            if body_html:
                message.content = Content("text/html", body_html)

            if reply_to:
                message.reply_to = Email(reply_to)

            # Enviar
            sg = SendGridAPIClient(self.config.sendgrid_api_key)
            response = sg.send(message)

            return {
                "success": response.status_code in [200, 201, 202],
                "provider": "sendgrid",
                "message_id": response.headers.get('X-Message-Id'),
                "to": to_email
            }

        except ImportError:
            return {
                "success": False,
                "error": "SendGrid library not installed (pip install sendgrid)",
                "provider": "sendgrid"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"SendGrid error: {str(e)}",
                "provider": "sendgrid"
            }

    def _send_via_mailgun(
        self,
        to_email: str,
        subject: str,
        body_html: Optional[str],
        body_text: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
        attachments: Optional[List[Dict[str, Any]]],
        reply_to: Optional[str]
    ) -> Dict[str, Any]:
        """Enviar email vía Mailgun API"""
        try:
            import requests

            url = f"https://api.mailgun.net/v3/{self.config.mailgun_domain}/messages"

            data = {
                "from": f"{self.config.from_name} <{self.config.from_email}>",
                "to": to_email,
                "subject": subject
            }

            if body_text:
                data["text"] = body_text

            if body_html:
                data["html"] = body_html

            if reply_to:
                data["h:Reply-To"] = reply_to

            response = requests.post(
                url,
                auth=("api", self.config.mailgun_api_key),
                data=data
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "provider": "mailgun",
                    "message_id": response.json().get('id'),
                    "to": to_email
                }
            else:
                return {
                    "success": False,
                    "error": f"Mailgun error: {response.text}",
                    "provider": "mailgun"
                }

        except ImportError:
            return {
                "success": False,
                "error": "requests library not installed",
                "provider": "mailgun"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Mailgun error: {str(e)}",
                "provider": "mailgun"
            }

    def send_template_email(
        self,
        to_email: str,
        template_name: str,
        template_vars: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enviar email usando un template.

        Args:
            to_email: Email del destinatario
            template_name: Nombre del template
            template_vars: Variables para el template

        Returns:
            Resultado del envío
        """
        # Por ahora, templates simples
        # TODO: Integrar con sistema de templates (Jinja2)

        templates = {
            "appointment_confirmation": {
                "subject": "Confirmación de Cita - {company_name}",
                "html": """
                <html>
                <body>
                    <h2>Confirmación de Cita</h2>
                    <p>Estimado/a {patient_name},</p>
                    <p>Su cita ha sido confirmada:</p>
                    <ul>
                        <li><strong>Tratamiento:</strong> {treatment}</li>
                        <li><strong>Fecha:</strong> {date}</li>
                        <li><strong>Hora:</strong> {time}</li>
                    </ul>
                    <p>¡Te esperamos!</p>
                    <p>{company_name}</p>
                </body>
                </html>
                """,
                "text": """
                Confirmación de Cita

                Estimado/a {patient_name},

                Su cita ha sido confirmada:
                - Tratamiento: {treatment}
                - Fecha: {date}
                - Hora: {time}

                ¡Te esperamos!

                {company_name}
                """
            },
            "appointment_reminder": {
                "subject": "Recordatorio de Cita - {company_name}",
                "html": """
                <html>
                <body>
                    <h2>Recordatorio de Cita</h2>
                    <p>Estimado/a {patient_name},</p>
                    <p>Le recordamos su cita de mañana:</p>
                    <ul>
                        <li><strong>Tratamiento:</strong> {treatment}</li>
                        <li><strong>Fecha:</strong> {date}</li>
                        <li><strong>Hora:</strong> {time}</li>
                    </ul>
                    <p>{company_name}</p>
                </body>
                </html>
                """,
                "text": """
                Recordatorio de Cita

                Estimado/a {patient_name},

                Le recordamos su cita de mañana:
                - Tratamiento: {treatment}
                - Fecha: {date}
                - Hora: {time}

                {company_name}
                """
            }
        }

        template = templates.get(template_name)
        if not template:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found"
            }

        # Renderizar template
        try:
            subject = template["subject"].format(**template_vars)
            body_html = template["html"].format(**template_vars)
            body_text = template["text"].format(**template_vars)

            return self.send_email(
                to_email=to_email,
                subject=subject,
                body_html=body_html,
                body_text=body_text
            )

        except KeyError as e:
            return {
                "success": False,
                "error": f"Missing template variable: {e}"
            }


# ========== FACTORY FUNCTION ========== #

def get_email_service(company_id: str) -> Optional[EmailService]:
    """
    Factory function para crear EmailService por empresa.

    Args:
        company_id: ID de la empresa

    Returns:
        EmailService configurado o None si no hay config
    """
    # Obtener configuración de variables de entorno
    # Patrón: {COMPANY_ID}_SMTP_HOST, {COMPANY_ID}_SMTP_PORT, etc.

    company_upper = company_id.upper()

    smtp_host = os.getenv(f'{company_upper}_SMTP_HOST') or os.getenv('SMTP_HOST')
    smtp_port = os.getenv(f'{company_upper}_SMTP_PORT') or os.getenv('SMTP_PORT')
    smtp_username = os.getenv(f'{company_upper}_SMTP_USERNAME') or os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv(f'{company_upper}_SMTP_PASSWORD') or os.getenv('SMTP_PASSWORD')

    sendgrid_key = os.getenv(f'{company_upper}_SENDGRID_API_KEY') or os.getenv('SENDGRID_API_KEY')

    from_email = os.getenv(f'{company_upper}_FROM_EMAIL')
    from_name = os.getenv(f'{company_upper}_FROM_NAME')

    if not from_email:
        logger.warning(f"[{company_id}] No FROM_EMAIL configured for email service")
        return None

    config = EmailConfig(
        company_id=company_id,
        from_email=from_email,
        from_name=from_name or company_id.capitalize(),
        smtp_host=smtp_host,
        smtp_port=int(smtp_port) if smtp_port else 587,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        sendgrid_api_key=sendgrid_key
    )

    return EmailService(config)
