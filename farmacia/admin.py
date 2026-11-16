from django.contrib import admin
from io import BytesIO

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from PIL import Image, ImageOps, UnidentifiedImageError

from .models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio,
    Sucursal,
    Suscripcion,
    ImagenProducto,
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


@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "es_premium",
    )

    list_filter = (
        "es_premium",
    )

    search_fields = (
        "usuario__username",
        "usuario__email",
    )

    list_editable = ("es_premium",)

class ImagenProductoForm(forms.ModelForm):
    archivo = forms.ImageField(
        required=False,
        label="Archivo de imagen"
    )

    class Meta:
        model = ImagenProducto
        fields = ("medicamento", "producto", "archivo")

    def clean(self):
        datos = super().clean()

        medicamento = datos.get("medicamento")
        producto = datos.get("producto")
        archivo = datos.get("archivo")

        if bool(medicamento) == bool(producto):
            raise ValidationError(
                "Selecciona un medicamento o un producto, no ambos."
            )

        if not archivo and not self.instance.pk:
            raise ValidationError(
                "Debes seleccionar una imagen."
            )

        if archivo and archivo.size > 5 * 1024 * 1024:
            raise ValidationError(
                "La imagen no puede superar los 5 MB."
            )

        return datos


@admin.register(ImagenProducto)
class ImagenProductoAdmin(admin.ModelAdmin):
    form = ImagenProductoForm

    list_display = (
        "id",
        "medicamento",
        "producto",
        "formato",
        "actualizado_en",
    )

    search_fields = (
        "medicamento__nombre",
        "producto__nombre",
    )

    def save_model(self, request, obj, form, change):
        archivo = form.cleaned_data.get("archivo")

        if archivo:
            try:
                imagen = Image.open(archivo)
                imagen = ImageOps.exif_transpose(imagen)
                imagen.thumbnail(
                    (800, 800),
                    Image.Resampling.LANCZOS
                )

                if imagen.mode not in ("RGB", "RGBA"):
                    imagen = imagen.convert("RGB")

                salida = BytesIO()

                imagen.save(
                    salida,
                    format="WEBP",
                    quality=78,
                    method=6
                )

                obj.imagen = salida.getvalue()
                obj.formato = "WEBP"

            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
            ):
                raise ValidationError(
                    "No se pudo procesar la imagen seleccionada."
                )

        super().save_model(request, obj, form, change)
