from flask import session, render_template,Blueprint, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from datetime import datetime, date, timedelta, timezone
from models import User, Car, Service, ServiceType, ServiceHistory, ServiceReminder, ServiceHistoryItem
from forms import CarForm, ServiceForm, ServiceHistoryForm, RegistrationForm, ResetPasswordForm
import json
import uuid
import time
import traceback
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
from pywebpush import webpush, WebPushException
from sqlalchemy import func, extract
from calendar import monthrange

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
                app.logger.error("No sender email configured in app config")
                return False

            # Debug logging before sending
            app.logger.debug(f"Email configuration:")
            app.logger.debug(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
            app.logger.debug(f"MAIL_PORT: {app.config.get('MAIL_PORT')} (type: {type(app.config.get('MAIL_PORT'))}")
            app.logger.debug(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
            app.logger.debug(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
            
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
            app.logger.debug("Email sent successfully")
            return True
            
        except Exception as e:
            app.logger.error(f"Error sending email: {str(e)}")
            app.logger.error(traceback.format_exc())
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
                    app.logger.error(f"Database error: {e}")
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

                otp = generate_otp()
                if send_otp_email(email, otp):
                    session['otp'] = otp
                    session['otp_email'] = email
                    session['first_name'] = form.first_name.data
                    session['last_name'] = form.last_name.data
                    session['otp_time'] = time.time()
                    session.pop('otp_verified', None)  # reset verification if resending OTP

                    flash('OTP sent to your email.', 'info')
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
                    if session.get('otp_sent'):
                        flash("Please wait before requesting another OTP.", "warning")
                    else:
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
        
        return render_template('car_form.html', form=form, title='Add Car')

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
        """Add a new service schedule for a car"""
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
            
            # Commit first to ensure service has an ID and relationships are established
            db.session.commit()
            
            # Now update schedules for all newly created services
            for service_type_id in form.service_type_ids.data:
                service = Service.query.filter_by(
                    car_id=car_id,
                    service_type_id=service_type_id
                ).order_by(Service.id.desc()).first()
                if service:
                    service.update_schedule()
            
            db.session.commit()
            flash('Service schedules added successfully!', 'success')
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
        
        return render_template('services/history.html', service_history=service_history,year=year, service_types=service_types)

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

            # Collect all selected service items and costs
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

            flash('Service history recorded successfully.', 'success')
            return redirect(url_for('car_services', car_id=car.id))

        return render_template(
            'services/service_form.html',
            form=form,
            title='Add Service Record',
            car=car,
            service_type_intervals=service_type_intervals
        )


    @app.route('/api/push-subscription', methods=['POST'])
    @login_required
    def save_push_subscription():
        """Save push notification subscription"""
        subscription = request.get_json()
        current_user.push_subscription = json.dumps(subscription)
        db.session.commit()
        return jsonify({'success': True})

    def send_push_notification(user, message, title="Car Service Reminder"):
        """Send push notification to a user"""
        if not user.push_subscription:
            return False
        
        try:
            subscription_info = json.loads(user.push_subscription)
            webpush(
                subscription_info=subscription_info,
                data=json.dumps({
                    'title': title,
                    'body': message,
                    'icon': '/static/icons/icon-192.svg'
                }),
                vapid_private_key=app.config['VAPID_PRIVATE_KEY'],
                vapid_claims=app.config['VAPID_CLAIMS']
            )
            return True
        except WebPushException as e:
            app.logger.error(f"Failed to send push notification: {str(e)}")
            return False

    @app.route('/service-worker.js')
    def service_worker():
        """Serve the service worker file"""
        return app.send_static_file('sw.js')


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

    @app.route('/settings/email', methods=['POST'])
    @login_required
    def update_email():
        """Update user email address"""
        new_email = request.form.get('email')
        if new_email and new_email != current_user.email:
            current_user.email = new_email
            db.session.commit()
            flash('Email address updated successfully!', 'success')
        return redirect(url_for('settings'))

    # Initialize default service types
    with app.app_context():
        create_default_service_types()

    
    # Analytics Page

    @app.route('/analytics')
    @login_required
    def analytics():
        # 1. Overall Statistics
        total_cars = Car.query.filter_by(user_id=current_user.id).count()
        total_services = ServiceHistory.query.join(Car).filter(Car.user_id == current_user.id).count()

        total_cost = (
            db.session.query(func.sum(ServiceHistoryItem.cost))
            .join(ServiceHistory)
            .join(Car)
            .filter(Car.user_id == current_user.id)
            .scalar()
        ) or 0.0

        # 2. Cost by Car
        cost_by_car = db.session.query(
            Car.make,
            Car.model,
            func.sum(ServiceHistoryItem.cost)
        ).join(ServiceHistory, ServiceHistory.car_id == Car.id
        ).join(ServiceHistoryItem, ServiceHistoryItem.history_id == ServiceHistory.id
        ).filter(Car.user_id == current_user.id
        ).group_by(Car.id, Car.make, Car.model).all()

        # 3. Monthly Service Trends
        monthly_data = db.session.query(
            func.date_format(ServiceHistory.service_date, '%Y-%m').label('month'),
            func.count(ServiceHistory.id),
            func.sum(ServiceHistoryItem.cost)
        ).join(ServiceHistoryItem, ServiceHistoryItem.history_id == ServiceHistory.id
        ).join(Car, ServiceHistory.car_id == Car.id
        ).filter(
            Car.user_id == current_user.id,
            ServiceHistory.service_date >= datetime.now() - timedelta(days=365)
        ).group_by('month'
        ).order_by('month'
        ).all()

        # 4. Service Type Distribution
        service_type_dist = db.session.query(
            ServiceType.name,
            func.count(ServiceHistoryItem.id)
        ).join(ServiceHistoryItem, ServiceType.id == ServiceHistoryItem.service_type_id
        ).join(ServiceHistory, ServiceHistory.id == ServiceHistoryItem.history_id
        ).join(Car, Car.id == ServiceHistory.car_id
        ).filter(Car.user_id == current_user.id
        ).group_by(ServiceType.name
        ).order_by(func.count(ServiceHistoryItem.id).desc()
        ).limit(10).all()

        # 5. Upcoming Services
        upcoming_services = Service.query.join(Car).filter(
            Car.user_id == current_user.id,
            Service.next_service_date >= datetime.now().date(),
            Service.next_service_date <= datetime.now().date() + timedelta(days=30)
        ).order_by(Service.next_service_date).all()

        # 6. Prepare chart data
        chart_data = {
            'cost_by_car': {
                'labels': [f"{make} {model}" for make, model, _ in cost_by_car],
                'data': [float(cost or 0) for _, _, cost in cost_by_car],
                'colors': ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b']
            },
            'monthly_trends': {
                'labels': [row.month for row in monthly_data],
                'counts': [row[1] for row in monthly_data],
                'costs': [float(row[2] or 0) for row in monthly_data]
            },
            'service_types': {
                'labels': [row[0] for row in service_type_dist],
                'counts': [row[1] for row in service_type_dist]
            }
        }

        return render_template(
            'analytics.html',
            total_cars=total_cars,
            total_services=total_services,
            total_cost=round(total_cost, 2),
            chart_data=chart_data,
            upcoming_services=upcoming_services,
            current_year=datetime.now().year
        )