from django.shortcuts import render
from django.db.models import Q
from .models import Medicamento

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