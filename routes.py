from flask import session, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from datetime import datetime, date
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from models import User, Car, Service, ServiceType, ServiceHistory
from forms import CarForm, ServiceForm, ServiceHistoryForm
import json

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True


@app.route('/')
def index():
    """Landing page for logged out users, dashboard for logged in users"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/dashboard')
@require_login
def dashboard():
    """Main dashboard showing service overview"""
    user_cars = Car.query.filter_by(user_id=current_user.id).all()
    
    # Get all services for user's cars
    all_services = []
    for car in user_cars:
        all_services.extend(car.services)
    
    # Categorize services
    overdue_services = [s for s in all_services if s.status == 'overdue']
    due_soon_services = [s for s in all_services if s.status == 'due_soon']
    upcoming_services = [s for s in all_services if s.status == 'upcoming']
    
    # Recent service history
    recent_history = ServiceHistory.query.join(Car).filter(
        Car.user_id == current_user.id
    ).order_by(ServiceHistory.service_date.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         user_cars=user_cars,
                         overdue_services=overdue_services,
                         due_soon_services=due_soon_services,
                         upcoming_services=upcoming_services,
                         recent_history=recent_history)


@app.route('/cars')
@require_login
def cars():
    """List all user's cars"""
    user_cars = Car.query.filter_by(user_id=current_user.id).all()
    return render_template('cars.html', cars=user_cars)


@app.route('/cars/add', methods=['GET', 'POST'])
@require_login
def add_car():
    """Add a new car"""
    form = CarForm()
    if form.validate_on_submit():
        car = Car(
            user_id=current_user.id,
            make=form.make.data,
            model=form.model.data,
            year=form.year.data,
            registration_number=form.registration_number.data,
            color=form.color.data,
            current_mileage=form.current_mileage.data
        )
        db.session.add(car)
        db.session.commit()
        flash('Car added successfully!', 'success')
        return redirect(url_for('cars'))
    
    return render_template('car_form.html', form=form, title='Add Car')


@app.route('/cars/<int:car_id>/edit', methods=['GET', 'POST'])
@require_login
def edit_car(car_id):
    """Edit an existing car"""
    car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
    form = CarForm(obj=car)
    
    if form.validate_on_submit():
        form.populate_obj(car)
        car.updated_at = datetime.now()
        db.session.commit()
        flash('Car updated successfully!', 'success')
        return redirect(url_for('cars'))
    
    return render_template('car_form.html', form=form, title='Edit Car', car=car)


@app.route('/cars/<int:car_id>/delete', methods=['POST'])
@require_login
def delete_car(car_id):
    """Delete a car"""
    car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
    db.session.delete(car)
    db.session.commit()
    flash('Car deleted successfully!', 'success')
    return redirect(url_for('cars'))


@app.route('/cars/<int:car_id>/services')
@require_login
def car_services(car_id):
    """List services for a specific car"""
    car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
    services = Service.query.filter_by(car_id=car_id).all()
    return render_template('services.html', car=car, services=services)


@app.route('/cars/<int:car_id>/services/add', methods=['GET', 'POST'])
@require_login
def add_service(car_id):
    """Add a new service schedule for a car"""
    car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
    form = ServiceForm()
    
    if form.validate_on_submit():
        service = Service(
            car_id=car_id,
            service_type_id=form.service_type_id.data,
            interval_months=form.interval_months.data,
            interval_mileage=form.interval_mileage.data,
            last_service_date=form.last_service_date.data,
            last_service_mileage=form.last_service_mileage.data,
            notify_days_before=form.notify_days_before.data
        )
        service.calculate_next_service()
        db.session.add(service)
        db.session.commit()
        flash('Service schedule added successfully!', 'success')
        return redirect(url_for('car_services', car_id=car_id))
    
    return render_template('service_form.html', form=form, title='Add Service Schedule', car=car)


@app.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@require_login
def edit_service(service_id):
    """Edit a service schedule"""
    service = Service.query.join(Car).filter(
        Service.id == service_id,
        Car.user_id == current_user.id
    ).first_or_404()
    
    form = ServiceForm(obj=service)
    
    if form.validate_on_submit():
        form.populate_obj(service)
        service.calculate_next_service()
        service.updated_at = datetime.now()
        db.session.commit()
        flash('Service schedule updated successfully!', 'success')
        return redirect(url_for('car_services', car_id=service.car_id))
    
    return render_template('service_form.html', form=form, title='Edit Service Schedule', car=service.car)


@app.route('/services/<int:service_id>/delete', methods=['POST'])
@require_login
def delete_service(service_id):
    """Delete a service schedule"""
    service = Service.query.join(Car).filter(
        Service.id == service_id,
        Car.user_id == current_user.id
    ).first_or_404()
    
    car_id = service.car_id
    db.session.delete(service)
    db.session.commit()
    flash('Service schedule deleted successfully!', 'success')
    return redirect(url_for('car_services', car_id=car_id))


@app.route('/history')
@require_login
def history():
    """View service history"""
    service_history = ServiceHistory.query.join(Car).filter(
        Car.user_id == current_user.id
    ).order_by(ServiceHistory.service_date.desc()).all()
    
    return render_template('history.html', service_history=service_history)


@app.route('/cars/<int:car_id>/history/add', methods=['GET', 'POST'])
@require_login
def add_service_history(car_id):
    """Add service history entry"""
    car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
    form = ServiceHistoryForm()
    
    if form.validate_on_submit():
        history = ServiceHistory(
            car_id=car_id,
            service_type_id=form.service_type_id.data,
            service_date=form.service_date.data,
            mileage=form.mileage.data,
            cost=form.cost.data,
            notes=form.notes.data,
            service_provider=form.service_provider.data
        )
        db.session.add(history)
        
        # Update related service schedule if exists
        service = Service.query.filter_by(
            car_id=car_id, 
            service_type_id=form.service_type_id.data
        ).first()
        if service:
            service.last_service_date = form.service_date.data
            service.last_service_mileage = form.mileage.data
            service.calculate_next_service()
            service.notification_sent = False  # Reset notification flag
        
        # Update car mileage if provided
        if form.mileage.data and form.mileage.data > car.current_mileage:
            car.current_mileage = form.mileage.data
        
        db.session.commit()
        flash('Service history added successfully!', 'success')
        return redirect(url_for('history'))
    
    return render_template('service_form.html', form=form, title='Add Service History', car=car)


@app.route('/api/push-subscription', methods=['POST'])
@require_login
def save_push_subscription():
    """Save push notification subscription"""
    subscription = request.get_json()
    current_user.push_subscription = json.dumps(subscription)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/service-worker.js')
def service_worker():
    """Serve the service worker file"""
    return app.send_static_file('sw.js')


# Initialize default service types
def create_default_service_types():
    """Create default service types if they don't exist"""
    default_types = [
        {'name': 'Oil Change', 'description': 'Engine oil and filter replacement', 'default_interval_months': 6, 'default_interval_mileage': 5000},
        {'name': 'Tire Rotation', 'description': 'Rotate tires for even wear', 'default_interval_months': 6, 'default_interval_mileage': 7500},
        {'name': 'Brake Inspection', 'description': 'Check brake pads, rotors, and fluid', 'default_interval_months': 12, 'default_interval_mileage': 12000},
        {'name': 'Air Filter', 'description': 'Replace engine air filter', 'default_interval_months': 12, 'default_interval_mileage': 12000},
        {'name': 'Transmission Service', 'description': 'Transmission fluid and filter change', 'default_interval_months': 24, 'default_interval_mileage': 30000},
        {'name': 'Coolant Service', 'description': 'Coolant flush and replacement', 'default_interval_months': 24, 'default_interval_mileage': 30000},
        {'name': 'Spark Plugs', 'description': 'Replace spark plugs', 'default_interval_months': 24, 'default_interval_mileage': 30000},
        {'name': 'Timing Belt', 'description': 'Replace timing belt', 'default_interval_months': 60, 'default_interval_mileage': 60000},
    ]
    
    for type_data in default_types:
        if not ServiceType.query.filter_by(name=type_data['name']).first():
            service_type = ServiceType(**type_data)
            db.session.add(service_type)
    
    db.session.commit()

# Initialize service types when the app starts
with app.app_context():
    create_default_service_types()
