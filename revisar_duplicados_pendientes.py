from collections import defaultdict

from farmacia.models import Producto
from farmacia.procesamento.guardar_productos import (
    normalizar_texto_producto,
    extraer_firma_producto,
)
from farmacia.management.commands.homologar_duplicados import (
    caracteristicas_adicionales,
)

grupos = defaultdict(list)

productos = (
    Producto.objects
    .select_related("medicamento")
    .prefetch_related("precios__farmacia")
    .filter(precios__isnull=False, medicamento__isnull=False)
    .distinct()
)

for producto in productos:
    activo = normalizar_texto_producto(
        producto.medicamento.principio_activo or ""
    )

    if not activo:
        continue

    firma = extraer_firma_producto(
        producto.nombre,
        producto.presentacion or "",
    )

    concentraciones, forma, caracteristicas, cantidad = firma

    if not concentraciones or not forma or not cantidad:
        continue

    precios = list(producto.precios.all())

    adicionales = caracteristicas_adicionales(
        producto,
        precios,
    )

    # Se omiten identidad comercial y bioequivalencia
    # para detectar posibles coincidencias que el anÃ¡lisis anterior excluyÃ³.
    clave = (activo, firma, adicionales)

    grupos[clave].append({
        "producto": producto,
        "farmacias": {
            precio.farmacia_id for precio in precios
        },
        "nombres_farmacias": sorted({
            precio.farmacia.nombre for precio in precios
        }),
    })

print("\n" + "=" * 70)
print("REPORTE DE POSIBLES DUPLICADOS PENDIENTES")
print("=" * 70)

total_grupos = 0
total_productos = 0

for clave, elementos in sorted(grupos.items(), key=lambda x: x[0]):
    if len(elementos) < 2:
        continue

    farmacias_vistas = set()
    conflicto = False

    for elemento in elementos:
        if farmacias_vistas.intersection(elemento["farmacias"]):
            conflicto = True
            break
        farmacias_vistas.update(elemento["farmacias"])

    if conflicto:
        continue

    total_grupos += 1
    total_productos += len(elementos)

    activo, firma, adicionales = clave

    print("\n" + "-" * 70)
    print(f"GRUPO {total_grupos}")
    print(f"Principio activo: {activo}")
    print(f"Firma: {firma}")
    print(f"CaracterÃ­sticas adicionales: {adicionales}")

    for elemento in elementos:
        p = elemento["producto"]

        print(
            f"ID {p.id} | {p.nombre} "
            f"| Laboratorio: {p.laboratorio or 'Sin dato'} "
            f"| Bioequivalente: {p.es_bioequivalente} "
            f"| Farmacias: {', '.join(elemento['nombres_farmacias'])}"
        )

print("\n" + "=" * 70)
print(f"Grupos encontrados: {total_grupos}")
print(f"Productos involucrados: {total_productos}")
print("ANALISIS DE SOLO LECTURA: NO SE MODIFICARON REGISTROS")
print("=" * 70)
