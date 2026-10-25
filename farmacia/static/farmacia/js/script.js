
document.addEventListener("DOMContentLoaded", function () {
    const botonUbicacion = document.getElementById("btn-ubicacion");
    const mensajeUbicacion = document.getElementById("mensaje-ubicacion");
    const contenedorMapa = document.getElementById("mapa-farmacias");

    let mapa = null;
    let marcadorUsuario = null;
    let marcadoresFarmacias = [];
    let ubicacionUsuario = null;

    
function calcularDistanciaKm(lat1, lon1, lat2, lon2) {
    const radioTierra = 6371;
    const radianes = grados => grados * Math.PI / 180;

    const diferenciaLatitud = radianes(lat2 - lat1);
    const diferenciaLongitud = radianes(lon2 - lon1);

    const a =
        Math.sin(diferenciaLatitud / 2) ** 2 +
        Math.cos(radianes(lat1)) *
        Math.cos(radianes(lat2)) *
        Math.sin(diferenciaLongitud / 2) ** 2;

    const c = 2 * Math.atan2(
        Math.sqrt(a),
        Math.sqrt(1 - a)
    );

    return radioTierra * c;
}


    if (!botonUbicacion || !mensajeUbicacion) {
        console.error("No se encontró el botón o el mensaje de ubicación.");
        return;
    }

    
    // Cargar y ordenar las farmacias según la ubicación del usuario.
    async function cargarFarmacias() {
        try {
            const respuesta = await fetch("/api/farmacias/");

            if (!respuesta.ok) {
                throw new Error("No se pudieron obtener las farmacias.");
            }

            const datos = await respuesta.json();

            // Evitar duplicar marcadores si volvemos a cargar.
            marcadoresFarmacias.forEach(function (marcador) {
                mapa.removeLayer(marcador);
            });
            marcadoresFarmacias = [];

            const farmaciasOrdenadas = datos.farmacias
                .map(function (farmacia) {
                    const latitud = Number(farmacia.latitud);
                    const longitud = Number(farmacia.longitud);

                    if (
                        farmacia.latitud == null ||
                        farmacia.longitud == null ||
                        !Number.isFinite(latitud) ||
                        !Number.isFinite(longitud) ||
                        latitud < -90 || latitud > 90 ||
                        longitud < -180 || longitud > 180
                    ) {
                        return null;
                    }

                    const distancia = ubicacionUsuario
                        ? calcularDistanciaKm(
                            ubicacionUsuario.latitud,
                            ubicacionUsuario.longitud,
                            latitud,
                            longitud
                        )
                        : null;

                    return {
                        ...farmacia,
                        latitud: latitud,
                        longitud: longitud,
                        distancia: distancia
                    };
                })
                .filter(function (farmacia) {
                    return farmacia !== null;
                });

            // Si conocemos la ubicación, mostrar primero las más cercanas.
            if (ubicacionUsuario) {
                farmaciasOrdenadas.sort(function (a, b) {
                    return a.distancia - b.distancia;
                });
            }

            farmaciasOrdenadas.forEach(function (farmacia) {
                const marcador = L.marker([
                    farmacia.latitud,
                    farmacia.longitud
                ]).addTo(mapa);

                const contenido = document.createElement("div");
                const nombre = document.createElement("strong");
                const direccion = document.createElement("p");

                nombre.textContent = farmacia.nombre;
                direccion.textContent =
                    farmacia.direccion || "Dirección no disponible";

                contenido.appendChild(nombre);
                contenido.appendChild(direccion);

                if (farmacia.distancia !== null) {
                    const distancia = document.createElement("p");
                    distancia.textContent =
                        "A " + farmacia.distancia.toFixed(2) + " km en línea recta";
                    contenido.appendChild(distancia);
                }

                marcador.bindPopup(contenido);
                marcadoresFarmacias.push(marcador);
            });

            console.log(
                "Farmacias cargadas:",
                marcadoresFarmacias.length
            );

            if (ubicacionUsuario && farmaciasOrdenadas.length > 0) {
                console.log(
                    "Farmacia más cercana:",
                    farmaciasOrdenadas[0].nombre,
                    farmaciasOrdenadas[0].distancia.toFixed(2) + " km"
                );
            }
        } catch (error) {
            console.error("Error al cargar las farmacias:", error);
            mensajeUbicacion.textContent =
                "No se pudieron cargar las farmacias. Inténtalo nuevamente.";
        }
    }




    // Crear el mapa inicial si Leaflet está disponible.
    if (contenedorMapa && typeof L !== "undefined") {
        mapa = L.map("mapa-farmacias").setView([-33.4489, -70.6693], 12);

        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(mapa);
        
        cargarFarmacias();
    } else if (contenedorMapa) {
        mensajeUbicacion.textContent =
            "No se pudo cargar el mapa. Revisa tu conexión a internet.";
    }

    botonUbicacion.addEventListener("click", function () {
        if (!navigator.geolocation) {
            mensajeUbicacion.textContent =
                "Tu navegador no admite la geolocalización.";
            return;
        }

        mensajeUbicacion.textContent =
            "Solicitando permiso para conocer tu ubicación...";

        navigator.geolocation.getCurrentPosition(
            function (posicion) {
                const latitud = posicion.coords.latitude;
                const longitud = posicion.coords.longitude;
                ubicacionUsuario = {
                    latitud: latitud,
                    longitud: longitud
                };

                mensajeUbicacion.textContent =
                    "¡Ubicación obtenida correctamente!";

                if (mapa) {
                    mapa.setView([latitud, longitud], 15);

                    if (marcadorUsuario) {
                        marcadorUsuario.setLatLng([latitud, longitud]);
                    } else {
                        marcadorUsuario = L.marker([latitud, longitud])
                            .addTo(mapa);
                    }

                    marcadorUsuario.bindPopup("¡Estás aquí!").openPopup();
                    cargarFarmacias();
                }

                console.log("Ubicación obtenida:", latitud, longitud);
            },
            function (error) {
                if (error.code === 1) {
                    mensajeUbicacion.textContent =
                        "Permiso denegado. Habilita la ubicación en tu navegador.";
                } else if (error.code === 2) {
                    mensajeUbicacion.textContent =
                        "No pudimos determinar tu ubicación. Inténtalo nuevamente.";
                } else if (error.code === 3) {
                    mensajeUbicacion.textContent =
                        "La solicitud tardó demasiado. Inténtalo otra vez.";
                } else {
                    mensajeUbicacion.textContent =
                        "Ocurrió un error al obtener tu ubicación.";
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            }
        );
    });
});
