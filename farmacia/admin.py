from django.contrib import admin

from .models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio,
    Sucursal
)


admin.site.register(Medicamento)
admin.site.register(Farmacia)
admin.site.register(Producto)
admin.site.register(Precio)

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "farmacia",
        "comuna",
        "origen",
        "aprobada",
    )

    list_filter = (
        "aprobada",
        "origen",
        "comuna",
        "farmacia",
    )

    search_fields = (
        "nombre",
        "direccion",
        "comuna",
    )

    list_editable = ("aprobada",)

    ordering = ("comuna", "nombre")