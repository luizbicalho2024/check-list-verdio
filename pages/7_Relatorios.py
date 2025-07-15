import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# --- Verificação de Login e Permissão ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()

user_info = st.session_state.get('user_info', {})
access_level = user_info.get('nivel_acesso')

if access_level not in ['gestor', 'admin']:
    st.error("Você não tem permissão para acessar esta página.")
    st.stop()

# --- Conexão com Supabase ---
@st.cache_resource
def init_supabase_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_supabase_connection()

# --- Funções ---
@st.cache_data(ttl=300)
def fetch_finalized_os(start_date, end_date):
    """Busca OS finalizadas dentro de um período."""
    response = supabase.table('ordens_de_servico').select("*").eq('status', 'Finalizada').gte('data_finalizacao', start_date.isoformat()).lte('data_finalizacao', end_date.isoformat()).execute()
    return response.data

def to_excel(df):
    """Converte um DataFrame para um arquivo Excel em memória."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio_OS')
    processed_data = output.getvalue()
    return processed_data

# --- Interface ---
st.set_page_config(layout="wide")
st.title("📊 Relatórios e Análises")

# --- Filtros ---
st.header("Filtros")
today = datetime.now()
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data de Início", today - timedelta(days=30))
with col2:
    end_date = st.date_input("Data de Fim", today)

if start_date > end_date:
    st.error("A data de início não pode ser posterior à data de fim.")
    st.stop()

# --- Carregar e Processar Dados ---
data = fetch_finalized_os(start_date, end_date)

if not data:
    st.warning("Nenhum dado encontrado para o período selecionado.")
else:
    df = pd.DataFrame(data)
    
    # --- Limpeza e Preparação dos Dados ---
    # Converte colunas de data
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%d/%m/%Y %H:%M')
    df['data_finalizacao'] = pd.to_datetime(df['data_finalizacao']).dt.strftime('%d/%m/%Y %H:%M')
    
    # Remove colunas desnecessárias para o relatório principal
    df_display = df.drop(columns=['checklist_respostas', 'fotos_urls', 'assinaturas_urls'], errors='ignore')

    st.markdown("---")
    st.header("Visão Geral")
    
    # --- Métricas ---
    total_servicos = len(df)
    servicos_por_tecnico = df['tecnico_nome'].value_counts()
    servicos_por_tipo = df['servico_tipo'].value_counts()
    
    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric("Total de Serviços Realizados", total_servicos)
    
    st.subheader("Serviços por Técnico")
    st.bar_chart(servicos_por_tecnico)
    
    st.subheader("Serviços por Tipo")
    st.bar_chart(servicos_por_tipo)
    
    st.markdown("---")
    st.header("Dados Detalhados")
    st.dataframe(df_display)
    
    # --- Exportação ---
    excel_data = to_excel(df_display)
    st.download_button(
        label="📥 Exportar para Excel (.xlsx)",
        data=excel_data,
        file_name=f"relatorio_os_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
