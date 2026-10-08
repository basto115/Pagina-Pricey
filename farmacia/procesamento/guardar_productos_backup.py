from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio
)


def guardar_producto(datos, nombre_farmacia):
    """
    Guarda o actualiza un producto obtenido
    desde un scraper.
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
        nombre=datos.get("nombre", ""),
        defaults={
            "principio_activo": datos.get(
                "principio_activo",
                ""
            )
        }
    )

    # Actualizar principio activo si antes
    # estaba vacío
    principio_activo = datos.get(
        "principio_activo",
        ""
    )

    if principio_activo and not medicamento.principio_activo:
        medicamento.principio_activo = principio_activo
        medicamento.save()

    # -----------------------------
    # PRODUCTO
    # -----------------------------

    producto, creado = Producto.objects.get_or_create(
        medicamento=medicamento,
        nombre=datos.get("nombre", ""),
        defaults={
            "presentacion": datos.get(
                "presentacion",
                ""
            ),
            "laboratorio": datos.get(
                "laboratorio",
                ""
            ),
            "sku": datos.get(
                "sku",
                ""
            )
        }
    )

    # Actualizar información si ya existía
    cambios = False

    if (
        datos.get("presentacion")
        and not producto.presentacion
    ):
        producto.presentacion = datos["presentacion"]
        cambios = True

    if (
        datos.get("laboratorio")
        and not producto.laboratorio
    ):
        producto.laboratorio = datos["laboratorio"]
        cambios = True

    if (
        datos.get("sku")
        and not producto.sku
    ):
        producto.sku = datos["sku"]
        cambios = True

    if cambios:
        producto.save()

    # -----------------------------
    # PRECIO
    # -----------------------------

    Precio.objects.update_or_create(
        producto=producto,
        farmacia=farmacia,
        defaults={
            "precio": datos.get("precio") or 0,

            "precio_normal": datos.get(
                "precio_normal"
            ),

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