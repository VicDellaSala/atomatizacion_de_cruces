import io
import fitz
import pytesseract

from PIL import Image


def preparar_imagen(imagen):
    """
    Mejora ligeramente la imagen antes del OCR.
    """

    imagen = imagen.convert("L")

    return imagen


def hacer_ocr_imagen(imagen):
    """
    Extrae texto mediante OCR.
    """

    imagen = preparar_imagen(imagen)

    texto = pytesseract.image_to_string(
        imagen,
        lang="spa"
    )

    return texto


def leer_imagen(archivo):
    """
    Lee JPG, JPEG o PNG.
    """

    archivo.seek(0)

    imagen = Image.open(
        io.BytesIO(archivo.read())
    )

    return hacer_ocr_imagen(imagen)


def leer_pdf(archivo):
    """
    Intenta leer texto normal del PDF.

    Si la página es un escaneo,
    convierte la página en imagen y aplica OCR.
    """

    archivo.seek(0)

    contenido = archivo.read()

    documento = fitz.open(
        stream=contenido,
        filetype="pdf"
    )

    textos = []

    for pagina in documento:

        # Primero intentar texto normal
        texto = pagina.get_text("text").strip()

        if len(texto) >= 30:

            textos.append(texto)

        else:

            # PDF escaneado
            pix = pagina.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False
            )

            imagen = Image.open(
                io.BytesIO(
                    pix.tobytes("png")
                )
            )

            texto_ocr = hacer_ocr_imagen(
                imagen
            )

            textos.append(texto_ocr)

    documento.close()

    return "\n".join(textos)


def leer_documento(archivo):
    """
    Detecta automáticamente el tipo de archivo.
    """

    nombre = archivo.name.lower()

    if nombre.endswith(".pdf"):
        return leer_pdf(archivo)

    if nombre.endswith(
        (".jpg", ".jpeg", ".png")
    ):
        return leer_imagen(archivo)

    return ""