from django.shortcuts import render
from .models import Medicamento

# Create your views here.

def inicio(request):
    medicamentos = Medicamento.objects.all()
    
    contexto = {
        'medicamentos': medicamentos
    }
    
    return render(request, 'inicio.html', contexto)


