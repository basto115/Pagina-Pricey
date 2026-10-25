from PIL import Image
import pytesseract

#pa ejecutar el tesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

#abrir imagen
imagen = Image.open("receta_prueba.png")

#para el texto en spanish
texto = pytesseract.image_to_string(imagen, lang="spa")

print("Texto reconocido:")
print(texto)