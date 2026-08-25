import streamlit as st
import pandas as pd

from modules.excel_reader import (
    leer_excel,
    obtener_resumen_excel,
    obtener_canales,
    filtrar_por_canal,
    obtener_contratos_reales,
    contar_contratos_reales,
    normalizar_texto,
)

from modules.document_reader import (
    leer_documento,
    leer_serial_documento,
)

from modules.matcher import (
    buscar_mejor_coincidencia,
)


# =========================================================
# CONFIGURACION
# =========================================================

st.set_page_config(
    page_title="Automatizacion de Cruces",
    page_icon="📄",
    layout="wide",
)

st.title(
    "📄 Automatizacion de Cruces de Contratos"
)

st.write(
    """
    Carga el Excel maestro, selecciona el agente autorizado
    y carga su carpeta de contratos.
    """
)

st.divider()


# =========================================================
# VARIABLES
# =========================================================

df = None
df_canal = None
canal_seleccionado = None
contract_files = []


# =========================================================
# 1. EXCEL
# =========================================================

st.header("1. Cargar base de datos")

excel_file = st.file_uploader(
    "Selecciona el archivo Excel",
    type=[
        "xlsx",
        "xls",
    ],
    key="excel_file",
)


if excel_file is not None:

    try:

        df = leer_excel(
            excel_file
        )

        resumen = obtener_resumen_excel(
            df
        )

        st.success(
            f"Excel cargado correctamente: "
            f"{excel_file.name}"
        )

        col1, col2 = st.columns(
            2
        )

        with col1:

            st.metric(
                "Filas totales",
                resumen[
                    "filas_totales"
                ],
            )

        with col2:

            st.metric(
                "Afiliados unicos",
                resumen[
                    "afiliados_unicos"
                ],
            )

        st.subheader(
            "Seleccionar agente autorizado"
        )

        canales = obtener_canales(
            df
        )

        if canales:

            canal_seleccionado = st.selectbox(
                "CANAL",
                canales,
            )

            df_canal = filtrar_por_canal(
                df,
                canal_seleccionado,
            )

            contratos_reales = (
                obtener_contratos_reales(
                    df_canal
                )
            )

            st.success(
                f"Agente seleccionado: "
                f"{canal_seleccionado}"
            )

            col1, col2, col3 = st.columns(
                3
            )

            with col1:

                st.metric(
                    "Filas originales",
                    len(
                        df_canal
                    ),
                )

            with col2:

                st.metric(
                    "Contratos esperados",
                    contar_contratos_reales(
                        df_canal
                    ),
                )

            with col3:

                st.metric(
                    "SIM CARD ignoradas",
                    len(
                        df_canal
                    )
                    - len(
                        contratos_reales
                    ),
                )

            with st.expander(
                f"Ver contratos de "
                f"{canal_seleccionado}"
            ):

                st.dataframe(
                    contratos_reales,
                    use_container_width=True,
                )

        else:

            st.error(
                "No se encontro la columna CANAL."
            )

    except Exception as e:

        st.error(
            f"Error leyendo Excel: {e}"
        )


st.divider()


# =========================================================
# 2. CARGAR CONTRATOS
# =========================================================

st.header(
    "2. Cargar contratos"
)


if canal_seleccionado:

    st.info(
        f"Selecciona la carpeta de contratos de "
        f"{canal_seleccionado}."
    )

else:

    st.info(
        "Primero carga el Excel y selecciona un agente."
    )


archivos_subidos = st.file_uploader(
    "Selecciona la carpeta de contratos",
    type=None,
    accept_multiple_files="directory",
    key="contract_folder",
)


if archivos_subidos:

    extensiones_validas = (
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
    )

    contract_files = [
        archivo
        for archivo in archivos_subidos
        if archivo.name.lower().endswith(
            extensiones_validas
        )
    ]

    archivos_ignorados = [
        archivo
        for archivo in archivos_subidos
        if not archivo.name.lower().endswith(
            extensiones_validas
        )
    ]

    st.success(
        f"{len(contract_files)} contratos validos cargados."
    )

    if archivos_ignorados:

        st.info(
            f"{len(archivos_ignorados)} archivos "
            f"temporales fueron ignorados."
        )


st.divider()


# =========================================================
# 3. RESUMEN
# =========================================================

st.header(
    "3. Resumen"
)

col1, col2, col3 = st.columns(
    3
)


with col1:

    if df_canal is not None:

        st.metric(
            "Contratos esperados",
            contar_contratos_reales(
                df_canal
            ),
        )

    else:

        st.metric(
            "Contratos esperados",
            0,
        )


with col2:

    st.metric(
        "Contratos cargados",
        len(
            contract_files
        ),
    )


with col3:

    if df_canal is not None:

        diferencia = (
            len(
                contract_files
            )
            - contar_contratos_reales(
                df_canal
            )
        )

        st.metric(
            "Diferencia",
            diferencia,
        )

    else:

        st.metric(
            "Diferencia",
            0,
        )


st.divider()


# =========================================================
# 4. VALIDACION
# =========================================================

st.header(
    "4. Validar contratos"
)


if st.button(
    "🔍 Iniciar validacion",
    type="primary",
    use_container_width=True,
):

    if df_canal is None:

        st.error(
            "Debes cargar el Excel y seleccionar un agente."
        )

    elif not contract_files:

        st.error(
            "Debes cargar la carpeta de contratos."
        )

    else:

        resultados = []

        contratos_encontrados = set()

        progreso = st.progress(
            0
        )

        estado_proceso = st.empty()

        total = len(
            contract_files
        )


        for numero, archivo in enumerate(
            contract_files,
            start=1
        ):

            try:

                # =========================================
                # PRIMER OCR RAPIDO
                # =========================================

                estado_proceso.write(
                    f"Procesando {numero} de {total}: "
                    f"{archivo.name} - lectura inicial"
                )

                texto = leer_documento(
                    archivo
                )

                resultado = buscar_mejor_coincidencia(
                    df_canal,
                    texto,
                    archivo.name,
                    segundo_intento=False,
                )


                # =========================================
                # RIF REPETIDO:
                # SEGUNDO OCR SOLO PARA SERIAL
                # =========================================

                if resultado.get(
                    "requiere_ocr_serial",
                    False
                ):

                    estado_proceso.write(
                        f"Procesando {numero} de {total}: "
                        f"{archivo.name} - buscando serial"
                    )

                    texto_serial = (
                        leer_serial_documento(
                            archivo
                        )
                    )

                    texto_completo = (
                        texto
                        + "\n"
                        + texto_serial
                    )

                    resultado = (
                        buscar_mejor_coincidencia(
                            df_canal,
                            texto_completo,
                            archivo.name,
                            segundo_intento=True,
                        )
                    )


                # =========================================
                # OBTENER FILA
                # =========================================

                indice = resultado[
                    "indice"
                ]

                fila_excel = None

                if indice is not None:

                    fila_excel = (
                        df_canal.loc[
                            indice
                        ]
                    )

                    contratos_encontrados.add(
                        indice
                    )


                # =========================================
                # DATOS A MOSTRAR
                # =========================================

                contexto = resultado.get(
                    "contexto",
                    {}
                )

                afiliado = ""
                rif = ""
                razon_social = ""
                serial = ""


                if fila_excel is not None:

                    afiliado = normalizar_texto(
                        fila_excel.get(
                            "AFILIADO",
                            ""
                        )
                    )

                    rif = normalizar_texto(
                        fila_excel.get(
                            "RIF",
                            ""
                        )
                    )

                    razon_social = normalizar_texto(
                        fila_excel.get(
                            "RAZON SOCIAL",
                            ""
                        )
                    )

                    serial = normalizar_texto(
                        fila_excel.get(
                            "SERIAL",
                            ""
                        )
                    )

                else:

                    afiliado = contexto.get(
                        "AFILIADO",
                        ""
                    )

                    rif = contexto.get(
                        "RIF",
                        ""
                    )

                    razon_social = contexto.get(
                        "RAZON SOCIAL",
                        ""
                    )

                    if rif:

                        serial = (
                            "NO SE PUDO DETECTAR"
                        )


                # =========================================
                # GUARDAR RESULTADO
                # =========================================

                resultados.append(
                    {
                        "ARCHIVO":
                            archivo.name,

                        "ESTADO":
                            resultado[
                                "estado"
                            ],

                        "PUNTOS":
                            resultado[
                                "puntos"
                            ],

                        "COINCIDENCIAS":
                            ", ".join(
                                resultado[
                                    "coincidencias"
                                ]
                            ),

                        "AFILIADO":
                            afiliado,

                        "RIF":
                            rif,

                        "RAZON SOCIAL":
                            razon_social,

                        "SERIAL POS":
                            serial,
                    }
                )


            except Exception as e:

                resultados.append(
                    {
                        "ARCHIVO":
                            archivo.name,

                        "ESTADO":
                            "ERROR",

                        "PUNTOS":
                            0,

                        "COINCIDENCIAS":
                            str(e),

                        "AFILIADO":
                            "",

                        "RIF":
                            "",

                        "RAZON SOCIAL":
                            "",

                        "SERIAL POS":
                            "",
                    }
                )


            progreso.progress(
                numero / total
            )


        estado_proceso.empty()

        st.success(
            "Validacion terminada."
        )


        # =================================================
        # DATAFRAME RESULTADOS
        # =================================================

        df_resultados = pd.DataFrame(
            resultados
        )


        encontrados = (
            df_resultados[
                "ESTADO"
            ]
            == "ENCONTRADO"
        ).sum()

        revisar = (
            df_resultados[
                "ESTADO"
            ]
            == "REVISAR"
        ).sum()

        no_encontrados = (
            df_resultados[
                "ESTADO"
            ]
            == "NO ENCONTRADO"
        ).sum()

        errores = (
            df_resultados[
                "ESTADO"
            ]
            == "ERROR"
        ).sum()


        col1, col2, col3, col4 = st.columns(
            4
        )


        with col1:

            st.metric(
                "✅ Encontrados",
                encontrados,
            )


        with col2:

            st.metric(
                "⚠️ Revisar",
                revisar,
            )


        with col3:

            st.metric(
                "❌ No encontrados",
                no_encontrados,
            )


        with col4:

            st.metric(
                "Errores",
                errores,
            )


        # =================================================
        # RESULTADOS
        # =================================================

        st.subheader(
            "Resultados"
        )

        st.dataframe(
            df_resultados,
            use_container_width=True,
        )


        # =================================================
        # FALTANTES
        # =================================================

        contratos_excel = (
            obtener_contratos_reales(
                df_canal
            )
        )


        indices_faltantes = [
            indice
            for indice
            in contratos_excel.index
            if indice
            not in contratos_encontrados
        ]


        df_faltantes = (
            contratos_excel.loc[
                indices_faltantes
            ]
        )


        st.subheader(
            "Contratos del Excel sin documento identificado"
        )

        st.metric(
            "Faltantes",
            len(
                df_faltantes
            ),
        )


        if not df_faltantes.empty:

            columnas_mostrar = [
                columna
                for columna in [
                    "AFILIADO",
                    "RAZON SOCIAL",
                    "RIF",
                    "SERIAL",
                    "PEDIDO",
                    "FACTURA",
                ]
                if columna
                in df_faltantes.columns
            ]

            st.dataframe(
                df_faltantes[
                    columnas_mostrar
                ],
                use_container_width=True,
            )


st.divider()

st.caption(
    "Sistema de validacion y cruce de contratos."
)