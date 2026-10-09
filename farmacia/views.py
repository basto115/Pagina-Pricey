from django.shortcuts import render
from .models import Medicamento

# Create your views here.

def inicio(request):
    medicamentos = Medicamento.objects.prefetch_related(
        'productos__precios__farmacia'
    )
    
    contexto = {
        'medicamentos': medicamentos
    }
    
    return render(request, 'inicio.html', contexto)
