from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.core.paginator import Paginator
from django.contrib import messages
from django.core.validators import validate_email

import re
import unicodedata
import pytesseract

from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError

from PIL import Image, UnidentifiedImageError, ImageOps, ImageFilter
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django.contrib.auth import (
    authenticate,
    login,
    logout,
    get_user_model,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from django.contrib.auth.decorators import login_required

from .models import Medicamento, Farmacia, Producto, Precio, Sucursal
from itertools import combinations

from math import radians, sin, cos, sqrt, atan2

def inicio(request):
    busqueda = request.GET.get("buscar", "").strip()

    categoria_seleccionada = request.GET.get("categoria", "").strip()

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
        
        if categoria_seleccionada:
            productos = productos.filter(categoria=categoria_seleccionada)

    #Dejenlo en 6 o a lo mucho 9, la pagina se alarga demasiado si ponen muchos
    
    paginador = Paginator(productos, 9)
    pagina_obj = paginador.get_page(request.GET.get("pagina"))
    
    rango_paginas = paginador.get_elided_page_range(
        number=pagina_obj.number,
        on_each_side=2,
        on_ends=1
    )

    contexto = {
            "productos": pagina_obj,
            "pagina_obj": pagina_obj,
            "busqueda": busqueda,
            "categoria_seleccionada": categoria_seleccionada,
            "categorias": Producto.objects.exclude(
                categoria__isnull=True)
                .exclude(
                    categoria=""
                ).values_list(
                    "categoria", flat=True
                ).distinct().order_by("categoria"),
            "rango_paginas": rango_paginas
        }
    
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(
            request,
            "partials/catalogo.html",
            contexto,
        )
    
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
            "productos_detalle": productos,
            "farmacias_mapa": list(farmacias_mapa.values()),
        },
    )

def detalle_producto(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.prefetch_related(
            Prefetch(
                "precios",
                queryset=Precio.objects.select_related(
                    "farmacia"
                ).order_by("precio"),
            )
        ),
        id=producto_id,
    )

    # Preparar los datos para el mapa.
    farmacias_mapa = {}

    for precio in producto.precios.all():
        farmacia = precio.farmacia

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
            "medicamento": producto,
            "productos_detalle": [producto],
            "farmacias_mapa": list(farmacias_mapa.values()),
            "es_producto_independiente": True,
        },
    )

@require_GET
def listar_farmacias(request):
    sucursales = Sucursal.objects.select_related(
        "farmacia"
    ).filter(
        aprobada=True
    ).order_by("nombre")

    datos = [
        {
            "id": sucursal.id,
            "nombre": sucursal.nombre,
            "direccion": sucursal.direccion,
            "comuna": sucursal.comuna,
            "latitud": (
                float(sucursal.latitud)
                if sucursal.latitud is not None
                else None
            ),
            "longitud": (
                float(sucursal.longitud)
                if sucursal.longitud is not None
                else None
            ),
            "sitio_web": sucursal.sitio_web,
            "farmacia": (
                sucursal.farmacia.nombre
                if sucursal.farmacia
                else None
            ),
            "tiene_precios": sucursal.farmacia_id is not None,
            "origen": sucursal.origen,
        }
        for sucursal in sucursales
        if sucursal.latitud is not None
        and sucursal.longitud is not None
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



@require_http_methods(["GET", "POST"])
def vista_registro(request):
    User = get_user_model()

    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        nombre_completo = request.POST.get("nombre_completo", "").strip()
        correo = request.POST.get("correo", "").strip().lower()
        contrasena = request.POST.get("contrasena", "")
        confirmar = request.POST.get("confirmar-contrasena", "")

        partes_nombre = nombre_completo.split()

        if not nombre_completo or not correo or not contrasena or not confirmar:
            messages.error(request, "Todos los campos son obligatorios.")

        elif len(partes_nombre) < 2:
            messages.error(
                request,
                "Ingresa tu nombre y al menos un apellido."
            )

        elif len(correo) > 150:
            messages.error(
                request,
                "El correo electrónico no puede superar los 150 caracteres."
            )

        else:
            try:
                validate_email(correo)

                if User.objects.filter(email__iexact=correo).exists():
                    messages.error(
                        request,
                        "Ese correo electrónico ya está registrado."
                    )

                elif User.objects.filter(username__iexact=correo).exists():
                    messages.error(
                        request,
                        "Ese correo ya está registrado como usuario."
                    )

                elif contrasena != confirmar:
                    messages.error(
                        request,
                        "Las contraseñas no coinciden."
                    )

                else:
                    usuario = User(
                        username=correo,
                        email=correo,
                        first_name=partes_nombre[0],
                        last_name=" ".join(partes_nombre[1:])
                    )

                    validate_password(contrasena, user=usuario)

                    usuario = User.objects.create_user(
                        username=correo,
                        email=correo,
                        password=contrasena,
                        first_name=partes_nombre[0],
                        last_name=" ".join(partes_nombre[1:])
                    )

                    messages.success(
                        request,
                        "¡Tu cuenta fue creada correctamente! Ya puedes iniciar sesión."
                    )

                    return redirect("login")

            except ValidationError as errores:
                for error in errores.messages:
                    messages.error(request, error)

    return render(request, "registro.html")


@require_http_methods(["GET", "POST"])
def vista_login(request):

    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        correo = request.POST.get("correo", "").strip().lower()
        contrasena = request.POST.get("contrasena", "")

        User = get_user_model()

        usuario = User.objects.filter(
            email__iexact=correo
        ).first()

        if usuario:
            usuario_autenticado = authenticate(
                request,
                username=usuario.username,
                password=contrasena,
            )

            if usuario_autenticado is not None:
                login(request, usuario_autenticado)

                messages.success(
                    request,
                    f"¡Bienvenido/a, {usuario.first_name}!"
                )

                return redirect("inicio")

        messages.error(
            request,
            "Correo electrónico o contraseña incorrectos."
        )

    return render(request, "login.html")


@require_http_methods(["POST"])
def cerrar_sesion(request):
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("inicio")

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
    
    #mensaje = f"{producto.nombre} se agregó a tu lista"
    
    #si viene de javascript devuelve un json (who's json?)
    if request.headers.get("X-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            #"mensaje": mensaje,
            "cantidad": lista[producto_id]
        })
    
    messages.success(request)
    return redirect(request.META.get("HTTP_REFERER", "inicio"))

#agregar o quitar productos
@require_POST
def modificar_cantidad_lista(request, producto_id):
    lista = request.session.get("lista_medicamentos", {})
    producto_id = str(producto_id)
    
    accion = request.POST.get("accion")
    eliminado = False
    
    if producto_id in lista:
        if accion == "aumentar":
            lista[producto_id] += 1
        
        elif accion == "disminuir":
            lista[producto_id] -= 1
            
            if lista[producto_id] <= 0:
                del lista[producto_id]
    request.session["lista_medicamentos"] = lista
    return JsonResponse({
        "cantidad": lista.get(producto_id, 0),
        "eliminado": eliminado,
    })
    
#borrar la lista
@require_POST
def eliminar_de_lista(request, producto_id):
    lista = request.session.get("lista_medicamentos", {})
    producto_id = str(producto_id)
    
    lista.pop(producto_id, None)
    request.session["lista_medicamentos"] = lista
    return JsonResponse({"eliminado": True,})

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
        cantidad = lista.get(str(producto.id), 1)
        precios_disponibles = [
            precio for precio in producto.precios.all()
            if precio.disponible
        ]
        
        items.append({
            "producto": producto,
            "cantidad": lista.get(str(producto.id), 1),
            "precios_disponibles": precios_disponibles,
        })
    
    comparacion_farmacias = []
    
    farmacias = Farmacia.objects.all().order_by("nombre")
    
    for farmacia in farmacias:
        total = 0
        productos_faltantes = []
        
        for item in items:
            precio_farmacia = next(
                (
                    precio for precio in item["precios_disponibles"] 
                    if precio.farmacia_id == farmacia.id
                ), 
                None
            )

            if precio_farmacia:
                total += precio_farmacia.precio * item["cantidad"]
            else:
                productos_faltantes.append(
                    item["producto"].nombre
                )
        
        comparacion_farmacias.append({
            "farmacia": farmacia,
            "total": total,
            "productos_faltantes": productos_faltantes,
            "completa": len(productos_faltantes) == 0,
        })
        
    #selecciona el menor precio por producto
    total_menor_precio = 0
    productos_menor_precio = []
    productos_sin_precio = []
    
    for item in items:
        if item["precios_disponibles"]:
            mejor_precio = min(
                item["precios_disponibles"],
                key=lambda precio: precio.precio
            )
            
            subtotal = mejor_precio.precio * item["cantidad"]
            total_menor_precio += subtotal
            
            productos_menor_precio.append({
                "producto": item["producto"],
                "cantidad": item["cantidad"],
                "farmacia": mejor_precio.farmacia,
                "precio_unitario": mejor_precio.precio,
                "subtotal": subtotal
            })
        else:
            productos_sin_precio.append(item["producto"].nombre)
            
        
    return render(request, "lista_medicamentos.html", 
                  {
                      "items": items,
                      "comparacion_farmacias": comparacion_farmacias,
                      "total_menor_precio": total_menor_precio,
                      "productos_menor_precio": productos_menor_precio,
                      "productos_sin_precio": productos_sin_precio
                      })

@require_GET
def planificar_ruta(request):
    
    print("GET recibido:", request.GET)
    print("Latitud recibida:", request.GET.get("lat"))
    print("Longitud recibida:", request.GET.get("lon"))

    lista = request.session.get("lista_medicamentos", {})
    
    if not lista:
        return JsonResponse({
            "error": "Tu lista de productos esta vacía."
        }, status=400)
    
    #obtener coord del usuario
    lat_usuario = request.GET.get("lat")
    lon_usuario = request.GET.get("lon")

    if not lat_usuario or not lon_usuario:
        return JsonResponse({
            "error": "No se recibió la ubicación del usuario."
        }, status=400)

    try:
        lat_usuario = float(lat_usuario)
        lon_usuario = float(lon_usuario)
    except (TypeError, ValueError):
        return JsonResponse({
            "error": "Las coordenadas del usuario no son válidas."
        }, status=400)

    productos = Producto.objects.filter(
        id__in=lista.keys()
    ).prefetch_related(
        Prefetch(
            "precios",
            queryset=Precio.objects.filter().select_related("farmacia")
        )
    )
    
    #obtener farmacia que tienen precios
    farmacias_obj = {}

    for producto in productos:
        for precio in producto.precios.all():
            if precio.farmacia:
                farmacias_obj[precio.farmacia_id] = precio.farmacia
    
    #buscar sucursales aprobadas de esa farmacias
    sucursales = Sucursal.objects.filter(
        farmacia_id__in=farmacias_obj.keys(),
        aprobada=True,
        latitud__isnull=False,
        longitud__isnull=False,
    )

    #calcular distancia entre dos coords
    def calcular_distancia(lat1, lon1, lat2, lon2):
        radio_tierra = 6371

        lat1, lon1, lat2, lon2 = map(
            radians,
            [lat1, lon1, lat2, lon2]
        )

        diferencia_lat = lat2 - lat1
        diferencia_lon = lon2 - lon1

        a = (
            sin(diferencia_lat / 2) ** 2
            + cos(lat1) * cos(lat2)
            * sin(diferencia_lon / 2) ** 2
        )

        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return radio_tierra * c
    
    #Seleccionar la sucursal más cercana de cada farmacia
    farmacias = {}

    for farmacia_id, farmacia in farmacias_obj.items():

        sucursales_farmacia = [
            sucursal for sucursal in sucursales
            if sucursal.farmacia_id == farmacia_id
        ]

        if sucursales_farmacia:
            sucursal_cercana = min(
                sucursales_farmacia,
                key=lambda s: calcular_distancia(
                    lat_usuario,
                    lon_usuario,
                    float(s.latitud),
                    float(s.longitud)
                )
            )

            farmacias[farmacia_id] = {
                "id": farmacia.id,
                "nombre": sucursal_cercana.nombre,
                "nombre_sucursal": farmacia.nombre,
                "cadena": farmacia.nombre,
                "sucursal_id": sucursal_cercana.id,
                "direccion": sucursal_cercana.direccion,
                "comuna": sucursal_cercana.comuna,
                "latitud": float(sucursal_cercana.latitud),
                "longitud": float(sucursal_cercana.longitud)
            }
        #por si la farmacia no tiene sucursal registrada (no deberia pasar pero uno nunca sabe xd)
        elif farmacia.latitud is not None and farmacia.longitud is not None:
            farmacias[farmacia_id] = {
                "id": farmacia.id,
                "nombre": farmacia.nombre,
                "nombre_sucursal": farmacia.nombre,
                "cadena": farmacia.nombre,
                "sucursal_id": None,
                "direccion": farmacia.direccion,
                "comuna": "",
                "latitud": float(farmacia.latitud),
                "longitud": float(farmacia.longitud)
            }

    resultado = []

    
    for producto in productos:
        cantidad = lista.get(str(producto.id), 1)
        precios = []
        
        for precio in producto.precios.all():
            farmacia = precio.farmacia
            
            if not farmacia or farmacia.id not in farmacias:
                continue

            datos_farmacia = farmacias[farmacia.id]
            
            datos_precio = {
                "farmacia_id": farmacia.id,
                "farmacia": farmacia.nombre,
                "sucursal": datos_farmacia["nombre_sucursal"],
                "precio": float(precio.precio),
                "disponible": precio.disponible,
                "latitud": datos_farmacia["latitud"],
                "longitud": datos_farmacia["longitud"]
            }
            
            precios.append(datos_precio)
            

        resultado.append({
            "producto_id": producto.id,
            "nombre": producto.nombre,
            "cantidad": cantidad,
            "precios": precios
        })
        
    # DEBUG: revisar cobertura de productos
    print("\n========== DEBUG COBERTURA DE PRODUCTOS ==========")

    for producto in resultado:
        print(f"\nProducto: {producto['nombre']}")
        print(f"ID: {producto['producto_id']}")
        print(f"Cantidad de precios válidos: {len(producto['precios'])}")

        for precio in producto["precios"]:
            print(
                f"  - {precio['farmacia']}: "
                f"${precio['precio']}"
            )

        if not producto["precios"]:
            print("  !!! PRODUCTO SIN PRECIOS VÁLIDOS !!!")

    print("\nFarmacias disponibles para planificar:")
    for farmacia_id, farmacia in farmacias.items():
        print(f"  - {farmacia_id}: {farmacia['cadena']}")

    print("=================================================\n")
    
    #evalua TODAS las combinaciones de farmacias
    ids_farmacias = list(farmacias.keys())
    alternativas = []
    
    for cantidad_farmacias in range(1, len(ids_farmacias) + 1):
        for combinacion in combinations(
            ids_farmacias, cantidad_farmacias
        ):
            compras = {}
            total = 0
            combinacion_valida = True
            precios_sin_confirmar = 0
        
            for producto in resultado:
                opciones = [
                    precio for precio in producto["precios"]
                    if precio["farmacia_id"] in combinacion
                ]
                
                if not opciones:
                    combinacion_valida = False
                    break
                
                mejor_precio = min(
                    opciones,
                    key=lambda x: (
                        not x["disponible"],
                        x["precio"]
                    )
                )
                
                if not mejor_precio["disponible"]:
                    precios_sin_confirmar += 1
                
                subtotal = mejor_precio["precio"] * producto["cantidad"]
                total += subtotal
                
                farmacia_id = mejor_precio["farmacia_id"]
                
                if farmacia_id not in compras:
                    compras[farmacia_id] = {
                        "farmacia": farmacias[farmacia_id],
                        "productos": [],
                        "subtotal": 0
                    }
                    
                compras[farmacia_id]["productos"].append({
                    "producto": producto["nombre"],
                    "cantidad": producto["cantidad"],
                    "precio_unitario": mejor_precio["precio"],
                    "subtotal": subtotal,
                    "disponible": mejor_precio["disponible"]
                })
                
                compras[farmacia_id]["subtotal"] += subtotal
                
            if combinacion_valida:
                alternativas.append({
                    "total": total,
                    "compras": list(compras.values()),
                    "cantidad_farmacias": len(compras),
                    "precios_sin_confirmar": precios_sin_confirmar
                })
                
    if not alternativas:
        return JsonResponse({
            "error": "No hay suficientes precios disponibles para cubrir todos los productos."
        }, status=400)
    
    #buscar la alternativa más económica de una sola farmacia
    alternativas.sort(
        key=lambda x: (x["precios_sin_confirmar"], x["total"], x["cantidad_farmacias"])
    )
    
    mejor_general = alternativas[0]
    
    alternativas_una = [
        x for x in alternativas
        if x["cantidad_farmacias"] == 1
    ]
    
    alternativas_varias = [
        x for x in alternativas
        if x["cantidad_farmacias"] > 1
    ]
    
    mejor_una = alternativas_una[0] if alternativas_una else None
    mejor_dividida = alternativas_varias[0] if alternativas_varias else None
    
    #aplicar umbral de ahorro de 10% (si el ahorro es menos de 10 entonces ñao ñao)
    if mejor_una and mejor_dividida:
        ahorro = (
            (mejor_una["total"] - mejor_dividida["total"])
            / mejor_una["total"]
        ) * 100
        
        if ahorro >= 10:
            recomendacion = mejor_dividida
            criterio = "dividir_compra"
        else: 
            recomendacion = mejor_una
            criterio = "una_farmacia"
        
    elif mejor_una:
        ahorro = 0
        recomendacion = mejor_una
        criterio = "una_farmacia"
    
    else:
        ahorro = 0
        recomendacion = mejor_general
        criterio = "varias_farmacias_necesarias"
    
    return JsonResponse({
        "productos": resultado,
        "recomendacion": {
            "criterio": criterio,
            "total": round(recomendacion["total"], 2),
            "ahorro_porcentual": round(ahorro, 2),
            "cantidad_farmacias": recomendacion["cantidad_farmacias"],
            "compras": recomendacion["compras"]
        },
        "alternativas": {
            "una_farmacia": mejor_una,
            "varias_farmacias": mejor_dividida
        },
        "precios_sin_disponibilidad_confirmada": [
            {
                "producto": producto["nombre"],
                "farmacia": precio["farmacia"],
                "precio": precio["precio"]
            }
            for producto in resultado
            for precio in producto["precios"]
            if not precio["disponible"]
        ],
    })


@login_required(login_url='login')
def mi_cuenta(request):
    return render(request, 'mi_cuenta.html')


@login_required(login_url='login')
@require_http_methods(["GET", "POST"])
def editar_cuenta(request):

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()

        password_actual = request.POST.get("password_actual", "")
        nueva_password = request.POST.get("nueva_password", "")
        confirmar_password = request.POST.get("confirmar_password", "")

        if not nombre:
            messages.error(request, "El nombre no puede estar vacío.")
            return render(request, 'editar_cuenta.html')

        # Comprobar si quiere cambiar la contraseña
        quiere_cambiar_password = any([
            password_actual,
            nueva_password,
            confirmar_password
        ])

        if quiere_cambiar_password:

            if not all([
                password_actual,
                nueva_password,
                confirmar_password
            ]):
                messages.error(
                    request,
                    "Debes completar los tres campos de contraseña."
                )
                return render(request, 'editar_cuenta.html')

            if not request.user.check_password(password_actual):
                messages.error(request, "La contraseña actual es incorrecta.")
                return render(request, 'editar_cuenta.html')

            if nueva_password != confirmar_password:
                messages.error(request, "Las nuevas contraseñas no coinciden.")
                return render(request, 'editar_cuenta.html')

            try:
                validate_password(nueva_password, user=request.user)
            except ValidationError as errores:
                for error in errores:
                    messages.error(request, error)
                return render(request, 'editar_cuenta.html')

            request.user.set_password(nueva_password)
            request.user.save()


            # Mantener la sesión iniciada después del cambio
            update_session_auth_hash(request, request.user)

        request.user.first_name = nombre
        request.user.last_name = apellido
        request.user.save()

        messages.success(request, "Tus datos se actualizaron correctamente.")
        return redirect("mi_cuenta")

    return render(request, 'editar_cuenta.html')