from apps.common.email import send_otp_email as sendgrid_otp
import os


def send_otp_email(email, otp, otp_type, name=None):
    """Send OTP via SendGrid in production, console in development"""

    print(f"\n{'='*50}")
    print(f"OTP EMAIL SENT")
    print(f"To: {email}")
    print(f"OTP Code: {otp}")
    print(f"{'='*50}\n")

    # Try SendGrid if API key exists
    api_key = os.getenv('SENDGRID_API_KEY')
    if api_key and api_key != 'your_sendgrid_api_key_here':
        sendgrid_otp(email, otp, otp_type, name)