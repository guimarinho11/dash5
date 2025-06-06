# Bibliotecas
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path


# Sempre primeiro
st.set_page_config(layout="wide", page_title="Dashboard de Despesas Semanal")

USERNAME = st.secrets["USERNAME"]
PASSWORD = st.secrets["PASSWORD"]

# Estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'login_attempted' not in st.session_state:
    st.session_state.login_attempted = False

# Função de login
def login():
    st.title("🔐 Login")
    with st.form("login_form"):
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if user.strip() == USERNAME and password.strip() == PASSWORD:
                st.session_state.logged_in = True
                st.rerun()  # Força a atualização da página
            else:
                st.session_state.login_attempted = True
                st.rerun()  # Força a atualização para mostrar o erro

    if st.session_state.login_attempted and not st.session_state.logged_in:
        st.error("Usuário ou senha incorretos.")

# Renderização condicional
if not st.session_state.logged_in:
    login()
    st.stop()

# Caminho do diretório contendo o arquivo CSV
data = r"Y:\Em desenvolvimento - Matheus\Estoque\dados_estoque\dados.csv"

# Carregar os dados
data1 = pd.read_csv(data, delimiter=';')

# Remover apóstrofos dos nomes das colunas
data1.columns = data1.columns.str.replace("'", "").str.strip()

# Ajustar tipos de dados
data1['PESO COLETADO POR SKU'] = data1['PESO COLETADO POR SKU'].astype(str).str.replace(',', '.')
data1['PESO COLETADO POR SKU'] = pd.to_numeric(data1['PESO COLETADO POR SKU'], errors='coerce')
data1['KG UND'] = data1['KG UND'].astype(str).str.replace(',', '.')
data1['KG UND'] = pd.to_numeric(data1['KG UND'], errors='coerce')

# Filtros únicos
matriculas_ordenadas = sorted(data1['MATRÍCULA'].unique())
nomes_ordenados = sorted(data1['NOME'].unique())
mes_ano_ordenados = sorted(data1['MÊS/ANO'].unique())

# Sidebar Filtros
st.sidebar.image("assets/logo claro.png", width=250)
st.sidebar.title("Filtros")

selected_nomes = st.sidebar.multiselect("NOME", nomes_ordenados, default=nomes_ordenados)
selected_matriculas = st.sidebar.multiselect("MATRÍCULA", matriculas_ordenadas, default=matriculas_ordenadas)
selected_mes_ano = st.sidebar.multiselect("MÊS/ANO", mes_ano_ordenados, default=mes_ano_ordenados)
exibir_media = st.sidebar.checkbox("Exibir linha de média", value=True)

# Filtrar DataFrame
df = data1[
    (data1["NOME"].isin(selected_nomes)) &
    (data1["MATRÍCULA"].isin(selected_matriculas)) &
    (data1["MÊS/ANO"].isin(selected_mes_ano))
]

st.title("Dashboard do Estoque")

# KPIs
col1, col2 = st.columns(2)
with col1:
    qtd_total = df["QTD COL"].sum()
    st.metric("Total Armazenado (QTD)", f"{qtd_total:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','))

with col2:
    peso_total = df["PESO COLETADO POR SKU"].sum()
    st.metric("Peso Total (kg)", f"{peso_total:,.2f}".replace('.', '#').replace(',', '.').replace('#', ','))

# Regras de pontuação
with st.expander("Cálculo da pontuação"):
    st.info("Pontuação = (Quantidade coletada * Peso) + Quantidade col. SKU + Quantidade coletada / 10000")

# Gráfico de Pontuação
def plot_pontuacao(df):
    dados_mensais = []
    for mes_ano in df["MÊS/ANO"].unique():
        dados_mes = df[df["MÊS/ANO"] == mes_ano].copy()
        dados_mes['QTD COLETADA POR USUARIO NO PERIODO'] = dados_mes.groupby(['MATRÍCULA'])['QTD COL'].transform('sum').round(2)
        dados_mes['PESO COLETADO POR USUARIO NO PERIODO'] = dados_mes.groupby(['MATRÍCULA'])['PESO COLETADO POR SKU'].transform('sum').round(2)
        dados_mes['QUANTIDADE SKU NO PERIODO'] = (
            dados_mes.groupby(['MATRÍCULA', 'DATA E HORA'])['SKU']
            .nunique()
            .groupby('MATRÍCULA')
            .sum()
            .reindex(dados_mes['MATRÍCULA'])
            .values
        )
        dados_mes = dados_mes.drop_duplicates(subset=[
            'MATRÍCULA', 
            'NOME',
            'QTD COLETADA POR USUARIO NO PERIODO',
            'PESO COLETADO POR USUARIO NO PERIODO',
            'QUANTIDADE SKU NO PERIODO'
        ])
        dados_mes['PONTUAÇÃO TOTAL'] = (
            dados_mes['QTD COLETADA POR USUARIO NO PERIODO'] +
            dados_mes['PESO COLETADO POR USUARIO NO PERIODO'] +
            dados_mes['QUANTIDADE SKU NO PERIODO']
        ) / 10000
        dados_mes['PONTUAÇÃO TOTAL'] = dados_mes['PONTUAÇÃO TOTAL'].round(2)
        dados_mes['MÊS/ANO'] = mes_ano
        dados_mensais.append(dados_mes)
    dados_totais = pd.concat(dados_mensais)
    dados_totais = dados_totais.sort_values('PONTUAÇÃO TOTAL', ascending=False)
    fig = go.Figure()
    for i, mes_ano in enumerate(sorted(dados_totais['MÊS/ANO'].unique())):
        dados_mes = dados_totais[dados_totais['MÊS/ANO'] == mes_ano]
        fig.add_trace(
            go.Bar(
                x=dados_mes['NOME'],
                y=dados_mes['PONTUAÇÃO TOTAL'],
                name=mes_ano,
                text=[f"{val:.2f}" for val in dados_mes['PONTUAÇÃO TOTAL']],
                textposition='inside',
                marker_color=["Orange", "Blue", "Yellow"][i % 3],
            )
        )
    fig.update_layout(
        title='PONTUAÇÃO POR MÊS',
        bargap=0.2,
        width=2000,
        height=600,
        barmode="group",
        showlegend=True,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, showticklabels=False),
    )
    return fig

st.plotly_chart(plot_pontuacao(df), use_container_width=True)

# Gráfico de Quantidade
def plot_quantidade(df):
    dados_mensais = []
    for mes_ano in df["MÊS/ANO"].unique():
        dados_mes = df[df["MÊS/ANO"] == mes_ano].copy()
        dados_mes['QTD ARMAZENADA POR USUARIO NO PERIODO'] = dados_mes.groupby(['MATRÍCULA'])['QTD COL'].transform('sum')
        dados_mes = dados_mes.drop_duplicates(subset=['MATRÍCULA', 'NOME'])
        dados_mes['MÊS/ANO'] = mes_ano
        dados_mensais.append(dados_mes)
    dados_totais = pd.concat(dados_mensais)
    dados_totais = dados_totais.sort_values('QTD ARMAZENADA POR USUARIO NO PERIODO', ascending=False)
    fig = go.Figure()
    for i, mes_ano in enumerate(sorted(dados_totais['MÊS/ANO'].unique())):
        dados_mes = dados_totais[dados_totais['MÊS/ANO'] == mes_ano]
        fig.add_trace(
            go.Bar(
                x=dados_mes['NOME'],
                y=dados_mes['QTD ARMAZENADA POR USUARIO NO PERIODO'],
                name=mes_ano,
                text=[f"{val:,.0f}".replace('.', '#').replace(',', '.').replace('#', ',') for val in dados_mes['QTD ARMAZENADA POR USUARIO NO PERIODO'].tolist()],
                textposition='inside',
                marker_color=["Orange", "Blue", "Yellow"][i % 3],
            )
        )
        if exibir_media:
            media_mes = dados_mes['QTD ARMAZENADA POR USUARIO NO PERIODO'].mean()
            fig.add_trace(
                go.Scatter(
                    x=dados_mes['NOME'],
                    y=[media_mes] * len(dados_mes['NOME']),
                    mode="lines+text",
                    name=f"Média {mes_ano}",
                    line=dict(color=["Orange", "Blue", "Yellow"][i % 3], width=2, dash="dash"),
                    text=[f"{media_mes:,.0f}".replace('.', '#').replace(',', '.').replace('#', ',') if j == 0 else "" for j in range(len(dados_mes['NOME']))],
                    textposition="top center",
                    textfont=dict(color="black"),
                )
            )
    fig.update_layout(
        title='QUANTIDADE ARMAZENADA POR USUÁRIO',
        bargap=0.2,
        width=2000,
        height=600,
        barmode="group",
        showlegend=True,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, showticklabels=False),
    )
    return fig

st.plotly_chart(plot_quantidade(df), use_container_width=True)

# Gráfico de Peso
def plot_peso(df):
    dados_mensais = []
    for mes_ano in df["MÊS/ANO"].unique():
        dados_mes = df[df["MÊS/ANO"] == mes_ano].copy()
        dados_mes['PESO COLETADO'] = dados_mes.groupby(['MATRÍCULA'])['PESO COLETADO POR SKU'].transform('sum')
        dados_mes['PESO COLETADO'] = dados_mes['PESO COLETADO'].round(2) / 1000
        dados_mes = dados_mes.drop_duplicates(subset=['MATRÍCULA', 'NOME'])
        dados_mes['MÊS/ANO'] = mes_ano
        dados_mensais.append(dados_mes)
    dados_totais = pd.concat(dados_mensais)
    dados_totais = dados_totais.sort_values('PESO COLETADO', ascending=False)
    fig = go.Figure()
    for i, mes_ano in enumerate(sorted(dados_totais['MÊS/ANO'].unique())):
        dados_mes = dados_totais[dados_totais['MÊS/ANO'] == mes_ano]
        fig.add_trace(
            go.Bar(
                x=dados_mes['NOME'],
                y=dados_mes['PESO COLETADO'],
                name=mes_ano,
                text=[f"{int(val):,}".replace(',', '.') for val in dados_mes['PESO COLETADO'].tolist()],
                textposition='inside',
                marker_color=["Orange", "Blue", "Yellow"][i % 3],
            )
        )
        if exibir_media:
            media_mes = dados_mes['PESO COLETADO'].mean()
            fig.add_trace(
                go.Scatter(
                    x=dados_mes['NOME'],
                    y=[media_mes] * len(dados_mes['NOME']),
                    mode="lines+text",
                    name=f"Média {mes_ano}",
                    line=dict(color=["Orange", "Blue", "Yellow"][i % 3], width=2, dash="dash"),
                    text=[f"{int(media_mes):,}".replace(',', '.') if j == 0 else "" for j in range(len(dados_mes['NOME']))],
                    textposition="top center",
                    textfont=dict(color="black"),
                )
            )
    fig.update_layout(
        title='PESO COLETADO POR USUÁRIO (EM TONELADAS)',
        bargap=0.2,
        width=2000,
        height=600,
        barmode="group",
        showlegend=True,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, showticklabels=False),
    )
    return fig

st.plotly_chart(plot_peso(df), use_container_width=True)

# Gráfico de SKU
def plot_sku(df):
    filtered_data = df[df['QTD COL'] > 0]
    dados_mensais = []
    for mes_ano in filtered_data["MÊS/ANO"].unique():
        dados_mes = filtered_data[filtered_data["MÊS/ANO"] == mes_ano].copy()
        dados_mes = dados_mes.sort_values(["MATRÍCULA", "DATA E HORA", "SKU"])
        dados_mes['CONTAGEM'] = dados_mes.groupby(['MATRÍCULA', 'SKU', 'DATA E HORA'])['MATRÍCULA'].transform('count')
        dados_mes['VALIDO'] = (dados_mes['CONTAGEM'] == 1).astype(int)
        quantidade_sku_por_usuario = (
            dados_mes[dados_mes['VALIDO'] == 1]
            .groupby(["MATRÍCULA", "NOME"])
            .size()
            .reset_index(name="QUANTIDADE SKU NO PERIODO")
        )
        dados_mes = pd.merge(
            dados_mes.drop_duplicates(subset=["MATRÍCULA", "NOME"]),
            quantidade_sku_por_usuario,
            on=["MATRÍCULA", "NOME"],
            how="left"
        )
        dados_mes["MÊS/ANO"] = mes_ano
        dados_mensais.append(dados_mes)
    dados_totais = pd.concat(dados_mensais)
    dados_totais = dados_totais.sort_values("QUANTIDADE SKU NO PERIODO", ascending=False)
    fig = go.Figure()
    for i, mes_ano in enumerate(sorted(dados_totais['MÊS/ANO'].unique())):
        dados_mes = dados_totais[dados_totais['MÊS/ANO'] == mes_ano]
        fig.add_trace(
            go.Bar(
                x=dados_mes['NOME'],
                y=dados_mes['QUANTIDADE SKU NO PERIODO'],
                name=mes_ano,
                text=[f"{val:,.0f}".replace('.', '#').replace(',', '.').replace('#', ',') for val in dados_mes['QUANTIDADE SKU NO PERIODO'].tolist()],
                textposition='inside',
                marker_color=["Orange", "Blue", "Yellow"][i % 3],
            )
        )
        if exibir_media:
            media_mes = dados_mes['QUANTIDADE SKU NO PERIODO'].mean()
            fig.add_trace(
                go.Scatter(
                    x=dados_mes['NOME'],
                    y=[media_mes] * len(dados_mes['NOME']),
                    mode="lines+text",
                    name=f"Média {mes_ano}",
                    line=dict(color=["Orange", "Blue", "Yellow"][i % 3], width=2, dash="dash"),
                    text=[f"{media_mes:,.0f}".replace('.', '#').replace(',', '.').replace('#', ',') if j == 0 else "" for j in range(len(dados_mes['NOME']))],
                    textposition="top center",
                    textfont=dict(color="black"),
                )
            )
    fig.update_layout(
        title="QUANTIDADE DE SKU'S ARMAZENADOS",
        bargap=0.2,
        width=2000,
        height=600,
        barmode="group",
        showlegend=True,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, showticklabels=False),
    )
    return fig

st.plotly_chart(plot_sku(df), use_container_width=True)

# Tabela
st.subheader("Tabela Origem - Estoque")
st.dataframe(df, use_container_width=False)