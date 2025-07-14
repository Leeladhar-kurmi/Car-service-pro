from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and profile"""
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    profile_image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Notification preferences
    reminder_type = db.Column(db.String(20), default='email')  # 'email', 'push', 'both'
    reminder_days = db.Column(db.JSON, default=lambda: [7, 3, 1])  # Days before service to send reminder
    push_subscription = db.Column(db.JSON)  # Web Push subscription info
    
    # Relationships
    cars = db.relationship('Car', backref='user', lazy=True, cascade='all, delete-orphan')
    service_history = db.relationship('ServiceHistory', back_populates='user', cascade='all, delete-orphan')
    # service_history = db.relationship('ServiceHistory', back_populates='car', lazy=True, cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Car(db.Model):
    __tablename__ = 'cars'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    nickname = db.Column(db.String(50))
    vin = db.Column(db.String(17))
    current_mileage = db.Column(db.Integer)
    registration_number = db.Column(db.String(100), unique=True, nullable=False)
    insurance_company = db.Column(db.String(50))
    expiry_date = db.Column(db.Date)
    vehicle_type = db.Column(db.String(20), nullable=False, default='car')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    services = db.relationship('Service', backref='car', lazy=True, cascade='all, delete-orphan')
    reminders = db.relationship('ServiceReminder', backref='car', lazy=True)
    service_history = db.relationship('ServiceHistory', back_populates='car', lazy=True, cascade='all, delete-orphan')

    @property
    def overdue_count(self):
        return ServiceReminder.query.filter_by(car_id=self.id, status='overdue').count()

    @property
    def due_soon_count(self):
        return ServiceReminder.query.filter_by(car_id=self.id, status='due_soon').count()

    @property
    def upcoming_count(self):
        return ServiceReminder.query.filter_by(car_id=self.id, status='upcoming').count()


    def __repr__(self):
        return f'<Car {self.year} {self.make} {self.model}>'

    def total_service_cost(self):
        return db.session.query(func.sum(ServiceHistory.total_cost)).filter(
            ServiceHistory.car_id == self.id
        ).scalar() or 0

    def last_service_date(self):
        return db.session.query(func.max(ServiceHistory.service_date)).filter(
            ServiceHistory.car_id == self.id
        ).scalar()


class ServiceType(db.Model):
    """Service type model for predefined service types"""
    __tablename__ = 'service_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    default_interval_months = db.Column(db.Integer)
    default_interval_mileage = db.Column(db.Integer)
    vehicle_type = db.Column(db.String(10))

    __table_args__ = (
    db.UniqueConstraint('name', 'vehicle_type', name='_name_vehicle_type_uc'),
)
    
    def __repr__(self):
        return f'<ServiceType {self.name}>'
    
    def average_cost(self, user_id=None):
        query = db.session.query(func.avg(ServiceHistory.cost)).join(
            Car
        ).filter(
            ServiceHistory.service_type_id == self.id
        )
        if user_id:
            query = query.filter(Car.user_id == user_id)
        return query.scalar() or 0


class Service(db.Model):
    """Service model for scheduled services with interval tracking"""
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'), nullable=False)
    
    # Interval Configuration
    interval_months = db.Column(db.Integer, nullable=False, default=12)
    interval_mileage = db.Column(db.Integer, nullable=False, default=10000)
    notify_days_before = db.Column(db.Integer, nullable=False, default=7)  # Default 1 week notice
    
    # Last Service Information
    last_service_date = db.Column(db.Date)
    last_service_mileage = db.Column(db.Integer)
    last_service_cost = db.Column(db.Float)
    last_service_notes = db.Column(db.Text)
    
    # Next Service Projections
    next_service_date = db.Column(db.Date)
    next_service_mileage = db.Column(db.Integer)
    
    # Additional Fields
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service_type = db.relationship('ServiceType', backref='services')
    reminders = db.relationship('ServiceReminder', backref='service', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Service, self).__init__(**kwargs)
        # Ensure intervals have default values
        if self.interval_months is None:
            if self.service_type and self.service_type.default_interval_months:
                self.interval_months = self.service_type.default_interval_months
            else:
                self.interval_months = 12  # Default to 12 months
        
        if self.interval_mileage is None:
            if self.service_type and self.service_type.default_interval_mileage:
                self.interval_mileage = self.service_type.default_interval_mileage
            else:
                self.interval_mileage = 10000  # Default to 10,000 KMs
    
    def update_schedule(self, current_mileage=None):
        """Update next service dates based on intervals"""
        # Date-based schedule
        if self.last_service_date and self.interval_months is not None:
            self.next_service_date = self.last_service_date + relativedelta(months=self.interval_months)
        else:
            self.next_service_date = None

        # Mileage-based schedule
        if self.last_service_mileage is not None and self.interval_mileage is not None:
            self.next_service_mileage = self.last_service_mileage + self.interval_mileage
        else:
            self.next_service_mileage = None

        # Create reminders only if next date is valid and we have a car
        if self.next_service_date and self.notify_days_before and self.car_id:
            self.create_reminders()

        return self

    
    def create_reminders(self):
        """Create reminders based on user preferences"""
        # Clear existing pending reminders
        ServiceReminder.query.filter_by(
            service_id=self.id,
            status='pending'
        ).delete()
        
        # Get the car with user loaded
        car = Car.query.get(self.car_id)
        if not car or not car.user:
            return  # Can't create reminders without a user
        
        # Get user's reminder preferences
        user = car.user
        reminder_days = user.reminder_days if user.reminder_days else [7, 3, 1]
        
        # Create new reminders
        for days in sorted(reminder_days, reverse=True):
            if days <= self.notify_days_before:
                ServiceReminder.create_reminder(self, days)
        
    def record_service(self, service_date, mileage, cost=None, notes=None):
        """Record a completed service and update schedule"""
        self.last_service_date = service_date
        self.last_service_mileage = mileage
        self.last_service_cost = cost
        self.last_service_notes = notes
        self.update_schedule()
        
        # Create service history entry
        history = ServiceHistory(
            car_id=self.car_id,
            service_type_id=self.service_type_id,
            service_date=service_date,
            mileage=mileage,
            cost=cost,
            notes=notes
        )
        db.session.add(history)
        return self


    def get_status(self, current_mileage=None):
        """Get current service status"""
        if not self.is_active:
            return 'inactive'

        today = datetime.now().date()
        status = 'upcoming'

        # Date-based logic
        if self.next_service_date:
            days_until = (self.next_service_date - today).days
            if days_until < 0:
                status = 'overdue'
            elif days_until <= self.notify_days_before:
                status = 'due_soon'

        # Mileage-based logic overrides date
        if current_mileage is not None and self.next_service_mileage is not None:
            miles_remaining = self.next_service_mileage - current_mileage
            if miles_remaining <= 0:
                status = 'overdue'
            elif miles_remaining <= 500:
                status = 'due_soon' if status != 'overdue' else 'overdue'

        return status
    
    

    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'car_id': self.car_id,
            'service_type': self.service_type.name,
            'interval_months': self.interval_months,
            'interval_mileage': self.interval_mileage,
            'last_service_date': self.last_service_date.isoformat() if self.last_service_date else None,
            'next_service_date': self.next_service_date.isoformat() if self.next_service_date else None,
            'status': self.get_status(self.car.current_mileage if self.car else None)
        }
    
    def calculate_next_service(self, current_mileage=None):
        """Calculate and return the next service status"""
        self.update_schedule(current_mileage=current_mileage)
        return self.get_status(current_mileage)

    def __repr__(self):
        return f'<Service {self.service_type.name} for Car {self.car_id}>'               


class ServiceHistory(db.Model):
    __tablename__ = 'service_history'
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    service_date = db.Column(db.Date, nullable=False)
    mileage = db.Column(db.Integer)
    total_cost = db.Column(db.Float)
    service_provider = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    car = db.relationship('Car', back_populates='service_history')
    user = db.relationship('User', back_populates='service_history')  # Add this
    service_items = db.relationship('ServiceHistoryItem', backref='history', cascade='all, delete-orphan')


class ServiceHistoryItem(db.Model):
    """Service Item model for each services"""
    id = db.Column(db.Integer, primary_key=True)
    history_id = db.Column(db.Integer, db.ForeignKey("service_history.id"), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey("service_types.id"), nullable=False)
    cost = db.Column(db.Float)

    # Relationships
    service_type = db.relationship('ServiceType')


class ServiceReminder(db.Model):
    """Model for service reminders"""
    __tablename__ = 'service_reminders'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False, index=True)
    reminder_type = db.Column(db.String(20), nullable=False)  # 'email', 'push', 'both'
    status = db.Column(db.String(20), default='pending', index=True)  # 'pending', 'sent', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def create_reminder(service, days_before):
        """Create a reminder for a service"""
        if service.next_service_date:
            reminder_date = datetime.combine(
                service.next_service_date - timedelta(days=days_before),
                datetime.min.time()
            )
            reminder = ServiceReminder(
                service_id=service.id,
                car_id=service.car_id,
                reminder_date=reminder_date,
                reminder_type='both',
                status='pending',
                created_at=datetime.utcnow()
            )
            db.session.add(reminder)
            db.session.commit()
            return reminder
        return None

    def update_status(self, new_status: str):
        """Update the status of the reminder and commit."""
        self.status = new_status
        db.session.commit()
        return self

    def send_notification(self, user, title, message, url=None, icon=None):
        """Send a push notification and update status based on result."""
        from push_notifications import PushNotificationService
        success = PushNotificationService.send_to_user(
            user=user,
            title=title,
            body=message,
            url=url,
            icon=icon
        )
        self.status = 'sent' if success else 'failed'
        db.session.commit()
        return success
