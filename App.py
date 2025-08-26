import streamlit as st
import pandas as pd
import re

# Título de la aplicación
st.title("Verificador Diario de Neteo de Compras y Ventas")

# Cargar archivo Excel
uploaded_file = st.file_uploader("Carga el archivo Excel del día", type=["xlsx"])

if uploaded_file is not None:
    # Leer el archivo Excel (asumiendo que la hoja es 'Sheet1')
    df = pd.read_excel(uploaded_file, sheet_name='Sheet1')

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

        # Agrupar por ticker base y sumar cantidades, conservando detalles de símbolos para mostrar en la tabla
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
        result["Compra Dólar MEP"] = result["Compra_Details"] if 'Compra Dólar MEP' in df["Operación - Nombre"].values else 0
        result["Venta"] = result["Venta_Total"].apply(lambda x: int(x) if x.is_integer() else x)
        result["Venta Dólar MEP"] = result["Venta_Details"] if 'Venta Dólar MEP' in df["Operación - Nombre"].values else 0
        result["Neto (Compra Total - Venta Total)"] = result["Neto"].apply(lambda x: f"{int(x) if x.is_integer() else x} - {int(result.loc[result.index[result['Neto'] == x].tolist()[0], 'Venta_Total']) if x.is_integer() else result.loc[result.index[result['Neto'] == x].tolist()[0], 'Venta_Total']} = {int(x) if x.is_integer() else x}")

        # Reordenar columnas para coincidir con el formato solicitado
        result = result[["Ticker Base", "Compra", "Compra Dólar MEP", "Venta", "Venta Dólar MEP", "Neto (Compra Total - Venta Total)"]].sort_values("Ticker Base")

        # Mostrar resultados
        st.subheader("Resultados del Neteo")
        st.dataframe(result)

        # Verificar si todos los tickers están neteados
        if (result["Neto (Compra Total - Venta Total)"] == '0').all():
            st.success("¡Todas las cantidades de compras y ventas están neteadas (neto = 0 para todos los tickers)!")
        else:
            st.warning("Algunas cantidades no están neteadas. Revisa los tickers con 'Neto' diferente de 0.")
            # Mostrar tickers con problemas
            st.subheader("Tickers con discrepancias")
            discrepancias = result[result["Neto (Compra Total - Venta Total)"] != '0']
            st.dataframe(discrepancias)

else:
    st.info("Por favor, carga un archivo Excel para analizar.")