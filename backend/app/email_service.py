import os
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.config import settings


def send_prescription_email(
    to_email: str,
    patient_name: str,
    pdf_path: str,
    consultation_id: int,
) -> tuple[bool, Optional[str]]:
    if not settings.EMAIL_ENABLED:
        return False, "Email disabled. Set EMAIL_ENABLED=true in .env"

    if not pdf_path or not os.path.exists(pdf_path):
        return False, "PDF file not found"

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        return False, "SMTP username/password missing"

    try:
        msg = EmailMessage()

        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        from_name = settings.SMTP_FROM_NAME or settings.APP_NAME

        msg["Subject"] = f"Your Prescription - RX-{consultation_id:04d}"
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        msg.set_content(
            f"""
Hello {patient_name},

Your doctor-approved prescription is attached with this email.

Prescription ID: RX-{consultation_id:04d}

Regards,
{settings.APP_NAME}
Powered by Groq AI + Smart Clinical Automation
""".strip()
        )

        with open(pdf_path, "rb") as file:
            pdf_data = file.read()

        msg.add_attachment(
            pdf_data,
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(pdf_path),
        )

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True, None

    except Exception as exc:
        return False, str(exc)