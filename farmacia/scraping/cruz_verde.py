import requests
from bs4 import BeautifulSoup


def obtener_producto(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    respuesta = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    respuesta.raise_for_status()

    soup = BeautifulSoup(respuesta.text, "html.parser")

    print("Código:", respuesta.status_code)
    print("Título:", soup.title.get_text(strip=True) if soup.title else "Sin título")

    return soup

if __name__ == "__main__":
    url = "https://beta.cruzverde.cl/paracetamol-500-mg-16-comprimidos/272241.html"

    obtener_producto(url)