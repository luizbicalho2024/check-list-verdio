import streamlit as st
from supabase import create_client, Client

# --- Verificação de Login ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.switch_page("1_Login.py")
    st.stop()

# --- Conexão com Supabase ---
@st.cache_resource
def init_supabase_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_supabase_connection()
user_info = st.session_state.get('user_info', {})
user_id = st.session_state.get('user_id')

# --- Funções de Busca ---
@st.cache_data(ttl=300)
def get_stats(user_id, access_level):
    stats = {
        "pendentes": 0,
        "aguardando_suporte": 0,
    }
    # Contagem de OS Pendentes para o técnico logado
    if access_level == 'tecnico':
        response = supabase.table('ordens_de_servico').select('id', count='exact').eq('tecnico_atribuido_id', user_id).eq('status', 'Pendente').execute()
        stats["pendentes"] = response.count

    # Contagem de OS Aguardando Suporte (para Suporte, Gestor, Admin)
    if access_level in ['suporte', 'gestor', 'admin']:
        response = supabase.table('ordens_de_servico').select('id', count='exact').eq('status', 'Aguardando Suporte').execute()
        stats["aguardando_suporte"] = response.count
    
    return stats

# --- Interface do Dashboard ---
st.set_page_config(layout="wide")
st.title(f"Dashboard - Bem-vindo(a), {user_info.get('nome', 'Usuário')}!")
st.markdown("---")

access_level = user_info.get('nivel_acesso')
stats = get_stats(user_id, access_level)

# --- Visualização para Técnico ---
if access_level == 'tecnico':
    st.header("Suas Tarefas")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Ordens de Serviço Pendentes", value=stats['pendentes'])
        if st.button("Ver Ordens Pendentes"):
            st.switch_page("pages/4_Ordens_Pendentes.py")

# --- Visualização para Suporte ---
if access_level == 'suporte':
    st.header("Fluxo de Trabalho do Suporte")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="OS Aguardando Finalização", value=stats['aguardando_suporte'])
        if st.button("Ver Fila de Finalização"):
            st.switch_page("pages/6_Aguardando_Suporte.py")
    with col2:
        st.metric(label="Criar Nova Ordem de Serviço", value="📝")
        if st.button("Criar Nova OS"):
            st.switch_page("pages/3_Nova_OS.py")

# --- Visualização para Gestor e Admin ---
if access_level in ['gestor', 'admin']:
    st.header("Visão Geral da Operação")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="OS Aguardando Finalização", value=stats['aguardando_suporte'])
        if st.button("Ver Fila de Finalização"):
            st.switch_page("pages/6_Aguardando_Suporte.py")
    with col2:
        st.metric(label="Relatórios e Análises", value="📊")
        if st.button("Acessar Relatórios"):
            st.switch_page("pages/7_Relatorios.py")
    with col3:
        st.metric(label="Criar Nova Ordem de Serviço", value="📝")
        if st.button("Criar Nova OS"):
            st.switch_page("pages/3_Nova_OS.py")

# --- Painel de Admin ---
if access_level == 'admin':
    st.markdown("---")
    st.header("Painel Administrativo")
    if st.button("Gerenciar Usuários e Templates"):
        st.switch_page("pages/8_Admin.py")

# --- Logout na Barra Lateral ---
with st.sidebar:
    st.subheader(f"Logado como:")
    st.write(f"**Nome:** {user_info.get('nome', 'N/A')}")
    st.write(f"**Nível:** {access_level.capitalize() if access_level else 'N/A'}")
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("1_Login.py")
