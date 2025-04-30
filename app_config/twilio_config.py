import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_CONFIG = {
    'account_sid': os.getenv('TWILIO_ACCOUNT_SID'),
    'auth_token': os.getenv('TWILIO_AUTH_TOKEN'),
    'whatsapp_number': os.getenv('TWILIO_WHATSAPP_NUMBER')
}

if not all(TWILIO_CONFIG.values()):
    raise ValueError(
        "Missing Twilio credentials. Please check your .env file and ensure all "
        "TWILIO_* variables are set."
    )