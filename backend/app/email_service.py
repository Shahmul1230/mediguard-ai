import os
import socket
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.config import settings


class SMTPIPv4(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        last_error = None

        addresses = socket.getaddrinfo(
            host,
            port,
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        for family, socktype, proto, canonname, sockaddr in addresses:
            try:
                sock = socket.socket(family, socktype, proto)

                if timeout is not None:
                    sock.settimeout(timeout)

                sock.connect(sockaddr)
                return sock

            except OSError as exc:
                last_error = exc

                try:
                    sock.close()
                except Exception:
                    pass

        raise OSError(f"Could not connect to {host}:{port} using IPv4. Last error: {last_error}")


class SMTPSSLIPv4(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        last_error = None

        addresses = socket.getaddrinfo(
            host,
            port,
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        for family, socktype, proto, canonname, sockaddr in addresses:
            try:
                raw_sock = socket.socket(family, socktype, proto)

                if timeout is not None:
                    raw_sock.settimeout(timeout)

                raw_sock.connect(sockaddr)
                ssl_sock = self.context.wrap_socket(raw_sock, server_hostname=host)
                return ssl_sock

            except OSError as exc:
                last_error = exc

                try:
                    raw_sock.close()
                except Exception:
                    pass

        raise OSError(f"Could not connect to {host}:{port} using IPv4 SSL. Last error: {last_error}")


def clean_smtp_password(password: str) -> str:
    return (password or "").replace(" ", "").strip()


def send_prescription_email(
    to_email: str,
    patient_name: str,
    pdf_path: str,
    consultation_id: int,
) -> tuple[bool, Optional[str]]:
    if not settings.EMAIL_ENABLED:
        return False, "Email disabled. Set EMAIL_ENABLED=true in environment variables"

    if not pdf_path or not os.path.exists(pdf_path):
        return False, f"PDF file not found at path: {pdf_path}"

    smtp_host = (settings.SMTP_HOST or "").strip()
    smtp_port = int(settings.SMTP_PORT or 587)
    smtp_username = (settings.SMTP_USERNAME or "").strip()
    smtp_password = clean_smtp_password(settings.SMTP_PASSWORD)
    smtp_from_email = (settings.SMTP_FROM_EMAIL or smtp_username).strip()
    smtp_from_name = (settings.SMTP_FROM_NAME or settings.APP_NAME).strip()

    if not smtp_host:
        return False, "SMTP_HOST is missing"

    if not smtp_username:
        return False, "SMTP_USERNAME is missing"

    if not smtp_password:
        return False, "SMTP_PASSWORD is missing"

    if not smtp_from_email:
        return False, "SMTP_FROM_EMAIL is missing"

    try:
        msg = EmailMessage()

        msg["Subject"] = f"Your Prescription - RX-{consultation_id:04d}"
        msg["From"] = f"{smtp_from_name} <{smtp_from_email}>"
        msg["To"] = to_email
        msg["Reply-To"] = smtp_from_email

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

        if smtp_port == 465:
            with SMTPSSLIPv4(smtp_host, smtp_port, timeout=30) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        else:
            with SMTPIPv4(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)

        return True, None

    except smtplib.SMTPAuthenticationError as exc:
        return (
            False,
            "SMTP authentication failed. Gmail App Password, 2-Step Verification, SMTP_USERNAME, and SMTP_PASSWORD check করুন. "
            f"Raw error: {exc}",
        )

    except smtplib.SMTPRecipientsRefused as exc:
        return False, f"Recipient email refused by SMTP server: {exc}"

    except smtplib.SMTPSenderRefused as exc:
        return False, f"Sender email refused. Check SMTP_FROM_EMAIL and SMTP_USERNAME. Raw error: {exc}"

    except socket.gaierror as exc:
        return False, f"DNS resolution failed for SMTP host {smtp_host}: {exc}"

    except OSError as exc:
        return False, f"SMTP network connection failed using IPv4: {exc}"

    except smtplib.SMTPException as exc:
        return False, f"SMTP error: {exc}"

    except Exception as exc:
        return False, f"Email sending failed: {exc}"