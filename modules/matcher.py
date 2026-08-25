import re

from modules.excel_reader import (
    normalizar_texto,
    obtener_contratos_reales,
)


def limpiar_para_busqueda(texto):
    """
    Deja solamente letras y números para
    facilitar búsquedas de RIF, seriales, afiliados, etc.
    """

    texto = normalizar_texto(texto)

    return re.sub(
        r"[^A-Z0-9]",
        "",
        texto
    )


def valor_aparece(valor, texto_limpio):
    """
    Busca un valor del Excel dentro del texto OCR.
    """

    valor = limpiar_para_busqueda(valor)

    if not valor:
        return False

    # Evitar coincidencias demasiado pequeñas
    if len(valor) < 5:
        return False

    return valor in texto_limpio


def evaluar_fila(fila, texto_documento, nombre_archivo=""):
    """
    Calcula qué tan probable es que una fila del Excel
    corresponda al contrato.
    """

    texto_total = (
        str(nombre_archivo)
        + " "
        + str(texto_documento)
    )

    texto_limpio = limpiar_para_busqueda(
        texto_total
    )

    coincidencias = []
    puntos = 0

    # ------------------------------
    # AFILIADO
    # ------------------------------

    if "AFILIADO" in fila.index:

        afiliado = fila["AFILIADO"]

        if valor_aparece(
            afiliado,
            texto_limpio
        ):
            coincidencias.append("AFILIADO")
            puntos += 35

    # ------------------------------
    # RIF
    # ------------------------------

    if "RIF" in fila.index:

        rif = fila["RIF"]

        if valor_aparece(
            rif,
            texto_limpio
        ):
            coincidencias.append("RIF")
            puntos += 30

    # ------------------------------
    # SERIAL POS
    # ------------------------------

    if "SERIAL" in fila.index:

        serial = fila["SERIAL"]

        if valor_aparece(
            serial,
            texto_limpio
        ):
            coincidencias.append("SERIAL")
            puntos += 35

    # ------------------------------
    # PEDIDO
    # ------------------------------

    if "PEDIDO" in fila.index:

        pedido = fila["PEDIDO"]

        if valor_aparece(
            pedido,
            texto_limpio
        ):
            coincidencias.append("PEDIDO")
            puntos += 20

    # ------------------------------
    # FACTURA
    # ------------------------------

    if "FACTURA" in fila.index:

        factura = fila["FACTURA"]

        if valor_aparece(
            factura,
            texto_limpio
        ):
            coincidencias.append("FACTURA")
            puntos += 20

    return {
        "puntos": puntos,
        "coincidencias": coincidencias,
    }


def buscar_mejor_coincidencia(
    df,
    texto_documento,
    nombre_archivo
):
    """
    Busca el contrato del Excel con mayor
    cantidad de coincidencias.
    """

    contratos = obtener_contratos_reales(df)

    mejor_indice = None
    mejor_resultado = None

    for indice, fila in contratos.iterrows():

        resultado = evaluar_fila(
            fila,
            texto_documento,
            nombre_archivo
        )

        if (
            mejor_resultado is None
            or resultado["puntos"]
            > mejor_resultado["puntos"]
        ):

            mejor_indice = indice
            mejor_resultado = resultado

    if mejor_resultado is None:

        return {
            "estado": "NO ENCONTRADO",
            "puntos": 0,
            "indice": None,
            "coincidencias": [],
        }

    puntos = mejor_resultado["puntos"]

    if puntos >= 50:
        estado = "ENCONTRADO"

    elif puntos >= 30:
        estado = "REVISAR"

    else:
        estado = "NO ENCONTRADO"

    return {
        "estado": estado,
        "puntos": puntos,
        "indice": mejor_indice,
        "coincidencias":
            mejor_resultado["coincidencias"],
    }