from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio
)


def guardar_producto(datos, nombre_farmacia):
    """
    Guarda un producto obtenido por un scraper
    en la base de datos de Django.
    """

    # -----------------------------
    # FARMACIA
    # -----------------------------

    farmacia, _ = Farmacia.objects.get_or_create(
        nombre=nombre_farmacia
    )

    # -----------------------------
    # MEDICAMENTO
    # -----------------------------

    medicamento, _ = Medicamento.objects.get_or_create(
        nombre=datos["nombre"],
        defaults={
            "principio_activo": datos.get(
                "principio_activo",
                ""
            )
        }
    )

    # Si el medicamento ya existe pero ahora
    # tenemos principio activo, lo actualizamos.
    if (
        datos.get("principio_activo")
        and not medicamento.principio_activo
    ):
        medicamento.principio_activo = datos["principio_activo"]
        medicamento.save()

    # -----------------------------
    # PRODUCTO
    # -----------------------------

    producto, _ = Producto.objects.get_or_create(
        medicamento=medicamento,
        nombre=datos["nombre"],
        defaults={
            "presentacion": datos.get(
                "presentacion",
                ""
            )
        }
    )

    # -----------------------------
    # PRECIO
    # -----------------------------

    Precio.objects.update_or_create(
        producto=producto,
        farmacia=farmacia,
        defaults={
            "precio": datos["precio"] or 0,
            "precio_normal": datos.get("precio_normal"),
            "disponible": datos.get(
                "disponible",
                False
            ),
            "url_producto": datos.get(
                "url",
                ""
            )
        }
    )

    return producto