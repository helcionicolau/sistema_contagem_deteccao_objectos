# credentials.py
from decouple import config

email_address = config("email_address")
email_password = config("email_password")
recipient_email = config("recipient_email")