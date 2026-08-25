import re

from difflib import SequenceMatcher

from modules.excel_reader import (
    normalizar_texto,
    obtener_contratos_reales,
)


# =========================================================
# NORMALIZACION
# =========================================================

def limpiar_para_busqueda(texto):
    """
    Mayusculas + solo letras y numeros.
    """

    texto = normalizar_texto(
        texto
    )

    return re.sub(
        r"[^A-Z0-9]",
        "",
        texto
    )


def valor_aparece(valor, texto):
    """
    Coincidencia exacta normalizada.
    """

    valor = limpiar_para_busqueda(
        valor
    )

    texto = limpiar_para_busqueda(
        texto
    )

    if not valor:
        return False

    if len(valor) < 5:
        return False

    return valor in texto


# =========================================================
# CONTEXTO DEL CLIENTE
# =========================================================

def obtener_contexto(candidatos):
    """
    Obtiene RIF, afiliado y razon social
    compartidos por las terminales candidatas.
    """

    contexto = {
        "RIF": "",
        "AFILIADO": "",
        "RAZON SOCIAL": "",
    }

    if candidatos.empty:
        return contexto

    for columna in contexto.keys():

        if columna not in candidatos.columns:
            continue

        valores = (
            candidatos[columna]
            .apply(normalizar_texto)
        )

        valores = [
            valor
            for valor in valores
            if valor
        ]

        valores_unicos = list(
            dict.fromkeys(
                valores
            )
        )

        if len(valores_unicos) == 1:

            contexto[columna] = (
                valores_unicos[0]
            )

        elif len(valores_unicos) > 1:

            contexto[columna] = "VARIOS"

    return contexto


# =========================================================
# SERIAL EXACTO
# =========================================================

def buscar_serial_exacto(
    contratos,
    texto_documento,
    nombre_archivo=""
):
    """
    Busca serial completo exacto.
    """

    texto_total = (
        str(nombre_archivo)
        + " "
        + str(texto_documento)
    )

    encontrados = []

    for indice, fila in contratos.iterrows():

        serial = fila.get(
            "SERIAL",
            ""
        )

        if valor_aparece(
            serial,
            texto_total
        ):

            encontrados.append(
                indice
            )

    return encontrados


# =========================================================
# BUSCAR RIF
# =========================================================

def buscar_rifs(
    contratos,
    texto_documento,
    nombre_archivo
):
    """
    Busca el RIF dentro del texto OCR
    y tambien dentro del nombre del archivo.
    """

    texto_total = (
        str(nombre_archivo)
        + " "
        + str(texto_documento)
    )

    encontrados = []

    if "RIF" not in contratos.columns:
        return []

    for rif in contratos["RIF"]:

        rif = normalizar_texto(
            rif
        )

        if not rif:
            continue

        if valor_aparece(
            rif,
            texto_total
        ):

            if rif not in encontrados:

                encontrados.append(
                    rif
                )

    return encontrados


# =========================================================
# ULTIMOS DIGITOS DEL SERIAL
# =========================================================

def buscar_final_serial(
    candidatos,
    texto_documento
):
    """
    Intenta distinguir terminal usando:
    - ultimos 8
    - 7
    - 6
    - 5
    - 4 caracteres

    Solo acepta cuando UNA sola terminal coincide.
    """

    texto = limpiar_para_busqueda(
        texto_documento
    )

    for cantidad in [
        8,
        7,
        6,
        5,
        4,
    ]:

        encontrados = []

        for indice, fila in candidatos.iterrows():

            serial = limpiar_para_busqueda(
                fila.get(
                    "SERIAL",
                    ""
                )
            )

            if len(serial) < cantidad:
                continue

            final = serial[
                -cantidad:
            ]

            if final in texto:

                encontrados.append(
                    indice
                )

        if len(encontrados) == 1:

            return {
                "indice": encontrados[0],
                "cantidad": cantidad,
            }

    return None


# =========================================================
# SERIAL APROXIMADO
# =========================================================

def similitud_serial(
    serial,
    texto_documento
):
    """
    Busca una version aproximada del serial
    dentro del OCR especial.

    Solo se utiliza despues de haber reducido
    candidatos por RIF.
    """

    serial = limpiar_para_busqueda(
        serial
    )

    texto = limpiar_para_busqueda(
        texto_documento
    )

    if len(serial) < 8:
        return 0.0

    if len(texto) < 8:
        return 0.0

    mejor = 0.0

    # Comparar distintas longitudes porque OCR
    # puede perder uno o dos caracteres.
    for longitud in [
        len(serial),
        len(serial) - 1,
        len(serial) - 2,
    ]:

        if longitud < 6:
            continue

        if len(texto) < longitud:
            continue

        for posicion in range(
            len(texto) - longitud + 1
        ):

            fragmento = texto[
                posicion:
                posicion + longitud
            ]

            similitud = SequenceMatcher(
                None,
                serial,
                fragmento
            ).ratio()

            if similitud > mejor:

                mejor = similitud

    return mejor


def buscar_serial_probable(
    candidatos,
    texto_documento
):
    """
    Busca el serial mas probable dentro
    de las terminales del mismo RIF.

    Solo devuelve candidato cuando existe
    diferencia clara contra el segundo mejor.
    """

    resultados = []

    for indice, fila in candidatos.iterrows():

        serial = fila.get(
            "SERIAL",
            ""
        )

        similitud = similitud_serial(
            serial,
            texto_documento
        )

        resultados.append(
            {
                "indice": indice,
                "similitud": similitud,
            }
        )

    resultados = sorted(
        resultados,
        key=lambda item: item["similitud"],
        reverse=True,
    )

    if not resultados:
        return None

    mejor = resultados[0]

    segunda = (
        resultados[1]["similitud"]
        if len(resultados) > 1
        else 0
    )

    # Necesitamos una lectura razonable
    if mejor["similitud"] < 0.78:

        return None

    # Y que sea claramente mejor
    if (
        mejor["similitud"]
        - segunda
    ) < 0.035:

        return None

    return mejor


# =========================================================
# BUSCAR MEJOR COINCIDENCIA
# =========================================================

def buscar_mejor_coincidencia(
    df,
    texto_documento,
    nombre_archivo,
    segundo_intento=False,
):
    """
    Flujo:

    PRIMER INTENTO:
    1. Serial exacto
    2. RIF
    3. RIF unico -> encontrado
    4. RIF repetido -> pedir segundo OCR

    SEGUNDO INTENTO:
    5. Serial exacto
    6. Ultimos caracteres
    7. Serial probable
    8. Si falla -> revisar sin inventar serial
    """

    contratos = obtener_contratos_reales(
        df
    )

    # =====================================================
    # 1. SERIAL EXACTO
    # =====================================================

    seriales = buscar_serial_exacto(
        contratos,
        texto_documento,
        nombre_archivo,
    )

    if len(seriales) == 1:

        indice = seriales[0]

        fila = contratos.loc[
            indice
        ]

        return {
            "estado": "ENCONTRADO",
            "puntos": 100,
            "indice": indice,
            "coincidencias": [
                "SERIAL EXACTO"
            ],
            "requiere_ocr_serial": False,
            "contexto": {
                "RIF": normalizar_texto(
                    fila.get(
                        "RIF",
                        ""
                    )
                ),
                "AFILIADO": normalizar_texto(
                    fila.get(
                        "AFILIADO",
                        ""
                    )
                ),
                "RAZON SOCIAL": normalizar_texto(
                    fila.get(
                        "RAZON SOCIAL",
                        ""
                    )
                ),
            },
        }

    # =====================================================
    # 2. BUSCAR RIF
    # =====================================================

    rifs = buscar_rifs(
        contratos,
        texto_documento,
        nombre_archivo,
    )

    if len(rifs) == 0:

        return {
            "estado": "NO ENCONTRADO",
            "puntos": 0,
            "indice": None,
            "coincidencias": [],
            "requiere_ocr_serial": False,
            "contexto": {
                "RIF": "",
                "AFILIADO": "",
                "RAZON SOCIAL": "",
            },
        }

    if len(rifs) > 1:

        return {
            "estado": "REVISAR",
            "puntos": 10,
            "indice": None,
            "coincidencias": [
                "VARIOS RIF DETECTADOS"
            ],
            "requiere_ocr_serial": False,
            "contexto": {
                "RIF": "VARIOS",
                "AFILIADO": "",
                "RAZON SOCIAL": "",
            },
        }

    rif_detectado = rifs[0]

    filtro = (
        contratos["RIF"]
        .apply(normalizar_texto)
        == rif_detectado
    )

    candidatos = contratos[
        filtro
    ].copy()

    contexto = obtener_contexto(
        candidatos
    )

    # =====================================================
    # 3. RIF UNICO
    # =====================================================

    if len(candidatos) == 1:

        indice = candidatos.index[0]

        return {
            "estado": "ENCONTRADO",
            "puntos": 50,
            "indice": indice,
            "coincidencias": [
                "RIF UNICO"
            ],
            "requiere_ocr_serial": False,
            "contexto": contexto,
        }

    # =====================================================
    # 4. RIF REPETIDO - PRIMER INTENTO
    # =====================================================

    if not segundo_intento:

        return {
            "estado": "REVISAR",
            "puntos": 20,
            "indice": None,
            "coincidencias": [
                "RIF REPETIDO - BUSCANDO SERIAL"
            ],
            "requiere_ocr_serial": True,
            "contexto": contexto,
        }

    # =====================================================
    # 5. SEGUNDO INTENTO:
    #    BUSCAR SERIAL EXACTO SOLO ENTRE ESE RIF
    # =====================================================

    seriales_rif = buscar_serial_exacto(
        candidatos,
        texto_documento,
        nombre_archivo,
    )

    if len(seriales_rif) == 1:

        indice = seriales_rif[0]

        return {
            "estado": "ENCONTRADO",
            "puntos": 100,
            "indice": indice,
            "coincidencias": [
                "RIF + SERIAL EXACTO"
            ],
            "requiere_ocr_serial": False,
            "contexto": contexto,
        }

    # =====================================================
    # 6. ULTIMOS CARACTERES
    # =====================================================

    resultado_final = buscar_final_serial(
        candidatos,
        texto_documento
    )

    if resultado_final is not None:

        indice = resultado_final[
            "indice"
        ]

        cantidad = resultado_final[
            "cantidad"
        ]

        return {
            "estado": "ENCONTRADO",
            "puntos": 80 + cantidad,
            "indice": indice,
            "coincidencias": [
                f"RIF + ULTIMOS {cantidad} SERIAL"
            ],
            "requiere_ocr_serial": False,
            "contexto": contexto,
        }

    # =====================================================
    # 7. SERIAL PROBABLE
    # =====================================================

    probable = buscar_serial_probable(
        candidatos,
        texto_documento
    )

    if probable is not None:

        indice = probable[
            "indice"
        ]

        porcentaje = round(
            probable[
                "similitud"
            ]
            * 100
        )

        return {
            "estado": "REVISAR",
            "puntos": porcentaje,
            "indice": indice,
            "coincidencias": [
                f"RIF + SERIAL PROBABLE {porcentaje}%"
            ],
            "requiere_ocr_serial": False,
            "contexto": contexto,
        }

    # =====================================================
    # 8. NO LOGRAMOS LEER SERIAL
    # =====================================================

    return {
        "estado": "REVISAR",
        "puntos": 20,
        "indice": None,
        "coincidencias": [
            "RIF DETECTADO - SERIAL NO DETECTADO"
        ],
        "requiere_ocr_serial": False,
        "contexto": contexto,
    }