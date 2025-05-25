import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ):
        """Send email using configured SMTP server"""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.EMAIL_FROM
        message["To"] = to_email
        
        # Add plain text part
        text_part = MIMEText(body, "plain")
        message.attach(text_part)
        
        # Add HTML part if provided
        if html_body:
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)
        
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER if settings.SMTP_USER else None,
                password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
                use_tls=False  # MailHog doesn't use TLS
            )
            logger.info(f"Email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise
    
    @staticmethod
    async def send_otp_email(to_email: str, otp_code: str):
        """Send OTP email"""
        subject = "Your UmaDex Login Code"
        body = f"""Your login code is: {otp_code}

This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.

If you didn't request this code, please ignore this email.
"""
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Your UmaDex Login Code</h2>
                <p>Your login code is:</p>
                <h1 style="background-color: #f0f0f0; padding: 20px; text-align: center; letter-spacing: 5px;">
                    {otp_code}
                </h1>
                <p>This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.</p>
                <p style="color: #666; font-size: 14px;">
                    If you didn't request this code, please ignore this email.
                </p>
            </body>
        </html>
        """
        
        await EmailService.send_email(to_email, subject, body, html_body)