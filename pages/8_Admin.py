import streamlit as st
from supabase import create_client, Client
import json
import uuid

# --- Verificação de Login e Permissão ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("Você precisa estar logado para acessar esta página.")
    st.stop()

user_info = st.session_state.get('user_info', {})
access_level = user_info.get('nivel_acesso')

if access_level != 'admin':
    st.error("Acesso restrito a administradores.")
    st.stop()

# --- Conexão com Supabase ---
@st.cache_resource
def init_supabase_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_supabase_connection()

# --- Funções de Admin ---
def create_user(email, password, name, level):
    try:
        # 1. Cria o usuário no serviço de Autenticação
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
        })
        
        if res.user:
            user_id = res.user.id
            # 2. Insere os dados adicionais na tabela 'usuarios'
            user_profile_data = {
                "id": user_id,
                "nome": name,
                "email": email,
                "nivel_acesso": level
            }
            supabase.table('usuarios').insert(user_profile_data).execute()
            return True, "Usuário criado com sucesso!"
        else:
            return False, "Não foi possível criar o usuário na autenticação."
            
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=60)
def get_users():
    return supabase.table('usuarios').select("nome, email, nivel_acesso").execute().data

@st.cache_data(ttl=60)
def get_templates():
    return supabase.table('templates_checklist').select("*").execute().data

def save_template(vehicle_type, items_str):
    items_list = [item.strip() for item in items_str.split('\n') if item.strip()]
    if not items_list:
        return False, "A lista de itens não pode estar vazia."
    
    try:
        # Upsert: atualiza se existir, insere se não existir
        supabase.table('templates_checklist').upsert({
            "tipo_veiculo": vehicle_type.lower(),
            "itens": items_list
        }, on_conflict='tipo_veiculo').execute()
        st.cache_data.clear()
        return True, "Template salvo com sucesso!"
    except Exception as e:
        return False, str(e)

# --- Interface ---
st.set_page_config(layout="wide")
st.title("⚙️ Painel Administrativo")

tab1, tab2 = st.tabs(["Gerenciar Usuários", "Gerenciar Templates de Checklist"])

with tab1:
    st.header("Gerenciar Usuários")
    
    with st.expander("Criar Novo Usuário"):
        with st.form("new_user_form", clear_on_submit=True):
            st.subheader("Dados do Novo Usuário")
            new_name = st.text_input("Nome Completo")
            new_email = st.text_input("Email")
            new_password = st.text_input("Senha Temporária", type="password")
            new_level = st.selectbox("Nível de Acesso", ["tecnico", "suporte", "gestor", "admin"])
            
            submitted = st.form_submit_button("Criar Usuário")
            if submitted:
                if not all([new_name, new_email, new_password]):
                    st.warning("Preencha todos os campos.")
                else:
                    success, message = create_user(new_email, new_password, new_name, new_level)
                    if success:
                        st.success(message)
                        st.cache_data.clear() # Limpa o cache para atualizar a lista
                    else:
                        st.error(f"Erro: {message}")

    st.header("Usuários Atuais")
    users = get_users()
    st.dataframe(users, use_container_width=True)

with tab2:
    st.header("Gerenciar Templates de Checklist")
    
    templates = get_templates()
    
    if templates:
        selected_template_type = st.selectbox("Editar Template Existente", options=[t['tipo_veiculo'] for t in templates])
        template_to_edit = next((t for t in templates if t['tipo_veiculo'] == selected_template_type), None)
        
        if template_to_edit:
            items_text = "\n".join(template_to_edit.get('itens', []))
            items_to_edit = st.text_area("Itens (um por linha)", value=items_text, height=250, key=f"edit_{selected_template_type}")
            if st.button("Salvar Alterações", key=f"save_{selected_template_type}"):
                success, message = save_template(selected_template_type, items_to_edit)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.markdown("---")
    with st.expander("Criar Novo Template"):
        with st.form("new_template_form", clear_on_submit=True):
            new_vehicle_type = st.text_input("Nome do Tipo de Veículo (ex: van, trator)")
            new_items = st.text_area("Itens do Checklist (um por linha)", height=250)
            
            submitted = st.form_submit_button("Criar Template")
            if submitted:
                if not new_vehicle_type or not new_items:
                    st.warning("Preencha todos os campos.")
                else:
                    success, message = save_template(new_vehicle_type, new_items)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

