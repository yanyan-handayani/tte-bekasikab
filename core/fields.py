from django.db import models
from .crypto import encrypt_str, decrypt_str

class EncryptedTextField(models.TextField):
    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return encrypt_str(value)

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return decrypt_str(value)

    def to_python(self, value):
        return value
