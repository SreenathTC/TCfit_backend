import os
import logging
import asyncio
from datetime import datetime
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware  # CORS import
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent
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
        "content": "Your email content with link: https://example.com/share"
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
        
        # Create and send email asynchronously
        from_addr = From(from_email)
        to_addr = To(to_email)
        subject_obj = Subject("Shared Content")  # Simple default subject
        content_obj = PlainTextContent(content)
        
        mail = Mail(from_addr, to_addr, subject_obj, content_obj)
        
        # Send email asynchronously using thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, sg.send, mail)
        
        logger.info(f"Email sent successfully from {from_email} to {to_email}")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Email sent successfully",
                "data": {
                    "from_email": from_email,
                    "to_email": to_email,
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
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Run with uvicorn
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=debug)