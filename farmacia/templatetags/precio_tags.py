
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def precio_chileno(valor):
    """Muestra los precios con punto como separador de miles."""
    try:
        numero = int(Decimal(str(valor)))
    except (InvalidOperation, TypeError, ValueError):
        return valor

    return f"{numero:,}".replace(",", ".")
