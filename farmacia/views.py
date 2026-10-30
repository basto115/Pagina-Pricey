from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.core.paginator import Paginator
from django.contrib import messages

import re
import unicodedata
import pytesseract

from PIL import Image, UnidentifiedImageError, ImageOps, ImageFilter
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

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
    
    no_encontrados = []

    if busqueda:
        # Separadores explícitos: coma, punto y coma o salto de línea.
        if any (separador in busqueda for separador in [",", ";", "\n"]):
            terminos = [
                termino.strip()
                for termino in busqueda.replace(";", ",")
                .replace("\n", ",")
                .split(",")
                if termino.strip()
            ]
        else:
            #si intenta buscar el nombre completo
            terminos = [busqueda]
            
            coincidencia_completa = productos.filter(
                Q(nombre__icontains=busqueda)
                | Q(medicamento__nombre__icontains=busqueda)
                | Q(medicamento__principio_activo__icontains=busqueda)
                | Q(presentacion__icontains=busqueda)
                | Q(laboratorio__icontains=busqueda)
                | Q(categoria__icontains=busqueda)
            ).exists()
            
            #si no lo encuentra intenta detectar varios productos 
            
            if not coincidencia_completa:
                nombres = list(
                    Medicamento.objects.exclude(nombre="")
                    .values_list("nombre", flat=True)
                    .distinct()
                )
                
                encontrados = [
                    nombre
                    for nombre in nombres
                    if nombre.lower() in busqueda.lower()
                ]
                
                if len(encontrados) >= 2:
                    terminos = encontrados
                elif encontrados:
                    terminos = encontrados
                elif len(busqueda.split()) >= 2:
                    terminos = busqueda.split()
                
        #busca cualquiera que coincida con el termino
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
                

    #Dejenlo en 6 o a lo mucho 9, la pagina se alarga demasiado si ponen muchos
    
    paginador = Paginator(productos, 6)
    pagina_obj = paginador.get_page(request.GET.get("pagina"))

    contexto = {
            "productos": pagina_obj,
            "pagina_obj": pagina_obj,
            "busqueda": busqueda,
        }
    
    return render(
        request,
        "inicio.html",
        contexto,
    )



def detalle_medicamento(request, medicamento_id):
    medicamento = get_object_or_404(
        Medicamento.objects.prefetch_related(
            Prefetch(
                "productos",
                queryset=Producto.objects.prefetch_related(
                    Prefetch(
                        "precios",
                        queryset=Precio.objects.select_related(
                            "farmacia"
                        ).order_by("precio"),
                    )
                ),
            )
        ),
        id=medicamento_id,
    )

    # Preparar los datos que necesita el mapa.
    farmacias_mapa = {}
    productos = list(medicamento.productos.all())

    for producto in productos:
        for precio in producto.precios.all():
            farmacia = precio.farmacia

            # Sin coordenadas no podemos situar la farmacia en el mapa.
            if farmacia.latitud is None or farmacia.longitud is None:
                continue

            if farmacia.id not in farmacias_mapa:
                farmacias_mapa[farmacia.id] = {
                    "id": farmacia.id,
                    "nombre": farmacia.nombre,
                    "direccion": farmacia.direccion,
                    "latitud": float(farmacia.latitud),
                    "longitud": float(farmacia.longitud),
                    "productos": [],
                }

            farmacias_mapa[farmacia.id]["productos"].append({
                "producto_id": producto.id,
                "producto_nombre": producto.nombre,
                "precio": str(precio.precio),
                "disponible": precio.disponible,
                "url_producto": precio.url_producto,
            })

    return render(
        request,
        "detalle_medicamento.html",
        {
            "medicamento": medicamento,
            "farmacias_mapa": list(farmacias_mapa.values()),
        },
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
        "resultados": [],
        "texto_reconocido": "",
        "error": "",
        "farmacias_mapa": [],
    }
    
    if request.method == "GET":
        return render(request, "leer_receta.html", contexto)
    
    archivo = request.FILES.get("receta")
    
    if not archivo:
        contexto["error"] = "Selecciona una imagen de la receta."
        return render(request, "leer_receta.html", contexto)
    
    if archivo.size > 10 * 1024 * 1024: 
        contexto["error"] = "La imagen no puede superar los 10 MB."
        return render(request, "leer_receta.html", contexto)
    
    if not archivo.content_type.startswith("image/"):
        contexto["error"] = "El archivo debe ser imagen."
        return render(request, "leer_receta.html", contexto)

    #para que lea las imagenes
    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen.verify()

        archivo.seek(0)
        imagen = Image.open(archivo).convert("RGB")
        
        #aumenta el tamaño para que no le cueste
        ancho, alto = imagen.size
        imagen = imagen.resize((ancho * 2, alto * 2))
        
        #convierte la escala a grises y la mejora
        imagen = ImageOps.grayscale(imagen)
        imagen = ImageOps.autocontrast(imagen)
        
        #elimina irregularidades (no se bien a que se refiere)
        imagen = imagen.filter(ImageFilter.SHARPEN)
        
        #convierte a blanco y negro
       # imagen = imagen.point(
       #     lambda pixel: 255 if pixel > 160 else 0
        #)

        if getattr(settings, "TESSERACT_CMD", None):
            pytesseract.pytesseract.tesseract_cmd = (
                settings.TESSERACT_CMD
            )

        texto = pytesseract.image_to_string(imagen, lang="spa", config="--psm 6")

        #separa el texto reconocido en lineas  
        lineas_receta = [
            normalizar_texto(linea)
            for linea in texto.splitlines()
            if linea.strip()
        ]       
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

    print("OCR NORMALIZADO:", repr(texto_normalizado))

    for medicamento in medicamentos:
        print(
            "MEDICAMENTO BD:",
            repr(medicamento.nombre),
            "->",
            repr(normalizar_texto(medicamento.nombre))
        )
    
    #buscar el nombre completo del medicamento 
    for medicamento in medicamentos:
        nombre = normalizar_texto(medicamento.nombre)
        
        productos = list(medicamento.productos.all())
        nombres_productos = [
            normalizar_texto(producto.nombre)
            for producto in productos
        ]
        
        nombre_encontrado = (
            bool(nombre) and nombre in texto_normalizado
        ) or any(
            nombre_producto
            and nombre_producto in texto_normalizado
            for nombre_producto in nombres_productos
        )

        palabras_nombre = nombre.split()

        if not nombre_encontrado and palabras_nombre:
            nombre_base = palabras_nombre[0]

            concentraciones = extraer_concentraciones(texto_normalizado)

            if (
                nombre_base in texto_normalizado
                and any(
                    concentracion in nombre
                    for concentracion in concentraciones
                )
            ):
                nombre_encontrado = True
            
        if nombre_encontrado:
            candidatos[medicamento.id] = {
                "medicamento": medicamento,
                "tipo": "Nombre reconocido",
                "confirmacion": False,
            }
        
            #busca por principio activo
                
        concentraciones = extraer_concentraciones(texto_normalizado)

        principios = {
            normalizar_texto(m.principio_activo)
            for m in medicamentos
            if m.principio_activo
        }


            
        for principio in principios:
                if not principio:
                    continue

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
                
                #no volver a agregar medicamentos encontrados por nombre
                pendientes = [
                    m for m in grupo
                    if m.id not in candidatos
                ]
                
                if concentraciones:
                    por_concentracion = [
                        m for m in pendientes
                        if any(
                            concentracion in normalizar_texto(m.nombre)
                            or any(
                                concentracion in normalizar_texto(p.nombre)
                                for p in m.productos.all()
                            )
                            for concentracion in concentraciones
                        )
                    ]
                    
                    pendientes = por_concentracion
                        

                 
        for medicamento in pendientes:
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

    print("TEXTO OCR:", texto)
    print("CANDIDATOS:", [
        c["medicamento"].nombre
        for c in candidatos.values()
    ])

    #mostrar medicamentos no encontrados
    no_encontrados = []

    for linea in lineas_receta:
        concentraciones_linea = extraer_concentraciones(linea)

        if not concentraciones_linea:
            continue

        coincidencia = False

        for medicamento in medicamentos:
            nombre = normalizar_texto(medicamento.nombre)
            principio = normalizar_texto(medicamento.principio_activo or "")
            nombres = [nombre, principio]

            nombres.extend(
                normalizar_texto(producto.nombre)
                for producto in medicamento.productos.all()
            )

            palabras_clave = [
                n.split()[0]
                for n in nombres
                if n
            ]

            nombre_en_linea = any(
                palabra in linea.split()
                for palabra in palabras_clave
            )

            concentracion_en_catalogo = any(
                concentracion in nombre
                for nombre in nombres
                for concentracion in concentraciones_linea
            )

            if nombre_en_linea and concentracion_en_catalogo:
                coincidencia = True
                break
        if not coincidencia and linea not in no_encontrados:
            no_encontrados.append(linea)
    

    contexto["no_encontrados"] = no_encontrados

    contexto["resultados"] = list(candidatos.values())

    

    # Preparar las farmacias para el mapa de la receta.
    farmacias_mapa = {}

    for resultado in contexto["resultados"]:
        medicamento = resultado["medicamento"]

        for precio in resultado["precios"]:
            farmacia = precio.farmacia

            # Omitir farmacias sin coordenadas.
            if farmacia.latitud is None or farmacia.longitud is None:
                continue

            if farmacia.id not in farmacias_mapa:
                farmacias_mapa[farmacia.id] = {
                    "id": farmacia.id,
                    "nombre": farmacia.nombre,
                    "direccion": farmacia.direccion,
                    "latitud": float(farmacia.latitud),
                    "longitud": float(farmacia.longitud),
                    "productos": [],
                }

            farmacias_mapa[farmacia.id]["productos"].append({
                "medicamento": medicamento.nombre,
                "producto": precio.producto.nombre,
                "precio": str(precio.precio),
                "disponible": precio.disponible,
                "url_producto": precio.url_producto,
            })

    contexto["farmacias_mapa"] = list(farmacias_mapa.values())

    return render(request, "leer_receta.html", contexto)

#lista de producto (no es un carrito)
@require_POST
def agregar_a_lista(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    lista = request.session.get("lista_medicamentos", {})
    
    producto_id = str(producto.id)
    
    cantidad_actual = lista.get(producto_id, 0)
    lista[producto_id] = cantidad_actual + 1
    
    request.session["lista_medicamentos"] = lista
    
    messages.success(request, f"{producto.nombre} se agregó a tu lista")
    
    return redirect(request.META.get("HTTP_REFERER", "inicio"))

#agregar o quitar productos
@require_POST
def modificar_cantidad_lista(request, producto_id):
    lista = request.session.get("lista_medicamentos", {})
    producto_id = str(producto_id)
    
    accion = request.POST.get("accion")
    
    if producto_id in lista:
        if accion == "aumentar":
            lista[producto_id] += 1
        
        elif accion == "disminuir":
            lista[producto_id] -= 1
            
            if lista[producto_id] <= 0:
                del lista[producto_id]
    request.session["lista_medicamentos"] = lista
    return redirect("ver_lista")

#borrar la lista
@require_POST
def eliminar_de_lista(request, producto_id):
    lista = request.session.get("lista_medicamentos", {})
    producto_id = str(producto_id)
    
    lista.pop(producto_id, None)
    request.session["lista_medicamentos"] = lista
    return redirect("ver_lista")

#para ver la lista... por eso se llama ver_lista...
def ver_lista(request):
    lista = request.session.get("lista_medicamentos", {})
    
    productos = Producto.objects.filter(
        id__in=lista.keys()
    ).prefetch_related(
        Prefetch(
            "precios",
            queryset=Precio.objects.select_related(
                "farmacia"
            ).order_by("precio")
        )
    )
    
    items = []
    
    for producto in productos:
        items.append({
            "producto": producto,
            "cantidad": lista.get(str(producto.id), 1),
        })
        
    return render(request, "lista_medicamentos.html", {"items": items,})
    