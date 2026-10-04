from django.db import models

# Create your models here.

class Medicamento(models.Model):
    nombre = models.CharField(max_length=200)
    principio_activo = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField(blank=True)
    
    def __str__(self):
        return self.nombre

class Farmacia(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, blank=True)
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
    
    def __str__(self):
        return self.nombre

class Producto(models.Model):
    medicamento = models.ForeignKey(
        Medicamento,
        on_delete=models.CASCADE,
        related_name="productos"
    )
    nombre = models.CharField(max_length=300)
    presentacion = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return self.nombre
    
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

    disponible = models.BooleanField(default=True)
    url_producto = models.URLField(blank=True)
    fecha_actualizacion = models.DateTimeField(
        auto_now=True
        )

    def __str__(self):
        return f"{self.producto} - {self.farmacia}"