import re
from django.core.exceptions import ValidationError


class StrongPasswordValidator:

    def validate(self, password, user=None):
        errores = []

        if not re.search(r"[A-Z]", password):
            errores.append("La contraseña debe contener al menos una mayúscula.")

        if not re.search(r"[a-z]", password):
            errores.append("La contraseña debe contener al menos una minúscula.")

        if not re.search(r"[0-9]", password):
            errores.append("La contraseña debe contener al menos un número.")

        if not re.search(r"[^A-Za-z0-9]", password):
            errores.append("La contraseña debe contener al menos un carácter especial.")

        if errores:
            raise ValidationError(errores)

    def get_help_text(self):
        return (
            "Debe incluir mayúsculas, minúsculas, números "
            "y al menos un carácter especial."
        )