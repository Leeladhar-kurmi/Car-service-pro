import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask-Mail configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')  
    MAIL_PORT = 587 
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'SQLALCHEMY_DATABASE_URI'
    SQLALCHEMY_TRACK_MODIFICATIONS = False 
    VAPID_PUBLIC_KEY = "VAPID_PUBLIC_KEY"