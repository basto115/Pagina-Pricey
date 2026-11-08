from farmacia.models import Producto

ids = [1, 8895, 23, 8897]

for producto_id in ids:
    try:
        producto = Producto.objects.get(id=producto_id)

        print("\n" + "=" * 60)
        print("ID:", producto.id)
        print("NOMBRE:", producto.nombre)
        print("PRESENTACIÓN:", producto.presentacion)
        print("LABORATORIO:", producto.laboratorio)

        if producto.medicamento:
            print("MEDICAMENTO:", producto.medicamento.nombre)
            print(
                "PRINCIPIO ACTIVO:",
                producto.medicamento.principio_activo
            )

        print("\n--- PRECIOS POR FARMACIA ---")

        precios = producto.precios.select_related(
            "farmacia"
        ).order_by("farmacia__nombre")

        if not precios.exists():
            print("No tiene precios registrados.")

        for precio in precios:
            print(
                f"{precio.farmacia.nombre} | "
                f"${precio.precio} | "
                f"Disponible: {precio.disponible} | "
                f"URL: {precio.url_producto}"
            )

    except Producto.DoesNotExist:
        print(f"No existe el producto con ID {producto_id}")