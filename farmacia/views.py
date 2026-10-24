
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.shortcuts import render, get_object_or_404

from .models import Medicamento, Farmacia, Precio


def inicio(request):
    busqueda = request.GET.get('buscar', '').strip()

    medicamentos = Medicamento.objects.prefetch_related(
        'productos__precios__farmacia'
    ).order_by('nombre')
    
    no_encontrados = []

    if busqueda:
        #separadores explicito (coma, punto y coma o espacios)
        if any(separador in busqueda for separador in [',', ';', '\n']):
            terminos = [
                termino.strip()
                for termino in busqueda.replace(';', ',')
                .replace('\n', ',').split(',')
                if termino.strip()
            ]
        else:
            #busqueda completa
            terminos = [busqueda]
            
            #si la frase no coincide con ningun medicamento
            # se intenta reconocer varios nombre registrados
            
            coincidencia_completa = Medicamento.objects.filter(
                Q(nombre__icontains=busqueda) |
                Q(principio_activo__icontains=busqueda) |
                Q(productos__nombre__icontains=busqueda)   
            ).distinct().exists()
            
            if not coincidencia_completa:
                nombres = list(
                    Medicamento.objects.values_list('nombre', flat=True)
                )
                
                encontrados = [
                    nombre for nombre in nombres
                    if nombre.lower() in busqueda.lower()
                ]
                
                if len(encontrados) >= 2:
                    terminos = encontrados
                elif len(busqueda.split()) >= 2:
                    terminos = busqueda.split()
                elif encontrados:
                    terminos = encontrados
        
        medicamentos_encontrados = Medicamento.objects.none()
        
        for termino in terminos:
            resultados = Medicamento.objects.filter(
                Q(nombre__icontains=termino) |
                Q(principio_activo__icontains=termino) |
                Q(productos__nombre__icontains=termino)
            ).distinct()
            
            if resultados.exists():
                medicamentos_encontrados = (
                    medicamentos_encontrados | resultados
                )
            else:
                no_encontrados.append(termino)
        
        medicamentos = medicamentos.filter(
            pk__in=medicamentos_encontrados.values('pk')
        )

    contexto = {
        'medicamentos': medicamentos,
        'busqueda': busqueda,
        'no_encontrados': no_encontrados,
    }

    return render(request, 'inicio.html', contexto)


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


@require_GET
def listar_farmacias(request):
    farmacias = Farmacia.objects.all().order_by('nombre')

    datos = [
        {
            'id': farmacia.id,
            'nombre': farmacia.nombre,
            'direccion': farmacia.direccion,
            'latitud': (
                float(farmacia.latitud)
                if farmacia.latitud is not None
                else None
            ),
            'longitud': (
                float(farmacia.longitud)
                if farmacia.longitud is not None
                else None
            ),
            'sitio_web': farmacia.sitio_web,
        }
        for farmacia in farmacias
    ]

    return JsonResponse({'farmacias': datos})


@require_GET
def listar_precios(request):
    precios = Precio.objects.select_related(
        'producto',
        'farmacia',
        'producto__medicamento'
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
            'fecha_actualizacion': (
                precio.fecha_actualizacion.isoformat()
            ),
            'url_producto': precio.url_producto,
        }
        for precio in precios
    ]

    return JsonResponse({'precios': datos})


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