FARMA PRICEY

Aplicación web desarrollada con Django para consultar medicamentos y comparar precios entre distintas farmacias. El proyecto permite consultar información de medicamentos, productos, farmacias y precios, y contempla la actualización automatizada de precios mediante módulos de extracción de datos.

1. Tecnologías utilizadas

Python

Django

HTML, CSS y JavaScript

PostgreSQL mediante Neon

Git y GitHub

GitHub Actions para la automatización de tareas

2. Requisitos previos

Antes de ejecutar el proyecto, se necesita tener instalado:

Python 3.12.

Git.

Acceso a la base de datos PostgreSQL configurada en Neon.

3. Instalación del proyecto

3.1. Crear el entorno virtual

Desde la carpeta raíz del proyecto, donde se encuentra manage.py, ejecutar:

python -m venv venv

3.2. Activar el entorno virtual

En Windows PowerShell:

.\venv\Scripts\Activate.ps1

3.3. Instalar las dependencias

python -m pip install -r requirements.txt

4. Configuración de variables de entorno

El proyecto utiliza un archivo .env para almacenar la configuración local necesaria para ejecutar Django y conectarse a la base de datos.

Crear el archivo .env en la ubicación que espera la configuración del proyecto.

Configurar las variables requeridas, incluyendo la conexión a PostgreSQL y la clave secreta de Django.

Verificar que Django cargue estas variables antes de iniciar la aplicación.

Los nombres de las variables deben coincidir con los utilizados en la configuración del proyecto.

Importante: el archivo .env contiene información sensible. No debe subirse al repositorio. Se recomienda incluirlo en .gitignore y mantener un archivo de ejemplo sin credenciales reales cuando sea necesario compartir la configuración.

5. Ejecución de la aplicación

Desde la carpeta que contiene manage.py, con el entorno virtual activado, ejecutar:

python manage.py runserver

Abrir la siguiente dirección en el navegador:

http://127.0.0.1:8000/

6. Endpoints de la API

La aplicación dispone de los siguientes endpoints de consulta:

Endpoint

Método HTTP

Descripción

/api/medicamentos/

GET

Devuelve una lista de medicamentos con su identificador, nombre y principio activo.

/api/farmacias/

GET

Devuelve información de las farmacias registradas.

/api/precios/

GET

Devuelve información de precios, productos, farmacias y disponibilidad.

Las tres rutas están destinadas a consultas mediante GET. Las peticiones POST se rechazan con el código HTTP 405 Method Not Allowed.

Las respuestas se entregan en formato JSON.

7. Pruebas automatizadas del backend

Para ejecutar las pruebas de la aplicación, utilizar:

python manage.py test farmacia

Django ejecuta las pruebas en una base de datos temporal, que se elimina al finalizar.

Las siete pruebas implementadas comprueban:

La respuesta de los tres endpoints.

El rechazo de peticiones POST.

El formato JSON de la API de medicamentos.

La presencia de un medicamento de prueba en la respuesta.

8. Actualización de precios

El proyecto dispone del comando actualizar_precios para consultar precios mediante los módulos de extracción de datos implementados.

8.1. Ejecutar una vista previa

python manage.py actualizar_precios

Este modo consulta los precios y muestra los resultados sin guardar las modificaciones en la base de datos.

8.2. Guardar los precios obtenidos

python manage.py actualizar_precios --guardar

Este modo guarda los precios válidos y actualiza los campos correspondientes según la lógica implementada en el comando.

Se recomienda revisar primero la vista previa para identificar posibles errores de extracción o datos inválidos.

9. Automatización con GitHub Actions

El repositorio cuenta con un flujo de GitHub Actions para ejecutar la actualización de precios de manera programada o manual.

El flujo instala las dependencias del proyecto y ejecuta el comando de actualización utilizando los secretos configurados en GitHub.

Para que la automatización funcione, los secretos requeridos deben estar configurados correctamente en el repositorio. Las credenciales no deben almacenarse directamente en el archivo de configuración del flujo.

10. Control de versiones

El código fuente y los cambios del proyecto se gestionan mediante Git y GitHub, lo que permite mantener el historial de modificaciones y facilitar la colaboración entre los integrantes del equipo.

------------
Configuración de OCR

El módulo de lectura de recetas utiliza Tesseract OCR para reconocer texto en imágenes, pytesseract para integrarlo con Python y Pillow para procesar imágenes.

Requisitos adicionales

Instalar Tesseract OCR en el sistema operativo. https://github.com/UB-Mannheim/tesseract/wiki?utm_source=chatgpt.com

Instalar los datos de idioma español (buscar el archivo spa.traineddata) (el archivo se debe copiar en la carperta tessdata de Tesseract-OCR). https://github.com/tesseract-ocr/tessdata?utm_source=chatgpt.com

Instalar las dependencias de Python mediante pip install -r requirements.txt.

Configurar la variable de entorno TESSERACT_CMD con la ruta del ejecutable tesseract.exe en Windows. En Linux o macOS, se puede utilizar la ruta del ejecutable disponible en el sistema.

Verificación

tesseract --version
tesseract --list-langs
python manage.py check

El repositorio contiene el código de integración, pero no incluye el ejecutable de Tesseract ni su instalación completa. Cada integrante debe instalar y configurar esta dependencia en su propio equipo.