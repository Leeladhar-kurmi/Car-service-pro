from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from app import db
import app

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Please check your login details and try again.', 'error')
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        # Input validation
        if not email or not password or not first_name or not last_name:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.register'))

        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', 'error')
            return redirect(url_for('auth.register'))

        # Create new user
        new_user = User()
        new_user.id = email  # Using email as ID for simplicity
        new_user.email = email
        new_user.password_hash = generate_password_hash(password)
        new_user.first_name = first_name
        new_user.last_name = last_name

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('auth.register'))

    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Create a default admin user for local development
def create_default_user():
    with app.app_context():
        try:
            user = User.query.filter_by(email='admin@local.dev').first()
            if not user:
                user = User()
                user.id = "local-admin"
                user.email = "admin@local.dev"
                user.first_name = "Admin"
                user.last_name = "User"
                db.session.add(user)
                db.session.commit()
            return user
        except Exception as e:
            print(f"Error creating default user: {e}")
            return None 