from farmacia.models import Producto

ids = [
    140, 9348, 1439, 16057, 1458, 8884, 1460, 15872,
    1465, 8864, 1468, 15508, 1469, 15813, 1481, 9951,
    1518, 10122, 2873, 15531, 2941, 16126, 3055, 15825,
    3288, 15876, 3519, 15756, 3520, 15766, 3540, 16256,
    3541, 15826, 3542, 10590, 3543, 10588, 3577, 13708,
    4413, 15828, 4565, 15985, 6126, 15543, 8899, 15881,
    11139, 15752, 13439, 15868, 13703, 15753, 13883, 16208,
    13884, 16212, 14090, 15775, 14388, 15530, 14443, 16241,
    14452, 16183, 14655, 16170
]

for p in Producto.objects.filter(id__in=ids).select_related("medicamento").prefetch_related("precios__farmacia").order_by("id"):
    activo = p.medicamento.principio_activo if p.medicamento else "SIN MEDICAMENTO"
    print("\n" + "=" * 80)
    print(f"ID: {p.id} | {p.nombre}")
    print(f"Activo: {activo}")
    print(f"Presentacion: {p.presentacion}")
    print(f"Categoria: {p.categoria}")
    print(f"Laboratorio: {p.laboratorio}")
    print(f"SKU: {p.sku}")
    print(f"Bioequivalente: {p.es_bioequivalente}")
    for precio in p.precios.all():
        print(f"  Farmacia: {precio.farmacia.nombre} | URL: {precio.url_producto}")
