import os
import logging
import asyncio
from datetime import datetime
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware  # CORS import
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, HtmlContent
from sendgrid.helpers.mail import TrackingSettings, ClickTracking, OpenTracking  # Add tracking imports  #Changed to HtmlContent
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Production-ready CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",           # Angular dev server
        "https://localhost:4200",          # HTTPS Angular dev
        "https://app.thethinkfit.in",      # Your production domain
        "https://thethinkfit.in",          # Main domain (if needed)
        "https://www.thethinkfit.in",      # WWW version (if needed)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only methods you need
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With"
    ],
)

# SendGrid configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

# Initialize SendGrid client
try:
    sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
    logger.info("SendGrid client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize SendGrid client: {str(e)}")
    sg = None

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def create_email_with_button(content, button_link=None):
    """
    Create HTML email with optional button link
    """
    def get_smart_button_text(url):
        """Get contextual button text based on URL"""
        if 'thethinkfit.in/invite' in url:
            return 'Join ThinkFit'
        elif 'thethinkfit.in' in url:
            return 'Open ThinkFit'
        elif 'document' in url or 'doc' in url:
            return 'View Document'
        elif 'share' in url or 'shared' in url:
            return 'View Shared Content'
        else:
            return 'Open Link'
    
    # Convert line breaks to HTML
    html_content = content.replace('\n', '<br>')
    
    # Create button HTML if button_link is provided
    button_html = ""
    if button_link:
        button_text = get_smart_button_text(button_link)
        
        # Smart color scheme based on link
        if 'thethinkfit.in' in button_link:
            # ThinkFit brand colors - fitness theme
            gradient = "background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);"
            shadow_color = "76, 175, 80"
        else:
            # Default professional colors
            gradient = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
            shadow_color = "102, 126, 234"
        
        button_html = f'''
        <div style="margin: 30px 0; text-align: center;">
            <a href="{button_link}" style="
                display: inline-block;
                padding: 14px 35px;
                {gradient}
                color: white;
                text-decoration: none;
                border-radius: 30px;
                font-family: Arial, sans-serif;
                font-size: 16px;
                font-weight: 600;
                box-shadow: 0 4px 15px rgba({shadow_color}, 0.3);
                transition: all 0.3s ease;
                border: none;
                cursor: pointer;
                min-width: 180px;
            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba({shadow_color}, 0.4)';" 
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba({shadow_color}, 0.3)';">
                {button_text}
            </a>
        </div>
        '''
    
    # Create complete HTML email template with ThinkFit branding
    html_email = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ThinkFit Notification</title>
    </head>
    <body style="
        font-family: Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 600px;
        margin: 0 auto;
        padding: 20px;
        background-color: #f5f5f5;
    ">
        <div style="
            background-color: white;
            padding: 40px 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            border-top: 4px solid #4CAF50;
        ">
            <!-- ThinkFit Header -->
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="
                    color: #4CAF50;
                    margin: 0;
                    font-size: 24px;
                    font-weight: 700;
                ">ThinkFit</h2>
                <p style="
                    color: #888;
                    margin: 5px 0 0 0;
                    font-size: 14px;
                ">Fitness. Competition. Success.</p>
            </div>
            
            <!-- Email Content -->
            <div style="
                font-size: 16px;
                line-height: 1.6;
                color: #555;
                text-align: center;
            ">
                {html_content}
            </div>
            
            <!-- Button (if provided) -->
            {button_html}
            
            <!-- Footer -->
            <div style="
                margin-top: 40px;
                padding-top: 25px;
                border-top: 1px solid #eee;
                font-size: 14px;
                color: #888;
                text-align: center;
            ">
                <p style="margin: 0;">Best regards,</p>
                <p style="margin: 5px 0 0 0; font-weight: 600; color: #4CAF50;">The ThinkFit Team</p>
                <p style="margin: 15px 0 0 0; font-size: 12px; color: #aaa;">
                    Start your fitness journey today!
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html_email

@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "running",
            "sendgrid_configured": sg is not None,
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=200
    )

@app.post('/send-email')
async def send_email(request: Request):
    """
    Send email endpoint
    Expected JSON payload:
    {
        "from_email": "sender@example.com",
        "to_email": "recipient@example.com", 
        "content": "Your email content here",
        "button_link": "https://app.thethinkfit.in/invite?orgid=..." (optional)
    }
    """
    try:
        # Check if SendGrid is configured
        if sg is None:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "SendGrid not configured. Please check SENDGRID_API_KEY environment variable."
                },
                status_code=500
            )
        
        data = await request.json()
        
        if not data:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "No JSON data provided"
                },
                status_code=400
            )
        
        # Get required fields
        from_email = data.get('from_email', '').strip()
        to_email = data.get('to_email', '').strip()
        content = data.get('content', '').strip()
        
        # Get optional button link
        button_link = data.get('button_link', '').strip()
        if button_link and not button_link.startswith('http'):
            button_link = ''  # Invalid link, ignore it
        
        # Validate required fields
        if not from_email:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "from_email is required"
                },
                status_code=400
            )
            
        if not to_email:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "to_email is required"
                },
                status_code=400
            )
            
        if not content:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "content is required"
                },
                status_code=400
            )
        
        # Validate email formats
        if not validate_email(from_email):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "Invalid from_email format"
                },
                status_code=400
            )
        
        if not validate_email(to_email):
            return JSONResponse(
                content={
                    "success": False,
                    "message": "Invalid to_email format"
                },
                status_code=400
            )
        
        #Create HTML email with optional button
        html_content = create_email_with_button(content, button_link)
        
        # Create and send email asynchronously
        from_addr = From(from_email)
        to_addr = To(to_email)
        subject_obj = Subject("Shared Content")
        content_obj = HtmlContent(html_content)  #HTML email with optional button
        
        mail = Mail(from_addr, to_addr, subject_obj, content_obj)
        
        # Explicitly disable click tracking to preserve original URLs
        tracking_settings = TrackingSettings()
        click_tracking = ClickTracking(enable=False, enable_text=False)
        open_tracking = OpenTracking(enable=False)
        tracking_settings.click_tracking = click_tracking
        tracking_settings.open_tracking = open_tracking
        mail.tracking_settings = tracking_settings
        
        # Send email asynchronously using thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, sg.send, mail)
        
        logger.info(f"Email sent successfully from {from_email} to {to_email} with button: {bool(button_link)}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Email sent successfully",
                "data": {
                    "from_email": from_email,
                    "to_email": to_email,
                    "has_button": bool(button_link),
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return JSONResponse(
            content={
                "success": False,
                "message": f"Failed to send email: {str(e)}"
            },
            status_code=500
        )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        content={
            "success": False,
            "message": "Endpoint not found"
        },
        status_code=404
    )

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    return JSONResponse(
        content={
            "success": False,
            "message": "Method not allowed"
        },
        status_code=405
    )

if __name__ == '__main__':
    # Check if SendGrid API key is configured
    if not SENDGRID_API_KEY:
        print("\n" + "="*50)
        print("WARNING: SENDGRID_API_KEY not configured!")
        print("Please set it in your .env file")
        print("="*50 + "\n")
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Run with uvicorn
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=debug)