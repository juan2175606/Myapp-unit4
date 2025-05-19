import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc
from dash.dash_table import DataTable
import json
import os

# Inicializar la aplicación Dash
app = Dash(__name__)
server = app.server  # Necesario para gunicorn en producción

# Información adicional
materia = "Aplicaciones 1, Universidad de La Salle, 2025"
nombre_estudiante = "Juan Andrés López Cubides"

# Rutas relativas
ruta_base = os.path.dirname(os.path.abspath(__file__))
ruta_datos = os.path.join(ruta_base, "data")
ruta_geojson = os.path.join(ruta_datos, "co_2018_MGN_DPTO_POLITICO.geojson")

# Cargar archivos
df_muertes = pd.read_excel(os.path.join(ruta_datos, "Anexo1.NoFetal2019_CE_15-03-23.xlsx"))
df_codigos_muerte = pd.read_excel(os.path.join(ruta_datos, "Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"), skiprows=8)
df_divipola = pd.read_excel(os.path.join(ruta_datos, "Anexo3.Divipola_CE_15-03-23.xlsx"))

# Preprocesamiento
df_muertes['AÑO'] = pd.to_numeric(df_muertes['AÑO'], errors='coerce')
df_muertes['MES'] = pd.to_numeric(df_muertes['MES'], errors='coerce')
df_muertes = df_muertes.dropna(subset=['AÑO', 'MES'])
df_muertes["FECHA"] = pd.to_datetime(df_muertes['AÑO'].astype(int).astype(str) + '-' + df_muertes['MES'].astype(int).astype(str) + '-01')
df_muertes['COD_MUERTE'] = df_muertes['COD_MUERTE'].str.strip()

# Homicidios y top 5 ciudades más violentas
homicidios = df_muertes[df_muertes['COD_MUERTE'].str.startswith('X95', na=False)]
homicidios_municipio_codigo = homicidios.groupby(["COD_MUNICIPIO", "COD_MUERTE"]).size().reset_index(name="TOTAL_HOMICIDIOS")
df_municipios = pd.merge(homicidios_municipio_codigo, df_divipola[["COD_MUNICIPIO", "MUNICIPIO"]].drop_duplicates(), on="COD_MUNICIPIO")
homicidios_por_ciudad = df_municipios.groupby("MUNICIPIO")["TOTAL_HOMICIDIOS"].sum().reset_index()
top_5_ciudades = homicidios_por_ciudad.nlargest(5, "TOTAL_HOMICIDIOS")

fig_barras = px.bar(
    top_5_ciudades, x="MUNICIPIO", y="TOTAL_HOMICIDIOS",
    title="Las 5 ciudades más violentas de Colombia (Homicidios - X95)",
    labels={"MUNICIPIO": "Ciudad", "TOTAL_HOMICIDIOS": "Total Homicidios"},
    color="TOTAL_HOMICIDIOS", color_continuous_scale="Reds"
)

# Muertes por departamento (mapa)
muertes_departamento = df_muertes.groupby("COD_DEPARTAMENTO").size().reset_index(name="TOTAL_MUERTES")
df_departamento = pd.merge(muertes_departamento, df_divipola[["COD_DEPARTAMENTO", "DEPARTAMENTO"]].drop_duplicates(), on="COD_DEPARTAMENTO")

with open(ruta_geojson, encoding="utf-8") as f:
    geojson = json.load(f)

fig_map = px.choropleth(
    df_departamento,
    geojson=geojson,
    locations="DEPARTAMENTO",
    featureidkey="properties.DPTO_CNMBR",
    color="TOTAL_MUERTES",
    color_continuous_scale="Reds",
    title="Total de muertes por departamento en Colombia (2019)"
)
fig_map.update_geos(fitbounds="locations", visible=False)

# Línea de tiempo de muertes por mes
muertes_por_mes = df_muertes.groupby("FECHA").size().reset_index(name="TOTAL_MUERTES")
fig_lineas = px.line(
    muertes_por_mes,
    x="FECHA",
    y="TOTAL_MUERTES",
    title="Total de muertes por mes en Colombia (2019)",
    labels={"FECHA": "Mes", "TOTAL_MUERTES": "Total de Muertes"}
)

# Tabla: 10 principales causas de muerte
top_10_causas = df_muertes.groupby("COD_MUERTE").size().reset_index(name="TOTAL_CASOS")
top_10_causas = pd.merge(
    top_10_causas,
    df_codigos_muerte[["Código de la CIE-10 cuatro caracteres", "Descripcion  de códigos mortalidad a cuatro caracteres"]],
    left_on="COD_MUERTE",
    right_on="Código de la CIE-10 cuatro caracteres",
    how="left"
)
top_10_causas = top_10_causas.nlargest(10, "TOTAL_CASOS")

# Ciudades y departamentos con menos homicidios
bottom_10_ciudades = homicidios_por_ciudad.nsmallest(10, "TOTAL_HOMICIDIOS")
fig_bottom_10_ciudades = px.pie(
    bottom_10_ciudades,
    names="MUNICIPIO",
    values="TOTAL_HOMICIDIOS",
    title="10 Ciudades con Menor Mortalidad en Colombia"
)

bottom_10_departamentos = df_departamento.nsmallest(10, "TOTAL_MUERTES")
fig_bottom_10_departamentos = px.pie(
    bottom_10_departamentos,
    names="DEPARTAMENTO",
    values="TOTAL_MUERTES",
    title="10 Departamentos con Menor Mortalidad en Colombia"
)

# Barras apiladas por sexo
df_sexos = df_muertes.groupby(['COD_DEPARTAMENTO', 'SEXO']).size().reset_index(name='TOTAL_MUERTES')
df_sexos = pd.merge(df_sexos, df_divipola[['COD_DEPARTAMENTO', 'DEPARTAMENTO']].drop_duplicates(), on="COD_DEPARTAMENTO")

fig_barras_sexo = px.bar(
    df_sexos,
    x="DEPARTAMENTO",
    y="TOTAL_MUERTES",
    color="SEXO",
    title="Comparación del total de muertes por sexo en cada departamento",
    labels={"DEPARTAMENTO": "Departamento", "TOTAL_MUERTES": "Total de Muertes", "SEXO": "Sexo"},
    color_discrete_map={"M": "blue", "F": "red"}
)

# Histograma por edades
bins = [0, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79, 84, 89, 150]
labels = ['0-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39',
          '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74',
          '75-79', '80-84', '85-89', '90+']

df_muertes['RANGO_EDAD'] = pd.cut(df_muertes['GRUPO_EDAD1'], bins=bins, labels=labels, right=True)
muertes_por_edad = df_muertes.groupby("RANGO_EDAD").size().reset_index(name="TOTAL_MUERTES")

fig_histograma = px.bar(
    muertes_por_edad,
    x="RANGO_EDAD",
    y="TOTAL_MUERTES",
    title="Distribución de Muertes por Rangos de Edad (2019)",
    labels={"RANGO_EDAD": "Rango de Edad", "TOTAL_MUERTES": "Total de Muertes"},
    color="TOTAL_MUERTES",
    color_continuous_scale="Blues"
)

# Layout
app.layout = html.Div([
    html.H1("Análisis de muertes en Colombia - 2019", style={'textAlign': 'center'}),
    html.H3(materia, style={'textAlign': 'center'}),
    html.H4(f"Desarrollado por: {nombre_estudiante}", style={'textAlign': 'center'}),

    html.Div([dcc.Graph(figure=fig_map), dcc.Graph(figure=fig_lineas)]),
    html.Div([dcc.Graph(figure=fig_barras), dcc.Graph(figure=fig_bottom_10_ciudades)]),
    html.Div([dcc.Graph(figure=fig_bottom_10_departamentos), dcc.Graph(figure=fig_histograma)]),
    html.Div([dcc.Graph(figure=fig_barras_sexo)]),

    html.H3("10 Principales Causas de Muerte", style={'textAlign': 'center'}),
    DataTable(
        data=top_10_causas.to_dict('records'),
        columns=[
            {"name": "Código de Muerte", "id": "COD_MUERTE"},
            {"name": "Descripción", "id": "Descripcion  de códigos mortalidad a cuatro caracteres"},
            {"name": "Total de Casos", "id": "TOTAL_CASOS"},
        ],
        style_table={'height': '300px', 'overflowY': 'auto'},
    ),
])

# No pongas if __name__ == '__main__' para despliegues con Gunicorn
