
document.addEventListener("DOMContentLoaded", function () {
    const botonUbicacion = document.getElementById("btn-ubicacion");
    const mensajeUbicacion = document.getElementById("mensaje-ubicacion");
    const contenedorMapa = document.getElementById("mapa-farmacias");

    let mapa = null;
    let marcadorUsuario = null;
    let marcadoresFarmacias = [];
    let grupoMarcadores = null;

    let ubicacionUsuario = null;
    let controlRuta = null;

    // Recuperar la ubicación guardada durante esta sesión.
    try {
        const ubicacionGuardada = sessionStorage.getItem("ubicacionUsuario");

        if (ubicacionGuardada) {
            const ubicacion = JSON.parse(ubicacionGuardada);
            const latitud = Number(ubicacion.lat);
            const longitud = Number(ubicacion.lng);

            if (
                Number.isFinite(latitud) &&
                Number.isFinite(longitud) &&
                latitud >= -90 && latitud <= 90 &&
                longitud >= -180 && longitud <= 180
            ) {
                ubicacionUsuario = {
                    latitud: latitud,
                    longitud: longitud
                };
            }
        }
    } catch (error) {
        console.warn("No se pudo recuperar la ubicación guardada.", error);
    }


    
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

    // Mapa de farmacias que aparecen en la lectura de recetas.
    const contenedorMapaReceta = document.getElementById("mapa-receta");

    if (contenedorMapaReceta && typeof L !== "undefined") {
        const elementoDatos = document.getElementById("farmacias-receta-data");
        const mensajeMapa = document.getElementById("mensaje-mapa-receta");

        let farmaciasReceta = [];

        if (elementoDatos) {
            try {
                farmaciasReceta = JSON.parse(elementoDatos.textContent);
            } catch (error) {
                console.error("No se pudieron leer los datos de las farmacias.", error);
            }
        }

        const mapaReceta = L.map("mapa-receta");

        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(mapaReceta);

        const puntosReceta = [];

        farmaciasReceta.forEach(function (farmacia) {
            const latitud = Number(farmacia.latitud);
            const longitud = Number(farmacia.longitud);

            if (
                !Number.isFinite(latitud) ||
                !Number.isFinite(longitud) ||
                latitud < -90 || latitud > 90 ||
                longitud < -180 || longitud > 180
            ) {
                return;
            }

            const contenido = document.createElement("div");
            const nombre = document.createElement("strong");

            nombre.textContent = farmacia.nombre;
            contenido.appendChild(nombre);

            const direccion = document.createElement("p");
            direccion.textContent = farmacia.direccion || "Dirección no disponible";
            contenido.appendChild(direccion);

            (farmacia.productos || []).forEach(function (producto) {
                const detalle = document.createElement("p");
                const precio = Number(producto.precio);

                detalle.textContent =
                    (producto.producto || producto.medicamento) + ": " +
                    (Number.isFinite(precio)
                        ? precio.toLocaleString("es-CL", {
                            style: "currency",
                            currency: "CLP",
                            maximumFractionDigits: 0
                        })
                        : "Precio no disponible");

                contenido.appendChild(detalle);
            });

            L.marker([latitud, longitud])
                .addTo(mapaReceta)
                .bindPopup(contenido);

            puntosReceta.push([latitud, longitud]);
        });

        // Mostrar también la ubicación guardada desde Inicio, si existe.
        try {
            const guardada = sessionStorage.getItem("ubicacionUsuario");

            if (guardada) {
                const ubicacion = JSON.parse(guardada);
                const latitud = Number(ubicacion.lat);
                const longitud = Number(ubicacion.lng);

                if (
                    Number.isFinite(latitud) &&
                    Number.isFinite(longitud) &&
                    latitud >= -90 && latitud <= 90 &&
                    longitud >= -180 && longitud <= 180
                ) {
                    L.circleMarker([latitud, longitud], {
                        radius: 8,
                        color: "#2563eb",
                        fillColor: "#3b82f6",
                        fillOpacity: 1
                    }).addTo(mapaReceta).bindPopup("Tu ubicación");

                    puntosReceta.push([latitud, longitud]);
                }
            }
        } catch (error) {
            console.warn("No se pudo recuperar la ubicación guardada.", error);
        }

        if (puntosReceta.length > 0) {
            mapaReceta.fitBounds(puntosReceta, {
                padding: [25, 25],
                maxZoom: 14
            });
        } else {
            mapaReceta.setView([-33.4489, -70.6693], 12);
        }

        if (mensajeMapa) {
            mensajeMapa.textContent = farmaciasReceta.length > 0
                ? "Selecciona un marcador para consultar los precios."
                : "No hay farmacias con coordenadas para los medicamentos reconocidos.";
        }

        setTimeout(function () {
            mapaReceta.invalidateSize();
        }, 100);
    }

    if (!botonUbicacion || !mensajeUbicacion) {
        console.error("No se encontró el botón o el mensaje de ubicación.");
        return;
    }

    const COLORES_FARMACIAS = {
        "cruz verde": "#16A34A",
        "dr simi": "#2563EB",
        "farmacias ahumada": "#E87924",
        "salcobrand": "#9333EA"
    };

    function obtenerColorFarmacia(farmacia) {
        const cadena = (farmacia.farmacia || "").trim().toLowerCase();
        return COLORES_FARMACIAS[cadena] || "#64748B";
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
            grupoMarcadores.clearLayers();
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
                const color = obtenerColorFarmacia(farmacia);

                const iconoFarmacia = L.divIcon({
                    className: "marcador-farmacia",
                    html: `
                        <div class="marcador-farmacia-circulo"
                            style="background-color: ${color};">
                        </div>
                    `,
                    iconSize: [18, 18],
                    iconAnchor: [9, 9],
                    popupAnchor: [0, -10]
                });

                const marcador = L.marker(
                    [farmacia.latitud, farmacia.longitud],
                    { icon: iconoFarmacia }
                );

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
                

                // Botón para calcular la ruta hasta esta farmacia.
                const botonRuta = document.createElement("button");
                botonRuta.textContent = "Cómo llegar";
                botonRuta.type = "button";
                botonRuta.className = "btn-ruta";

                botonRuta.style.marginTop = "8px";
                botonRuta.style.padding = "7px 12px";
                botonRuta.style.border = "none";
                botonRuta.style.borderRadius = "6px";
                botonRuta.style.backgroundColor = "#0F766E";
                botonRuta.style.color = "#FFFFFF";
                botonRuta.style.cursor = "pointer";

                botonRuta.addEventListener("click", function () {
                    // Comprobar que el usuario haya compartido su ubicación.
                    if (!ubicacionUsuario) {
                        mensajeUbicacion.textContent =
                            "Primero debes obtener tu ubicación para calcular la ruta.";
                        return;
                    }

                    // Comprobar que Leaflet Routing Machine esté cargado.
                    if (
                        typeof L.Routing === "undefined" ||
                        typeof L.Routing.control !== "function"
                    ) {
                        mensajeUbicacion.textContent =
                            "No se pudo cargar el complemento de rutas. Revisa tu conexión.";
                        return;
                    }

                    // Eliminar la ruta anterior, si existe.
                    if (controlRuta) {
                        mapa.removeControl(controlRuta);
                        controlRuta = null;
                    }

                     mensajeUbicacion.textContent =
                        "Calculando ruta hacia " + farmacia.nombre + "...";

                    try {
                        // Crear el control sin agregarlo todavía al mapa.
                        const nuevoControlRuta = L.Routing.control({
                            waypoints: [
                                L.latLng(
                                    ubicacionUsuario.latitud,
                                    ubicacionUsuario.longitud
                                ),
                                L.latLng(
                                    farmacia.latitud,
                                    farmacia.longitud
                                )
                            ],

                            router: L.Routing.osrmv1({
                                serviceUrl: "https://router.project-osrm.org/route/v1"
                            }),

                            addWaypoints: false,
                            draggableWaypoints: false,
                            fitSelectedRoutes: true,
                            show: true,
                            routeWhileDragging: false,
                            language: "es",

                            // Evita crear marcadores adicionales para la ruta.
                            createMarker: function () {
                                return null;
                            }
                        });

                        // Guardar el control antes de agregarlo al mapa.
                        controlRuta = nuevoControlRuta;

                        // El resultado de la ruta.
                        controlRuta.on("routesfound", function (evento) {
                            if (
                                !evento.routes || evento.routes.length === 0
                            ) {
                                mensajeUbicacion.textContent =
                                    "No se encontró una ruta para esta farmacia.";
                                return;
                            }

                            const ruta = evento.routes[0];
                            const distanciaKm = ruta.summary.totalDistance / 1000;
                            const duracionMinutos = Math.round(ruta.summary.totalTime / 60);

                            mensajeUbicacion.textContent = 
                                "Ruta hacia " +
                                farmacia.nombre +
                                ": " +
                                distanciaKm.toFixed(2) +
                                " km. Duración estimada: " +
                                duracionMinutos +
                                " minutos.";
                    
                        });

                        // Gestionar errores del servicio de rutas.
                        controlRuta.on( "routingerror", function (){
                            mensajeUbicacion.textContent =
                                "No se pudo calcular la ruta. Inténtalo nuevamente.";
                        });

                        // Agregar el control al mapa después de registrar los eventos.
                        controlRuta.addTo(mapa);
                            
                    } catch (error) {
                        console.error("Error al calcular la ruta:", error);

                        mensajeUbicacion.textContent = 
                            "Ocurrió un error al intentar calcular la ruta.";
                    }

                });

                contenido.appendChild(botonRuta);
                marcador.bindPopup(contenido);
                grupoMarcadores.addLayer(marcador);
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

        // Crear el grupo de marcadores después de inicializar el mapa.
        grupoMarcadores = L.markerClusterGroup({
            maxClusterRadius: 50,
            disableClusteringAtZoom: 17,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            animate: true
        });
        
        // Agregar el grupo al mapa.
        mapa.addLayer(grupoMarcadores);
        
        cargarFarmacias();
    } else if (contenedorMapa) {
        mensajeUbicacion.textContent =
            "No se pudo cargar el mapa. Revisa tu conexión a internet.";
    }

    botonUbicacion.addEventListener("click", function () {
        if (ubicacionUsuario) {
            mensajeUbicacion.textContent =
                "Ya tenemos tu ubicación guardada durante esta sesión.";

            if (mapa) {
                mapa.setView([
                    ubicacionUsuario.latitud,
                    ubicacionUsuario.longitud
                ], 15);

                if (marcadorUsuario) {
                    marcadorUsuario.setLatLng([
                        ubicacionUsuario.latitud,
                        ubicacionUsuario.longitud
                    ]);
                } else {
                    marcadorUsuario = L.marker([
                        ubicacionUsuario.latitud,
                        ubicacionUsuario.longitud
                    ]).addTo(mapa);
                }

                marcadorUsuario.bindPopup("¡Estás aquí!").openPopup();
                cargarFarmacias();
            }

            return;
        }



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
                // Guardar para reutilizar en otras páginas durante esta sesión.
                try {
                    sessionStorage.setItem(
                        "ubicacionUsuario",
                        JSON.stringify({
                            lat: latitud,
                            lng: longitud
                        })
                    );
                } catch (error) {
                    console.warn("No se pudo guardar la ubicación.", error);
                }

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
