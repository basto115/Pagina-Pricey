
document.addEventListener("DOMContentLoaded", function () {
    const botonUbicacion = document.getElementById("btn-ubicacion");
    const mensajeUbicacion = document.getElementById("mensaje-ubicacion");
    const contenedorMapa = document.getElementById("mapa-farmacias");

    let mapa = null;
    let marcadorUsuario = null;

    if (!botonUbicacion || !mensajeUbicacion) {
        console.error("No se encontró el botón o el mensaje de ubicación.");
        return;
    }

    // Crear el mapa inicial si Leaflet está disponible.
    if (contenedorMapa && typeof L !== "undefined") {
        mapa = L.map("mapa-farmacias").setView([-33.4489, -70.6693], 12);

        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(mapa);
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
