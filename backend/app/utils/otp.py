import os
import random
from datetime import datetime, timedelta
import logging
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import Twilio
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logging.warning("Twilio not installed. OTP messages will be logged but not sent.")

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# OTP configuration
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
# Set this to True for testing to always use the same code
TESTING_MODE = True
TESTING_OTP = os.getenv("TESTING_OTP", "123456")  # Default testing OTP

# In-memory OTP storage (replace with database in production)
# Format: {phone_number: (otp, expiry_timestamp)}
otp_storage: Dict[str, Tuple[str, datetime]] = {}

def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a random numeric OTP of specified length"""
    if TESTING_MODE:
        return TESTING_OTP
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

def store_otp(phone_number: str, otp: str) -> None:
    """Store OTP with expiry time"""
    expiry = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    otp_storage[phone_number] = (otp, expiry)

def get_stored_otp(phone_number: str) -> Optional[str]:
    """Get stored OTP if not expired"""
    if phone_number not in otp_storage:
        return None
    
    otp, expiry = otp_storage[phone_number]
    
    if datetime.now() > expiry:
        # OTP expired
        del otp_storage[phone_number]
        return None
        
    return otp

def verify_otp(phone_number: str, provided_otp: str) -> bool:
    """Verify if provided OTP matches stored OTP"""
    # If in testing mode and provided OTP matches testing OTP, always succeed
    if TESTING_MODE and provided_otp == TESTING_OTP:
        logging.info(f"TESTING MODE: OTP verification succeeded for {phone_number}")
        return True
    
    stored_otp = get_stored_otp(phone_number)
    
    if not stored_otp:
        logging.warning(f"No stored OTP found for {phone_number} or OTP expired")
        return False
    
    if stored_otp == provided_otp:
        # Clear OTP after successful verification
        del otp_storage[phone_number]
        logging.info(f"OTP verification succeeded for {phone_number}")
        return True
    
    logging.warning(f"OTP verification failed for {phone_number}. Provided: {provided_otp}, Expected: {stored_otp}")    
    return False

def send_otp(phone_number: str) -> Tuple[bool, str]:
    """Generate and send OTP via Twilio"""
    otp = generate_otp()
    store_otp(phone_number, otp)
    
    if TESTING_MODE:
        # In testing mode, always return the same OTP
        logging.info(f"TESTING MODE: Using fixed OTP for {phone_number}: {otp}")
        return True, f"Testing mode: OTP for {phone_number} is {otp}"
    
    if not TWILIO_AVAILABLE or not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        # Log OTP for development purposes
        logging.info(f"Development mode: OTP for {phone_number} is {otp}")
        return True, f"Development mode: OTP for {phone_number} is {otp}"
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your FoodieSpot verification code is: {otp}. Valid for {OTP_EXPIRY_MINUTES} minutes.",
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        return True, "OTP sent successfully"
    except Exception as e:
        logging.error(f"Failed to send OTP: {str(e)}")
        return False, f"Failed to send OTP: {str(e)}"
