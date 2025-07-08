from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from models import db
from dotenv import load_dotenv
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from models import ServiceReminder, Service
from flask_mail import Message
from scheduler import start_scheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize extensions
login_manager = LoginManager()
mail = Mail()

# Initialize scheduler
scheduler = APScheduler()

def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    application = app
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Set up error file handler
    file_handler = logging.FileHandler(os.path.join(log_dir, 'error.log'))
    file_handler.setLevel(logging.ERROR)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)

    # Clear existing handlers (important!)
    if app.logger.hasHandlers():
        app.logger.handlers.clear()

    # Add only our custom handler
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.ERROR)

    # Optional: add console output for debugging (can be removed)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    app.logger.addHandler(console_handler)
    
    

    # Working Test Email configuration
    # app.config['MAIL_SERVER'] = "mail.meramenu.in"
    # app.config['MAIL_PORT'] = 587
    # app.config['MAIL_USE_TLS'] = True
    # app.config['MAIL_USE_AUTH'] = False
    # app.config['MAIL_USERNAME'] = "usersupport@meramenu.in"
    # app.config['MAIL_PASSWORD'] = "Madhya@102024"  
    # app.config['MAIL_DEFAULT_SENDER'] = ('CarServicePro', "usersupport@meramenu.in")
    # app.config['VAPID_PUBLIC_KEY'] = ''
    
    # Email configuration
    # app.config['MAIL_SERVER'] = "az1-ss107.a2hosting.com"
    # app.config['MAIL_PORT'] = 587
    # app.config['MAIL_USE_TLS'] = True
    # app.config['MAIL_USE_AUTH'] = False
    # app.config['MAIL_USERNAME'] = "support@carservice.helpersin.com"
    # app.config['MAIL_PASSWORD'] = "Q!W@e3r4t5Q!W@e3r4t5"  
    # app.config['MAIL_DEFAULT_SENDER'] = ('CarServicePro', "support@carservice.helpersin.com")
    # app.config['VAPID_PUBLIC_KEY'] = ''
    
    

    
    # Typed conversions with safe fallbacks
    def str_to_bool(val):
        return str(val).lower() in ['true', '1', 'yes']
    
    def str_to_tuple(val):
        try:
            return eval(val) if val else None
        except Exception:
            return None
        
    # DATABASE
    DATABASE_URL = os.environ.get("DATABASE_URL")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    
    # MAIL
    MAIL_DEFAULT_SENDER = str_to_tuple(os.environ.get("CAR_SERVICE_MAIL_DEFAULT_SENDER"))
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_USE_AUTH = str_to_bool(os.environ.get("MAIL_USE_AUTH"))
    MAIL_USE_TLS = str_to_bool(os.environ.get("MAIL_USE_TLS"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    
    # SECRET + VAPID
    SECRET_KEY = os.environ.get("SECRET_KEY")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
    VAPID_CLAIMS =({"sub": "mailto:admin@carservicepro.com"})


    # Print all with types
    # print(f"DATABASE_URL ({type(DATABASE_URL)}): {DATABASE_URL}")
    # print(f"DB_PASSWORD ({type(DB_PASSWORD)}): {DB_PASSWORD}")
    # print(f"MAIL_DEFAULT_SENDER ({type(MAIL_DEFAULT_SENDER)}): {MAIL_DEFAULT_SENDER}")
    # print(f"MAIL_PORT ({type(MAIL_PORT)}): {MAIL_PORT}")
    # print(f"MAIL_SERVER ({type(MAIL_SERVER)}): {MAIL_SERVER}")
    # print(f"MAIL_USE_AUTH ({type(MAIL_USE_AUTH)}): {MAIL_USE_AUTH}")
    # print(f"MAIL_USE_TLS ({type(MAIL_USE_TLS)}): {MAIL_USE_TLS}")
    # print(f"MAIL_USERNAME ({type(MAIL_USERNAME)}): {MAIL_USERNAME}")
    # print(f"MAIL_PASSWORD ({type(MAIL_PASSWORD)}): {MAIL_PASSWORD}")
    # print(f"SECRET_KEY ({type(SECRET_KEY)}): {SECRET_KEY}")
    # print(f"VAPID_PUBLIC_KEY ({type(VAPID_PUBLIC_KEY)}): {VAPID_PUBLIC_KEY}")
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_recycle": 280,"pool_pre_ping": True}
    # print(f"VAPID_PUBLIC_KEY ({type(VAPID_PUBLIC_KEY)}): {VAPID_PUBLIC_KEY}")
    
    # Email configuration from env
    app.config['MAIL_SERVER'] = MAIL_SERVER
    app.config['MAIL_PORT'] = MAIL_PORT
    app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
    app.config['MAIL_USE_AUTH'] = MAIL_USE_AUTH
    app.config['MAIL_USERNAME'] = MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
    app.config['VAPID_PUBLIC_KEY'] = VAPID_PUBLIC_KEY
    app.config['VAPID_PRIVATE_KEY'] = VAPID_PRIVATE_KEY
    app.config['VAPID_CLAIMS'] = VAPID_CLAIMS
    # print(f"VAPID_PRIVATE_KEY ({type(VAPID_PRIVATE_KEY)}): {VAPID_PRIVATE_KEY}")
    # print(f"VAPID_CLAIMS ({type(VAPID_CLAIMS)}): {VAPID_CLAIMS}")


    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    login_manager.login_view = 'login'

    # Configure Flask-APScheduler
    app.config['SCHEDULER_API_ENABLED'] = False
    scheduler.init_app(app)
    start_scheduler(app)

    # Create database directory if it doesn't exist
    os.makedirs('instance', exist_ok=True)

    # Add custom Jinja2 test
    @app.template_test('test_year_filter')
    def test_year_filter(service_history, year):
        """Test if a service date matches the given year"""
        return service_history.service_date.year == year

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(user_id)

    # Create tables and register routes
    with app.app_context():
        db.create_all()
        # logging.info("Database tables created")
        
        # Register routes (this will also create default service types)
        from routes import register_routes
        register_routes(app, db, mail)

    return app

# Create the application instance
app = create_app()
