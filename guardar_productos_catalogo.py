import re

from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio,
)


def normalizar_nombre_busqueda(nombre):
    if not nombre:
        return ""

    nombre = nombre.replace("×", " ")
    nombre = re.sub(r"\s+x\s+", " ", nombre)

    return nombre.strip()


def buscar_medicamento(nombre, principio_activo=""):
    nombre_busqueda = normalizar_nombre_busqueda(nombre)

    medicamentos = Medicamento.objects.all()

    for medicamento in medicamentos:
        if normalizar_nombre_busqueda(
            medicamento.nombre
        ) == nombre_busqueda:
            if principio_activo and not medicamento.principio_activo:
                medicamento.principio_activo = principio_activo
                medicamento.save(update_fields=["principio_activo"])

            return medicamento

    return Medicamento.objects.create(
        nombre=nombre,
        principio_activo=principio_activo or "",
    )


def detectar_categoria(nombre, principio_activo=""):
    texto = (nombre or "").lower()

    # Si se obtuvo el principio activo, es una señal útil
    # de que se trata de un medicamento.
    patrones_medicamento = (
        r"\bmg\b",
        r"\bmcg\b",
        r"\bcomprimidos?\b",
        r"\bcápsulas?\b",
        r"\bjarabe\b",
        r"\bsolución oral\b",
        r"\bsuspensión oral\b",
        r"\bgotas\b",
        r"\bampollas?\b",
        r"\binyectable\b",
        r"\bcrema\b.*\bmg\b",
        r"\bparches?\b",
    )

    if principio_activo or any(
        re.search(patron, texto)
        for patron in patrones_medicamento
    ):
        return "medicamentos"

    palabras_cosmeticos = (
        "maquillaje", "labial", "máscara de pestañas",
        "base de maquillaje", "sombra de ojos",
    )

    if any(palabra in texto for palabra in palabras_cosmeticos):
        return "cosmeticos"

    palabras_cuidado = (
        "shampoo", "champú", "acondicionador",
        "desodorante", "agua termal", "protector solar",
        "crema hidratante", "limpiador facial",
        "jabón", "pañales", "pasta dental",
        "cepillo dental", "toallas húmedas",
    )

    if any(palabra in texto for palabra in palabras_cuidado):
        return "cuidado_personal"

    return "otros"


def guardar_producto(datos, nombre_farmacia):
    nombre = (datos.get("nombre") or "").strip()

    if not nombre:
        raise ValueError("El producto no tiene nombre.")

    farmacia, _ = Farmacia.objects.get_or_create(
        nombre=nombre_farmacia
    )

    principio_activo = (
        datos.get("principio_activo") or ""
    ).strip()

    categoria = detectar_categoria(
        nombre,
        principio_activo,
    )

    # Solo asociamos un medicamento cuando el producto
    # se identifica como tal.
    medicamento = None

    if categoria == "medicamentos":
        medicamento = buscar_medicamento(
            nombre,
            principio_activo,
        )

    # Buscar el producto dentro del grupo correspondiente.
    productos = Producto.objects.filter(
        medicamento=medicamento
    )

    nombre_busqueda = normalizar_nombre_busqueda(nombre)
    producto = None

    for existente in productos:
        if normalizar_nombre_busqueda(
            existente.nombre
        ) == nombre_busqueda:
            producto = existente
            break

    if producto is None:
        producto = Producto.objects.create(
            medicamento=medicamento,
            nombre=nombre,
            categoria=categoria,
            presentacion=datos.get("presentacion") or "",
            laboratorio=datos.get("laboratorio") or "",
            sku=str(datos.get("sku") or ""),
        )
    else:
        cambios = []

        if producto.categoria != categoria:
            producto.categoria = categoria
            cambios.append("categoria")

        if not producto.presentacion and datos.get("presentacion"):
            producto.presentacion = datos["presentacion"]
            cambios.append("presentacion")

        if not producto.laboratorio and datos.get("laboratorio"):
            producto.laboratorio = datos["laboratorio"]
            cambios.append("laboratorio")

        if not producto.sku and datos.get("sku"):
            producto.sku = str(datos["sku"])
            cambios.append("sku")

        if cambios:
            producto.save(update_fields=cambios)

    precio = datos.get("precio")

    # No sobrescribir un precio real con cero si el scraper
    # no pudo extraer el precio.
    if precio is not None and precio > 0:
        Precio.objects.update_or_create(
            producto=producto,
            farmacia=farmacia,
            defaults={
                "precio": precio,
                "precio_normal": datos.get("precio_normal"),
                "disponible": datos.get("disponible", False),
                "url_producto": datos.get("url") or "",
            },
        )

    return producto
