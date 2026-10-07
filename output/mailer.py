import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)


def send_report(attachment_path: Path, summary_text: str,
                num_recommendations: int, top_score: float):
    gmail_addr = os.getenv("GMAIL_ADDRESS", "").strip()
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.getenv("EMAIL_RECIPIENT", gmail_addr).strip()

    if not gmail_addr or not gmail_pass:
        logger.error("EMAIL FAILED: Gmail credentials not set. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
        return False

    logger.info("Preparing the daily email")

    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"[Job Shortlist] {today} | {num_recommendations} picks | top score {top_score:.0f}"

    msg = MIMEMultipart()
    msg["From"] = gmail_addr
    msg["To"] = recipient
    msg["Subject"] = subject

    msg.attach(MIMEText(summary_text, "plain", "utf-8"))

    if attachment_path.exists():
        ext = attachment_path.suffix.lstrip(".")
        subtype = ext if ext else "octet-stream"
        with open(attachment_path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype=subtype)
            attachment.add_header(
                "Content-Disposition", "attachment",
                filename=attachment_path.name,
            )
            msg.attach(attachment)

    # Try SSL first (port 465), then STARTTLS (port 587)
    for method, port in [("SSL", 465), ("STARTTLS", 587)]:
        try:
            if method == "SSL":
                with smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=30) as server:
                    server.login(gmail_addr, gmail_pass)
                    server.sendmail(gmail_addr, recipient, msg.as_string())
            else:
                with smtplib.SMTP("smtp.gmail.com", port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(gmail_addr, gmail_pass)
                    server.sendmail(gmail_addr, recipient, msg.as_string())

            logger.info(f"Email sent successfully via {method}:{port} to {recipient}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.warning(f"SMTP auth failed via {method}:{port}: {e}")
            continue
        except Exception as e:
            logger.warning(f"SMTP failed via {method}:{port}: {e}")
            continue

    logger.error(
        "EMAIL FAILED: All SMTP methods failed. Possible causes:\n"
        "  1. Gmail blocked login from this IP (check https://myaccount.google.com/notifications)\n"
        "  2. App Password is incorrect (regenerate at https://myaccount.google.com/apppasswords)\n"
        "  3. 2FA is not enabled on the Google account"
    )
    return False
