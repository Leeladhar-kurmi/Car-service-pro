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
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Email configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    app.config['VAPID_PUBLIC_KEY'] = ''

    # Verify email configuration
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        app.logger.error("Email configuration is incomplete. Please check your .env file.")
    
    # Add debug logging for email configuration
    app.logger.debug("Mail configuration:")
    app.logger.debug(f"MAIL_SERVER: {app.config['MAIL_SERVER']}")
    app.logger.debug(f"MAIL_PORT: {app.config['MAIL_PORT']}")
    app.logger.debug(f"MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
    app.logger.debug(f"MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
    app.logger.debug(f"MAIL_DEFAULT_SENDER: {app.config['MAIL_DEFAULT_SENDER']}")

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    login_manager.login_view = 'login'

    # Configure Flask-APScheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.start()

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
        logging.info("Database tables created")
        
        # Register routes (this will also create default service types)
        from routes import register_routes
        register_routes(app, db, mail)

    # Add scheduler jobs
    @scheduler.task('cron', id='check_reminders', hour='*')
    def check_reminders():
        """Check and send service reminders"""
        with app.app_context():
            # Get pending reminders that are due
            pending_reminders = ServiceReminder.query.filter_by(
                status='pending'
            ).filter(
                ServiceReminder.reminder_date <= datetime.utcnow()
            ).all()
            
            for reminder in pending_reminders:
                service = reminder.service
                car = service.car
                user = car.user
                
                # Prepare notification message
                message = f"""
                Service Reminder: {service.service_type.name}
                Car: {car.nickname} ({car.make} {car.model} {car.year})
                Due Date: {service.next_service_date.strftime('%Y-%m-%d')}
                """
                
                # Send email notification
                if reminder.reminder_type in ['email', 'both']:
                    try:
                        msg = Message(
                            'Car Service Reminder',
                            recipients=[user.email],
                            body=message
                        )
                        mail.send(msg)
                    except Exception as e:
                        app.logger.error(f"Failed to send email reminder: {str(e)}")
                
                # Send push notification
                if reminder.reminder_type in ['push', 'both']:
                    try:
                        # Your push notification logic here
                        pass
                    except Exception as e:
                        app.logger.error(f"Failed to send push reminder: {str(e)}")
                
                # Update reminder status
                reminder.status = 'sent'
                db.session.commit()


    return app

# Create the application instance
app = create_app()
