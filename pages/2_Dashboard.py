import streamlit as st
import firebase_admin
from firebase_admin import firestore

# --- Verificação de Login ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()

# --- Conexão com Firebase ---
db = firestore.client()
user_info = st.session_state.get('user_info', {})
user_id = st.session_state.get('user_uid')

# --- Funções de Busca ---
@st.cache_data(ttl=300) # Cache de 5 minutos
def get_stats(user_id, access_level):
    stats = {
        "pendentes": 0,
        "aguardando_suporte": 0,
        "finalizadas_mes": 0
    }
    # Contagem de OS Pendentes para o técnico logado
    if access_level == 'tecnico':
        pendentes_query = db.collection('ordens_de_servico').where('tecnico_atribuido_id', '==', user_id).where('status', '==', 'Pendente').stream()
        stats["pendentes"] = len(list(pendentes_query))

    # Contagem de OS Aguardando Suporte (para Suporte, Gestor, Admin)
    if access_level in ['suporte', 'gestor', 'admin']:
        aguardando_query = db.collection('ordens_de_servico').where('status', '==', 'Aguardando Suporte').stream()
        stats["aguardando_suporte"] = len(list(aguardando_query))

    # Adicionar contagem de finalizadas no mês se necessário
    # ... (lógica de data aqui) ...
    
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
    
    # Adicionar mais métricas relevantes para o técnico aqui

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
