import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Gestão de Banco de Horas", layout="wide")

st.title("⏳ Painel de Gestão: Banco de Horas")

# --- ÁREA DE UPLOAD ---
st.write("Faça o upload do ficheiro exportado do sistema de ponto (Excel ou CSV).")
arquivo_upload = st.file_uploader("Escolha o ficheiro", type=["csv", "xlsx"])

# --- Função Auxiliar: Converter para Decimal (apenas para cálculos internos) ---
def converter_para_horas_decimais(valor):
    if not isinstance(valor, str): return 0.0
    valor = valor.strip()
    sinal = -1 if valor.startswith("-") else 1
    if valor.startswith("-") or valor.startswith("+"): valor = valor[1:]
    try:
        parts = valor.split(':')
        if len(parts) == 2:
            return (int(parts[0]) + int(parts[1]) / 60) * sinal
        return 0.0
    except:
        return 0.0

# --- Função Auxiliar: Estilo Condicional ---
def estilizar_tabela(val):
    """
    Vermelho/Negrito para negativos.
    Verde/Negrito para positivos.
    Cinza para zerados.
    """
    val_str = str(val).strip()
    if val_str.startswith('-'):
        return 'color: #ff4b4b; font-weight: bold;' # Vermelho Streamlit
    elif val_str == "00:00" or val_str == "0":
        return 'color: gray;'
    else:
        return 'color: #2e7d32; font-weight: bold;' # Verde Escuro

# --- Processamento ---
if arquivo_upload is not None:
    try:
        # 1. Extrair Data do Cabeçalho
        data_relatorio = "Data não identificada"
        try:
            if arquivo_upload.name.endswith('.csv'):
                df_head = pd.read_csv(arquivo_upload, header=None, nrows=3)
            else:
                df_head = pd.read_excel(arquivo_upload, header=None, nrows=3, engine='openpyxl')
            val_data = str(df_head.iloc[2, 0])
            if val_data and val_data != 'nan': data_relatorio = val_data
        except: pass
        
        arquivo_upload.seek(0)

        # 2. Ler Dados
        if arquivo_upload.name.endswith('.csv'):
            df = pd.read_csv(arquivo_upload, skiprows=4)
        else:
            df = pd.read_excel(arquivo_upload, skiprows=4, engine='openpyxl', dtype={'Total Banco': str})

        if 'Total Banco' not in df.columns or 'Cargo' not in df.columns:
            st.error("Erro: Colunas 'Total Banco' ou 'Cargo' não encontradas.")
        else:
            st.info(f"📅 **Dados de:** {data_relatorio}")

            # Tratamentos
            df['Total Banco'] = df['Total Banco'].astype(str)
            df['Saldo_Decimal'] = df['Total Banco'].apply(converter_para_horas_decimais)
            
            # --- FILTROS ---
            st.sidebar.header("Filtros")
            cargos = st.sidebar.multiselect("Filtrar por Cargo", options=df['Cargo'].dropna().unique(), default=df['Cargo'].dropna().unique())
            df_filtrado = df[df['Cargo'].isin(cargos)]

            if not df_filtrado.empty:
                # --- KPIS ---
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                
                total_devedores = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].shape[0]
                total_credores = df_filtrado[df_filtrado['Saldo_Decimal'] > 0].shape[0]
                
                # Maior Dívida
                maior_divida_str = "00:00"
                if total_devedores > 0:
                     idx_pior = df_filtrado['Saldo_Decimal'].idxmin()
                     maior_divida_str = df_filtrado.loc[idx_pior, 'Total Banco']

                # Maior Crédito
                maior_credito_str = "00:00"
                if total_credores > 0:
                     idx_melhor = df_filtrado['Saldo_Decimal'].idxmax()
                     maior_credito_str = df_filtrado.loc[idx_melhor, 'Total Banco']

                col1.metric("🔴 Precisam de Atenção", f"{total_devedores}", delta_color="inverse")
                col2.metric("🟢 Podem tirar Folga", f"{total_credores}")
                col3.metric("Maior Débito", f"{maior_divida_str}", delta_color="inverse")
                col4.metric("Maior Crédito", f"{maior_credito_str}")

                st.divider()

                # --- ABAS DE GESTÃO ---
                aba1, aba2, aba3 = st.tabs(["🔴 Devedores (Ação Corretiva)", "🟢 Credores (Planejar Folgas)", "📋 Visão Geral"])

                # --- ABA 1: DEVEDORES ---
                with aba1:
                    st.subheader("Quem está devendo horas?")
                    st.write("Lista ordenada de quem deve mais para quem deve menos.")
                    
                    df_neg = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].sort_values('Saldo_Decimal', ascending=True)
                    
                    if not df_neg.empty:
                        st.dataframe(
                            df_neg[['Nome', 'Cargo', 'Total Banco']]
                            .style.applymap(estilizar_tabela, subset=['Total Banco']),
                            use_container_width=True,
                            height=500
                        )
                    else:
                        st.success("Ninguém está com saldo negativo! 🎉")

                # --- ABA 2: CREDORES ---
                with aba2:
                    st.subheader("Quem tem horas para retirar?")
                    st.write("Lista ordenada de quem tem mais horas acumuladas.")
                    
                    # Filtra Positivos e ordena Decrescente (Maior saldo no topo)
                    df_pos = df_filtrado[df_filtrado['Saldo_Decimal'] > 0].sort_values('Saldo_Decimal', ascending=False)
                    
                    if not df_pos.empty:
                        st.dataframe(
                            df_pos[['Nome', 'Cargo', 'Total Banco']]
                            .style.applymap(estilizar_tabela, subset=['Total Banco']),
                            use_container_width=True,
                            height=500
                        )
                    else:
                        st.info("Ninguém tem saldo positivo no momento.")

                # --- ABA 3: GERAL ---
                with aba3:
                    st.subheader("Tabela Completa")
                    st.dataframe(
                        df_filtrado[['Nome', 'Cargo', 'Saldo Anterior', 'Saldo Período', 'Total Banco']]
                        .style.applymap(estilizar_tabela, subset=['Total Banco']),
                        use_container_width=True
                    )

            else:
                st.warning("Sem dados para os filtros selecionados.")
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
else:
    st.info("👆 Aguardando upload.")
