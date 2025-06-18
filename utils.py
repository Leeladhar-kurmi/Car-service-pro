# import pyotp
# from flask_mail import Mail, Message
# from datetime import datetime, timedelta
# import secrets

# mail = Mail()

# def generate_otp_secret():
#     """Generate a random secret key for OTP"""
#     return pyotp.random_base32()

# def generate_otp(secret):
#     """Generate a 6-digit OTP using the secret key"""
#     totp = pyotp.TOTP(secret, interval=300)  # OTP valid for 5 minutes
#     return totp.now()

# def verify_otp(secret, otp):
#     """Verify if the OTP is valid"""
#     totp = pyotp.TOTP(secret, interval=300)  # Same interval as generation
#     return totp.verify(otp)

# def send_otp_email(app, email, otp):
#     """Send OTP via email"""
#     try:
#         msg = Message(
#             'Your CarServicePro Registration OTP',
#             sender=app.config['MAIL_DEFAULT_SENDER'],
#             recipients=[email]
#         )
#         msg.body = f"""
#         Hello!
        
#         Your OTP for CarServicePro registration is: {otp}
        
#         This OTP is valid for 5 minutes.
        
#         If you didn't request this OTP, please ignore this email.
        
#         Best regards,
#         CarServicePro Team
#         """
#         mail.send(msg)
#         return True
#     except Exception as e:
#         print(f"Error sending email: {str(e)}")
#         return False 