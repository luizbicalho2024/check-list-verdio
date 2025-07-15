import streamlit as st
from supabase import create_client, Client
import uuid

# --- Verificação de Login e Permissão ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()

user_info = st.session_state.get('user_info', {})
access_level = user_info.get('nivel_acesso')

if access_level not in ['suporte', 'gestor', 'admin']:
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
@st.cache_data(ttl=600)
def get_technicians():
    """Busca todos os usuários com nível de acesso 'tecnico'."""
    response = supabase.table('usuarios').select('id, nome').eq('nivel_acesso', 'tecnico').execute()
    techs = {item['nome']: item['id'] for item in response.data}
    return techs

def create_os(data):
    """Cria uma nova Ordem de Serviço no Supabase."""
    try:
        response = supabase.table('ordens_de_servico').insert(data).execute()
        return True, response.data[0]['id']
    except Exception as e:
        return False, str(e)

# --- Listas de Opções ---
TIPOS_VEICULO = ["Carro", "Moto", "Caminhão", "Máquina"]
TIPOS_RASTREADOR = ["GPRS", "Satélite", "RFID", "Teclado", "DMS", "ADAS", "TDI", "Câmera"]
TIPOS_SERVICO = ["Instalação", "Manutenção", "Desinstalação"]

# --- Interface ---
st.set_page_config(layout="wide")
st.title("📋 Criar Nova Ordem de Serviço")
st.markdown("Preencha os dados abaixo para registrar uma nova OS.")

technicians = get_technicians()
if not technicians:
    st.warning("Nenhum técnico encontrado no sistema. Cadastre técnicos no painel de admin.")
    st.stop()

with st.form("nova_os_form", clear_on_submit=True):
    st.header("Dados do Cliente e Veículo")
    col1, col2 = st.columns(2)
    with col1:
        cliente_nome = st.text_input("Nome do Cliente")
        veiculo_modelo = st.text_input("Modelo do Veículo")
        veiculo_tipo = st.selectbox("Tipo de Veículo", options=TIPOS_VEICULO)
    with col2:
        cliente_endereco = st.text_input("Endereço do Serviço")
        veiculo_placa = st.text_input("Placa do Veículo")

    st.header("Detalhes do Serviço")
    col3, col4 = st.columns(2)
    with col3:
        servico_tipo = st.selectbox("Tipo de Serviço", options=TIPOS_SERVICO)
        rastreador_tipo = st.selectbox("Tipo de Rastreador", options=TIPOS_RASTREADOR)
    with col4:
        tecnico_nome_selecionado = st.selectbox("Atribuir ao Técnico", options=list(technicians.keys()))
    
    problema_reclamado = st.text_area("Problema Reclamado / Detalhes Adicionais")

    submitted = st.form_submit_button("Criar Ordem de Serviço")

    if submitted:
        if not all([cliente_nome, cliente_endereco, veiculo_modelo, veiculo_placa, tecnico_nome_selecionado]):
            st.error("Por favor, preencha todos os campos obrigatórios.")
        else:
            with st.spinner("Criando OS..."):
                tecnico_id = technicians[tecnico_nome_selecionado]
                os_data = {
                    "id": str(uuid.uuid4()),
                    "cliente_nome": cliente_nome,
                    "cliente_endereco": cliente_endereco,
                    "veiculo_modelo": veiculo_modelo,
                    "veiculo_placa": veiculo_placa.upper(),
                    "veiculo_tipo": veiculo_tipo.lower(),
                    "servico_tipo": servico_tipo,
                    "rastreador_tipo": rastreador_tipo,
                    "problema_reclamado": problema_reclamado,
                    "tecnico_atribuido_id": tecnico_id,
                    "tecnico_nome": tecnico_nome_selecionado,
                    "criado_por_suporte_id": st.session_state['user_id'],
                    "status": "Pendente",
                }
                
                success, result = create_os(os_data)
                
                if success:
                    st.success(f"Ordem de Serviço criada com sucesso! ID: {result}")
                else:
                    st.error(f"Erro ao criar OS: {result}")

# --- Logout na Barra Lateral ---
# (código de logout omitido para brevidade)
