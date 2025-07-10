import os
import logging
from flask import Flask, request, jsonify
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "sendgrid_configured": sg is not None,
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/send-email', methods=['POST'])
def send_email():
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
            return jsonify({
                "success": False,
                "message": "SendGrid not configured. Please check SENDGRID_API_KEY environment variable."
            }), 500
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No JSON data provided"
            }), 400
        
        # Get required fields
        from_email = data.get('from_email', '').strip()
        to_email = data.get('to_email', '').strip()
        content = data.get('content', '').strip()
        
        # Validate required fields
        if not from_email:
            return jsonify({
                "success": False,
                "message": "from_email is required"
            }), 400
            
        if not to_email:
            return jsonify({
                "success": False,
                "message": "to_email is required"
            }), 400
            
        if not content:
            return jsonify({
                "success": False,
                "message": "content is required"
            }), 400
        
        # Validate email formats
        if not validate_email(from_email):
            return jsonify({
                "success": False,
                "message": "Invalid from_email format"
            }), 400
        
        if not validate_email(to_email):
            return jsonify({
                "success": False,
                "message": "Invalid to_email format"
            }), 400
        
        # Create and send email
        from_addr = From(from_email)
        to_addr = To(to_email)
        subject_obj = Subject("Shared Content")  # Simple default subject
        content_obj = PlainTextContent(content)
        
        mail = Mail(from_addr, to_addr, subject_obj, content_obj)
        
        # Send email
        response = sg.send(mail)
        
        logger.info(f"Email sent successfully from {from_email} to {to_email}")
        
        return jsonify({
            "success": True,
            "message": "Email sent successfully",
            "data": {
                "from_email": from_email,
                "to_email": to_email,
                "status_code": response.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "message": "Endpoint not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "message": "Method not allowed"
    }), 405

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
    
    # Run the Flask app
    app.run(debug=debug, host='0.0.0.0', port=port)