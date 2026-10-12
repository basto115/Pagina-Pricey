
from django.shortcuts import render
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.shortcuts import render, get_object_or_404

from .models import Medicamento, Farmacia, Producto, Precio


def inicio(request):
    busqueda = request.GET.get("buscar", "").strip()

    productos = Producto.objects.select_related(
        "medicamento"
    ).prefetch_related(
        "precios__farmacia"
    ).order_by("nombre")

    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda)
            | Q(medicamento__nombre__icontains=busqueda)
            | Q(medicamento__principio_activo__icontains=busqueda)
        )

    return render(
        request,
        "inicio.html",
        {
            "productos": productos,
            "busqueda": busqueda,
        },
    )


def listar_farmacias(request):
    farmacias = Farmacia.objects.all().order_by("nombre")

    datos = [
        {
            "id": farmacia.id,
            "nombre": farmacia.nombre,
            "direccion": farmacia.direccion,
            "latitud": (
                float(farmacia.latitud)
                if farmacia.latitud is not None else None
            ),
            "longitud": (
                float(farmacia.longitud)
                if farmacia.longitud is not None else None
            ),
            "sitio_web": farmacia.sitio_web,
        }
        for farmacia in farmacias
    ]

    return JsonResponse({"farmacias": datos})


def listar_precios(request):
    precios = Precio.objects.select_related(
        "producto",
        "producto__medicamento",
        "farmacia",
    ).all().order_by("precio")

    datos = [
        {
            "id": precio.id,
            "producto": precio.producto.nombre,
            "categoria": precio.producto.categoria,
            "medicamento": (
                precio.producto.medicamento.nombre
                if precio.producto.medicamento_id
                else None
            ),
            "farmacia": precio.farmacia.nombre,
            "precio": precio.precio,
            "precio_normal": precio.precio_normal,
            "disponible": precio.disponible,
            "fecha_actualizacion": (
                precio.fecha_actualizacion.isoformat()
            ),
            "url_producto": precio.url_producto,
        }
        for precio in precios
    ]

    return JsonResponse(
        {"precios": datos},
        json_dumps_params={"ensure_ascii": False},
    )


@require_GET
def api_medicamentos(request):
    medicamentos = Medicamento.objects.all().values(
        "id",
        "nombre",
        "principio_activo",
    )

    return JsonResponse(
        list(medicamentos),
        safe=False,
        json_dumps_params={"ensure_ascii": False},
    )

def detalle_medicamento(request, medicamento_id):
    medicamento = get_object_or_404(
        Medicamento.objects.prefetch_related(
            'productos__precios__farmacia'
        ),
        id=medicamento_id
    )

    return render(
        request,
        'detalle_medicamento.html',
        {'medicamento': medicamento}
    )