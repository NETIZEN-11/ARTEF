"""
Contact API endpoints for sending messages to administrators.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, ValidationError
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])

# Email configuration (using Gmail SMTP)
ADMIN_EMAIL = "shingh979875@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


class ContactRequest(BaseModel):
    """Contact form submission model."""
    name: str = Field(..., min_length=2, max_length=100, description="Full name of the requester")
    email: EmailStr = Field(..., description="Email address of the requester")
    organization: Optional[str] = Field(None, max_length=100, description="Organization or company name")
    reason: str = Field(..., description="Reason for contact")
    message: str = Field(..., min_length=10, max_length=2000, description="Message content")


class ContactResponse(BaseModel):
    """Response after submitting contact form."""
    success: bool
    message: str
    timestamp: str


def send_email_notification(
    name: str,
    email: str,
    organization: Optional[str],
    reason: str,
    message: str
) -> None:
    """
    Send email notification to admin about the contact request.
    
    This function runs in the background to avoid blocking the API response.
    """
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"ARTEF Contact Request: {reason}"
        msg["From"] = "noreply@artef.local"
        msg["To"] = ADMIN_EMAIL
        msg["Reply-To"] = email

        # Create HTML email body
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
        .field {{ margin-bottom: 20px; }}
        .field-label {{ font-weight: bold; color: #4f46e5; margin-bottom: 5px; }}
        .field-value {{ background: white; padding: 10px; border-radius: 4px; border-left: 3px solid #2563eb; }}
        .message-box {{ background: white; padding: 15px; border-radius: 4px; border: 1px solid #e5e7eb; margin-top: 10px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
        .badge {{ display: inline-block; background: #2563eb; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 New Contact Request</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">ARTEF Platform - Administrator Notification</p>
        </div>
        <div class="content">
            <div class="field">
                <div class="field-label">📅 Received At:</div>
                <div class="field-value">{datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")}</div>
            </div>
            
            <div class="field">
                <div class="field-label">👤 Name:</div>
                <div class="field-value">{name}</div>
            </div>
            
            <div class="field">
                <div class="field-label">📧 Email:</div>
                <div class="field-value"><a href="mailto:{email}" style="color: #2563eb;">{email}</a></div>
            </div>
            
            {f'''<div class="field">
                <div class="field-label">🏢 Organization:</div>
                <div class="field-value">{organization}</div>
            </div>''' if organization else ''}
            
            <div class="field">
                <div class="field-label">🎯 Reason:</div>
                <div class="field-value"><span class="badge">{reason.replace('_', ' ').title()}</span></div>
            </div>
            
            <div class="field">
                <div class="field-label">💬 Message:</div>
                <div class="message-box">{message}</div>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background: #eff6ff; border-left: 4px solid #2563eb; border-radius: 4px;">
                <p style="margin: 0;"><strong>⚡ Quick Action:</strong> Reply directly to this email to respond to {name}.</p>
            </div>
        </div>
        <div class="footer">
            <p>This is an automated notification from ARTEF Platform</p>
            <p>Agent Red-Teaming & Evaluation Framework</p>
        </div>
    </div>
</body>
</html>
        """

        # Create plain text version
        text_body = f"""
ARTEF Platform - New Contact Request
=====================================

Received At: {datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")}

Name: {name}
Email: {email}
Organization: {organization or 'Not provided'}
Reason: {reason.replace('_', ' ').title()}

Message:
{message}

---
Reply to this email to respond to {name}.
This is an automated notification from ARTEF Platform.
        """

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)

        # Note: For Gmail, you need to use an App Password, not your regular password
        # The user should set up Gmail App Password and configure environment variables
        # For now, we'll log the message instead of actually sending
        
        logger.info(f"Contact request received from {name} ({email})")
        logger.info(f"Reason: {reason}")
        logger.info(f"Message preview: {message[:100]}...")
        
        # Send email via Gmail SMTP
        import os
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        if gmail_password:
            try:
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(ADMIN_EMAIL, gmail_password)
                    server.send_message(msg)
                    logger.info(f"✅ Email sent successfully to {ADMIN_EMAIL}")
            except Exception as email_error:
                logger.error(f"❌ Failed to send email: {str(email_error)}")
        else:
            logger.warning("⚠️ GMAIL_APP_PASSWORD not set, email not sent to inbox")
        
        # Also save to file as backup
        import os
        log_dir = "contact_logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_dir}/contact_{timestamp}_{email.replace('@', '_')}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_body)
        logger.info(f"Contact request saved to {filename}")
        
    except Exception as e:
        logger.error(f"Failed to process contact request: {str(e)}")
        # Don't raise exception to avoid blocking the API response


@router.post("/admin", response_model=ContactResponse, status_code=200)
async def contact_admin(
    raw_request: Request,
    background_tasks: BackgroundTasks
) -> ContactResponse:
    """
    Submit a contact request to the administrator.
    
    This endpoint allows users to send messages to the platform administrators
    for account access requests, support, or other inquiries. The request is
    processed in the background and an email notification is sent.
    
    **No authentication required** - This is a public endpoint for prospective users.
    """
    try:
        body = await raw_request.json()
        logger.info(f"Raw contact request body: {body}")
        
        # Manually validate
        request = ContactRequest(**body)
        logger.info(f"Contact request validated: {request.model_dump()}")
        
    except ValidationError as e:
        logger.error(f"Validation error: {e.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation failed",
                "errors": e.errors(),
                "message": "Please check all required fields are filled correctly"
            }
        )
    except Exception as e:
        logger.error(f"Error parsing request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate reason
    valid_reasons = [
        "account_access",
        "password_reset",
        "technical_support",
        "demo_request",
        "partnership",
        "other"
    ]
    
    if request.reason not in valid_reasons:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"
        )
    
    # Add email sending to background tasks
    background_tasks.add_task(
        send_email_notification,
        name=request.name,
        email=request.email,
        organization=request.organization,
        reason=request.reason,
        message=request.message
    )
    
    return ContactResponse(
        success=True,
        message="Your message has been sent successfully. An administrator will contact you shortly.",
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/health", status_code=200)
async def contact_health() -> dict:
    """Health check for contact endpoints."""
    return {
        "status": "healthy",
        "admin_email": ADMIN_EMAIL,
        "smtp_server": SMTP_SERVER,
        "timestamp": datetime.utcnow().isoformat()
    }
