from datetime import datetime, timedelta
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint


# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    push_subscription = db.Column(db.Text, nullable=True)  # JSON string for push notifications

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime,
                           default=datetime.now,
                           onupdate=datetime.now)

    # Relationships
    cars = db.relationship('Car', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email or "User"


# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)


class Car(db.Model):
    __tablename__ = 'cars'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    registration_number = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(30), nullable=True)
    current_mileage = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    services = db.relationship('Service', backref='car', lazy=True, cascade='all, delete-orphan')
    service_history = db.relationship('ServiceHistory', backref='car', lazy=True, cascade='all, delete-orphan')

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


class ServiceType(db.Model):
    __tablename__ = 'service_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    default_interval_months = db.Column(db.Integer, default=6)
    default_interval_mileage = db.Column(db.Integer, default=5000)
    
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    services = db.relationship('Service', backref='service_type', lazy=True)
    service_history = db.relationship('ServiceHistory', backref='service_type', lazy=True)

    def __str__(self):
        return self.name


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'), nullable=False)
    
    # Service intervals
    interval_months = db.Column(db.Integer, nullable=True)
    interval_mileage = db.Column(db.Integer, nullable=True)
    
    # Last service details
    last_service_date = db.Column(db.Date, nullable=True)
    last_service_mileage = db.Column(db.Integer, nullable=True)
    
    # Next service calculation
    next_service_date = db.Column(db.Date, nullable=True)
    next_service_mileage = db.Column(db.Integer, nullable=True)
    
    # Notification settings
    notify_days_before = db.Column(db.Integer, default=7)
    notification_sent = db.Column(db.Boolean, default=False)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def calculate_next_service(self):
        """Calculate next service date and mileage based on intervals"""
        if self.last_service_date and self.interval_months:
            self.next_service_date = self.last_service_date + timedelta(days=self.interval_months * 30)
        
        if self.last_service_mileage and self.interval_mileage:
            self.next_service_mileage = self.last_service_mileage + self.interval_mileage

    def is_due(self):
        """Check if service is due based on date or mileage"""
        today = datetime.now().date()
        current_mileage = self.car.current_mileage
        
        # Check date-based due
        if self.next_service_date and self.next_service_date <= today:
            return True
            
        # Check mileage-based due
        if self.next_service_mileage and current_mileage >= self.next_service_mileage:
            return True
            
        return False

    def is_due_soon(self):
        """Check if service is due within notification period"""
        today = datetime.now().date()
        current_mileage = self.car.current_mileage
        
        # Check date-based due soon
        if self.next_service_date:
            due_date = self.next_service_date - timedelta(days=self.notify_days_before)
            if today >= due_date:
                return True
        
        # Check mileage-based due soon (within 200 miles of due mileage)
        if self.next_service_mileage and current_mileage >= (self.next_service_mileage - 200):
            return True
            
        return False

    @property
    def status(self):
        """Get current service status"""
        if self.is_due():
            return 'overdue'
        elif self.is_due_soon():
            return 'due_soon'
        else:
            return 'upcoming'


class ServiceHistory(db.Model):
    __tablename__ = 'service_history'
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'), nullable=False)
    
    service_date = db.Column(db.Date, nullable=False)
    mileage = db.Column(db.Integer, nullable=True)
    cost = db.Column(db.Numeric(10, 2), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    service_provider = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __str__(self):
        return f"{self.service_type.name} - {self.service_date}"
