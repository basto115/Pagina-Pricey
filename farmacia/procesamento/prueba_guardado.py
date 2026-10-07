#esto configura django para que se pueda usar en prueba
import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()

#esto es la prueba

from farmacia.scraping.cruz_verde import obtener_producto
from farmacia.procesamento.normalizar import normalizar_producto
from farmacia.procesamento.guardar_productos import guardar_producto


url = (
    "https://beta.cruzverde.cl/"
    "paracetamol-500-mg-16-comprimidos/"
    "272241.html"
)

#eto e scraping
datos = obtener_producto(url)

#normalización

datos_normalizados = normalizar_producto(
    datos,
    "Cruz Verde"
)

#guardado
producto = guardar_producto(
    datos,
    "Cruz Verde"
)

print("\n--- PRODUCTO GUARDADO ---")
print("Medicamento:", producto.medicamento.nombre)
print("Producto:", producto.nombre)
print("ID:", producto.id)