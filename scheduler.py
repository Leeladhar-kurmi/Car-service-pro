from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import logging
from app import app, db
from models import ServiceReminder, User
from push_notifications import send_push_notification
import json

scheduler = APScheduler()


def check_service_reminders():
    """Check for services that need reminders and send notifications"""
    with app.app_context():
        logging.info("Checking for service reminders...")
        
        # Get all active services that haven't been notified yet
        services = ServiceReminder.query.filter(
            ServiceReminder.status == 'pending',
            ServiceReminder.reminder_date <= datetime.now()
        ).all()
        
        notifications_sent = 0
        
        for service in services:
            status = service.get_due_status()
            if status['is_due'] or status['is_due_soon']:
                # Send notification
                user = service.car.owner
                if user.push_subscription:
                    try:
                        subscription_info = json.loads(user.push_subscription)
                        
                        # Build notification message
                        if status['is_due']:
                            title = f"Service Overdue: {service.service_type.name}"
                            message = f"Your {service.car} is overdue for {service.service_type.name}"
                        else:
                            title = f"Service Due Soon: {service.service_type.name}"
                            message = f"Your {service.car} will need {service.service_type.name} soon"
                        
                        # Add specific details about why it's due
                        details = []
                        if status['due_by_date'] and status['days_remaining'] is not None:
                            if status['days_remaining'] <= 0:
                                details.append("Overdue by date")
                            else:
                                details.append(f"Due in {status['days_remaining']} days")
                                
                        if status['due_by_mileage'] and status['km_remaining'] is not None:
                            if status['km_remaining'] <= 0:
                                details.append(f"Overdue by {abs(status['km_remaining'])} KM")
                            else:
                                details.append(f"Due in {status['km_remaining']} KM")
                        
                        if details:
                            message += f" ({', '.join(details)})"
                        
                        # Send push notification
                        send_push_notification(
                            subscription_info,
                            title,
                            message,
                            icon='/static/icons/icon-192.svg',
                            badge='/static/icons/icon-192.svg'
                        )
                        
                        # Mark as notified
                        service.notification_sent = True
                        notifications_sent += 1
                        
                    except Exception as e:
                        logging.error(f"Failed to send notification for service {service.id}: {str(e)}")
        
        if notifications_sent > 0:
            db.session.commit()
            logging.info(f"Sent {notifications_sent} service reminder notifications")
        else:
            logging.info("No service reminders to send")


def start_scheduler(app):
    """Initialize and start the scheduler"""
    scheduler.init_app(app)
    scheduler.start()
    
    # Add job to check service reminders daily at 9 AM
    scheduler.add_job(
        func=check_service_reminders,
        trigger="cron",
        hour=9,
        minute=0,
        id='service_reminders',
        name='Check service reminders',
        replace_existing=True
    )
    
    logging.info("Scheduler started with service reminder job")
