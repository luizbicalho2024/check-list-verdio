import streamlit as st
import firebase_admin
from firebase_admin import firestore, storage
from streamlit_drawable_canvas import st_canvas
import pandas as pd
from datetime import datetime
import io

# --- Verificação de Login e OS Selecionada ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()
if 'selected_os_id' not in st.session_state:
    st.error("Nenhuma Ordem de Serviço selecionada. Volte para a lista de Ordens Pendentes.")
    if st.button("Voltar"):
        st.switch_page("pages/4_Ordens_Pendentes.py")
    st.stop()

# --- Conexão com Firebase ---
db = firestore.client()
bucket = storage.bucket()
os_id = st.session_state.selected_os_id

# --- Funções ---
@st.cache_data(ttl=30)
def get_os_details(os_id):
    doc_ref = db.collection('ordens_de_servico').document(os_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

@st.cache_data(ttl=3600)
def get_checklist_template(vehicle_type):
    doc_ref = db.collection('templates_checklist').document(vehicle_type)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('itens', [])
    return []

def upload_file(file_bytes, destination_blob_name):
    """Faz upload de um arquivo para o Firebase Storage."""
    try:
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(file_bytes, content_type='image/png')
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"Erro no upload: {e}")
        return None

# --- Carregar Dados ---
os_data = get_os_details(os_id)
if not os_data:
    st.error("Não foi possível carregar os dados da Ordem de Serviço.")
    st.stop()

checklist_items = get_checklist_template(os_data.get('veiculo_tipo'))

# --- Interface do Checklist ---
st.set_page_config(layout="wide")
st.title(f"📝 Executando Checklist - OS: {os_id}")
st.info(f"**Cliente:** {os_data.get('cliente_nome')} | **Veículo:** {os_data.get('veiculo_modelo')} - {os_data.get('veiculo_placa')}")
st.markdown("---")

with st.form("checklist_form"):
    # --- Seções do Formulário ---
    tab1, tab2, tab3 = st.tabs(["✅ Checklist do Veículo", "📸 Fotos e ID", "🖋️ Assinaturas e Finalização"])

    with tab1:
        st.header("Itens do Veículo")
        st.write("Marque o estado de cada item.")
        checklist_respostas = {}
        if not checklist_items:
            st.warning("Nenhum template de checklist encontrado para este tipo de veículo.")
        else:
            for item in checklist_items:
                checklist_respostas[item] = st.radio(item, ["Intacto", "Defeito"], horizontal=True, key=f"check_{item}")

    with tab2:
        st.header("Registros Fotográficos e ID")
        col1, col2 = st.columns(2)
        with col1:
            rastreador_id = st.text_input("ID do Rastreador Instalado", value=os_data.get('rastreador_id', ''))
            foto_placa = st.camera_input("Foto da Placa do Veículo")
            foto_local_instalacao = st.camera_input("Foto do Local de Instalação")
        with col2:
            foto_rastreador = st.camera_input("Foto do Rastreador (Número de Série)")
            foto_extra = st.camera_input("Foto Extra (Opcional)")

    with tab3:
        st.header("Finalização do Serviço")
        observacoes = st.text_area("Observações Gerais", height=150)
        bloqueio_instalado = st.toggle("Bloqueio foi instalado/ativado?", value=False)
        
        st.subheader("Assinaturas")
        col_sig1, col_sig2 = st.columns(2)
        with col_sig1:
            st.write("Assinatura do Instalador")
            assinatura_tecnico = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=150,
                width=400,
                drawing_mode="freedraw",
                key="canvas_tecnico",
            )
        with col_sig2:
            st.write("Assinatura do Cliente")
            assinatura_cliente = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=150,
                width=400,
                drawing_mode="freedraw",
                key="canvas_cliente",
            )

    submitted = st.form_submit_button("Salvar e Finalizar Serviço", type="primary")

# --- Lógica de Submissão ---
if submitted:
    with st.spinner("Salvando dados e fazendo upload dos arquivos... Por favor, aguarde."):
        update_data = {
            "checklist_respostas": checklist_respostas,
            "rastreador_id": rastreador_id,
            "observacoes": observacoes,
            "bloqueio_instalado": bloqueio_instalado,
            "status": "Aguardando Suporte",
            "data_finalizacao": firestore.SERVER_TIMESTAMP,
            "fotos_urls": {},
            "assinaturas_urls": {}
        }
        
        # Upload de fotos
        if foto_placa:
            url = upload_file(foto_placa.getvalue(), f"fotos_os/{os_id}/placa.png")
            if url: update_data["fotos_urls"]["placa"] = url
        if foto_local_instalacao:
            url = upload_file(foto_local_instalacao.getvalue(), f"fotos_os/{os_id}/local_instalacao.png")
            if url: update_data["fotos_urls"]["local"] = url
        if foto_rastreador:
            url = upload_file(foto_rastreador.getvalue(), f"fotos_os/{os_id}/rastreador.png")
            if url: update_data["fotos_urls"]["rastreador"] = url
        if foto_extra:
            url = upload_file(foto_extra.getvalue(), f"fotos_os/{os_id}/extra.png")
            if url: update_data["fotos_urls"]["extra"] = url

        # Upload de assinaturas
        if assinatura_tecnico.image_data is not None:
            img_bytes = io.BytesIO()
            pd.DataFrame(assinatura_tecnico.image_data).to_feather(img_bytes) # Workaround to get bytes
            url = upload_file(assinatura_tecnico.image_data.tobytes(), f"assinaturas/{os_id}/tecnico.png")
            if url: update_data["assinaturas_urls"]["tecnico"] = url
        
        if assinatura_cliente.image_data is not None:
            url = upload_file(assinatura_cliente.image_data.tobytes(), f"assinaturas/{os_id}/cliente.png")
            if url: update_data["assinaturas_urls"]["cliente"] = url

        # Atualiza o documento no Firestore
        try:
            db.collection('ordens_de_servico').document(os_id).update(update_data)
            st.success("Serviço finalizado e dados salvos com sucesso!")
            st.balloons()
            # Limpa o ID da OS da sessão
            del st.session_state['selected_os_id']
            st.info("Você será redirecionado para o Dashboard em 3 segundos.")
            import time
            time.sleep(3)
            st.switch_page("pages/2_Dashboard.py")
        except Exception as e:
            st.error(f"Ocorreu um erro ao salvar os dados no banco de dados: {e}")

# --- Logout na Barra Lateral ---
with st.sidebar:
    # ... (código de logout) ...
    pass
