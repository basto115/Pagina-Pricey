# FARMA PRICEY

Aplicación web desarrollada con **Django** que permite consultar medicamentos y comparar sus precios entre distintas cadenas de farmacias en Chile.

FARMA PRICEY busca facilitar el acceso a información sobre medicamentos, permitiendo consultar productos, comparar precios, localizar sucursales cercanas y reconocer medicamentos a partir de imágenes de recetas médicas.

## 1. Funcionalidades principales

- **Búsqueda de medicamentos:** búsqueda por nombre comercial, principio activo y coincidencias parciales.
- **Comparación de precios:** consulta y comparación de precios entre Cruz Verde, Salcobrand, Farmacia Ahumada y Dr. Simi.
- **Detalle de medicamentos:** información de medicamentos, presentaciones, productos asociados y precios disponibles.
- **Mi lista:** permite agregar medicamentos, modificar cantidades y comparar el costo de una compra entre farmacias.
- **Mapas y geolocalización:** visualización de sucursales, ubicación del usuario y planificación de rutas de compra.
- **Lectura de recetas médicas (OCR):** reconocimiento de texto en imágenes de recetas mediante Tesseract OCR y búsqueda de medicamentos coincidentes en el catálogo.
- **Autenticación de usuarios:** registro e inicio de sesión, con funcionalidades premium.
- **Actualización de información:** extracción e incorporación de productos y actualización automatizada de precios.

## 2. Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python 3.12 | Lenguaje principal |
| Django | Framework backend |
| HTML5, CSS3 y JavaScript | Desarrollo frontend |
| PostgreSQL | Base de datos |
| Neon | Servicio de base de datos PostgreSQL |
| Git y GitHub | Control de versiones |
| GitHub Actions | Automatización de actualizaciones |
| BeautifulSoup | Extracción y procesamiento de información |
| Playwright | Automatización de navegación durante el scraping |
| Pillow | Procesamiento de imágenes |
| Tesseract OCR | Reconocimiento de texto en recetas |
| pytesseract | Integración de Tesseract con Python |
| Leaflet | Mapas interactivos |
| Docker | Contenerización de la aplicación |
| Gunicorn | Servidor de aplicaciones Django |
| WhiteNoise | Administración de archivos estáticos |

## 3. Requisitos previos

Para ejecutar el proyecto localmente se necesita:

- Python 3.12.
- Git.
- Acceso a una base de datos PostgreSQL configurada en Neon.
- Tesseract OCR con el idioma español, para utilizar la lectura de recetas.
- Docker Desktop, si se desea ejecutar el proyecto mediante contenedores.

## 4. Instalación del proyecto

### 4.1. Clonar el repositorio

```bash
git clone https://github.com/basto115/Pagina-Pricey.git
```

Ingresar a la carpeta del proyecto:

```bash
cd Pagina-Pricey
```

### 4.2. Crear el entorno virtual

```bash
python -m venv venv
```

### 4.3. Activar el entorno virtual

En Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4.4. Instalar las dependencias

```bash
python -m pip install -r requirements.txt
```

### 4.5. Configurar las variables de entorno

Crear un archivo `.env` en la raíz del proyecto, donde se encuentra `manage.py`.

Configurar las variables necesarias:

```env
SECRET_KEY=tu_clave_secreta
DEBUG=True
DATABASE_URL=tu_url_de_conexion_postgresql
ALLOWED_HOSTS=localhost,127.0.0.1
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Si se utiliza el envío de correos electrónicos mediante SMTP, también se deben configurar:

```env
EMAIL_HOST=servidor_smtp
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=usuario_smtp
EMAIL_HOST_PASSWORD=clave_smtp
DEFAULT_FROM_EMAIL=correo_remitente
```

Las variables deben coincidir con las utilizadas en `config/settings.py`.

**Importante:** El archivo `.env` contiene credenciales e información sensible. No debe subirse al repositorio ni compartirse públicamente.

## 5. Base de datos y migraciones

El proyecto utiliza PostgreSQL alojado en Neon.

Una vez configurada la conexión mediante `DATABASE_URL`, ejecutar:

```bash
python manage.py migrate
```

Para crear un usuario administrador:

```bash
python manage.py createsuperuser
```

La base de datos de Neon contiene la información persistente del proyecto. El archivo SQLite local no se utiliza como base de datos principal.

## 6. Ejecución de la aplicación

Con el entorno virtual activado y las variables de entorno configuradas, ejecutar:

```bash
python manage.py runserver
```

Abrir en el navegador:

```text
http://127.0.0.1:8000/
```

## 7. API REST

La aplicación dispone de los siguientes endpoints de consulta:

| Endpoint | Método HTTP | Descripción |
|---|---|---|
| `/api/medicamentos/` | GET | Devuelve medicamentos con su identificador, nombre y principio activo. |
| `/api/farmacias/` | GET | Devuelve información de las farmacias registradas. |
| `/api/precios/` | GET | Devuelve información de precios, productos, farmacias y disponibilidad. |

Los tres endpoints están destinados a consultas mediante GET. Las peticiones POST son rechazadas con el código HTTP `405 Method Not Allowed`.

Las respuestas se entregan en formato JSON.

## 8. Pruebas automatizadas del backend

Para ejecutar las pruebas de Django:

```bash
python manage.py test farmacia
```

Las siete pruebas implementadas comprueban:

- La respuesta de los tres endpoints.
- El rechazo de peticiones POST.
- El formato JSON de la API de medicamentos.
- La presencia de un medicamento de prueba en la respuesta.

Django utiliza una base de datos temporal para ejecutar las pruebas, que se elimina al finalizar.

## 9. Extracción y actualización de datos

El proyecto dispone de comandos de Django para incorporar productos y actualizar precios de las distintas cadenas de farmacias.

### 9.1. Actualización de productos

El comando `actualizar_productos` permite extraer e incorporar productos desde las fuentes disponibles.

Ejemplo:

```bash
python manage.py actualizar_productos --farmacia Ahumada --limite 20000 --guardar
```

El parámetro `--farmacia` permite seleccionar la cadena de farmacias y `--limite` establecer la cantidad máxima de productos a procesar.

El parámetro `--guardar` permite almacenar los resultados en la base de datos.

### 9.2. Actualización de precios

El comando `actualizar_precios` permite consultar los precios de los productos registrados.

Vista previa, sin guardar modificaciones:

```bash
python manage.py actualizar_precios
```

Guardar los precios obtenidos:

```bash
python manage.py actualizar_precios --guardar
```

Se recomienda revisar primero la vista previa para identificar posibles errores de extracción o datos inválidos.

## 10. Automatización con GitHub Actions

El repositorio cuenta con un flujo de GitHub Actions para ejecutar actualizaciones de precios de manera programada o manual.

Archivo de configuración:

```text
.github/workflows/actualizar-precios.yml
```

El flujo instala las dependencias necesarias y ejecuta el comando de actualización utilizando los secretos configurados en GitHub.

Para que la automatización funcione, las credenciales requeridas deben estar configuradas en los secretos del repositorio.

No se deben almacenar contraseñas ni credenciales directamente en los archivos de configuración del flujo.

## 11. Configuración de OCR

El módulo de lectura de recetas utiliza:

- **Tesseract OCR:** motor de reconocimiento de texto.
- **pytesseract:** integración de Tesseract con Python.
- **Pillow:** procesamiento y mejora de imágenes.

El sistema procesa imágenes de recetas médicas, mejora su contraste y aplica reconocimiento de texto utilizando el idioma español.

### 11.1. Instalación en Windows

Instalar Tesseract OCR desde:

https://github.com/UB-Mannheim/tesseract/wiki

Instalar los datos de idioma español (`spa.traineddata`) desde:

https://github.com/tesseract-ocr/tessdata

El archivo debe estar ubicado en la carpeta `tessdata` de la instalación de Tesseract.

Configurar la ruta del ejecutable en el archivo `.env`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 11.2. Verificación de la instalación

Comprobar que Tesseract esté disponible:

```bash
tesseract --version
```

Comprobar los idiomas instalados:

```bash
tesseract --list-langs
```

Debe aparecer `spa` entre los idiomas disponibles.

## 12. Ejecución mediante Docker

El proyecto incluye un `Dockerfile` y un `.dockerignore` para construir y ejecutar la aplicación en un entorno Linux mediante contenedores.

La imagen Docker incorpora:

- Python 3.12.
- Dependencias del proyecto.
- Tesseract OCR.
- Datos de idioma español.
- Configuración de archivos estáticos mediante WhiteNoise.
- Gunicorn como servidor de aplicaciones.

### 12.1. Construir la imagen

Desde la raíz del proyecto:

```bash
docker build -t farma-pricey .
```

### 12.2. Verificar Tesseract dentro del contenedor

```bash
docker run --rm farma-pricey tesseract --version
```

Comprobar los idiomas disponibles:

```bash
docker run --rm farma-pricey tesseract --list-langs
```

### 12.3. Ejecutar la aplicación

En Windows, si el archivo `.env` contiene una ruta de Tesseract propia del sistema operativo, utilizar:

```powershell
docker run --rm --env-file .env -e TESSERACT_CMD=tesseract -p 8000:10000 farma-pricey
```

Abrir:

```text
http://localhost:8000/
```

El servidor permanece ejecutándose mientras el contenedor esté activo. Para detenerlo, presionar `Ctrl + C` en la terminal.

**Importante:** El contenedor ejecuta las migraciones de Django al iniciar. Debe verificarse que `DATABASE_URL` apunte a la base de datos correcta antes de ejecutarlo.

## 13. Despliegue en Render

La aplicación está preparada para desplegarse mediante Docker en Render, utilizando Neon como servicio de base de datos PostgreSQL.

La configuración de producción requiere las siguientes variables de entorno:

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django. |
| `DEBUG` | Debe establecerse en `False`. |
| `DATABASE_URL` | URL de conexión a PostgreSQL en Neon. |
| `ALLOWED_HOSTS` | Dominios autorizados para Django. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS autorizados para solicitudes CSRF. |
| `TESSERACT_CMD` | Ejecutable de Tesseract; utilizar `tesseract`. |

Si se utiliza SMTP, también deben configurarse las variables correspondientes al servicio de correo.

La aplicación utiliza Gunicorn para atender solicitudes y WhiteNoise para servir archivos estáticos.

El `Dockerfile` se encarga de instalar las dependencias del sistema, recopilar los archivos estáticos y ejecutar las migraciones antes de iniciar el servidor.

## 14. Control de versiones

El proyecto utiliza Git y GitHub para mantener el historial de modificaciones y facilitar la colaboración entre los integrantes del equipo.

El archivo `.gitignore` excluye archivos y directorios locales, incluyendo:

- Entornos virtuales.
- Archivos `.env`.
- Base de datos SQLite local.
- Archivos temporales y caché.
- Archivos generados durante la ejecución.

---

**Repositorio:** https://github.com/basto115/Pagina-Pricey
