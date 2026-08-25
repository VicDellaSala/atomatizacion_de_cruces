import pandas as pd


def normalizar_texto(valor):
    """
    Convierte cualquier valor a texto limpio y uniforme.
    """
    if pd.isna(valor):
        return ""

    texto = str(valor).strip().upper()

    if texto.endswith(".0"):
        texto = texto[:-2]

    return texto


def leer_excel(archivo_excel):
    """
    Lee preferiblemente la hoja VENTA.
    """

    try:
        df = pd.read_excel(
            archivo_excel,
            sheet_name="VENTA"
        )
    except Exception:
        df = pd.read_excel(archivo_excel)

    # Normalizar encabezados
    df.columns = [
        normalizar_texto(columna)
        for columna in df.columns
    ]

    return df


def obtener_columnas_disponibles(df):
    return list(df.columns)


def obtener_canales(df):
    """
    Obtiene todos los agentes/canales.
    """

    if "CANAL" not in df.columns:
        return []

    canales = (
        df["CANAL"]
        .apply(normalizar_texto)
    )

    canales = canales[
        canales != ""
    ]

    return sorted(
        canales.unique().tolist()
    )


def filtrar_por_canal(df, canal):
    """
    Filtra únicamente el canal seleccionado.
    """

    if "CANAL" not in df.columns:
        return df.copy()

    canal = normalizar_texto(canal)

    filtro = (
        df["CANAL"]
        .apply(normalizar_texto)
        == canal
    )

    return df[filtro].copy()


def obtener_afiliados_unicos(df):
    """
    Obtiene los afiliados únicos.
    """

    if "AFILIADO" not in df.columns:
        return []

    afiliados = (
        df["AFILIADO"]
        .apply(normalizar_texto)
    )

    afiliados = afiliados[
        afiliados != ""
    ]

    return sorted(
        afiliados.unique().tolist()
    )


def obtener_contratos_reales(df):
    """
    Obtiene solo las filas correspondientes
    al equipo principal.

    TERMINAL = 0 corresponde a SIM CARD
    y NO cuenta como contrato separado.
    """

    if "TERMINAL" not in df.columns:
        return df.copy()

    terminal = pd.to_numeric(
        df["TERMINAL"],
        errors="coerce"
    )

    contratos = df[
        terminal.fillna(0) > 0
    ].copy()

    return contratos


def contar_contratos_reales(df):
    return len(
        obtener_contratos_reales(df)
    )


def obtener_resumen_excel(df):
    afiliados = obtener_afiliados_unicos(df)

    return {
        "filas_totales": len(df),
        "afiliados_unicos": len(afiliados),
        "lista_afiliados": afiliados,
        "columnas": obtener_columnas_disponibles(df),
    }


def obtener_datos_contrato(df, indice):
    """
    Obtiene los datos importantes de una fila
    de contrato/equipo.
    """

    fila = df.loc[indice]

    datos = {}

    columnas_interes = [
        "AFILIADO",
        "CONCATENAR",
        "RAZON SOCIAL",
        "RIF",
        "SERIAL",
        "EQUIPO",
        "PEDIDO",
        "FACTURA",
        "BANCO",
        "TELEFONO",
    ]

    for columna in columnas_interes:

        if columna in df.columns:
            datos[columna] = normalizar_texto(
                fila.get(columna, "")
            )

    return datos