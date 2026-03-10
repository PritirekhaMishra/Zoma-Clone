"""
Nightlife Services Configuration
================================
PostgreSQL database for nightlife booking system
"""
SERVICES = {
    "main": {
        "name": "Nightlife Main Service",
        "port": 5001
    },
    "vendor": {
        "name": "Nightlife Vendor Service",
        "port": 5002
    },
    "booking": {
        "name": "Nightlife Booking Service",
        "port": 5003
    },
    "orders": {
        "name": "Nightlife Orders Service",
        "port": 5004
    }
}
import os 
# Database configuration
DATABASE_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': os.environ.get('POSTGRES_PORT', '5432'),
    'database': 'zoma_nightlife',
    'user': os.environ.get('POSTGRES_USER', 'postgres'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'password')
}

# Email configuration
EMAIL_CONFIG = {
    'MAIL_SERVER': os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    'MAIL_PORT': int(os.environ.get('MAIL_PORT', 587)),
    'MAIL_USE_TLS': os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true',
    'MAIL_USERNAME': os.environ.get('MAIL_USERNAME', ''),
    'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD', ''),
    'MAIL_DEFAULT_SENDER': os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@zomaclonemail.com')
}

# OTP configuration
OTP_CONFIG = {
    'OTP_LENGTH': 6,
    'OTP_EXPIRE_MINUTES': 10,
    'MAX_BOOKINGS_PER_USER_PER_DAY': 3
}

# Booking ID format
BOOKING_ID_PREFIX = 'NL'
BOOKING_ID_FORMAT = '{prefix}-{date}-{sequence:04d}'

# Commission settings
PLATFORM_COMMISSION_PERCENT = 5
PLATFORM_FEE_FIXED = 10

DEBUG = True
SECRET_KEY = "nightlife-secret"

CORS_ORIGINS = ["*"]

# ----------------------------------------
# Helper Functions
# ----------------------------------------

def success_response(data=None, message="Success"):
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(message="Error", status_code=400):
    return {
        "success": False,
        "message": message
    }, status_code


def get_db_path(service_name):
    """
    Returns database connection string
    """
    return (
        f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
        f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}"
        f"/{DATABASE_CONFIG['database']}"
    )