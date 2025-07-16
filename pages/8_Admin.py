import streamlit as st
from supabase import create_client, Client
import pandas as pd

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

# Conexão padrão para leitura (usa a chave anônima pública)
@st.cache_resource
def init_supabase_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# CONEXÃO DE ADMIN (usa a chave de serviço secreta)
def get_admin_supabase_client():
    """Cria um cliente Supabase com permissões de administrador."""
    try:
        url = st.secrets["supabase"]["url"]
        service_key = st.secrets["supabase"]["service_key"]
        return create_client(url, service_key)
    except Exception as e:
        st.error("A chave de serviço (service_key) não foi encontrada nos segredos. Operações de administrador estão desativadas.")
        st.error(e)
        return None

# Cliente para operações de leitura geral
supabase_anon: Client = init_supabase_connection()
# Cliente para operações de escrita/modificação de administrador
supabase_admin: Client = get_admin_supabase_client()

# --- Funções de Admin ---

def create_user(email, password, name, level):
    if not supabase_admin: return False, "Cliente de admin não inicializado."
    try:
        # Usa o cliente admin para criar o usuário na autenticação
        res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        
        if res.user:
            user_id = res.user.id
            user_profile_data = {
                "id": user_id,
                "nome": name,
                "email": email,
                "nivel_acesso": level,
                "is_active": True
            }
            # Usa o cliente admin para inserir o perfil no banco de dados
            supabase_admin.table('usuarios').insert(user_profile_data).execute()
            st.cache_data.clear()
            return True, "Usuário criado com sucesso!"
        else:
            return False, "Não foi possível criar o usuário na autenticação."
            
    except Exception as e:
        return False, str(e)

def update_user(user_id, new_name, new_level, new_email, new_password):
    if not supabase_admin: return False, "Cliente de admin não inicializado."
    try:
        auth_updates = {}
        if new_email: auth_updates['email'] = new_email
        if new_password: auth_updates['password'] = new_password
        
        if auth_updates:
            # Usa o cliente admin para atualizar e-mail/senha
            supabase_admin.auth.admin.update_user_by_id(user_id, auth_updates)

        profile_updates = {"nome": new_name, "nivel_acesso": new_level}
        if new_email: profile_updates['email'] = new_email

        # Usa o cliente admin para atualizar o perfil
        supabase_admin.table('usuarios').update(profile_updates).eq('id', user_id).execute()
        
        st.cache_data.clear()
        return True, "Usuário atualizado com sucesso!"
    except Exception as e:
        return False, str(e)

def toggle_user_status(user_id, current_status):
    if not supabase_admin: return False, "Cliente de admin não inicializado."
    try:
        new_status = not current_status
        # Usa o cliente admin para ativar/desativar
        supabase_admin.table('usuarios').update({"is_active": new_status}).eq('id', user_id).execute()
        st.cache_data.clear()
        return True, f"Usuário {'ativado' if new_status else 'desativado'} com sucesso!"
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=60)
def get_all_users():
    # Para ler dados, o cliente anônimo é suficiente
    response = supabase_anon.table('usuarios').select("id, nome, email, nivel_acesso, is_active").execute()
    return response.data

# --- Interface ---
st.set_page_config(layout="wide")
st.title("⚙️ Painel Administrativo")

# Verifica se o cliente admin foi inicializado corretamente
if not supabase_admin:
    st.stop()

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
                        st.rerun()
                    else:
                        st.error(f"Erro: {message}")

    st.header("Usuários Atuais")
    users = get_all_users()
    
    if not users:
        st.info("Nenhum usuário cadastrado.")
    else:
        user_emails = [user['email'] for user in users]
        selected_email = st.selectbox("Selecione um usuário para gerenciar", options=user_emails, index=None, placeholder="Escolha um usuário...")
        
        if selected_email:
            selected_user = next((user for user in users if user['email'] == selected_email), None)
            
            if selected_user:
                st.markdown(f"### Gerenciando: {selected_user['nome']}")
                
                with st.form(f"edit_form_{selected_user['id']}", border=True):
                    st.write("**Editar Informações**")
                    edit_name = st.text_input("Nome", value=selected_user['nome'])
                    edit_email = st.text_input("Email", value=selected_user['email'])
                    edit_level = st.selectbox(
                        "Nível de Acesso", 
                        options=["tecnico", "suporte", "gestor", "admin"],
                        index=["tecnico", "suporte", "gestor", "admin"].index(selected_user['nivel_acesso'])
                    )
                    edit_password = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password")
                    
                    if st.form_submit_button("Salvar Alterações"):
                        success, message = update_user(
                            selected_user['id'], 
                            edit_name, 
                            edit_level,
                            edit_email,
                            edit_password
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

                status_btn_text = "Reativar Usuário" if not selected_user['is_active'] else "Desativar Usuário"
                status_btn_type = "primary" if not selected_user['is_active'] else "secondary"
                
                if st.button(status_btn_text, key=f"toggle_{selected_user['id']}", type=status_btn_type):
                    success, message = toggle_user_status(selected_user['id'], selected_user['is_active'])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

with tab2:
    st.header("Gerenciar Templates de Checklist")
    # ... (código anterior omitido para brevidade) ...
