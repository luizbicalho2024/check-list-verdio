import streamlit as st
import firebase_admin
from firebase_admin import firestore
from datetime import datetime

# --- Verificação de Login e Permissão ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()

user_info = st.session_state.get('user_info', {})
access_level = user_info.get('nivel_acesso')

if access_level not in ['suporte', 'gestor', 'admin']:
    st.error("Você não tem permissão para acessar esta página.")
    st.stop()

# --- Conexão com Firebase ---
db = firestore.client()

# --- Funções ---
@st.cache_data(ttl=600) # Cache de 10 minutos
def get_technicians():
    """Busca todos os usuários com nível de acesso 'tecnico'."""
    techs_ref = db.collection('usuarios').where('nivel_acesso', '==', 'tecnico').stream()
    techs = {doc.to_dict().get('nome'): doc.id for doc in techs_ref}
    return techs

def create_os(data):
    """Cria uma nova Ordem de Serviço no Firestore."""
    try:
        os_ref = db.collection('ordens_de_servico').document()
        os_ref.set(data)
        return True, os_ref.id
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
        cliente_nome = st.text_input("Nome do Cliente", key="cliente")
        veiculo_modelo = st.text_input("Modelo do Veículo", key="modelo")
        veiculo_tipo = st.selectbox("Tipo de Veículo", options=TIPOS_VEICULO, key="tipo_veiculo")
    with col2:
        cliente_endereco = st.text_input("Endereço do Serviço", key="endereco")
        veiculo_placa = st.text_input("Placa do Veículo", key="placa")

    st.header("Detalhes do Serviço")
    col3, col4 = st.columns(2)
    with col3:
        servico_tipo = st.selectbox("Tipo de Serviço", options=TIPOS_SERVICO, key="tipo_servico")
        rastreador_tipo = st.selectbox("Tipo de Rastreador", options=TIPOS_RASTREADOR, key="tipo_rastreador")
    with col4:
        tecnico_nome_selecionado = st.selectbox("Atribuir ao Técnico", options=list(technicians.keys()), key="tecnico")
    
    problema_reclamado = st.text_area("Problema Reclamado / Detalhes Adicionais", key="problema")

    submitted = st.form_submit_button("Criar Ordem de Serviço")

    if submitted:
        # Validação
        if not all([cliente_nome, cliente_endereco, veiculo_modelo, veiculo_placa, tecnico_nome_selecionado]):
            st.error("Por favor, preencha todos os campos obrigatórios.")
        else:
            with st.spinner("Criando OS..."):
                tecnico_id = technicians[tecnico_nome_selecionado]
                os_data = {
                    "cliente_nome": cliente_nome,
                    "cliente_endereco": cliente_endereco,
                    "veiculo_modelo": veiculo_modelo,
                    "veiculo_placa": veiculo_placa.upper(),
                    "veiculo_tipo": veiculo_tipo.lower(),
                    "servico_tipo": servico_tipo,
                    "rastreador_tipo": rastreador_tipo,
                    "problema_reclamado": problema_reclamado,
                    "tecnico_atribuido_id": tecnico_id,
                    "tecnico_nome": tecnico_nome_selecionado, # Facilita a exibição
                    "criado_por_suporte_id": st.session_state['user_uid'],
                    "data_criacao": firestore.SERVER_TIMESTAMP,
                    "status": "Pendente",
                    # Inicializa campos que serão preenchidos pelo técnico
                    "rastreador_id": "",
                    "checklist_respostas": {},
                    "observacoes": "",
                    "bloqueio_instalado": False,
                    "fotos_urls": {},
                    "assinaturas_urls": {},
                    "localizacao_gps": None,
                    "data_finalizacao": None
                }
                
                success, result = create_os(os_data)
                
                if success:
                    st.success(f"Ordem de Serviço criada com sucesso! ID: {result}")
                else:
                    st.error(f"Erro ao criar OS: {result}")

# --- Logout na Barra Lateral ---
with st.sidebar:
    st.subheader(f"Logado como:")
    st.write(f"**Nome:** {user_info.get('nome', 'N/A')}")
    st.write(f"**Nível:** {access_level.capitalize() if access_level else 'N/A'}")
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("1_Login.py")
