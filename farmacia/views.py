
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator

import re
import unicodedata
import pytesseract

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

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

    #mostrar 6 medicamentos por pagina
    paginador = Paginator(medicamentos, 6)
    pagina_obj = paginador.get_page(request.GET.get('pagina'))
    
    contexto = {
        'medicamentos': pagina_obj,
        'pagina_obj': pagina_obj,
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
    
def vista_login(request):
    return render(request, 'login.html')

def vista_resgitro(request):
    return render(request, 'registro.html')

def normalizar_texto(texto):
    texto = unicodedata.normalize("NFD", texto.casefold())
    texto = "".join(
        caracter for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    return re.sub(r"\s+", " ", texto).strip()

def extraer_concentraciones(texto):
    return re.findall(
        r"(?<!\w)\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|ug|ml|g|%)\b",
        texto.casefold()
    )

@require_http_methods(["GET", "POST"])
def leer_receta(request):
    contexto = {
        "resultado": [],
        "texto_reconocido": "",
        "error": "",
    }
    
    if request.method == "GET":
        return render(request, "leer_receta.html", contexto)
    
    archivo = request.FILES.get("receta")
    
    if not archivo:
        contexto["error"] = "Selecciona una imagen de la receta."
        return render(request, "leer_receta.html", contexto)
    
    if archivo.size > 5 * 1024 * 1024: 
        contexto["error"] = "La imagen no puede superar los 5 MB."
        return render(request, "leer_receta.html", contexto)
    
    if not archivo.content_type.startswith("image/"):
        contexto["error"] = "El archivo debe ser imagen."
        return render(request, "leer_receta.html", contexto)

    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen.verify()

        archivo.seek(0)
        imagen = Image.open(archivo).convert("RGB")

        if getattr(settings, "TESSERACT_CMD", None):
            pytesseract.pytesseract.tesseract_cmd = (
                settings.TESSERACT_CMD
            )

        texto = pytesseract.image_to_string(imagen, lang="spa")
        contexto["texto_reconocido"] = texto

    except pytesseract.TesseractNotFoundError:
        contexto["error"] = (
            "No se encontró Tesseract. Revisa su instalación y configuración."
        )
        return render(request, "leer_receta.html", contexto)

    except (UnidentifiedImageError, OSError, ValueError) as e:
        print(f"Error al abrir la receta: {e!r}")
        contexto["error"] = (
            "No se puede abrir la imagen. Prueba con otra."
        )
        return render(request, "leer_receta.html", contexto)

    except pytesseract.TesseractError:
        contexto["error"] = (
            "No se pudo reconocer el texto. Intenta con una imagen más clara."
        )
        return render(request, "leer_receta.html", contexto)
    
    texto_normalizado = normalizar_texto(texto)
    
    if not texto_normalizado:
        contexto["error"] = (
            "No se reconoció texto. Prueba con una imagen más nítida."
        )
        return render(request, "leer_receta.html", contexto)
    
    medicamentos = list(
        Medicamento.objects.prefetch_related(
            "productos__precios__farmacia"
        ).all()
    )
    
    candidatos = {}
    
    #buscar el nombre completo del medicamento 
    for medicamento in medicamentos:
        nombre = normalizar_texto(medicamento.nombre)
        
        productos = list(medicamento.productos.all())
        nombres_productos = [
            normalizar_texto(producto.nombre)
            for producto in productos
        ]
        
        if nombre in texto_normalizado or any(
            nombre_producto and nombre_producto in texto_normalizado
            for nombre_producto in nombres_productos
        ): 
            candidatos[medicamento.id] = {
                "medicamento": medicamento,
                "tipo": "Nombre reconocido",
                "confirmacion": False,
            }
        
        #si no reconoce el nombre, busca por principio activo 
        if not candidatos:
            principios = {
                normalizar_texto(m.principio_activo)
                for m in medicamentos
                if m.principio_activo
            }
            
            concentraciones = extraer_concentraciones(texto_normalizado)
            
            for principio in principios:
                if not re.search(
                    rf"(?<!\w){re.escape(principio)}(?!\w)",
                    texto_normalizado
                ):
                    continue
                
                grupo = [
                    m for m in medicamentos
                    if (
                        principio in normalizar_texto(m.nombre)
                        or normalizar_texto(m.principio_activo or "") == principio
                    )
                ]
                
                coincidencias = grupo
                
                if concentraciones:
                    por_concentracion = [
                        m for m in grupo
                        if any(
                            concentracion in normalizar_texto(m.nombre)
                            or any(
                                concentracion in normalizar_texto(p.nombre)
                                for p in m.productos.all()
                            )
                            for concentracion in concentraciones
                        )
                    ]
                    
                    if por_concentracion:
                        coincidencias = por_concentracion
                    
            for medicamento in coincidencias:
                candidatos[medicamento.id] = {
                    "medicamento": medicamento,
                    "tipo": (
                        "Principio activo y concentración"
                        if concentraciones
                        else "Coincidencia por principio activo"
                    ),
                    "confirmacion": True,
                }

    #adjunta el precio 
    
    for candidato in candidatos.values():
        medicamento = candidato["medicamento"]

        precios = Precio.objects.filter(
            producto__medicamento=medicamento
        ).select_related(
            "producto", "farmacia"
        ).order_by("precio")

        candidato["precios"] = list(precios)

    contexto["resultados"] = list(candidatos.values())

    return render(request, "leer_receta.html", contexto)
