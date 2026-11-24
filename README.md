FARMA PRICEY

Aplicación web desarrollada con Django que permite consultar medicamentos y comparar sus precios entre distintas cadenas de farmacias en Chile.

FARMA PRICEY busca facilitar el acceso a información sobre medicamentos, permitiendo consultar productos, comparar precios, localizar sucursales cercanas, planificar rutas de compra y reconocer medicamentos a partir de imágenes de recetas mediante OCR.

1. Funcionalidades

Búsqueda de medicamentos: permite buscar por nombre, principio activo y coincidencias parciales.

Comparación de precios: consulta y compara los precios de medicamentos entre Cruz Verde, Salcobrand, Farmacia Ahumada y Dr. Simi.

Detalle de medicamentos: muestra información del medicamento, productos disponibles, precios por farmacia y enlaces a las tiendas.

Mi lista: permite agregar medicamentos, modificar cantidades y eliminar productos de una lista.

Comparación de compra: calcula el costo de los productos agrupados por farmacia y permite identificar alternativas de compra al menor precio.

Geolocalización: permite obtener la ubicación del usuario mediante el navegador y visualizar sucursales cercanas.

Mapas y rutas: muestra las farmacias disponibles en el mapa y permite planificar rutas de compra según los medicamentos de la lista.

Reconocimiento de recetas (OCR): permite cargar imágenes de recetas médicas para extraer los nombres de los medicamentos mediante reconocimiento óptico de caracteres.

Registro e inicio de sesión: permite crear cuentas de usuario e iniciar sesión en la plataforma.

Recuperación de contraseña: permite solicitar la recuperación de contraseña mediante correo electrónico.

2. Tecnologías utilizadas

Tecnología

Uso

Python 3.12

Lenguaje principal del proyecto.

Django 6.1.1

Framework para el desarrollo backend.

PostgreSQL

Sistema de gestión de base de datos.

Neon

Servicio de base de datos PostgreSQL en la nube.

HTML5

Estructura de las páginas web.

CSS3

Diseño y estilos de la interfaz.

JavaScript

Interactividad y funcionalidades dinámicas del frontend.

Bootstrap

Diseño adaptable y componentes de interfaz.

Django REST Framework

Desarrollo de endpoints para la consulta de información.

Leaflet

Visualización de mapas interactivos.

OpenStreetMap

Fuente de información geográfica y cartográfica.

Leaflet Routing Machine

Planificación y visualización de rutas.

Leaflet MarkerCluster

Agrupación de marcadores de sucursales en el mapa.

Tesseract OCR

Reconocimiento de texto en imágenes de recetas.

Pytesseract

Integración de Tesseract con Python.

Pillow

Procesamiento de imágenes para el reconocimiento OCR.

BeautifulSoup

Procesamiento y extracción de información durante el scraping.

Requests

Solicitudes HTTP para la obtención de información.

Docker

Contenerización de la aplicación.

Gunicorn

Servidor WSGI para ejecutar Django en producción.

WhiteNoise

Gestión y publicación de archivos estáticos en producción.

Git y GitHub

Control de versiones y almacenamiento del código fuente.

GitHub Actions

Automatización de tareas de actualización de precios.

Render

Plataforma de despliegue de la aplicación.

3. Requisitos previos

Para ejecutar el proyecto localmente se necesita:

Python 3.12 o superior.

PostgreSQL o una base de datos PostgreSQL alojada en Neon.

Git.

Tesseract OCR instalado en el sistema.

Un navegador web actualizado.

4. Instalación y configuración

4.1 Clonar el repositorio

git clone URL_DEL_REPOSITORIO
cd Pagina-Pricey

4.2 Crear y activar el entorno virtual

python -m venv venv

En Windows:

venv\Scripts\activate

En Linux o macOS:

source venv/bin/activate

4.3 Instalar dependencias

pip install -r requirements.txt

4.4 Configurar variables de entorno

Crear un archivo .env en la raíz del proyecto con las siguientes variables:

# Django
SECRET_KEY=tu_clave_secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos
DATABASE_URL=tu_url_de_postgresql

# Tesseract OCR (ruta de instalación en Windows)
TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"

# Correo electrónico
EMAIL_HOST=tu_servidor_smtp
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo
EMAIL_HOST_PASSWORD=tu_contraseña
DEFAULT_FROM_EMAIL=tu_correo

Nota: La variable DATABASE_URL debe contener la URL de conexión a la base de datos PostgreSQL. En producción, las variables se configuran directamente en el entorno de Render.

La variable TESSERACT_CMD debe apuntar a la ubicación del ejecutable de Tesseract en el entorno local. En Docker y Render se utiliza tesseract.

4.5 Aplicar migraciones

python manage.py migrate

4.6 Ejecutar el servidor

python manage.py runserver

La aplicación estará disponible en:

http://127.0.0.1:8000/

5. API REST

El proyecto cuenta con endpoints para consultar información relacionada con medicamentos, farmacias y precios.

Endpoint

Descripción

/api/medicamentos/

Consulta los medicamentos registrados.

/api/farmacias/

Consulta las sucursales de farmacias disponibles.

/api/precios/

Consulta los precios registrados de los productos.

Los endpoints permiten obtener información mediante solicitudes HTTP GET.

6. Pruebas

El proyecto cuenta con pruebas automatizadas para verificar el funcionamiento de diferentes componentes del sistema, incluyendo:

Modelos y relaciones entre entidades.

Consultas y búsqueda de medicamentos.

Gestión de productos y precios.

Endpoints de la API.

Funcionalidades principales de la aplicación.

Para ejecutar las pruebas:

python manage.py test farmacia

7. Scraping y actualización de información

FARMA PRICEY incorpora procesos de extracción de información desde los sitios web de las cadenas de farmacias para obtener productos y actualizar sus precios.

Las farmacias consideradas son:

Cruz Verde.

Salcobrand.

Farmacia Ahumada.

Dr. Simi.

7.1 Importar productos

El comando actualizar_productos permite obtener e importar productos desde las fuentes configuradas para cada farmacia.

Ejemplo:

python manage.py actualizar_productos --farmacia Ahumada --limite 1000 --guardar

7.2 Actualizar precios

El comando actualizar_precios permite consultar los precios de los productos registrados.

Para ejecutar una actualización y guardar los cambios:

python manage.py actualizar_precios --guardar

7.3 Automatización con GitHub Actions

El proyecto utiliza GitHub Actions para automatizar la ejecución del proceso de actualización de precios mediante el flujo de trabajo:

.github/workflows/actualizar-precios.yml

Este proceso permite ejecutar periódicamente la actualización de precios de las farmacias configuradas, además de permitir su ejecución manual desde GitHub Actions.

8. Reconocimiento de recetas mediante OCR

El sistema incorpora reconocimiento óptico de caracteres (OCR) mediante Tesseract, integrado con Python a través de Pytesseract.

Esta funcionalidad permite cargar imágenes de recetas médicas y extraer el texto presente en ellas, identificando los nombres de los medicamentos para facilitar su búsqueda dentro de la plataforma.

Se utiliza Pillow para el procesamiento de las imágenes y Tesseract OCR con soporte para el idioma español.

9. Arquitectura del sistema

FARMA PRICEY utiliza el patrón arquitectónico MVT (Model-View-Template) proporcionado por Django.

Model: administra los datos y las relaciones entre medicamentos, productos, precios, farmacias y sucursales.

View: procesa las solicitudes, ejecuta la lógica de negocio y entrega la información correspondiente.

Template: presenta la información al usuario mediante las interfaces desarrolladas con HTML, CSS y JavaScript.

Esta arquitectura permite mantener separada la gestión de datos, la lógica de la aplicación y la presentación de la información.

10. Docker

El proyecto incorpora Docker para contenerizar la aplicación y facilitar su ejecución en distintos entornos.

El Dockerfile utiliza una imagen base de Python 3.12-slim e instala las dependencias necesarias para ejecutar Django y Tesseract OCR, incluyendo el soporte para el idioma español.

También se utiliza un archivo .dockerignore para excluir archivos y directorios que no deben incorporarse a la imagen, como el entorno virtual, archivos .env, cachés y archivos temporales.

10.1 Construir la imagen

docker build -t farma-pricey .

10.2 Ejecutar el contenedor

docker run --rm --env-file .env -p 8000:10000 farma-pricey

En caso de utilizar una configuración local de Tesseract con una ruta de Windows en el archivo .env, se puede sobrescribir la variable al ejecutar el contenedor:

docker run --rm --env-file .env -e TESSERACT_CMD=tesseract -p 8000:10000 farma-pricey

La aplicación estará disponible en:

http://localhost:8000/

11. Despliegue en Render

FARMA PRICEY se encuentra desplegado en Render utilizando Docker como entorno de ejecución y Neon como servicio de base de datos PostgreSQL.

La configuración de producción contempla:

Docker: construcción de la imagen con las dependencias necesarias para ejecutar la aplicación.

Python 3.12: entorno de ejecución del proyecto.

Gunicorn: servidor WSGI encargado de ejecutar Django.

WhiteNoise: gestión de archivos estáticos.

Tesseract OCR: instalado dentro del contenedor, con soporte para el idioma español.

Neon: almacenamiento de la información mediante PostgreSQL.

Variables de entorno: configuración de claves, conexión a la base de datos y credenciales de correo electrónico.

Las variables sensibles se configuran desde el apartado de Environment de Render, evitando almacenarlas directamente en el repositorio.

12. Control de versiones

El proyecto utiliza Git para el control de versiones y GitHub como plataforma de almacenamiento y colaboración.

Para obtener los últimos cambios:

git pull origin main

Para registrar nuevos cambios:

git add .
git commit -m "Descripción de los cambios"
git push origin main
