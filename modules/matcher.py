import re
from difflib import SequenceMatcher

from modules.excel_reader import (
    normalizar_texto,
    obtener_contratos_reales,
)


# =========================================================
# NORMALIZACIÓN
# =========================================================

def limpiar_para_busqueda(texto):
    """
    Convierte texto a mayúsculas y elimina
    espacios, guiones y símbolos.

    Ejemplo:
    J-50405638-3 -> J504056383
    """

    texto = normalizar_texto(texto)

    return re.sub(
        r"[^A-Z0-9]",
        "",
        texto
    )


def normalizar_serial(valor):
    """
    Normaliza un serial.
    """

    return limpiar_para_busqueda(valor)


def valor_aparece(valor, texto_limpio):
    """
    Busca un valor dentro del texto OCR.
    """

    valor = limpiar_para_busqueda(valor)

    if not valor:
        return False

    # Evita buscar valores demasiado pequeños
    if len(valor) < 5:
        return False

    return valor in texto_limpio


# =========================================================
# SERIAL
# =========================================================

def similitud_serial(serial_excel, texto_documento):
    """
    Busca el serial del Excel dentro del documento.

    1. Intenta coincidencia exacta.
    2. Si falla, permite una pequeña diferencia OCR.
    """

    serial = normalizar_serial(
        serial_excel
    )

    texto = limpiar_para_busqueda(
        texto_documento
    )

    if not serial:
        return 0.0

    # Coincidencia exacta
    if serial in texto:
        return 1.0

    # Serial demasiado corto
    if len(serial) < 8:
        return 0.0

    longitud = len(serial)

    mejor_similitud = 0.0

    # Buscar fragmentos del mismo tamaño
    for posicion in range(
        max(
            1,
            len(texto) - longitud + 1
        )
    ):

        fragmento = texto[
            posicion:
            posicion + longitud
        ]

        if len(fragmento) != longitud:
            continue

        similitud = SequenceMatcher(
            None,
            serial,
            fragmento
        ).ratio()

        if similitud > mejor_similitud:
            mejor_similitud = similitud

        if mejor_similitud >= 0.98:
            break

    return mejor_similitud


# =========================================================
# EVALUAR FILA
# =========================================================

def evaluar_fila(
    fila,
    texto_documento,
    nombre_archivo=""
):
    """
    Evalúa una terminal específica del Excel.

    PRIORIDAD:
    SERIAL > AFILIADO > RIF > PEDIDO/FACTURA
    """

    texto_total = (
        str(nombre_archivo)
        + "\n"
        + str(texto_documento)
    )

    texto_limpio = limpiar_para_busqueda(
        texto_total
    )

    coincidencias = []

    puntos = 0

    serial_encontrado = False
    serial_similitud = 0.0

    rif_encontrado = False
    afiliado_encontrado = False


    # =====================================================
    # SERIAL POS
    # =====================================================

    if "SERIAL" in fila.index:

        serial = fila.get(
            "SERIAL",
            ""
        )

        serial_similitud = similitud_serial(
            serial,
            texto_total
        )

        # Serial exacto
        if serial_similitud == 1.0:

            coincidencias.append(
                "SERIAL EXACTO"
            )

            puntos += 100

            serial_encontrado = True

        # Serial bastante parecido
        elif serial_similitud >= 0.90:

            coincidencias.append(
                "SERIAL POSIBLE"
            )

            puntos += 75

            serial_encontrado = True


    # =====================================================
    # AFILIADO
    # =====================================================

    if "AFILIADO" in fila.index:

        afiliado = fila.get(
            "AFILIADO",
            ""
        )

        if valor_aparece(
            afiliado,
            texto_limpio
        ):

            coincidencias.append(
                "AFILIADO"
            )

            puntos += 30

            afiliado_encontrado = True


    # =====================================================
    # RIF
    # =====================================================

    if "RIF" in fila.index:

        rif = fila.get(
            "RIF",
            ""
        )

        if valor_aparece(
            rif,
            texto_limpio
        ):

            coincidencias.append(
                "RIF"
            )

            puntos += 20

            rif_encontrado = True


    # =====================================================
    # PEDIDO
    # =====================================================

    if "PEDIDO" in fila.index:

        pedido = fila.get(
            "PEDIDO",
            ""
        )

        if valor_aparece(
            pedido,
            texto_limpio
        ):

            coincidencias.append(
                "PEDIDO"
            )

            puntos += 20


    # =====================================================
    # FACTURA
    # =====================================================

    if "FACTURA" in fila.index:

        factura = fila.get(
            "FACTURA",
            ""
        )

        if valor_aparece(
            factura,
            texto_limpio
        ):

            coincidencias.append(
                "FACTURA"
            )

            puntos += 20


    return {
        "puntos": puntos,
        "coincidencias": coincidencias,
        "serial_encontrado": serial_encontrado,
        "serial_similitud": serial_similitud,
        "rif_encontrado": rif_encontrado,
        "afiliado_encontrado": afiliado_encontrado,
    }


# =========================================================
# BUSCAR MEJOR COINCIDENCIA
# =========================================================

def buscar_mejor_coincidencia(
    df,
    texto_documento,
    nombre_archivo
):
    """
    Busca la terminal correcta.

    REGLAS:

    1. SERIAL exacto tiene máxima prioridad.
    2. SERIAL parecido requiere revisión.
    3. AFILIADO puede identificar el contrato.
    4. RIF puede identificarlo SOLO si ese RIF
       corresponde a una única terminal.
    5. Si el mismo RIF tiene varias terminales y
       no encontramos serial, NO inventamos cuál es.
    """

    contratos = obtener_contratos_reales(
        df
    )

    candidatos = []

    for indice, fila in contratos.iterrows():

        resultado = evaluar_fila(
            fila,
            texto_documento,
            nombre_archivo
        )

        candidatos.append(
            {
                "indice": indice,
                **resultado,
            }
        )


    # =====================================================
    # 1. SERIAL
    # =====================================================

    candidatos_serial = [
        candidato
        for candidato in candidatos
        if candidato["serial_encontrado"]
    ]

    if candidatos_serial:

        mejor = max(
            candidatos_serial,
            key=lambda x: (
                x["serial_similitud"],
                x["puntos"]
            )
        )

        if mejor["serial_similitud"] == 1.0:

            estado = "ENCONTRADO"

        else:

            estado = "REVISAR"

        return {
            "estado": estado,
            "puntos": mejor["puntos"],
            "indice": mejor["indice"],
            "coincidencias":
                mejor["coincidencias"],
            "serial_similitud":
                mejor["serial_similitud"],
        }


    # =====================================================
    # 2. AFILIADO
    # =====================================================

    candidatos_afiliado = [
        candidato
        for candidato in candidatos
        if candidato["afiliado_encontrado"]
    ]

    # Si solamente una terminal coincide con el afiliado
    if len(candidatos_afiliado) == 1:

        mejor = candidatos_afiliado[0]

        return {
            "estado": "ENCONTRADO",
            "puntos": mejor["puntos"],
            "indice": mejor["indice"],
            "coincidencias":
                mejor["coincidencias"],
            "serial_similitud": 0,
        }

    # Si hay varias terminales con mismo afiliado
    if len(candidatos_afiliado) > 1:

        mejor = max(
            candidatos_afiliado,
            key=lambda x: x["puntos"]
        )

        return {
            "estado": "REVISAR",
            "puntos": mejor["puntos"],
            "indice": None,
            "coincidencias": [
                "AFILIADO - SERIAL NO IDENTIFICADO"
            ],
            "serial_similitud": 0,
        }


    # =====================================================
    # 3. RIF
    # =====================================================

    candidatos_rif = [
        candidato
        for candidato in candidatos
        if candidato["rif_encontrado"]
    ]


    # -----------------------------------------------------
    # SOLO UNA TERMINAL CON ESE RIF
    # -----------------------------------------------------

    if len(candidatos_rif) == 1:

        mejor = candidatos_rif[0]

        return {
            "estado": "ENCONTRADO",
            "puntos": mejor["puntos"],
            "indice": mejor["indice"],
            "coincidencias": [
                "RIF ÚNICO"
            ],
            "serial_similitud": 0,
        }


    # -----------------------------------------------------
    # MISMO RIF EN VARIAS TERMINALES
    # -----------------------------------------------------

    if len(candidatos_rif) > 1:

        mejor = max(
            candidatos_rif,
            key=lambda x: x["puntos"]
        )

        return {
            "estado": "REVISAR",
            "puntos": mejor["puntos"],

            # No asignamos ninguna terminal
            # porque no sabemos cuál serial corresponde
            "indice": None,

            "coincidencias": [
                "RIF - SERIAL NO IDENTIFICADO"
            ],

            "serial_similitud": 0,
        }


    # =====================================================
    # 4. NO ENCONTRADO
    # =====================================================

    return {
        "estado": "NO ENCONTRADO",
        "puntos": 0,
        "indice": None,
        "coincidencias": [],
        "serial_similitud": 0,
    }