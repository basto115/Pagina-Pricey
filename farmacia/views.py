from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator

from .models import Medicamento, Farmacia, Producto, Precio


def inicio(request):
    busqueda = request.GET.get("buscar", "").strip()

    productos = Producto.objects.prefetch_related(
        Prefetch(
            "precios",
            queryset=Precio.objects.select_related("farmacia").order_by("precio"),
        ),
        "medicamento",
    ).order_by("nombre")

    if busqueda:
        terminos = [
            termino.strip()
            for termino in busqueda.replace(";", ",").split(",")
            if termino.strip()
        ]

        consulta = Q()
        for termino in terminos:
            consulta |= (
                Q(nombre__icontains=termino)
                | Q(medicamento__nombre__icontains=termino)
                | Q(medicamento__principio_activo__icontains=termino)
                | Q(presentacion__icontains=termino)
                | Q(laboratorio__icontains=termino)
                | Q(categoria__icontains=termino)
            )

        productos = productos.filter(consulta).distinct()

    paginador = Paginator(productos, 12)
    pagina_obj = paginador.get_page(request.GET.get("pagina"))

    return render(
        request,
        "inicio.html",
        {
            "productos": pagina_obj,
            "pagina_obj": pagina_obj,
            "busqueda": busqueda,
        },
    )


def detalle_medicamento(request, medicamento_id):
    medicamento = get_object_or_404(
        Medicamento.objects.prefetch_related(
            "productos__precios__farmacia"
        ),
        id=medicamento_id,
    )
    return render(
        request,
        "detalle_medicamento.html",
        {"medicamento": medicamento},
    )


@require_GET
def listar_farmacias(request):
    farmacias = Farmacia.objects.all().order_by("nombre")
    datos = [
        {
            "id": farmacia.id,
            "nombre": farmacia.nombre,
            "direccion": farmacia.direccion,
            "latitud": float(farmacia.latitud) if farmacia.latitud is not None else None,
            "longitud": float(farmacia.longitud) if farmacia.longitud is not None else None,
            "sitio_web": farmacia.sitio_web,
        }
        for farmacia in farmacias
    ]
    return JsonResponse({"farmacias": datos})


@require_GET
def listar_precios(request):
    precios = Precio.objects.select_related(
        "producto", "farmacia", "producto__medicamento"
    ).all().order_by("precio")

    datos = [
        {
            "id": precio.id,
            "producto": precio.producto.nombre,
            "medicamento": (
                precio.producto.medicamento.nombre
                if precio.producto.medicamento else None
            ),
            "categoria": precio.producto.categoria,
            "farmacia": precio.farmacia.nombre,
            "precio": precio.precio,
            "precio_normal": precio.precio_normal,
            "disponible": precio.disponible,
            "fecha_actualizacion": precio.fecha_actualizacion.isoformat(),
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
        "id", "nombre", "principio_activo"
    )
    return JsonResponse(
        list(medicamentos),
        safe=False,
        json_dumps_params={"ensure_ascii": False},
    )


def vista_login(request):
    return render(request, "login.html")


def vista_resgitro(request):
    return render(request, "registro.html")
