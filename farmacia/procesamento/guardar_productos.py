import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio,
)



def normalizar_nombre_busqueda(nombre):
    if not nombre:
        return ""

    texto = str(nombre).strip().casefold()

    # Unificar los símbolos de multiplicación y sus variantes.
    texto = (
        texto.replace("Ãƒâ€”", " x ")
        .replace("Ã—", " x ")
        .replace("×", " x ")
    )

    # Normalizar caracteres Unicode y eliminar tildes.
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    # Conservar números, unidades y separadores relevantes.
    texto = re.sub(r"[^\w\s.,/-]", " ", texto)
    texto = " ".join(texto.split())

    return texto



def texto_sin_acentos(texto):
    """Facilita la comparación de palabras con y sin acentos."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )


def detectar_categoria(nombre, principio_activo=""):
    """Clasificación inicial orientativa del catálogo."""
    texto = texto_sin_acentos(
        f"{nombre} {principio_activo}"
    ).lower()

    cosmeticos = [
        "maquillaje", "labial", "mascara de pestanas",
        "base de maquillaje", "sombra de ojos", "rubor",
        "delineador", "esmalte de unas",
    ]

    cuidado_personal = [
        "shampoo", "champu", "acondicionador", "desodorante",
        "agua termal", "protector solar", "crema hidratante",
        "limpiador facial", "jabon", "panales",
        "pasta dental", "cepillo dental", "toallas humedas",
        "crema corporal", "agua micelar",
    ]

    medicamentos = [
        "comprimido", "capsula", "jarabe", "solucion oral",
        "suspension oral", "gotas", "ampolla", "inyectable",
        "supositorio", "ovulo", "antibiotico", "analgesico",
    ]

    if principio_activo:
        return "medicamentos"

    if any(p in texto for p in cosmeticos):
        return "cosmeticos"

    if any(p in texto for p in cuidado_personal):
        return "cuidado_personal"

    if any(p in texto for p in medicamentos):
        return "medicamentos"

    return "otros"


def buscar_medicamento(nombre, principio_activo=""):
    """Busca un medicamento por nombre normalizado."""
    clave = normalizar_nombre_busqueda(nombre)

    for medicamento in Medicamento.objects.all().only(
        "id", "nombre", "principio_activo"
    ):
        if normalizar_nombre_busqueda(medicamento.nombre) == clave:
            if principio_activo and not medicamento.principio_activo:
                medicamento.principio_activo = principio_activo
                medicamento.save(update_fields=["principio_activo"])
            return medicamento

    return Medicamento.objects.create(
        nombre=nombre,
        principio_activo=principio_activo or "",
    )


def convertir_precio(valor):
    """Convierte un precio válido a Decimal en pesos enteros."""
    if valor is None or isinstance(valor, bool):
        return None

    try:
        precio = Decimal(str(valor).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None

    if not precio.is_finite() or precio <= 0:
        return None

    return precio.quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )


def guardar_producto(datos, nombre_farmacia):
    """Crea o actualiza el producto y el precio cuando corresponde."""
    nombre = str(datos.get("nombre") or "").strip()

    if not nombre:
        print("Producto omitido: no tiene nombre.")
        return None

    principio_activo = str(
        datos.get("principio_activo") or ""
    ).strip()

    categoria = detectar_categoria(nombre, principio_activo)
    clave = normalizar_nombre_busqueda(nombre)

    producto = None

    for candidato in Producto.objects.filter(categoria=categoria).iterator():
        if normalizar_nombre_busqueda(candidato.nombre) == clave:
            producto = candidato
            break

    medicamento = None

    if categoria == "medicamentos":
        if producto and producto.medicamento_id:
            medicamento = producto.medicamento
        else:
            medicamento = buscar_medicamento(
                nombre,
                principio_activo,
            )

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

        if categoria == "medicamentos" and producto.medicamento_id is None:
            producto.medicamento = medicamento
            cambios.append("medicamento")

        for campo in ("presentacion", "laboratorio", "sku"):
            valor_nuevo = str(datos.get(campo) or "").strip()

            if not getattr(producto, campo) and valor_nuevo:
                setattr(producto, campo, valor_nuevo)
                cambios.append(campo)

        if cambios:
            producto.save(update_fields=cambios)

    farmacia, _ = Farmacia.objects.get_or_create(
        nombre=nombre_farmacia
    )

    precio_nuevo = convertir_precio(datos.get("precio"))

    # Un precio ausente o inválido no sobrescribe precios existentes.
    if precio_nuevo is None:
        return producto

    valores = {"precio": precio_nuevo}

    precio_normal = convertir_precio(datos.get("precio_normal"))
    if precio_normal is not None:
        valores["precio_normal"] = precio_normal

    url = str(datos.get("url") or "").strip()
    if url:
        valores["url_producto"] = url

    # Solo cambia la disponibilidad si el scraper entrega un booleano.
    disponible = datos.get("disponible")
    if isinstance(disponible, bool):
        valores["disponible"] = disponible

    Precio.objects.update_or_create(
        producto=producto,
        farmacia=farmacia,
        defaults=valores,
    )

    return producto
