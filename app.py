import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Monitoramento de Banco de Horas", layout="wide")

st.title("⏳ Painel de Controle: Banco de Horas da Equipe")

# --- Função para limpar e converter as horas (ex: "-06:00" -> -6.0) ---
def converter_para_horas_decimais(valor):
    if not isinstance(valor, str):
        return 0.0
    
    valor = valor.strip()
    sinal = 1
    
    if valor.startswith("-"):
        sinal = -1
        valor = valor[1:]
    elif valor.startswith("+"):
        valor = valor[1:]
        
    try:
        horas, minutos = map(int, valor.split(':'))
        decimal = horas + (minutos / 60)
        return decimal * sinal
    except:
        return 0.0

# --- Carregamento dos Dados ---
# O arquivo carregado parece ter 4 linhas de cabeçalho antes da tabela real
arquivo = "horas.csv"

try:
    # Ler o CSV pulando as 4 primeiras linhas
    df = pd.read_csv(arquivo, skiprows=4)
    
    # Processar a coluna de Total Banco (Converter para número)
    # Ajuste 'Total Banco' se o nome exato na coluna for diferente
    coluna_saldo = 'Total Banco' 
    df['Saldo_Decimal'] = df[coluna_saldo].apply(converter_para_horas_decimais)
    
    # --- BARRA LATERAL (Filtros) ---
    st.sidebar.header("Filtros")
    cargos = st.sidebar.multiselect("Filtrar por Cargo", options=df['Cargo'].unique(), default=df['Cargo'].unique())
    df_filtrado = df[df['Cargo'].isin(cargos)]

    # --- ALERTAS E MÉTRICAS (KPIs) ---
    col1, col2, col3 = st.columns(3)
    
    total_devedores = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].shape[0]
    total_credores = df_filtrado[df_filtrado['Saldo_Decimal'] > 0].shape[0]
    maior_divida = df_filtrado['Saldo_Decimal'].min()
    
    col1.metric("Pessoas com Saldo Negativo", f"{total_devedores} colaboradores", delta_color="inverse")
    col2.metric("Pessoas com Saldo Positivo", f"{total_credores} colaboradores")
    col3.metric("Maior Débito Encontrado", f"{maior_divida:.2f} horas", delta_color="inverse")

    # --- ALERTA VISUAL: Tabela de Atenção ---
    st.subheader("⚠️ Alertas: Colaboradores com Saldo Negativo Crítico")
    limite_alerta = st.slider("Definir limite de alerta (horas negativas)", min_value=-50.0, max_value=0.0, value=-10.0, step=0.5)
    
    df_alerta = df_filtrado[df_filtrado['Saldo_Decimal'] <= limite_alerta][['Nome', 'Cargo', 'Total Banco', 'Saldo_Decimal']]
    
    if not df_alerta.empty:
        st.error(f"Atenção! {len(df_alerta)} pessoas têm mais de {abs(limite_alerta)} horas de débito.")
        st.dataframe(df_alerta.style.format({"Saldo_Decimal": "{:.2f}"}), use_container_width=True)
    else:
        st.success("Nenhum colaborador ultrapassou o limite de alerta configurado.")

    # --- VISUALIZAÇÃO GRÁFICA ---
    st.divider()
    st.subheader("📊 Visão Geral da Equipe")
    
    # Gráfico de Barras
    fig = px.bar(
        df_filtrado.sort_values('Saldo_Decimal'), 
        x='Saldo_Decimal', 
        y='Nome', 
        orientation='h',
        color='Saldo_Decimal',
        title="Saldo de Horas por Colaborador",
        color_continuous_scale=['red', 'gray', 'green'],
        height=600
    )
    # Adicionar linha vertical no zero
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="black")
    st.plotly_chart(fig, use_container_width=True)

    # --- TABELA GERAL ---
    with st.expander("Ver Tabela Completa"):
        # Colorir números negativos de vermelho e positivos de verde
        def colorir_saldo(val):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}'

        st.dataframe(
            df_filtrado[['Nome', 'Cargo', 'Saldo Anterior', 'Saldo Período', 'Total Banco', 'Saldo_Decimal']]
            .style.applymap(lambda x: 'color: red' if x < 0 else 'color: green', subset=['Saldo_Decimal']),
            use_container_width=True
        )

except FileNotFoundError:
    st.error(f"Arquivo '{arquivo}' não encontrado. Certifique-se de que ele está na mesma pasta do script.")
except Exception as e:
    st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
