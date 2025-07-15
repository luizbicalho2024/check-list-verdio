import streamlit as st
import firebase_admin
from firebase_admin import firestore
from datetime import datetime

# --- Verificação de Login ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()

# --- Conexão com Firebase ---
db = firestore.client()
user_info = st.session_state.get('user_info', {})
user_id = st.session_state.get('user_uid')

# --- Funções ---
@st.cache_data(ttl=60) # Cache de 1 minuto para dados voláteis
def get_pending_os(technician_id):
    """Busca as OS pendentes para um técnico específico."""
    os_ref = db.collection('ordens_de_servico').where('tecnico_atribuido_id', '==', technician_id).where('status', '==', 'Pendente').order_by('data_criacao').stream()
    os_list = [doc.to_dict() | {"id": doc.id} for doc in os_ref]
    return os_list

def start_service(os_id):
    """Muda o status da OS para 'Em Andamento'."""
    try:
        os_ref = db.collection('ordens_de_servico').document(os_id)
        os_ref.update({"status": "Em Andamento"})
        st.session_state['selected_os_id'] = os_id
        return True
    except Exception as e:
        st.error(f"Erro ao iniciar serviço: {e}")
        return False

# --- Interface ---
st.set_page_config(layout="wide")
st.title("✅ Minhas Ordens de Serviço Pendentes")

pending_os_list = get_pending_os(user_id)

if not pending_os_list:
    st.info("Você não tem nenhuma Ordem de Serviço pendente no momento. Bom trabalho! 👍")
else:
    st.write(f"Você tem **{len(pending_os_list)}** serviço(s) para realizar.")
    st.markdown("---")

    for os in pending_os_list:
        with st.expander(f"**OS: {os['id']}** | Cliente: {os['cliente_nome']} | Veículo: {os['veiculo_modelo']} ({os['veiculo_placa']})"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("Detalhes do Cliente")
                st.write(f"**Nome:** {os['cliente_nome']}")
                st.write(f"**Endereço:** {os['cliente_endereco']}")
            with col2:
                st.subheader("Detalhes do Veículo")
                st.write(f"**Modelo:** {os['veiculo_modelo']}")
                st.write(f"**Placa:** {os['veiculo_placa']}")
                st.write(f"**Tipo:** {os['veiculo_tipo'].capitalize()}")
            with col3:
                st.subheader("Detalhes do Serviço")
                st.write(f"**Tipo:** {os['servico_tipo']}")
                st.write(f"**Rastreador:** {os['rastreador_tipo']}")
            
            st.markdown("**Problema Reclamado / Detalhes:**")
            st.warning(os.get('problema_reclamado', 'Nenhum detalhe fornecido.'))
            
            if st.button("Iniciar Serviço", key=f"start_{os['id']}"):
                if start_service(os['id']):
                    st.success(f"Iniciando serviço para a OS {os['id']}...")
                    st.switch_page("pages/5_Checklist.py")

# --- Logout na Barra Lateral ---
with st.sidebar:
    st.subheader(f"Logado como:")
    st.write(f"**Nome:** {user_info.get('nome', 'N/A')}")
    st.write(f"**Nível:** {user_info.get('nivel_acesso', 'N/A').capitalize()}")
    if st.button("Logout", key="sidebar_logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("1_Login.py")
