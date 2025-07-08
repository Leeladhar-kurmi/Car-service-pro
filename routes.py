from flask import session, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_login import current_user, login_required, login_user, logout_user
from datetime import datetime, timedelta, timezone
from models import User, Car, Service, ServiceType, ServiceHistory, ServiceReminder, ServiceHistoryItem
from forms import CarForm, ServiceForm, RegistrationForm, ResetPasswordForm, UpdateEmailForm
from push_notifications import PushNotificationService
import json
import uuid
import time
import traceback
from flask_mail import Message
import pyotp
from sqlalchemy import func, extract
from collections import defaultdict
import random
# from scheduler import check_service_reminders

# NOTE: If you see import errors for flask_mail, pyotp, sqlalchemy, install them with:
# pip install flask-mail pyotp sqlalchemy

def register_routes(app, db, mail):
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

    # Make session permanent
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    def generate_otp():
        """Generate a 6-digit OTP"""
        return str(pyotp.random.randint(0, 999999)).zfill(6)
        

    def send_otp_email(email, otp):
        """Send OTP via email with improved error handling"""
        try:
            sender = app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')
            if not sender:
                # app.logger.error("No sender email configured in app config")
                return False

            # Debug logging before sending
            # app.logger.debug(f"Email configuration:")
            # app.logger.debug(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
            # app.logger.debug(f"MAIL_PORT: {app.config.get('MAIL_PORT')} (type: {type(app.config.get('MAIL_PORT'))}")
            # app.logger.debug(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
            # app.logger.debug(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
            
            msg = Message(
                subject='Your CarServicePro Registration OTP',
                sender=sender,
                recipients=[email]
            )
            msg.body = f"""
            Hello!

            Your OTP for CarServicePro registration is: {otp}

            This OTP is valid for 5 minutes.

            If you didn't request this OTP, please ignore this email.

            Best regards,
            CarServicePro Team
            """
            
            mail.send(msg)
            # app.logger.debug("Email sent successfully")
            return True
            
        except Exception as e:
            # app.logger.error(f"Error sending email: {str(e)}")
            # app.logger.error(traceback.format_exc())
            return False  
        
    @app.route('/')
    def index():
        """Landing page for logged out users, dashboard for logged in users"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('landing.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Handle user registration with OTP verification"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        # Clear session state on initial GET
        if request.method == 'GET':
            session.pop('otp_verified', None)
            session.pop('otp', None)
            session.pop('otp_email', None)
            session.pop('otp_time', None)

        form = RegistrationForm()
        show_otp = 'otp' in session and not session.get('otp_verified')

        if form.validate_on_submit():
            action = request.form.get('action')
            email = form.email.data.strip()
            otp_input = form.otp.data.strip() if form.otp.data else None

            app.logger.debug(f"Form submitted with action: {action}")
            app.logger.debug(f"Email: {email}, Session state: {dict((k, v) for k, v in session.items() if 'otp' in k or k == 'otp_verified')}")

            # STEP 3: Complete Registration
            if action == 'complete_registration' and session.get('otp_verified'):
                if session.get('otp_email') != email:
                    flash("Email mismatch. Please verify OTP again.", 'danger')
                    return render_template('register.html', form=form, show_otp=False)

                try:
                    # Create and save user
                    user = User(
                        id=str(uuid.uuid4()),
                        email = email,
                        first_name = session.get('first_name'),
                        last_name = session.get('last_name'),
                    )
                    user.set_password(form.password.data)
                    db.session.add(user)
                    db.session.commit()

                    # Clear session
                    session.pop('otp_verified', None)
                    session.pop('otp', None)
                    session.pop('otp_email', None)
                    session.pop('first_name', None)
                    session.pop('last_name', None)
                    session.pop('otp_time', None)

                    flash('Registration successful! Please log in.', 'success')
                    return redirect(url_for('login'))

                except Exception as e:
                    db.session.rollback()
                    # app.logger.error(f"Database error: {e}")
                    flash('An error occurred during registration. Please try again.', 'danger')
                    return render_template('register.html', form=form, show_otp=False)

            # STEP 2: Verify OTP
            elif action == 'verify_otp':
                if not (session.get('otp') and session.get('otp_email') == email):
                    flash('Please request a new OTP.', 'warning')
                    return render_template('register.html', form=form, show_otp=True)

                if time.time() - session.get('otp_time', 0) > 300:  # OTP expires in 5 minutes
                    flash('OTP expired. Please request a new one.', 'warning')
                    session.pop('otp', None)
                    session.pop('otp_time', None)
                    return render_template('register.html', form=form, show_otp=False)

                if otp_input == session.get('otp'):
                    session['otp_verified'] = True
                    flash('OTP verified successfully! Please set your password.', 'success')
                    show_otp = False
                else:
                    flash('Invalid OTP. Please try again.', 'danger')
                    show_otp = True

                return render_template('register.html', form=form, show_otp=show_otp)

            # STEP 1: Send OTP
            elif action == 'send_otp':
                if User.query.filter_by(email=email).first():
                    flash('Email is already registered.', 'danger')
                    return render_template('register.html', form=form, show_otp=False)

                # Cooldown check (e.g., 60 seconds)
                last_otp_time = session.get('otp_time')
                if last_otp_time and time.time() - last_otp_time < 60:
                    remaining = int(60 - (time.time() - last_otp_time))
                    flash(f'Please wait {remaining} seconds before requesting another OTP.', 'warning')
                    return render_template('register.html', form=form, show_otp=True)

                otp = generate_otp()
                if send_otp_email(email, otp):
                    session['otp'] = otp
                    session['otp_email'] = email
                    session['first_name'] = form.first_name.data
                    session['last_name'] = form.last_name.data
                    session['otp_time'] = time.time()
                    session.pop('otp_verified', None)  # reset verification if resending OTP

                    flash('OTP sent to your email. It will expire in 5 minutes.', 'info')
                    show_otp = True
                else:
                    flash('Failed to send OTP. Please try again.', 'danger')
                    show_otp = False

                return render_template('register.html', form=form, show_otp=show_otp)

        # Default rendering
        return render_template('register.html', form=form, show_otp=show_otp)
    
    @app.route('/reset-password', methods=['GET', 'POST'])
    def reset_password():
        form = ResetPasswordForm()

        # Clear session on GET
        if request.method == "GET":
            session.pop('reset_email', None)
            session.pop('reset_otp', None)
            session.pop('otp_sent', None)
            session.pop('otp_verified', None)
            session.pop('otp_created_at', None)

        # Pre-fill email from session if needed
        if not form.email.data and session.get('reset_email'):
            form.email.data = session['reset_email']

        if form.validate_on_submit():
            action = request.form.get('action')

            if action == "send_otp":
                user = User.query.filter_by(email=form.email.data).first()
                if not user:
                    flash("Email not registered.", "danger")
                else:
                    otp_created_at = session.get('otp_created_at')
                    if otp_created_at:
                        time_since_otp = datetime.now(timezone.utc) - otp_created_at
                        if time_since_otp < timedelta(seconds = 60):
                            flash(f"Please {60 - int(time_since_otp.total_seconds())} Seconds before requesting another OTP.", "warning")
                    otp = generate_otp()
                    
                    session['reset_email'] = form.email.data
                    session['reset_otp'] = otp
                    session['otp_sent'] = True
                    session['otp_created_at'] = datetime.now(timezone.utc)
                    send_otp_email(form.email.data, otp)
                    flash("OTP sent to your email. It will expire in 5 minutes.", "info")

            elif action == "verify_otp":
                if not session.get('otp_sent'):
                    flash("OTP not sent yet.", "warning")
                elif datetime.now(timezone.utc) - session.get('otp_created_at') > timedelta(minutes=5):
                    flash("OTP has expired. Please request a new one.", "danger")
                    session.pop('reset_otp', None)
                    session.pop('otp_sent', None)
                elif form.otp.data == session.get('reset_otp'):
                    session['otp_verified'] = True
                    flash("OTP verified! Now reset your password.", "success")
                else:
                    flash("Invalid OTP.", "danger")

            elif action == "reset_password":
                if not session.get('otp_verified'):
                    flash("OTP verification required first.", "warning")
                else:
                    user = User.query.filter_by(email=session.get('reset_email')).first()
                    if user:
                        user.set_password(form.password.data)
                        db.session.commit()
                        flash("Password updated successfully! You can now log in.", "success")
                        session.clear()  # Clear all session variables
                        return redirect(url_for('login'))
                    else:
                        flash("Error updating password.", "danger")

        return render_template("reset_password.html", form=form)
    
    @app.route('/settings/email', methods=['GET', 'POST'])
    @login_required
    def update_email():
        form = UpdateEmailForm()

        # Only clear session on the first GET visit
        if request.method == 'GET' and not session.get('email_otp_sent'):
            session.pop('pending_new_email', None)
            session.pop('email_otp', None)
            session.pop('email_otp_sent', None)
            session.pop('email_otp_verified', None)
            session.pop('email_otp_created_at', None)

        # Pre-fill new_email if stored
        if not form.new_email.data and session.get('pending_new_email'):
            form.new_email.data = session['pending_new_email']

        print("Form validated:", form.validate_on_submit())
        print("Form errors:", form.errors)
        print("Request method:", request.method)
        print("Action received:", request.form.get('action'))
        print("New email entered:", form.new_email.data)

        if form.validate_on_submit():
            action = request.form.get('action')

            # Step 1: Send OTP
            if action == 'send_otp':
                new_email = form.new_email.data.strip()

                if new_email == current_user.email:
                    flash("New email cannot be the same as your current email.", "warning")
                    return redirect(url_for('update_email'))

                # Check cooldown
                last_sent = session.get('email_otp_created_at')
                if last_sent:
                    last_sent_dt = datetime.fromisoformat(last_sent)
                    time_diff = datetime.now(timezone.utc) - last_sent_dt
                    if time_diff < timedelta(seconds=60):
                        wait_time = 60 - int(time_diff.total_seconds())
                        flash(f"Please wait {wait_time} seconds before requesting another OTP.", "warning")
                        return redirect(url_for('update_email'))

                otp = str(random.randint(100000, 999999))

                # Send OTP using working function
                if send_otp_email(new_email, otp):
                    session['pending_new_email'] = new_email
                    session['email_otp'] = otp
                    session['email_otp_sent'] = True
                    session['email_otp_verified'] = False
                    session['email_otp_created_at'] = datetime.now(timezone.utc).isoformat()
                    flash("OTP sent to your new email address. It will expire in 5 minutes.", "info")
                else:
                    flash("Failed to send email. Please try again later.", "danger")

                return redirect(url_for('update_email'))

            # Step 2: Verify OTP
            elif action == 'verify_otp':
                entered_otp = form.otp.data.strip()
                saved_otp = session.get('email_otp')
                sent_time = session.get('email_otp_created_at')

                if not saved_otp or not sent_time:
                    flash("No OTP has been sent yet.", "warning")
                    return redirect(url_for('update_email'))

                if datetime.now(timezone.utc) - datetime.fromisoformat(sent_time) > timedelta(minutes=5):
                    flash("OTP has expired. Please request a new one.", "danger")
                    session.pop('email_otp', None)
                    session.pop('email_otp_sent', None)
                    return redirect(url_for('update_email'))

                if entered_otp != saved_otp:
                    flash("Invalid OTP. Please try again.", "danger")
                    return redirect(url_for('update_email'))

                # OTP is valid → update email
                new_email = session.get('pending_new_email')
                current_user.email = new_email
                db.session.commit()

                session.clear()
                flash("Email updated successfully. Please log in again.", "success")
                logout_user()
                return redirect(url_for('login'))

        return render_template("settings_email.html", form=form)

    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle user login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Logged in successfully!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            
            flash('Invalid email or password.', 'danger')
        
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """Logout route"""
        logout_user()
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main dashboard showing service overview"""
        user_cars = Car.query.filter_by(user_id=current_user.id).all()
        
        # Get all services for user's cars
        all_services = []
        for car in user_cars:
            all_services.extend(car.services)
        
        # Categorize services
        overdue_services = [s for s in all_services if s.calculate_next_service(s.car.current_mileage) == 'overdue']
        due_soon_services = [s for s in all_services if s.calculate_next_service(s.car.current_mileage) == 'due_soon']
        upcoming_services = [s for s in all_services if s.calculate_next_service(s.car.current_mileage) == 'upcoming']
        
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
    @login_required
    def cars():
        """List all user's cars"""
        cars = Car.query.filter_by(user_id=current_user.id).all()

        total_overdue = 0
        total_due_soon = 0
        total_upcoming = 0

        for car in cars:
            car_overdue = 0
            car_due_soon = 0
            car_upcoming = 0

            for service in car.services:
                status = service.calculate_next_service(car.current_mileage)

                if status == "overdue":
                    car_overdue += 1
                    total_overdue += 1
                elif status == "due_soon":
                    car_due_soon += 1
                    total_due_soon += 1
                elif status == "upcoming":
                    car_upcoming += 1
                    total_upcoming += 1

            # Assign to temp dynamic attributes
            car._overdue_count = car_overdue
            car._due_soon_count = car_due_soon
            car._upcoming_count = car_upcoming

        return render_template(
            'cars.html',
            cars=cars,
            overdue_count=total_overdue,
            due_soon_count=total_due_soon,
            upcoming_count=total_upcoming,
            datetime=datetime
        )

    
    @app.route('/cars/add', methods=['GET', 'POST'])
    @login_required
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
                current_mileage=form.current_mileage.data,
                insurance_company=form.insurance_company.data,
                expiry_date=form.expiry_date.data,
            )
            db.session.add(car)
            db.session.commit()
            flash('Car added successfully!', 'success')
            return redirect(url_for('cars'))
        
        return render_template('car_form.html', form=form, title='Add Vehicle')

    @app.route('/cars/<int:car_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_car(car_id):
        """Edit an existing car"""
        car = Car.query.get_or_404(car_id)
        form = CarForm(obj=car, car = car)
        
        if form.validate_on_submit():
            form.populate_obj(car)
            car.updated_at = datetime.now()
            db.session.commit()
            flash('Car updated successfully!', 'success')
            return redirect(url_for('cars'))
        
        return render_template('car_form.html', form=form, title='Edit Car', car=car)

    @app.route('/cars/<int:car_id>/delete', methods=['POST'])
    @login_required
    def delete_car(car_id):
        """Delete a car"""
        car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
        db.session.delete(car)
        db.session.commit()
        flash('Car deleted successfully!', 'success')
        return redirect(url_for('cars'))

    @app.route('/cars/<int:car_id>/services')
    @login_required
    def car_services(car_id):
        """List services for a specific car"""
        car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
        services = Service.query.filter_by(car_id=car_id).all()
        for service in services:
            service.status = service.get_status(car.current_mileage)
        return render_template('services/services.html', car=car, services=services)

    @app.route('/cars/<int:car_id>/services/add', methods=['GET', 'POST'])
    @login_required
    def add_service(car_id):
        """Add or update a service schedule for a car"""
        car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
        form = ServiceForm()
        
        form.service_type_ids.choices = [(stype.id, stype.name) for stype in ServiceType.query.all()]
        service_type_intervals ={m.id:{"mileage": m.default_interval_mileage or 0,
                                       "months":m.default_interval_months or 0 }
                                    for m in ServiceType.query.all()}

        if form.validate_on_submit():
            for service_type_id in form.service_type_ids.data:
                service_type = ServiceType.query.get(service_type_id)

                # Dynamic field names from JS
                mileage_key = f'interval_mileage_{service_type_id}'
                months_key = f'interval_months_{service_type_id}'

                # Safely get user-edited values from submitted form
                try:
                    interval_mileage = int(request.form.get(mileage_key, 13000))
                except (ValueError, TypeError):
                    interval_mileage = 13000

                try:
                    interval_months = int(request.form.get(months_key, 13))
                except (ValueError, TypeError):
                    interval_months = 13

                # Check if a service already exists for this car and service_type
                existing_service = Service.query.filter_by(car_id=car_id, service_type_id=service_type_id).first()
                if existing_service:
                    # Update the existing service
                    existing_service.interval_months = interval_months
                    existing_service.interval_mileage = interval_mileage
                    existing_service.last_service_date = form.last_service_date.data
                    existing_service.last_service_mileage = form.last_service_mileage.data
                    existing_service.notify_days_before = form.notify_days_before.data
                    existing_service.updated_at = datetime.now()
                    existing_service.update_schedule()
                else:
                    # Create a new service
                    service = Service(
                        car_id=car_id,
                        service_type_id=service_type_id,
                        interval_months=interval_months,
                        interval_mileage=interval_mileage,
                        last_service_date=form.last_service_date.data,
                        last_service_mileage=form.last_service_mileage.data,
                        notify_days_before=form.notify_days_before.data
                    )
                    db.session.add(service)
            db.session.commit()
            flash('Service schedules added or updated successfully!', 'success')
            return redirect(url_for('car_services', car_id=car_id))
        
        return render_template('services/service_form.html', form=form, title='Add Service Schedule', car=car, service_type_intervals = service_type_intervals)

    @app.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_service(service_id):
        service = Service.query.join(Car).filter(
            Service.id == service_id,
            Car.user_id == current_user.id
        ).first_or_404()

        # Service type interval defaults
        service_type_intervals = {
            st.id: {
                "mileage": st.default_interval_mileage or 0,
                "months": st.default_interval_months or 0
            }
            for st in ServiceType.query.all()
        }

        form = ServiceForm()
        form.service_type_ids.choices = [(st.id, st.name) for st in ServiceType.query.order_by(ServiceType.name)]

        if request.method == 'GET':
            # Pre-fill form
            form.service_type_ids.data = [service.service_type_id]
            form.interval_months.data = service.interval_months
            form.interval_mileage.data = service.interval_mileage
            form.last_service_date.data = service.last_service_date
            form.last_service_mileage.data = service.last_service_mileage
            form.notify_days_before.data = service.notify_days_before

        if form.validate_on_submit():
            # Pick the first (only) selected service type
            selected_id = form.service_type_ids.data[0]
            service.service_type_id = selected_id

            # Get dynamic interval fields from request.form
            try:
                service.interval_mileage = int(request.form.get(f'interval_mileage_{selected_id}', 0))
            except (ValueError, TypeError):
                service.interval_mileage = 0

            try:
                service.interval_months = int(request.form.get(f'interval_months_{selected_id}', 0))
            except (ValueError, TypeError):
                service.interval_months = 0

            service.last_service_date = form.last_service_date.data
            service.last_service_mileage = form.last_service_mileage.data
            service.notify_days_before = form.notify_days_before.data
            service.updated_at = datetime.now()

            service.calculate_next_service()

            db.session.commit()
            flash('Service schedule updated successfully!', 'success')
            return redirect(url_for('car_services', car_id=service.car_id))

        return render_template(
            'services/service_form.html',
            form=form,
            title='Edit Service Schedule',
            car=service.car,
            service_type_intervals=service_type_intervals
        )

    @app.route('/services/<int:service_id>/delete', methods=['POST'])
    @login_required
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
    @login_required
    def history():
        """View service history"""
        # Start with base query
        query = ServiceHistory.query.join(Car).filter(Car.user_id == current_user.id)
        
        # Apply car filter
        car_id = request.args.get('car')
        if car_id:
            query = query.filter(Car.id == car_id)
        
        # Apply service type filter
        service_types = ServiceType.query.order_by(ServiceType.name).all()

        # Also get filtered service history or data if needed
        selected_service_type = request.args.get('service_type')

        total_cost = db.session.query(func.sum(ServiceHistory.total_cost))\
            .filter(ServiceHistory.user_id == current_user.id)\
            .scalar()
        
        if selected_service_type:
            # Filter logic, example:
            service_history = ServiceHistory.query\
                .join(ServiceHistory.service_items)\
                .filter(ServiceHistoryItem.service_type_id == selected_service_type)\
                .all()
        else:
            service_history = ServiceHistory.query.all()
        
        # Apply year filter
        year = request.args.get('year')
        if year:
            # Extract year from service_date
            query = query.filter(db.extract('year', ServiceHistory.service_date) == int(year))
        
        # Get results ordered by date
        service_history = query.order_by(ServiceHistory.service_date.desc()).all()
        year=datetime.now().year
        
        return render_template('services/history.html', total_cost=total_cost, service_history=service_history,year=year, service_types=service_types)

    @app.route('/cars/<int:car_id>/history/add', methods=['GET', 'POST'])
    @login_required
    def add_service_history(car_id):
        car = Car.query.filter_by(id=car_id, user_id=current_user.id).first_or_404()
        form = ServiceForm()

        # Populate choices for multi-checkbox field
        form.service_type_ids.choices = [(stype.id, stype.name) for stype in ServiceType.query.all()]

        # Pass default intervals to template
        service_type_intervals = {
            st.id: {
                "mileage": st.default_interval_mileage or 0,
                "months": st.default_interval_months or 0
            }
            for st in ServiceType.query.all()
        }

        if form.validate_on_submit():
            total_cost = 0.0
            service_items = []

            for service_type_id in form.service_type_ids.data:
                cost_key = f"service_cost_{service_type_id}"
                try:
                    cost = float(request.form.get(cost_key, 0))
                except (TypeError, ValueError):
                    cost = 0.0
                total_cost += cost

                item = ServiceHistoryItem(
                    service_type_id=service_type_id,
                    cost=cost
                )
                service_items.append(item)

                # Update the corresponding Service schedule
                service = Service.query.filter_by(car_id=car.id, service_type_id=service_type_id).first()
                if service:
                    service.last_service_date = form.last_service_date.data
                    service.last_service_mileage = form.last_service_mileage.data
                    service.last_service_cost = cost
                    service.last_service_notes = form.notes.data
                    service.update_schedule()
                    # Set status to upcoming by recalculating
                    # Optionally, delete the old schedule and create a new one if needed

            # Create main history record
            history = ServiceHistory(
                car_id=car.id,
                user_id=current_user.id,
                service_date=form.last_service_date.data,
                mileage=form.last_service_mileage.data,
                total_cost=total_cost,
                service_provider=form.service_provider.data,
                notes=form.notes.data
            )

            # Associate items with the history
            history.service_items.extend(service_items)

            db.session.add(history)
            db.session.commit()

            flash('Service history recorded and schedule updated successfully.', 'success')
            return redirect(url_for('car_services', car_id=car.id))

        return render_template(
            'services/service_form.html',
            form=form,
            title='Add Service Record',
            car=car,
            service_type_intervals=service_type_intervals
        )

    @app.route('/vapid-public-key')
    def vapid_public_key():
        """Endpoint to get VAPID public key"""
        return jsonify({
            'key': app.config['VAPID_PUBLIC_KEY']
        })

    @app.route('/api/push-subscription', methods=['POST', 'DELETE'])
    @login_required
    def handle_push_subscription():
        """Handle push notification subscription changes"""
        if request.method == 'POST':
            # Save subscription
            subscription = request.get_json()
            if not subscription:
                return jsonify({'error': 'Invalid data'}), 400
                
            current_user.push_subscription = json.dumps(subscription)
            db.session.commit()
            return jsonify({'success': True})
            
        elif request.method == 'DELETE':
            # Remove subscription
            data = request.get_json()
            if not data or not data.get('endpoint'):
                return jsonify({'error': 'Endpoint required'}), 400
                
            if current_user.push_subscription:
                try:
                    sub_data = json.loads(current_user.push_subscription)
                    if sub_data.get('endpoint') == data['endpoint']:
                        current_user.push_subscription = None
                        db.session.commit()
                except json.JSONDecodeError:
                    pass
                    
            return jsonify({'success': True})

    @app.route('/api/test-notification', methods=['POST'])
    @login_required
    def send_test_notification():
        """Send a test push notification"""
        if PushNotificationService.send_test_notification(current_user):
            return jsonify({'success': True})
        return jsonify({'error': 'Failed to send notification'}), 500
    
    @app.route('/service-worker')
    def serve_sw():
        return send_from_directory('static', 'js/service-worker.js', mimetype='application/javascript')


    @app.route('/settings', methods=['GET'])
    @login_required
    def settings():
        """User settings page"""
        return render_template('settings.html', vapid_public_key=app.config['VAPID_PUBLIC_KEY'])

    @app.route('/settings/save', methods=['POST'])
    @login_required
    def save_settings():
        """Save user notification preferences"""
        reminder_type = request.form.get('reminder_type')
        reminder_days = request.form.getlist('reminder_days[]')
        
        # Update user preferences
        current_user.reminder_type = reminder_type
        current_user.reminder_days = [int(days) for days in reminder_days]
        db.session.commit()
        
        # Update existing reminders
        services = Service.query.join(Car).filter(Car.user_id == current_user.id).all()
        for service in services:
            # Cancel existing reminders
            for reminder in service.reminders:
                if reminder.status == 'pending':
                    reminder.status = 'cancelled'
            
            # Create new reminders based on updated preferences
            for days in current_user.reminder_days:
                ServiceReminder.create_reminder(service, days)
        
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))


    # Initialize default service types
    with app.app_context():
        create_default_service_types()

    
    # Analytics Page

    @app.route('/analytics')
    @login_required
    def analytics():

        def generate_color_list(n):
            """Generate a list of n distinct pastel hex colors."""
            colors = []
            for _ in range(n):
                hue = random.randint(0, 360)
                saturation = 70 + random.randint(0, 20)
                lightness = 60 + random.randint(0, 20)
                color = f'hsl({hue}, {saturation}%, {lightness}%)'
                colors.append(color)
            return colors
        
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', None, type=int)

        cars = Car.query.filter_by(user_id=current_user.id).all()
        car_ids = [car.id for car in cars]

        # Cost by Car
        cost_by_car = {
            f"{car.make} {car.model}": car.total_service_cost() or 0
            for car in cars
        }

        # Monthly Trends (initialize all months)
        month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_counts = {m: 0 for m in month_labels}
        monthly_costs = {m: 0.0 for m in month_labels}

        query = db.session.query(ServiceHistory).filter(
            ServiceHistory.user_id == current_user.id,
            extract('year', ServiceHistory.service_date) == year
        )
        if month:
            query = query.filter(extract('month', ServiceHistory.service_date) == month)

        for record in query.all():
            month_key = record.service_date.strftime('%b')
            monthly_counts[month_key] += 1
            monthly_costs[month_key] += record.total_cost or 0

        # Service Type Distribution
        type_distribution = defaultdict(int)
        type_costs = defaultdict(float)

        items = db.session.query(ServiceHistoryItem, ServiceType).join(ServiceType).join(ServiceHistory).filter(
            ServiceHistory.user_id == current_user.id
        ).all()

        for item, s_type in items:
            type_distribution[s_type.name] += 1
            type_costs[s_type.name] += item.cost or 0

        today = datetime.today()
        next_30_days = today + timedelta(days=30)

        # Upcoming Service Reminders
        upcoming_services = ServiceReminder.query.filter(
            ServiceReminder.car_id.in_(car_ids),
            ServiceReminder.status.in_(['pending', 'due_soon']),
            ServiceReminder.reminder_date >= today,
            ServiceReminder.reminder_date <= next_30_days
        ).order_by(ServiceReminder.reminder_date.asc()).all()

        # Prepare reminder_data for clean use in template
        reminder_data = []
        for r in upcoming_services:
            car = Car.query.get(r.car_id)
            service = Service.query.get(r.service_id)
            if car and service:
                reminder_data.append({
                    'car_name': f"{car.make} {car.model}",
                    'service_type': service.service_type.name,
                    'next_date': r.reminder_date.strftime('%b %d') if r.reminder_date else 'N/A'
                })

        # Prepare chart data
        chart_data = {
            'cost_by_car': {
                'labels': list(cost_by_car.keys()),
                'data': list(cost_by_car.values()),
                'colors': [f'#{random.randint(0, 0xFFFFFF):06x}' for _ in cost_by_car]
            },
            'monthly_trends': {
                'labels': month_labels,
                'counts': [monthly_counts[m] for m in month_labels],
                'costs': [monthly_costs[m] for m in month_labels]
            },
            'service_types': {
                'labels': list(type_distribution.keys()),
                'counts': list(type_distribution.values()),
                'colors': [f'#{random.randint(0, 0xFFFFFF):06x}' for _ in type_distribution]
            }
        }

        service_items_query = (
            db.session.query(ServiceHistoryItem)
            .join(ServiceHistory)
            .join(Car)
            .filter(Car.user_id == current_user.id)
        )

        service_items = service_items_query.all()

        service_type_cost = {}
        for item in service_items:
            type_name = item.service_type.name
            service_type_cost[type_name] = service_type_cost.get(type_name, 0) + (item.cost or 0)

        chart_data['cost_by_service_type'] = {
            'labels': list(service_type_cost.keys()),
            'data': list(service_type_cost.values()),
            'colors': generate_color_list(len(service_type_cost))  # helper to generate random colors
        }

        # Totals
        total_cost = db.session.query(func.sum(ServiceHistory.total_cost))\
            .filter(ServiceHistory.user_id == current_user.id).scalar() or 0.0

        total_services = db.session.query(func.count(ServiceHistory.id))\
            .filter(ServiceHistory.user_id == current_user.id).scalar()

        # All service type names (optional use)
        type_names = {t.id: t.name for t in ServiceType.query.all()}

        # Render template
        return render_template(
            'analytics.html',
            total_cars=len(cars),
            total_services=total_services,
            total_cost=total_cost,
            chart_data=chart_data,
            upcoming_services=upcoming_services,
            upcoming_reminders=reminder_data,
            selected_year=year,
            selected_month=month,
            type_names=type_names
        )
    
    @app.route('/privacy')
    def privacy_policy():
        return render_template('privacy.html', current_year=datetime.now().year)
    
    @app.route('/create-test-reminder')
    def create_test_reminder():
        try:
            # Create a test user
            user = User.query.filter_by(email='testuser@example.com').first()
            if not user:
                user = User(email='testuser@example.com', username='Test User')
                user.set_password('test123')  # if you use password auth
                db.session.add(user)
                db.session.commit()

            # Create a car for the user
            car = Car.query.filter_by(user_id=user.id, nickname='TestCar').first()
            if not car:
                car = Car(
                    user_id=user.id,
                    make='Honda',
                    model='City',
                    year=2020,
                    nickname='TestCar'
                )
                db.session.add(car)
                db.session.commit()

            # Create a service type
            service_type = ServiceType.query.filter_by(name='Oil Change').first()
            if not service_type:
                service_type = ServiceType(name='Oil Change')
                db.session.add(service_type)
                db.session.commit()

            # Create a service record
            service = Service(
                car_id=car.id,
                service_type_id=service_type.id,
                date=datetime.utcnow() - timedelta(days=90),
                mileage=20000,
                next_service_date=datetime.utcnow()  # due today
            )
            db.session.add(service)
            db.session.commit()

            # Create a reminder
            reminder = ServiceReminder(
                service_id=service.id,
                reminder_type='email',  # or 'push' or 'both'
                reminder_date=datetime.utcnow(),  # due now
                status='pending'
            )
            db.session.add(reminder)
            db.session.commit()

            return jsonify({"status": "success", "message": "Test reminder created."})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
        

    @app.route('/offline')
    def offline():
        return render_template('offline.html')
    
    
    @app.route('/manifest')
    def manifest():
        return send_from_directory('static', 'manifest.json')
          
    # Test route for chack the error log file
    # @app.route('/test-error')
    # def trigger_error():
    #     try:
    #         1 / 0
    #     except Exception as e:
    #         app.logger.error(f'Error occurred: {e}', exc_info=True)
    #     return 'Error has been logged.'

    # @app.route('/test-reminders')
    # def test_reminders():
    #     check_service_reminders()
    #     return "Checked reminders!"
