#esto configura django para que se pueda usar en prueba
import os
import sys
import django

# Obtener la carpeta principal del proyecto
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

# Agregar el proyecto a la ruta de Python
sys.path.insert(0, BASE_DIR)

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

#esto es scraping
datos = obtener_producto(url)

#normalización

datos_normalizados = normalizar_producto(
    datos,
    "Cruz Verde"
)

# Guardado
producto = guardar_producto(
    datos_normalizados,
    "Cruz Verde"
)

print("\n--- PRODUCTO GUARDADO ---")
print(
    "Medicamento:",
    producto.medicamento.nombre
    if producto.medicamento
    else "No asociado"
)
print("Producto:", producto.nombre)
print("Categoría:", producto.categoria)
print("ID:", producto.id)