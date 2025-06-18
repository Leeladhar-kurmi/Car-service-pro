from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, DateField, TextAreaField, DecimalField, PasswordField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo, ValidationError
from wtforms.widgets import TextInput, NumberInput, ListWidget, CheckboxInput
from models import ServiceType, Car
from datetime import date
from flask import request



class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

# Custom TextInput widget for mileage that looks like a number input
class MileageInput(TextInput):
    def __call__(self, field, **kwargs):
        kwargs['type'] = 'text'
        kwargs['inputmode'] = 'numeric'
        kwargs['pattern'] = '[0-9]*'
        kwargs['max'] = '999999'
        kwargs['data-max'] = '999999'
        if 'class' in kwargs:
            kwargs['class'] += ' mileage-input'
        else:
            kwargs['class'] = 'mileage-input'
        return super().__call__(field, **kwargs)

class CarForm(FlaskForm):
    make = StringField('Brand', validators=[DataRequired(), Length(min=1, max=50)])
    model = StringField('Model', validators=[DataRequired(), Length(min=1, max=50)])
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=1900, max=2030)], 
                       widget=NumberInput())
    registration_number = StringField('Registration Number', 
                                    validators=[DataRequired(), Length(min=10, max=10)])
    color = StringField('Color', validators=[DataRequired(), Length(max=30)])
    current_mileage = IntegerField('Current Mileage', 
                                  validators=[DataRequired(), NumberRange(min=0, max=999999)], 
                                  widget=MileageInput())
    insurance_company = StringField("Insurance Company", validators=[DataRequired()])
    expiry_date = DateField('Expairy Date', validators=[DataRequired()])

    def __init__(self, *args, car=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_car = car

    def validate_registration_number(self, field):
        if self.existing_car and field.data == self.existing_car.registration_number:
            # Don't validate if registration number hasn't changed
            return

        # Only check if someone else already uses this reg number
        existing = Car.query.filter_by(registration_number=field.data).first()
        if existing:
            raise ValidationError("This registration number is already in use.")


class ServiceForm(FlaskForm):
    service_type_ids = MultiCheckboxField(
        'Service Types',
        coerce=int,
        validators=[],
        choices=[]  # will be populated in __init__
    )

    interval_months = IntegerField('Interval (Months)', validators=[Optional(), NumberRange(min=1)], 
                                   widget=NumberInput())
    interval_mileage = IntegerField('Interval (Miles)', 
                                    validators=[Optional(), NumberRange(min=1, max=999999)], 
                                    widget=MileageInput())
    last_service_date = DateField('Last Service Date', validators=[Optional()])
    last_service_mileage = IntegerField('Last Service Mileage', 
                                        validators=[DataRequired(), NumberRange(min=0, max=999999)], 
                                        widget=MileageInput())
    notify_days_before = IntegerField('Notify Days Before', 
                                      validators=[DataRequired(), NumberRange(min=1, max=90)], 
                                      widget=NumberInput(), default=7)

    def __init__(self, *args, **kwargs):
        super(ServiceForm, self).__init__(*args, **kwargs)

        # Dynamically load all service types into the checkbox choices
        self.service_type_ids.choices = [
            (st.id, st.name) for st in ServiceType.query.order_by(ServiceType.name).all()
        ]



class ServiceHistoryForm(FlaskForm):
    service_type_ids = SelectMultipleField(
        'Service Types',
        coerce=int,
        validators=[DataRequired()],
        render_kw={"multiple": "multiple"}
    )
    service_date = DateField('Service Date', validators=[DataRequired()], default=date.today)
    mileage = IntegerField('Mileage at Service', 
                          validators=[Optional(), NumberRange(min=0, max=999999)], 
                          widget=MileageInput())
    cost = DecimalField('Cost (₹)', validators=[Optional(), NumberRange(min=0)], places=2)
    service_provider = StringField('Service Provider', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

    def __init__(self, *args, **kwargs):
        super(ServiceHistoryForm, self).__init__(*args, **kwargs)
        self.service_type_ids.choices = [
            (st.id, st.name) for st in ServiceType.query.order_by(ServiceType.name).all()
        ]

class RegistrationForm(FlaskForm):
    email = StringField('Email')
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    password = PasswordField('Password')
    confirm_password = PasswordField('Confirm Password')
    otp = StringField('OTP', render_kw={"placeholder": "Enter 6-digit OTP"})

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)

    def validate(self, extra_validators=None):
        action = request.form.get('action', '')
        valid = super().validate(extra_validators)  # Ensures base validation runs

        # Step 1: Validate name & email
        if action == 'send_otp':
            if not self.email.data:
                self.email.errors.append("Email is required.")
                valid = False
            else:
                try:
                    Email()(self, self.email)
                except ValidationError as e:
                    self.email.errors.append(str(e))
                    valid = False

            if not self.first_name.data or len(self.first_name.data) < 2:
                self.first_name.errors.append("First name must be at least 2 characters.")
                valid = False

            if not self.last_name.data or len(self.last_name.data) < 2:
                self.last_name.errors.append("Last name must be at least 2 characters.")
                valid = False

        # Step 2: Validate OTP
        elif action == 'verify_otp':
            if not self.otp.data:
                self.otp.errors.append('OTP is required.')
                valid = False
            elif len(self.otp.data) != 6 or not self.otp.data.isdigit():
                self.otp.errors.append('OTP must be a 6-digit number.')
                valid = False

        # Step 3: Validate passwords
        elif action == 'complete_registration':
            if not self.password.data:
                self.password.errors.append("Password is required.")
                valid = False
            elif len(self.password.data) < 8:
                self.password.errors.append("Password must be at least 8 characters.")
                valid = False

            if not self.confirm_password.data:
                self.confirm_password.errors.append("Please confirm your password.")
                valid = False
            elif self.password.data != self.confirm_password.data:
                self.confirm_password.errors.append("Passwords must match.")
                valid = False

        return valid

class ResetPasswordForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    otp = StringField("OTP")
    password = PasswordField("New Password")
    confirm_password = PasswordField("Confirm Password")

    def validate(self, extra_validators=None):
        action = request.form.get('action', '')

        if action == "send_otp":
            return self.email.validate(self)

        elif action == "verify_otp":
            valid = True
            if not self.otp.data or len(self.otp.data.strip()) != 6:
                self.otp.errors.append("Please enter a valid 6-digit OTP.")
                valid = False
            return valid

        elif action == "reset_password":
            valid = True

            if not self.password.data:
                self.password.errors.append("Password is required.")
                valid = False
            elif len(self.password.data) < 8:
                self.password.errors.append("Password must be at least 8 characters long.")
                valid = False

            if not self.confirm_password.data:
                self.confirm_password.errors.append("Please confirm your password.")
                valid = False
            elif self.password.data != self.confirm_password.data:
                self.confirm_password.errors.append("Passwords must match.")
                valid = False

            return valid

        return super().validate(extra_validators=extra_validators)