import re

from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio,
)


def normalizar_nombre_busqueda(nombre):
    """Normaliza nombres para ayudar a identificar productos existentes."""
    if not nombre:
        return ""

    nombre = str(nombre).lower().strip()
    nombre = nombre.replace("×", " ")
    nombre = nombre.replace("(b)", "")

    # Quita la x cuando se utiliza como separador entre cantidades.
    nombre = re.sub(r"\s+x\s+", " ", nombre)

    # Normaliza espacios repetidos.
    nombre = " ".join(nombre.split())

    return nombre


def detectar_categoria(nombre, principio_activo=""):
    """
    Clasifica el producto usando su nombre y principio activo.
    La clasificación es orientativa y puede necesitar ajustes.
    """
    texto = f"{nombre} {principio_activo}".lower()

    palabras_medicamento = [
        "comprimido",
        "cápsula",
        "capsula",
        "jarabe",
        "solución oral",
        "solucion oral",
        "suspensión oral",
        "suspension oral",
        "gotas",
        "ampolla",
        "inyectable",
        "supositorio",
        "óvulo",
        "ovulo",
        "mg",
        "mcg",
        "antibiótico",
        "antibiotico",
        "analgésico",
        "analgesico",
    ]

    palabras_cosmeticos = [
        "maquillaje",
        "labial",
        "máscara de pestañas",
        "mascara de pestañas",
        "base de maquillaje",
        "sombra de ojos",
        "rubor",
        "delineador",
        "esmalte de uñas",
    ]

    palabras_cuidado_personal = [
        "shampoo",
        "champú",
        "acondicionador",
        "desodorante",
        "agua termal",
        "protector solar",
        "crema hidratante",
        "limpiador facial",
        "jabón",
        "jabon",
        "pañales",
        "panales",
        "pasta dental",
        "cepillo dental",
        "toallas húmedas",
        "toallas humedas",
        "crema corporal",
        "agua micelar",
    ]

    if principio_activo:
        return "medicamentos"

    if any(palabra in texto for palabra in palabras_cosmeticos):
        return "cosmeticos"

    if any(palabra in texto for palabra in palabras_cuidado_personal):
        return "cuidado_personal"

    if any(palabra in texto for palabra in palabras_medicamento):
        return "medicamentos"

    return "otros"


def buscar_medicamento(nombre, principio_activo=""):
    """Busca un medicamento existente antes de crear uno nuevo."""
    nombre_busqueda = normalizar_nombre_busqueda(nombre)

    for medicamento in Medicamento.objects.all():
        if normalizar_nombre_busqueda(medicamento.nombre) == nombre_busqueda:
            if principio_activo and not medicamento.principio_activo:
                medicamento.principio_activo = principio_activo
                medicamento.save(update_fields=["principio_activo"])

            return medicamento

    return Medicamento.objects.create(
        nombre=nombre,
        principio_activo=principio_activo or "",
    )


def guardar_producto(datos, nombre_farmacia):
    """
    Guarda o actualiza un producto y su precio.
    No registra precios ausentes, inválidos o iguales a cero.
    """
    nombre = (datos.get("nombre") or "").strip()

    if not nombre:
        print("Producto omitido: no tiene nombre.")
        return None

    principio_activo = (datos.get("principio_activo") or "").strip()

    categoria = detectar_categoria(nombre, principio_activo)

    medicamento = None

    if categoria == "medicamentos":
        medicamento = buscar_medicamento(
            nombre,
            principio_activo,
        )

    farmacia, _ = Farmacia.objects.get_or_create(
        nombre=nombre_farmacia,
    )

    nombre_busqueda = normalizar_nombre_busqueda(nombre)

    productos = Producto.objects.filter(
        categoria=categoria,
        medicamento=medicamento,
    )

    producto = None

    for producto_existente in productos:
        if (
            normalizar_nombre_busqueda(producto_existente.nombre)
            == nombre_busqueda
        ):
            producto = producto_existente
            break

    if producto is None:
        producto = Producto.objects.create(
            medicamento=medicamento,
            nombre=nombre,
            categoria=categoria,
            presentacion=datos.get("presentacion") or "",
            laboratorio=datos.get("laboratorio") or "",
            sku=datos.get("sku") or "",
        )
    else:
        cambios = []

        if not producto.presentacion and datos.get("presentacion"):
            producto.presentacion = datos["presentacion"]
            cambios.append("presentacion")

        if not producto.laboratorio and datos.get("laboratorio"):
            producto.laboratorio = datos["laboratorio"]
            cambios.append("laboratorio")

        if not producto.sku and datos.get("sku"):
            producto.sku = datos["sku"]
            cambios.append("sku")

        if producto.categoria != categoria:
            producto.categoria = categoria
            cambios.append("categoria")

        if cambios:
            producto.save(update_fields=cambios)

    precio_obtenido = datos.get("precio")

    try:
        precio_obtenido = float(precio_obtenido)
    except (TypeError, ValueError):
        precio_obtenido = None

    if precio_obtenido is not None and precio_obtenido > 0:
        precio_normal = datos.get("precio_normal")

        if precio_normal is not None:
            try:
                precio_normal = float(precio_normal)
                if precio_normal <= 0:
                    precio_normal = None
            except (TypeError, ValueError):
                precio_normal = None

        Precio.objects.update_or_create(
            producto=producto,
            farmacia=farmacia,
            defaults={
                "precio": precio_obtenido,
                "precio_normal": precio_normal,
                "disponible": datos.get("disponible", False),
                "url_producto": datos.get("url") or "",
            },
        )

    return producto
