import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Monitorização de Banco de Horas", layout="wide")

st.title("⏳ Painel de Controlo: Banco de Horas da Equipa")

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

# --- Função Auxiliar: Estilo Condicional (Vermelho para Negativo) ---
def estilo_negativo(val):
    """Colore o texto de vermelho se começar com '-' e verde caso contrário"""
    color = 'red' if str(val).strip().startswith('-') else 'green'
    # Deixa negrito se for negativo
    weight = 'bold' if str(val).strip().startswith('-') else 'normal'
    return f'color: {color}; font-weight: {weight}'

# --- Processamento ---
if arquivo_upload is not None:
    try:
        # 1. Extrair Data/Hora (Cabeçalho)
        data_relatorio = "Data não identificada"
        try:
            if arquivo_upload.name.endswith('.csv'):
                df_head = pd.read_csv(arquivo_upload, header=None, nrows=3)
            else:
                df_head = pd.read_excel(arquivo_upload, header=None, nrows=3, engine='openpyxl')
            val_data = str(df_head.iloc[2, 0])
            if val_data and val_data != 'nan': data_relatorio = val_data
        except: pass
        
        arquivo_upload.seek(0) # Resetar ponteiro

        # 2. Ler Dados
        if arquivo_upload.name.endswith('.csv'):
            df = pd.read_csv(arquivo_upload, skiprows=4)
        else:
            df = pd.read_excel(arquivo_upload, skiprows=4, engine='openpyxl', dtype={'Total Banco': str})

        if 'Total Banco' not in df.columns or 'Cargo' not in df.columns:
            st.error("Erro: Colunas 'Total Banco' ou 'Cargo' não encontradas.")
        else:
            st.info(f"📅 **Dados atualizados em:** {data_relatorio}")

            # Tratamentos
            df['Total Banco'] = df['Total Banco'].astype(str)
            # Criamos a coluna decimal APENAS para ordenar e gerar gráfico, mas não vamos exibi-la
            df['Saldo_Decimal'] = df['Total Banco'].apply(converter_para_horas_decimais)
            
            # --- FILTROS ---
            st.sidebar.header("Filtros")
            cargos = st.sidebar.multiselect("Filtrar por Cargo", options=df['Cargo'].dropna().unique(), default=df['Cargo'].dropna().unique())
            df_filtrado = df[df['Cargo'].isin(cargos)]

            if not df_filtrado.empty:
                # --- KPIS ---
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                total_devedores = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].shape[0]
                total_credores = df_filtrado[df_filtrado['Saldo_Decimal'] > 0].shape[0]
                maior_divida = df_filtrado[df_filtrado['Saldo_Decimal'] < 0]['Total Banco'].min() if total_devedores > 0 else "00:00"
                # Para mostrar a maior dívida, pegamos o valor original em string correspondente ao menor decimal
                if total_devedores > 0:
                     idx_pior = df_filtrado['Saldo_Decimal'].idxmin()
                     maior_divida_str = df_filtrado.loc[idx_pior, 'Total Banco']
                else:
                     maior_divida_str = "00:00"

                col1.metric("Pessoas com Saldo Negativo", f"{total_devedores}", delta_color="inverse")
                col2.metric("Pessoas com Saldo Positivo", f"{total_credores}")
                col3.metric("Maior Débito", f"{maior_divida_str}", delta_color="inverse")

                # --- ALERTA CRÍTICO ---
                with st.expander("⚠️ Configurar Alerta Crítico", expanded=False):
                    limite = st.slider("Limite (horas negativas)", -50.0, 0.0, -10.0, 0.5)
                    df_crit = df_filtrado[df_filtrado['Saldo_Decimal'] <= limite]
                    if not df_crit.empty:
                        st.error(f"Atenção! {len(df_crit)} pessoas ultrapassaram {limite} horas.")
                        # Mostra tabela sem o decimal
                        st.dataframe(
                            df_crit[['Nome', 'Cargo', 'Total Banco']]
                            .style.applymap(estilo_negativo, subset=['Total Banco']),
                            use_container_width=True
                        )
                    else:
                        st.success("Ninguém na zona crítica.")

                # --- TABELA DEVEDORES (SEM DECIMAL) ---
                st.divider()
                st.subheader("📉 Lista de Devedores (Apenas Saldo Negativo)")
                
                # Ordena pelo decimal (bastidores), mas exibe apenas colunas úteis
                df_neg = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].sort_values('Saldo_Decimal', ascending=True)

                if not df_neg.empty:
                    st.dataframe(
                        df_neg[['Nome', 'Cargo', 'Total Banco']]
                        .style.applymap(estilo_negativo, subset=['Total Banco']),
                        use_container_width=True
                    )
                else:
                    st.success("Ninguém com saldo negativo!")

                # --- TABELA GERAL (SEM DECIMAL) ---
                st.divider()
                with st.expander("Ver Tabela Completa"):
                    st.dataframe(
                        df_filtrado[['Nome', 'Cargo', 'Saldo Anterior', 'Saldo Período', 'Total Banco']]
                        .style.applymap(estilo_negativo, subset=['Saldo Anterior', 'Saldo Período', 'Total Banco']),
                        use_container_width=True
                    )

            else:
                st.warning("Sem dados para os filtros selecionados.")
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
else:
    st.info("👆 Aguardando upload.")
