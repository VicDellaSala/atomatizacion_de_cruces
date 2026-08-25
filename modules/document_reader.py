import io

import fitz
import pytesseract

from PIL import Image, ImageEnhance, ImageFilter


# =========================================================
# PREPARACION DE IMAGEN
# =========================================================

def preparar_imagen_general(imagen):
    """
    Preparacion ligera para el OCR principal.
    """

    imagen = imagen.convert("L")

    imagen = ImageEnhance.Contrast(
        imagen
    ).enhance(1.5)

    return imagen


def preparar_imagen_serial(imagen):
    """
    Preparacion especial para buscar seriales.

    Se aumenta contraste y nitidez solamente
    en el segundo intento.
    """

    imagen = imagen.convert("L")

    imagen = ImageEnhance.Contrast(
        imagen
    ).enhance(2.0)

    imagen = ImageEnhance.Sharpness(
        imagen
    ).enhance(1.8)

    imagen = imagen.filter(
        ImageFilter.SHARPEN
    )

    return imagen


# =========================================================
# OCR GENERAL
# =========================================================

def hacer_ocr_general(imagen):
    """
    OCR rapido para localizar principalmente:
    - RIF
    - razon social
    - afiliado
    - serial si Tesseract logra leerlo
    """

    imagen = preparar_imagen_general(
        imagen
    )

    return pytesseract.image_to_string(
        imagen,
        lang="spa",
        config="--psm 6"
    )


# =========================================================
# OCR ESPECIAL PARA SERIAL
# =========================================================

def hacer_ocr_serial(imagen):
    """
    OCR adicional orientado a numeros y seriales.

    Este OCR NO se ejecuta para todos los documentos.
    Solo se usa cuando existe un RIF con varias terminales.
    """

    imagen = preparar_imagen_serial(
        imagen
    )

    configuracion = (
        "--psm 11 "
        "-c tessedit_char_whitelist="
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    return pytesseract.image_to_string(
        imagen,
        lang="spa",
        config=configuracion
    )


# =========================================================
# OBTENER IMAGEN DE ARCHIVO
# =========================================================

def imagen_desde_archivo(archivo):
    """
    Devuelve una imagen PIL de la primera pagina.

    Funciona con PDF, JPG, JPEG y PNG.
    """

    nombre = archivo.name.lower()

    archivo.seek(0)

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------

    if nombre.endswith(".pdf"):

        contenido = archivo.read()

        documento = fitz.open(
            stream=contenido,
            filetype="pdf"
        )

        if len(documento) == 0:

            documento.close()

            return None

        pagina = documento[0]

        pix = pagina.get_pixmap(
            matrix=fitz.Matrix(
                1.8,
                1.8
            ),
            alpha=False
        )

        imagen = Image.open(
            io.BytesIO(
                pix.tobytes("png")
            )
        )

        documento.close()

        return imagen

    # -----------------------------------------------------
    # IMAGEN
    # -----------------------------------------------------

    if nombre.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
        )
    ):

        contenido = archivo.read()

        return Image.open(
            io.BytesIO(contenido)
        )

    return None


# =========================================================
# LECTURA NORMAL DE IMAGEN
# =========================================================

def leer_imagen(archivo):
    """
    OCR principal de JPG, JPEG o PNG.
    """

    imagen = imagen_desde_archivo(
        archivo
    )

    if imagen is None:
        return ""

    return hacer_ocr_general(
        imagen
    )


# =========================================================
# LECTURA NORMAL DE PDF
# =========================================================

def leer_pdf(archivo):
    """
    Lectura rapida del PDF.

    Si tiene texto real, lo utiliza.
    Si es escaneado, OCR solamente de la primera pagina.
    """

    archivo.seek(0)

    contenido = archivo.read()

    documento = fitz.open(
        stream=contenido,
        filetype="pdf"
    )

    if len(documento) == 0:

        documento.close()

        return ""

    pagina = documento[0]

    texto_digital = (
        pagina.get_text("text")
        .strip()
    )

    # Si el PDF tiene texto seleccionable
    if len(texto_digital) >= 80:

        documento.close()

        return texto_digital

    # PDF escaneado
    pix = pagina.get_pixmap(
        matrix=fitz.Matrix(
            1.4,
            1.4
        ),
        alpha=False
    )

    imagen = Image.open(
        io.BytesIO(
            pix.tobytes("png")
        )
    )

    documento.close()

    return hacer_ocr_general(
        imagen
    )


# =========================================================
# LECTOR PRINCIPAL
# =========================================================

def leer_documento(archivo):
    """
    Primera lectura rapida del documento.
    """

    nombre = archivo.name.lower()

    if nombre.endswith(".pdf"):

        return leer_pdf(
            archivo
        )

    if nombre.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
        )
    ):

        return leer_imagen(
            archivo
        )

    return ""


# =========================================================
# SEGUNDO OCR PARA SERIAL
# =========================================================

def leer_serial_documento(archivo):
    """
    Segunda lectura especial.

    Solo debe llamarse cuando el RIF tenga
    varias terminales y necesitemos identificar
    cual serial corresponde.

    En lugar de procesar toda la pagina varias veces,
    se analizan zonas donde normalmente aparece
    la informacion del equipo/serial.
    """

    imagen = imagen_desde_archivo(
        archivo
    )

    if imagen is None:
        return ""

    ancho, alto = imagen.size

    textos = []

    # =====================================================
    # ZONA 1
    # Mitad derecha / zona media-baja.
    # En el formulario mostrado es donde aparece Serial POS.
    # =====================================================

    zona_serial = imagen.crop(
        (
            int(ancho * 0.43),
            int(alto * 0.42),
            ancho,
            int(alto * 0.78),
        )
    )

    texto_zona_serial = hacer_ocr_serial(
        zona_serial
    )

    textos.append(
        texto_zona_serial
    )

    # =====================================================
    # ZONA 2
    # Franja mas amplia para contratos cuyo formulario
    # tenga el serial ligeramente desplazado.
    # =====================================================

    zona_equipo = imagen.crop(
        (
            0,
            int(alto * 0.38),
            ancho,
            int(alto * 0.80),
        )
    )

    texto_zona_equipo = hacer_ocr_serial(
        zona_equipo
    )

    textos.append(
        texto_zona_equipo
    )

    return "\n".join(
        textos
    )