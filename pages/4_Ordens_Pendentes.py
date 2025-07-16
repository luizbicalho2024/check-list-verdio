import streamlit as st
from supabase import create_client, Client
import json

# --- Verificação de Login ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
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

# --- Funções ---
@st.cache_data(ttl=60)
def get_pending_os(technician_id):
    """Busca as OS pendentes para um técnico específico."""
    response = supabase.table('ordens_de_servico').select("*").eq('tecnico_atribuido_id', technician_id).eq('status', 'Pendente').order('created_at').execute()
    return response.data

def start_service(os_id):
    """Muda o status da OS para 'Em Andamento'."""
    try:
        supabase.table('ordens_de_servico').update({"status": "Em Andamento"}).eq('id', os_id).execute()
        st.session_state['selected_os_id'] = os_id
        st.cache_data.clear() # Limpa o cache para refletir a mudança
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
        with st.expander(f"**OS: {os['id'][:8]}...** | Cliente: {os['cliente_nome']} | Veículo: {os['veiculo_modelo']} ({os['veiculo_placa']})"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("Detalhes do Cliente")
                st.write(f"**Nome:** {os['cliente_nome']}")
                st.write(f"**Endereço:** {os['cliente_endereco']}")
            with col2:
                st.subheader("Detalhes do Veículo")
                st.write(f"**Modelo:** {os['veiculo_modelo']}")
                st.write(f"**Placa:** {os['veiculo_placa']}")
                st.write(f"**Tipo:** {os.get('veiculo_tipo', '').capitalize()}")
            with col3:
                st.subheader("Detalhes do Serviço")
                st.write(f"**Tipo:** {os['servico_tipo']}")
                
                # --- CORREÇÃO APLICADA AQUI ---
                # Lê os detalhes do rastreador da nova coluna JSON
                rastreador_info_str = "N/A"
                if os.get('rastreador_detalhes'):
                    try:
                        # Carrega o JSON
                        details = json.loads(os['rastreador_detalhes'])
                        # Pega a lista de tipos
                        tipos = details.get('tipos', [])
                        # Formata para exibição
                        rastreador_info_str = ", ".join(tipos)
                        # Adiciona a quantidade de câmeras, se houver
                        if 'Câmera' in tipos and details.get('camera_qtd', 0) > 0:
                            rastreador_info_str += f" ({details['camera_qtd']}x)"
                    except (json.JSONDecodeError, TypeError):
                        # Fallback para o caso de dados mal formatados
                        rastreador_info_str = str(os['rastreador_detalhes'])

                st.write(f"**Rastreador(es):** {rastreador_info_str}")
            
            st.markdown("**Problema Reclamado / Detalhes:**")
            st.warning(os.get('problema_reclamado', 'Nenhum detalhe fornecido.'))
            
            if st.button("Iniciar Serviço", key=f"start_{os['id']}"):
                if start_service(os['id']):
                    st.success(f"Iniciando serviço para a OS {os['id'][:8]}...")
                    st.switch_page("pages/5_Checklist.py")
