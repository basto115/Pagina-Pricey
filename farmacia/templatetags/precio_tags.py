
from decimal import Decimal, InvalidOperation
from django import template

register = template.Library()


@register.filter(name='precio_chileno')
def precio_chileno(valor):
    if valor is None or valor == '':
        return ''

    try:
        numero = int(Decimal(str(valor)))
    except (InvalidOperation, ValueError, TypeError):
        return valor

    return f"${numero:,}".replace(",", ".")
