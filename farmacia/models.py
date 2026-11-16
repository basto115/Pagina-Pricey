from django.db import models
from django.conf import settings

class Medicamento(models.Model):
    nombre = models.CharField(max_length=200)

    principio_activo = models.CharField(
        max_length=200,
        blank=True
    )

    descripcion = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.nombre


class Farmacia(models.Model):
    nombre = models.CharField(max_length=200)

    direccion = models.CharField(
        max_length=300,
        blank=True
    )

    latitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    sitio_web = models.URLField(
        blank=True
    )

    def __str__(self):
        return self.nombre
    
class Sucursal(models.Model):
    farmacia = models.ForeignKey(
        Farmacia,
        on_delete=models.SET_NULL,
        related_name="sucursales",
        null=True,
        blank=True
    )
    
    nombre = models.CharField(max_length=200)
    
    direccion = models.CharField(
        max_length=300,
        blank=True
    )
    
    comuna = models.CharField(
        max_length=100,
        blank=True
    )
    
    latitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )    
    
    sitio_web = models.URLField(blank=True)
    
    origen = models.CharField(
        max_length=30,
        default="manual"
    )
    
    osm_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )
    
    aprobada = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre
    
class Producto(models.Model):
    medicamento = models.ForeignKey(
        Medicamento,
        on_delete=models.SET_NULL,
        related_name="productos",
        null=True,
        blank=True
    )

    es_bioequivalente = models.BooleanField(
        default=False
    )

    nombre = models.CharField(
        max_length=300
    )

    presentacion = models.CharField(
        max_length=200,
        blank=True
    )

    laboratorio = models.CharField(
        max_length=200,
        blank=True
    )

    sku = models.CharField(
        max_length=100,
        blank=True
    )

    categoria = models.CharField(
        max_length=50,
        default="medicamentos"
    )

    def __str__(self):
        return self.nombre

class ImagenProducto(models.Model):
    medicamento = models.OneToOneField(
        Medicamento,
        on_delete=models.CASCADE,
        related_name="imagen",
        null=True,
        blank=True
    )

    producto = models.OneToOneField(
        Producto,
        on_delete=models.CASCADE,
        related_name="imagen",
        null=True,
        blank=True
    )

    imagen = models.BinaryField()
    
    formato = models.CharField(
        max_length=20,
        default="WEBP"
    )

    actualizado_en = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        medicamento__isnull=False,
                        producto__isnull=True
                    )
                    | models.Q(
                        medicamento__isnull=True,
                        producto__isnull=False
                    )
                ),
                name="imagen_medicamento_o_producto"
            )
        ]

    def __str__(self):
        return (
            f"Imagen de {self.medicamento}"
            if self.medicamento_id
            else f"Imagen de {self.producto}"
        )

class Precio(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="precios"
    )

    farmacia = models.ForeignKey(
        Farmacia,
        on_delete=models.CASCADE,
        related_name="precios"
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=0
    )

    precio_normal = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )

    disponible = models.BooleanField(
        default=True
    )

    url_producto = models.URLField(
        max_length=1000,
        blank=True,
        null=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.producto} - {self.farmacia}"


class ProgresoImportacion(models.Model):
    farmacia = models.CharField(
        max_length=100,
        unique=True
    )

    ultima_url = models.URLField(
        max_length=1000,
        blank=True
    )

    actualizado_en = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.farmacia} - {self.ultima_url}"

class Suscripcion(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="suscripcion"
    )

    es_premium = models.BooleanField(default=False)

    def __str__(self):
        plan = "Premium" if self.es_premium else "Gratis"
        return f"{self.usuario.username} - {plan}"