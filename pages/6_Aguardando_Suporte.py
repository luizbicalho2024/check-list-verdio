import streamlit as st
from supabase import create_client, Client
import json
from docxtpl import DocxTemplate
from io import BytesIO
import requests

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
@st.cache_data(ttl=60)
def get_awaiting_support_os():
    """Busca as OS que aguardam finalização do suporte."""
    response = supabase.table('ordens_de_servico').select("*").eq('status', 'Aguardando Suporte').order('data_finalizacao').execute()
    return response.data

def finalize_os(os_id):
    """Muda o status da OS para 'Finalizada'."""
    try:
        supabase.table('ordens_de_servico').update({"status": "Finalizada"}).eq('id', os_id).execute()
        st.cache_data.clear() # Limpa o cache para atualizar a lista
        return True
    except Exception as e:
        st.error(f"Erro ao finalizar OS: {e}")
        return False

def generate_docx(os_data):
    """Gera um arquivo DOCX a partir de um template e dos dados da OS."""
    try:
        doc = DocxTemplate("template.docx")
        
        # Carrega imagens da URL para o template
        context = os_data.copy()
        
        # Prepara o contexto para o template
        # Checklist
        if isinstance(os_data.get('checklist_respostas'), str):
            checklist = json.loads(os_data['checklist_respostas'])
            for item, status in checklist.items():
                # Transforma 'Luzes de Freio' em 'Luzes_de_Freio'
                tag = item.replace(' ', '_').replace('-', '_')
                context[tag] = status
        
        # Imagens
        def get_image_from_url(url):
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                return BytesIO(response.content)
            except requests.exceptions.RequestException:
                return None

        if isinstance(os_data.get('fotos_urls'), str):
            fotos = json.loads(os_data['fotos_urls'])
            for key, url in fotos.items():
                context[f'foto_{key}'] = get_image_from_url(url)

        if isinstance(os_data.get('assinaturas_urls'), str):
            assinaturas = json.loads(os_data['assinaturas_urls'])
            for key, url in assinaturas.items():
                context[f'assinatura_{key}'] = get_image_from_url(url)
        
        # Renderiza o documento
        doc.render(context)
        
        # Salva o documento em memória
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream
    except Exception as e:
        st.error(f"Erro ao gerar DOCX: {e}")
        return None

# --- Interface ---
st.set_page_config(layout="wide")
st.title(" Fila de Finalização de Serviços")
st.markdown("Revise os serviços concluídos pelos técnicos e finalize o cadastro no sistema.")

os_list = get_awaiting_support_os()

if not os_list:
    st.info("Não há nenhum serviço aguardando finalização no momento.")
else:
    st.write(f"Há **{len(os_list)}** serviço(s) na fila.")
    st.markdown("---")

    for os in os_list:
        with st.expander(f"**OS: {os['id'][:8]}...** | Técnico: {os.get('tecnico_nome', 'N/A')} | Veículo: {os['veiculo_placa']}"):
            st.subheader(f"Detalhes do Serviço - {os['cliente_nome']}")
            
            # Decodifica JSON se necessário
            checklist_respostas = json.loads(os.get('checklist_respostas', '{}'))
            fotos_urls = json.loads(os.get('fotos_urls', '{}'))
            assinaturas_urls = json.loads(os.get('assinaturas_urls', '{}'))
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Técnico:** {os.get('tecnico_nome')}")
                st.write(f"**Veículo:** {os.get('veiculo_modelo')} - {os.get('veiculo_placa')}")
                st.write(f"**ID do Rastreador:** {os.get('rastreador_id')}")
                st.write(f"**Bloqueio Instalado:** {'Sim' if os.get('bloqueio_instalado') else 'Não'}")
                st.markdown("**Observações do Técnico:**")
                st.info(os.get('observacoes') or "Nenhuma observação.")

            with col2:
                st.markdown("**Checklist:**")
                for item, status in checklist_respostas.items():
                    st.write(f"- {item}: **{status}**")

            st.markdown("---")
            st.subheader("Registros Visuais")
            
            img_col1, img_col2, img_col3, img_col4 = st.columns(4)
            with img_col1:
                st.image(fotos_urls.get('placa', 'https://placehold.co/200x150?text=Placa'), caption="Placa")
            with img_col2:
                st.image(fotos_urls.get('local', 'https://placehold.co/200x150?text=Local'), caption="Local de Instalação")
            with img_col3:
                st.image(fotos_urls.get('rastreador', 'https://placehold.co/200x150?text=Rastreador'), caption="Rastreador")
            with img_col4:
                st.image(fotos_urls.get('extra', 'https://placehold.co/200x150?text=Extra'), caption="Extra")

            st.subheader("Assinaturas")
            sig_col1, sig_col2 = st.columns(2)
            with sig_col1:
                st.image(assinaturas_urls.get('tecnico', 'https://placehold.co/300x100?text=Ass.+Técnico'), caption="Assinatura do Técnico")
            with sig_col2:
                st.image(assinaturas_urls.get('cliente', 'https://placehold.co/300x100?text=Ass.+Cliente'), caption="Assinatura do Cliente")

            st.markdown("---")
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✅ Cadastro Realizado", key=f"finalize_{os['id']}", type="primary"):
                    if finalize_os(os['id']):
                        st.success(f"OS {os['id'][:8]}... finalizada com sucesso!")
                        st.rerun()

            with btn_col2:
                docx_file = generate_docx(os)
                if docx_file:
                    st.download_button(
                        label="📄 Gerar Relatório (.docx)",
                        data=docx_file,
                        file_name=f"OS_{os['veiculo_placa']}_{os['id'][:8]}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"docx_{os['id']}"
                    )
