import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Monitorização de Banco de Horas", layout="wide")

st.title("⏳ Painel de Controlo: Banco de Horas da Equipa")

# --- ÁREA DE UPLOAD (Aceita CSV e XLSX) ---
st.write("Faça o upload do ficheiro exportado do sistema de ponto (Excel ou CSV).")
arquivo_upload = st.file_uploader("Escolha o ficheiro", type=["csv", "xlsx"])

# --- Função de Conversão ---
def converter_para_horas_decimais(valor):
    """Converte strings de tempo (ex: '-05:30') para float (-5.5)."""
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
        parts = valor.split(':')
        if len(parts) == 2:
            horas, minutos = map(int, parts)
            decimal = horas + (minutos / 60)
            return decimal * sinal
        return 0.0
    except:
        return 0.0

# --- Processamento ---
if arquivo_upload is not None:
    try:
        # 1. Extrair Data/Hora do Cabeçalho (Linha 3 do arquivo original)
        data_relatorio = "Data não identificada"
        try:
            if arquivo_upload.name.endswith('.csv'):
                df_head = pd.read_csv(arquivo_upload, header=None, nrows=3)
            else:
                df_head = pd.read_excel(arquivo_upload, header=None, nrows=3, engine='openpyxl')
            
            # Pega o valor da 3ª linha, 1ª coluna (índice 2, 0)
            val_data = str(df_head.iloc[2, 0])
            if val_data and val_data != 'nan':
                data_relatorio = val_data
        except Exception:
            pass # Se falhar a data, segue o fluxo
        
        # Resetar o ponteiro do arquivo para ler os dados completos
        arquivo_upload.seek(0)

        # 2. Ler Dados Principais
        if arquivo_upload.name.endswith('.csv'):
            df = pd.read_csv(arquivo_upload, skiprows=4)
        else:
            df = pd.read_excel(arquivo_upload, skiprows=4, engine='openpyxl', dtype={'Total Banco': str})

        # Verifica colunas essenciais
        if 'Total Banco' not in df.columns or 'Cargo' not in df.columns:
            st.error("Erro: O ficheiro não tem as colunas esperadas ('Total Banco', 'Cargo'). Verifique o relatório.")
        else:
            # Exibir Carimbo de Data
            st.info(f"📅 **Data de Extração dos Dados:** {data_relatorio}")

            # Tratamento de dados
            df['Total Banco'] = df['Total Banco'].astype(str)
            df['Saldo_Decimal'] = df['Total Banco'].apply(converter_para_horas_decimais)
            
            # --- BARRA LATERAL (Filtros) ---
            st.sidebar.header("Filtros")
            lista_cargos = df['Cargo'].dropna().unique()
            cargos = st.sidebar.multiselect("Filtrar por Cargo", options=lista_cargos, default=lista_cargos)
            
            df_filtrado = df[df['Cargo'].isin(cargos)]

            if df_filtrado.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            else:
                # --- MÉTRICAS (KPIs) ---
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                total_devedores = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].shape[0]
                total_credores = df_filtrado[df_filtrado['Saldo_Decimal'] > 0].shape[0]
                
                # Menor saldo (maior dívida)
                if not df_filtrado[df_filtrado['Saldo_Decimal'] < 0].empty:
                    maior_divida = df_filtrado['Saldo_Decimal'].min()
                else:
                    maior_divida = 0.0
                
                col1.metric("Pessoas com Saldo Negativo", f"{total_devedores}", delta_color="inverse")
                col2.metric("Pessoas com Saldo Positivo", f"{total_credores}")
                col3.metric("Maior Débito (Horas)", f"{maior_divida:.2f}", delta_color="inverse")

                # --- ALERTA DE CRÍTICOS (Slider) ---
                with st.expander("⚠️ Configurar Alerta de Nível Crítico (Clique para abrir)", expanded=False):
                    limite_alerta = st.slider("Definir limite crítico", min_value=-50.0, max_value=0.0, value=-10.0, step=0.5)
                    df_criticos = df_filtrado[df_filtrado['Saldo_Decimal'] <= limite_alerta]
                    if not df_criticos.empty:
                        st.error(f"Atenção! {len(df_criticos)} pessoas ultrapassaram {limite_alerta} horas.")
                    else:
                        st.success("Ninguém na zona crítica configurada.")

                # --- TABELA SOMENTE DE NEGATIVOS (Destaque Principal) ---
                st.divider()
                st.subheader("📉 Lista de Devedores (Apenas Saldo Negativo)")
                
                df_negativos = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].sort_values('Saldo_Decimal', ascending=True)

                if not df_negativos.empty:
                    st.dataframe(
                        df_negativos[['Nome', 'Cargo', 'Total Banco', 'Saldo_Decimal']]
                        .style.format({"Saldo_Decimal": "{:.2f}"})
                        .applymap(lambda x: 'color: red; font-weight: bold;', subset=['Total Banco', 'Saldo_Decimal']),
                        use_container_width=True
                    )
                else:
                    st.success("Excelente! Ninguém na equipa tem saldo negativo.")

                # --- TABELA GERAL (Expander) ---
                st.divider()
                with st.expander("Ver Tabela Completa (Todos os Colaboradores)"):
                    st.dataframe(
                        df_filtrado[['Nome', 'Cargo', 'Saldo Anterior', 'Saldo Período', 'Total Banco', 'Saldo_Decimal']]
                        .style.applymap(lambda x: 'color: red' if x < 0 else 'color: green', subset=['Saldo_Decimal'])
                        .format({"Saldo_Decimal": "{:.2f}"}),
                        use_container_width=True
                    )

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o ficheiro: {e}")

else:
    st.info("👆 Aguardando o upload do ficheiro (CSV ou XLSX).")
