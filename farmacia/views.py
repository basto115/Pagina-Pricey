from django.shortcuts import render
from django.db.models import Q
from .models import Medicamento, Farmacia, Precio
from django.http import JsonResponse
from django.views.decorators.http import require_GET

# Create your views here.

def inicio(request):
    busqueda = request.GET.get('buscar', '').strip()

    medicamentos = Medicamento.objects.prefetch_related(
        'productos__precios__farmacia'
    )

    if busqueda:
        medicamentos = medicamentos.filter(
            Q(nombre__icontains=busqueda) |
            Q(principio_activo__icontains=busqueda)
        )

    contexto = {
        'medicamentos': medicamentos,
        'busqueda': busqueda,
    }

    return render(request, 'inicio.html', contexto)

@require_GET
def listar_farmacias(request):
    farmacias = Farmacia.objects.all().order_by('nombre')

    datos = [
        {
            'id': farmacia.id,
            'nombre': farmacia.nombre,
            'direccion': farmacia.direccion,
            'latitud': float(farmacia.latitud) if farmacia.latitud is not None else None,
            'longitud': float(farmacia.longitud) if farmacia.longitud is not None else None,
            'sitio_web': farmacia.sitio_web,
        }
        for farmacia in farmacias
    ]

    return JsonResponse({'farmacias': datos})


@require_GET
def listar_precios(request):
    precios = Precio.objects.select_related(
        'producto',
        'farmacia'
    ).all().order_by('precio')

    datos = [
        {
            'id': precio.id,
            'producto': precio.producto.nombre,
            'medicamento': precio.producto.medicamento.nombre,
            'farmacia': precio.farmacia.nombre,
            'precio': precio.precio,
            'precio_normal': precio.precio_normal,
            'disponible': precio.disponible,
            'fecha_actualizacion': precio.fecha_actualizacion.isoformat(),
            'url_producto': precio.url_producto,
        }
        for precio in precios
    ]

    return JsonResponse({'precios': datos})

#api sencilla por ahora

@require_GET
def api_medicamentos(request):
    medicamentos = Medicamento.objects.all().values(
        'id',
        'nombre',
        'principio_activo',
    )
    
    return JsonResponse(
        list(medicamentos),
        safe=False,
        json_dumps_params={'ensure_ascii': False},
    )