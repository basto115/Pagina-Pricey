from farmacia.scraping.cruz_verde import obtener_producto
from farmacia.procesamento.guardar_productos import guardar_producto


url = (
    "https://beta.cruzverde.cl/"
    "paracetamol-500-mg-16-comprimidos/"
    "272241.html"
)


datos = obtener_producto(url)

producto = guardar_producto(
    datos,
    "Cruz Verde"
)

print("\n--- PRODUCTO GUARDADO ---")
print("Medicamento:", producto.medicamento.nombre)
print("Producto:", producto.nombre)
print("ID:", producto.id)