from django.contrib import admin
from .models import Medicamento, Farmacia, Producto, Precio
# Register your models here.

admin.site.register(Medicamento)
admin.site.register(Farmacia)
admin.site.register(Producto)
admin.site.register(Precio)