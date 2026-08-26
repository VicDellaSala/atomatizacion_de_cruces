import pandas as pd
import re


# =========================================================
# NORMALIZACION
# =========================================================

def normalizar_texto(valor):
    """
    Convierte cualquier valor a texto limpio y uniforme.
    """

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().upper()

    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto)

    # Excel a veces convierte identificadores a 123456.0
    if texto.endswith(".0"):
        texto = texto[:-2]

    return texto


def normalizar_columna(valor):
    """
    Limpia nombres de columnas.
    """

    return normalizar_texto(valor).strip()


# =========================================================
# LEER EXCEL
# =========================================================

def leer_excel(archivo_excel):
    """
    Lee la hoja VENTA o VENTAS.

    No importa en qué posición estén las columnas.
    """

    hojas_posibles = [
        "VENTA",
        "VENTAS",
    ]

    ultimo_error = None

    for hoja in hojas_posibles:

        try:

            df = pd.read_excel(
                archivo_excel,
                sheet_name=hoja,
                header=0,
            )

            # Limpiar nombres de columnas
            df.columns = [
                normalizar_columna(columna)
                for columna in df.columns
            ]

            # Eliminar columnas totalmente vacias
            df = df.dropna(
                axis=1,
                how="all"
            )

            # Eliminar filas totalmente vacias
            df = df.dropna(
                axis=0,
                how="all"
            )

            df = df.reset_index(
                drop=True
            )

            return df

        except Exception as e:

            ultimo_error = e

    raise ValueError(
        "No se encontro una hoja llamada VENTA ni VENTAS. "
        f"Ultimo error: {ultimo_error}"
    )


# =========================================================
# ENCONTRAR COLUMNA
# =========================================================

def encontrar_columna(
    df,
    nombre_objetivo
):
    """
    Busca una columna sin importar su posicion.

    Primero intenta coincidencia exacta.
    Luego coincidencia parcial.
    """

    objetivo = normalizar_texto(
        nombre_objetivo
    )

    # -----------------------------------------------------
    # COINCIDENCIA EXACTA
    # -----------------------------------------------------

    for columna in df.columns:

        columna_normalizada = normalizar_texto(
            columna
        )

        if columna_normalizada == objetivo:

            return columna

    # -----------------------------------------------------
    # COINCIDENCIA PARCIAL
    # -----------------------------------------------------

    for columna in df.columns:

        columna_normalizada = normalizar_texto(
            columna
        )

        if objetivo in columna_normalizada:

            return columna

    return None


# =========================================================
# COLUMNAS DISPONIBLES
# =========================================================

def obtener_columnas_disponibles(df):
    """
    Devuelve todas las columnas encontradas.
    """

    return list(
        df.columns
    )


# =========================================================
# CANALES
# =========================================================

def obtener_canales(df):
    """
    Devuelve los agentes/canales encontrados.
    """

    columna_canal = encontrar_columna(
        df,
        "CANAL"
    )

    if columna_canal is None:
        return []

    canales = (
        df[columna_canal]
        .apply(normalizar_texto)
    )

    canales = canales[
        canales != ""
    ]

    return sorted(
        canales.unique().tolist()
    )


def filtrar_por_canal(
    df,
    canal
):
    """
    Filtra el Excel por el canal seleccionado.
    """

    columna_canal = encontrar_columna(
        df,
        "CANAL"
    )

    if columna_canal is None:

        return df.iloc[0:0].copy()

    canal = normalizar_texto(
        canal
    )

    filtro = (
        df[columna_canal]
        .apply(normalizar_texto)
        == canal
    )

    return df[
        filtro
    ].copy()


# =========================================================
# AFILIADOS
# =========================================================

def obtener_afiliados_unicos(df):
    """
    Obtiene los afiliados unicos.
    """

    columna_afiliado = encontrar_columna(
        df,
        "AFILIADO"
    )

    if columna_afiliado is None:
        return []

    afiliados = (
        df[columna_afiliado]
        .apply(normalizar_texto)
    )

    afiliados = afiliados[
        afiliados != ""
    ]

    return sorted(
        afiliados.unique().tolist()
    )


# =========================================================
# CONTRATOS REALES
# =========================================================

def obtener_contratos_reales(df):
    """
    Las filas con TERMINAL = 0 corresponden a SIM CARD.

    No se eliminan del Excel original, pero no cuentan
    como un contrato independiente.
    """

    columna_terminal = encontrar_columna(
        df,
        "TERMINAL"
    )

    if columna_terminal is None:

        return df.copy()

    terminal = pd.to_numeric(
        df[columna_terminal],
        errors="coerce"
    )

    contratos = df[
        terminal.fillna(0) > 0
    ].copy()

    return contratos


def contar_contratos_reales(df):
    """
    Cuenta solamente contratos reales.
    """

    return len(
        obtener_contratos_reales(
            df
        )
    )


# =========================================================
# RESUMEN GENERAL
# =========================================================

def obtener_resumen_excel(df):
    """
    Genera resumen general del Excel.
    """

    afiliados = obtener_afiliados_unicos(
        df
    )

    return {
        "filas_totales":
            len(df),

        "afiliados_unicos":
            len(afiliados),

        "lista_afiliados":
            afiliados,

        "columnas":
            obtener_columnas_disponibles(
                df
            ),
    }


# =========================================================
# CONTRATO POR AFILIADO
# =========================================================

def obtener_contrato_por_afiliado(
    df,
    afiliado
):
    """
    Obtiene todas las filas de un afiliado.
    """

    columna_afiliado = encontrar_columna(
        df,
        "AFILIADO"
    )

    if columna_afiliado is None:

        return pd.DataFrame()

    afiliado = normalizar_texto(
        afiliado
    )

    filtro = (
        df[columna_afiliado]
        .apply(normalizar_texto)
        == afiliado
    )

    return df[
        filtro
    ].copy()


# =========================================================
# AFILIADOS POR CANAL
# =========================================================

def obtener_afiliados_por_canal(
    df,
    canal
):
    """
    Devuelve afiliados unicos de un canal.
    """

    df_canal = filtrar_por_canal(
        df,
        canal
    )

    return obtener_afiliados_unicos(
        df_canal
    )


# =========================================================
# RESUMEN DEL CANAL
# =========================================================

def obtener_resumen_canal(
    df,
    canal
):
    """
    Genera resumen del canal seleccionado.
    """

    df_canal = filtrar_por_canal(
        df,
        canal
    )

    afiliados = obtener_afiliados_unicos(
        df_canal
    )

    return {
        "canal":
            normalizar_texto(
                canal
            ),

        "filas":
            len(df_canal),

        "contratos_reales":
            contar_contratos_reales(
                df_canal
            ),

        "afiliados_unicos":
            len(afiliados),

        "lista_afiliados":
            afiliados,
    }