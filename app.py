import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Monitoramento de Banco de Horas", layout="wide")

st.title("⏳ Painel de Controle: Banco de Horas da Equipe")

# --- ÁREA DE UPLOAD ---
st.write("Faça o upload do arquivo CSV exportado do sistema de ponto.")
arquivo_upload = st.file_uploader("Escolha o arquivo CSV", type=["csv"])

# --- Função de Conversão (Mantida igual) ---
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

# --- Processamento (Só roda se tiver arquivo) ---
if arquivo_upload is not None:
    try:
        # Ler o arquivo enviado (pulando as 4 linhas de cabeçalho padrão)
        df = pd.read_csv(arquivo_upload, skiprows=4)
        
        # Verifica se as colunas essenciais existem
        if 'Total Banco' not in df.columns or 'Cargo' not in df.columns:
            st.error("Erro: O arquivo não tem as colunas esperadas ('Total Banco', 'Cargo'). Verifique se é o relatório correto.")
        else:
            # Processamento dos dados
            df['Saldo_Decimal'] = df['Total Banco'].apply(converter_para_horas_decimais)
            
            # --- BARRA LATERAL (Filtros) ---
            st.sidebar.header("Filtros")
            lista_cargos = df['Cargo'].dropna().unique()
            cargos = st.sidebar.multiselect("Filtrar por Cargo", options=lista_cargos, default=lista_cargos)
            
            # Filtrar DataFrame
            df_filtrado = df[df['Cargo'].isin(cargos)]

            if df_filtrado.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            else:
                # --- ALERTAS E MÉTRICAS ---
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                total_devedores = df_filtrado[df_filtrado['Saldo_Decimal'] < 0].shape[0]
                total_credores = df_filtrado[df_filtrado['Saldo_Decimal'] > 0].shape[0]
                
                # Tratamento para caso não haja ninguém com saldo negativo
                if not df_filtrado[df_filtrado['Saldo_Decimal'] < 0].empty:
                    maior_divida = df_filtrado['Saldo_Decimal'].min()
                else:
                    maior_divida = 0.0
                
                col1.metric("Pessoas com Saldo Negativo", f"{total_devedores}", delta_color="inverse")
                col2.metric("Pessoas com Saldo Positivo", f"{total_credores}")
                col3.metric("Maior Débito (Horas)", f"{maior_divida:.2f}", delta_color="inverse")

                # --- ALERTA VISUAL ---
                st.subheader("⚠️ Alertas: Colaboradores com Saldo Negativo Crítico")
                limite_alerta = st.slider("Definir limite de alerta (horas negativas)", min_value=-50.0, max_value=0.0, value=-10.0, step=0.5)
                
                df_alerta = df_filtrado[df_filtrado['Saldo_Decimal'] <= limite_alerta][['Nome', 'Cargo', 'Total Banco', 'Saldo_Decimal']]
                
                if not df_alerta.empty:
                    st.error(f"Atenção! {len(df_alerta)} pessoas têm mais de {abs(limite_alerta)} horas de débito.")
                    st.dataframe(df_alerta.style.format({"Saldo_Decimal": "{:.2f}"}), use_container_width=True)
                else:
                    st.success("Nenhum colaborador ultrapassou o limite de alerta.")

                # --- GRÁFICO ---
                st.divider()
                st.subheader("📊 Visão Geral da Equipe")
                
                fig = px.bar(
                    df_filtrado.sort_values('Saldo_Decimal'), 
                    x='Saldo_Decimal', 
                    y='Nome', 
                    orientation='h',
                    color='Saldo_Decimal',
                    title="Saldo de Horas por Colaborador",
                    color_continuous_scale=['red', 'gray', 'green'],
                    height=max(600, len(df_filtrado) * 20) # Ajusta altura dinamicamente
                )
                fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="black")
                st.plotly_chart(fig, use_container_width=True)

                # --- TABELA GERAL ---
                with st.expander("Ver Tabela Completa"):
                    st.dataframe(
                        df_filtrado[['Nome', 'Cargo', 'Saldo Anterior', 'Saldo Período', 'Total Banco', 'Saldo_Decimal']]
                        .style.applymap(lambda x: 'color: red' if x < 0 else 'color: green', subset=['Saldo_Decimal'])
                        .format({"Saldo_Decimal": "{:.2f}"}),
                        use_container_width=True
                    )

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
        st.info("Dica: Verifique se o arquivo CSV tem o mesmo formato do modelo (cabeçalho nas primeiras 4 linhas).")

else:
    st.info("👆 Aguardando o upload do arquivo CSV para gerar o relatório.")
