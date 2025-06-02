from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, DateField, TextAreaField, DecimalField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from wtforms.widgets import NumberInput
from models import ServiceType
from datetime import date


class CarForm(FlaskForm):
    make = StringField('Make', validators=[DataRequired(), Length(min=1, max=50)])
    model = StringField('Model', validators=[DataRequired(), Length(min=1, max=50)])
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=1900, max=2030)], 
                       widget=NumberInput())
    registration_number = StringField('Registration Number', 
                                    validators=[DataRequired(), Length(min=1, max=20)])
    color = StringField('Color', validators=[Optional(), Length(max=30)])
    current_mileage = IntegerField('Current Mileage', validators=[Optional(), NumberRange(min=0)], 
                                  widget=NumberInput())

    def __init__(self, *args, **kwargs):
        super(CarForm, self).__init__(*args, **kwargs)
        if not self.current_mileage.data:
            self.current_mileage.data = 0


class ServiceForm(FlaskForm):
    service_type_id = SelectField('Service Type', coerce=int, validators=[DataRequired()])
    interval_months = IntegerField('Interval (Months)', validators=[Optional(), NumberRange(min=1)], 
                                  widget=NumberInput())
    interval_mileage = IntegerField('Interval (Miles)', validators=[Optional(), NumberRange(min=1)], 
                                   widget=NumberInput())
    last_service_date = DateField('Last Service Date', validators=[Optional()])
    last_service_mileage = IntegerField('Last Service Mileage', validators=[Optional(), NumberRange(min=0)], 
                                       widget=NumberInput())
    notify_days_before = IntegerField('Notify Days Before', validators=[DataRequired(), NumberRange(min=1, max=90)], 
                                     widget=NumberInput(), default=7)

    def __init__(self, *args, **kwargs):
        super(ServiceForm, self).__init__(*args, **kwargs)
        self.service_type_id.choices = [
            (st.id, st.name) for st in ServiceType.query.order_by(ServiceType.name).all()
        ]


class ServiceHistoryForm(FlaskForm):
    service_type_id = SelectField('Service Type', coerce=int, validators=[DataRequired()])
    service_date = DateField('Service Date', validators=[DataRequired()], default=date.today)
    mileage = IntegerField('Mileage at Service', validators=[Optional(), NumberRange(min=0)], 
                          widget=NumberInput())
    cost = DecimalField('Cost ($)', validators=[Optional(), NumberRange(min=0)], places=2)
    service_provider = StringField('Service Provider', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

    def __init__(self, *args, **kwargs):
        super(ServiceHistoryForm, self).__init__(*args, **kwargs)
        self.service_type_id.choices = [
            (st.id, st.name) for st in ServiceType.query.order_by(ServiceType.name).all()
        ]
