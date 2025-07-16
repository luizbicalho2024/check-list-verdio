import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from datetime import datetime
import io
import json
from PIL import Image

# --- Verificação de Login e OS Selecionada ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()
if 'selected_os_id' not in st.session_state:
    st.error("Nenhuma Ordem de Serviço selecionada. Volte para a lista de Ordens Pendentes.")
    if st.button("Voltar"):
        st.switch_page("pages/4_Ordens_Pendentes.py")
    st.stop()

# --- Conexão com Supabase ---
@st.cache_resource
def init_supabase_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_supabase_connection()
os_id = st.session_state.selected_os_id

# --- Funções ---
@st.cache_data(ttl=30)
def get_os_details(os_id):
    response = supabase.table('ordens_de_servico').select("*").eq('id', os_id).single().execute()
    return response.data

@st.cache_data(ttl=3600)
def get_checklist_template(vehicle_type):
    """
    Busca o template de checklist para um tipo de veículo.
    CORRIGIDO: Agora não causa erro se nenhum template for encontrado.
    """
    # Remove .single() para evitar um erro se nenhum template for encontrado.
    # A query agora retornará uma lista de resultados.
    response = supabase.table('templates_checklist').select('itens').eq('tipo_veiculo', vehicle_type).execute()
    
    # Verifica se a lista de resultados não está vazia.
    if response.data:
        # Pega o primeiro item da lista
        template_data = response.data[0]
        return template_data.get('itens', [])
    
    # Se nenhum template foi encontrado, retorna uma lista vazia.
    return []

def upload_file_to_supabase(bucket_name, file_bytes, destination_path):
    """Faz upload de um arquivo para o Supabase Storage."""
    try:
        supabase.storage.from_(bucket_name).upload(
            file=file_bytes, 
            path=destination_path, 
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        res = supabase.storage.from_(bucket_name).get_public_url(destination_path)
        return res
    except Exception as e:
        st.error(f"Erro no upload para o bucket '{bucket_name}': {e}")
        return None

# --- Carregar Dados ---
os_data = get_os_details(os_id)
if not os_data:
    st.error("Não foi possível carregar os dados da Ordem de Serviço.")
    st.stop()

checklist_items = get_checklist_template(os_data.get('veiculo_tipo'))

# --- Interface do Checklist ---
st.set_page_config(layout="wide")
st.title(f"📝 Executando Checklist - OS: {os_id[:8]}...")
st.info(f"**Cliente:** {os_data.get('cliente_nome')} | **Veículo:** {os_data.get('veiculo_modelo')} - {os_data.get('veiculo_placa')}")
st.markdown("---")

with st.form("checklist_form"):
    tab1, tab2, tab3 = st.tabs(["✅ Checklist do Veículo", "📸 Fotos e ID", "🖋️ Assinaturas e Finalização"])

    with tab1:
        st.header("Itens do Veículo")
        checklist_respostas = {}
        if not checklist_items:
            # Mensagem de aviso se nenhum template for encontrado
            st.warning(f"Nenhum template de checklist encontrado para o tipo de veículo '{os_data.get('veiculo_tipo')}'. Vá ao Painel de Admin para criar um.")
        else:
            st.write("Marque o estado de cada item.")
            for item in checklist_items:
                checklist_respostas[item] = st.radio(item, ["Intacto", "Defeito"], horizontal=True, key=f"check_{item}")

    with tab2:
        st.header("Registros Fotográficos e ID")
        col1, col2 = st.columns(2)
        with col1:
            rastreador_id = st.text_input("ID do Rastreador Principal Instalado", value=os_data.get('rastreador_id', ''))
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
            assinatura_tecnico = st_canvas(height=150, width=400, drawing_mode="freedraw", key="canvas_tecnico")
        with col_sig2:
            st.write("Assinatura do Cliente")
            assinatura_cliente = st_canvas(height=150, width=400, drawing_mode="freedraw", key="canvas_cliente")

    submitted = st.form_submit_button("Salvar e Finalizar Serviço", type="primary")

# --- Lógica de Submissão ---
if submitted:
    with st.spinner("Salvando dados e fazendo upload..."):
        fotos_urls = {}
        assinaturas_urls = {}
        
        if foto_placa:
            url = upload_file_to_supabase("fotos_os", foto_placa.getvalue(), f"{os_id}/placa.png")
            if url: fotos_urls["placa"] = url
        if foto_local_instalacao:
            url = upload_file_to_supabase("fotos_os", foto_local_instalacao.getvalue(), f"{os_id}/local_instalacao.png")
            if url: fotos_urls["local"] = url
        if foto_rastreador:
            url = upload_file_to_supabase("fotos_os", foto_rastreador.getvalue(), f"{os_id}/rastreador.png")
            if url: fotos_urls["rastreador"] = url
        if foto_extra:
            url = upload_file_to_supabase("fotos_os", foto_extra.getvalue(), f"{os_id}/extra.png")
            if url: fotos_urls["extra"] = url

        def process_signature(canvas_data, bucket, path):
            if canvas_data.image_data is not None:
                img = Image.fromarray(canvas_data.image_data.astype('uint8'), 'RGBA')
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return upload_file_to_supabase(bucket, buffer.getvalue(), path)
            return None

        url_sig_tecnico = process_signature(assinatura_tecnico, "assinaturas", f"{os_id}/tecnico.png")
        if url_sig_tecnico: assinaturas_urls["tecnico"] = url_sig_tecnico
        
        url_sig_cliente = process_signature(assinatura_cliente, "assinaturas", f"{os_id}/cliente.png")
        if url_sig_cliente: assinaturas_urls["cliente"] = url_sig_cliente

        update_data = {
            "checklist_respostas": json.dumps(checklist_respostas),
            "rastreador_id": rastreador_id,
            "observacoes": observacoes,
            "bloqueio_instalado": bloqueio_instalado,
            "status": "Aguardando Suporte",
            "data_finalizacao": datetime.now().isoformat(),
            "fotos_urls": json.dumps(fotos_urls),
            "assinaturas_urls": json.dumps(assinaturas_urls)
        }
        
        try:
            supabase.table('ordens_de_servico').update(update_data).eq('id', os_id).execute()
            st.success("Serviço finalizado e dados salvos com sucesso!")
            st.balloons()
            del st.session_state['selected_os_id']
            st.cache_data.clear()
            import time
            time.sleep(3)
            st.switch_page("pages/2_Dashboard.py")
        except Exception as e:
            st.error(f"Erro ao salvar no banco de dados: {e}")
