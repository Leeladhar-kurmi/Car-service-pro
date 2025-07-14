from flask_apscheduler import APScheduler
from datetime import datetime
import logging
from models import ServiceReminder
from push_notifications import PushNotificationService

scheduler = APScheduler()

def check_service_reminders():
    """Check for services that need reminders and send notifications"""
    from app import db, app  # Import here to avoid circular import at module level
    with app.app_context():
        logging.info("Checking for service reminders...")
        
        # Get pending reminders due now or in past
        pending_reminders = ServiceReminder.query.filter(
            ServiceReminder.status == 'pending',
            ServiceReminder.reminder_date <= datetime.utcnow()
        ).all()
        
        notifications_sent = 0
        
        for reminder in pending_reminders:
            try:
                car = reminder.car
                user = car.user  # Corrected from car.owner
                service = reminder.service
                
                if not user.push_subscription:
                    continue
                    
                # Build notification message
                if reminder.status == 'overdue':
                    title = f"Service Overdue: {service.service_type.name}"
                    message = f"Your {car.nickname or car.make} is overdue for {service.service_type.name}"
                else:
                    title = f"Service Due Soon: {service.service_type.name}"
                    message = f"Your {car.nickname or car.make} needs {service.service_type.name} soon"
                
                # Add details
                details = []
                if service.next_service_date:
                    days_left = (service.next_service_date - datetime.utcnow().date()).days
                    if days_left <= 0:
                        details.append(f"Overdue by {-days_left} days")
                    else:
                        details.append(f"Due in {days_left} days")
                
                if service.next_service_mileage and car.current_mileage:
                    miles_left = service.next_service_mileage - car.current_mileage
                    if miles_left <= 0:
                        details.append(f"Overdue by {-miles_left} KMs")
                    else:
                        details.append(f"Due in {miles_left} KMs")
                
                if details:
                    message += f" ({', '.join(details)})"
                
                # Send notification
                success = PushNotificationService.send_to_user(
                    user=user,
                    title=title,
                    body=message,
                    url=f"/cars/{car.id}/services",
                    icon='/static/icons/icon-192.svg'
                )
                
                if success:
                    reminder.status = 'sent'
                    notifications_sent += 1
                else:
                    reminder.status = 'failed'
                    
                db.session.commit()
                
            except Exception as e:
                logging.error(f"Failed to process reminder {reminder.id}: {str(e)}")
                db.session.rollback()
        
        logging.info(f"Sent {notifications_sent} notifications")
        return notifications_sent

def start_scheduler(app):
    """Initialize and start the scheduler"""
    if not scheduler.running:
        scheduler.init_app(app)
        
        # Add job to check service reminders daily at 9 AM
        scheduler.add_job(
            id='service_reminders',
            func=check_service_reminders,
            trigger='cron',
            hour=9,
            minute=0,
            replace_existing=True
        )
        
        try:
            scheduler.start()
            logging.info("Scheduler started successfully")
        except Exception as e:
            logging.error(f"Failed to start scheduler: {str(e)}")