import streamlit as st
import pandas as pd
import re

# Título de la aplicación
st.title("Verificador Diario de Neteo de Compras y Ventas")

# Cargar archivo Excel
uploaded_file = st.file_uploader("Carga el archivo Excel del día", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Leer el archivo Excel (usando la primera hoja por defecto)
        df = pd.read_excel(uploaded_file, sheet_name=0)

        # Verificar que las columnas necesarias existen
        required_columns = ["Operación - Nombre", "Instrumento - Símbolo", "Cantidad"]
        if not all(col in df.columns for col in required_columns):
            st.error("El archivo debe contener las columnas: 'Operación - Nombre', 'Instrumento - Símbolo', 'Cantidad'")
        else:
            # Función para obtener el ticker base (eliminando sufijos "D", ".D" o "O")
            def get_base_ticker(symbol):
                return re.sub(r'(\.D|D|O)$', '', str(symbol).strip())

            # Crear columna para ticker base
            df["Ticker Base"] = df["Instrumento - Símbolo"].apply(get_base_ticker)

            # Separar operaciones de compras y ventas
            compras = df[df["Operación - Nombre"].isin(["Compra", "Compra Dólar MEP"])][["Ticker Base", "Cantidad", "Operación - Nombre", "Instrumento - Símbolo"]]
            ventas = df[df["Operación - Nombre"].isin(["Venta", "Venta Dólar MEP"])][["Ticker Base", "Cantidad", "Operación - Nombre", "Instrumento - Símbolo"]]

            # Agrupar por ticker base y sumar cantidades, conservando detalles de símbolos
            compras_sum = compras.groupby("Ticker Base").agg(
                Compra_Total=('Cantidad', 'sum'),
                Compra_Details=('Instrumento - Símbolo', lambda x: ', '.join(f"{q} ({s})" for q, s in zip(compras.loc[x.index, 'Cantidad'], x)))
            ).reset_index()

            ventas_sum = ventas.groupby("Ticker Base").agg(
                Venta_Total=('Cantidad', 'sum'),
                Venta_Details=('Instrumento - Símbolo', lambda x: ', '.join(f"{q} ({s})" for q, s in zip(ventas.loc[x.index, 'Cantidad'], x)))
            ).reset_index()

            # Combinar compras y ventas
            result = pd.merge(compras_sum, ventas_sum, on="Ticker Base", how="outer").fillna({'Compra_Total': 0, 'Venta_Total': 0, 'Compra_Details': '', 'Venta_Details': ''})
            result["Neto"] = result["Compra_Total"] - result["Venta_Total"]
            result["Compra"] = result["Compra_Total"].apply(lambda x: int(x) if x.is_integer() else x)
            result["Compra Dólar MEP"] = result["Compra_Details"].where(result["Compra_Details"] != '', 0)
            result["Venta"] = result["Venta_Total"].apply(lambda x: int(x) if x.is_integer() else x)
            result["Venta Dólar MEP"] = result["Venta_Details"].where(result["Venta_Details"] != '', 0)
            result["Neto (Compra Total - Venta Total)"] = result.apply(
                lambda row: f"{int(row['Compra_Total']) if row['Compra_Total'].is_integer() else row['Compra_Total']} - {int(row['Venta_Total']) if row['Venta_Total'].is_integer() else row['Venta_Total']} = {int(row['Neto']) if row['Neto'].is_integer() else row['Neto']}",
                axis=1
            )

            # Reordenar columnas para coincidir con el formato solicitado
            result = result[["Ticker Base", "Compra", "Compra Dólar MEP", "Venta", "Venta Dólar MEP", "Neto (Compra Total - Venta Total)"]].sort_values("Ticker Base")

            # Mostrar resultados
            st.subheader("Resultados del Neteo")
            st.dataframe(result)

            # Verificar si todos los tickers están neteados
            if (result["Neto"] == 0).all():
                st.success("¡Todas las cantidades de compras y ventas están neteadas (neto = 0 para todos los tickers)!")
            else:
                st.warning("Algunas cantidades no están neteadas. Revisa los tickers con 'Neto' diferente de 0.")
                # Mostrar tickers con problemas
                st.subheader("Tickers con discrepancias")
                discrepancias = result[result["Neto"] != 0][["Ticker Base", "Compra", "Compra Dólar MEP", "Venta", "Venta Dólar MEP", "Neto (Compra Total - Venta Total)"]]
                st.dataframe(discrepancias)

    except Exception as e:
        st.error(f"Error al procesar el archivo Excel: {str(e)}")
        st.info("Asegúrate de que el archivo sea un Excel válido (.xlsx) y que contenga las columnas requeridas.")

else:
    st.info("Por favor, carga un archivo Excel para analizar.")
