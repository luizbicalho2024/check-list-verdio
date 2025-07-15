import streamlit as st
from supabase import create_client, Client
import time

# --- Configuração da Página ---
st.set_page_config(
    page_title="Check-List Veicular",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Funções de Autenticação e Supabase ---

# Inicializa a conexão com o Supabase
@st.cache_resource
def init_supabase_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro ao conectar com o Supabase. Verifique suas credenciais em secrets.toml.")
        st.error(e)
        st.stop()

supabase: Client = init_supabase_connection()

def login_user(email, password):
    """Autentica o usuário com email e senha usando Supabase Auth."""
    try:
        # Tenta fazer o login
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        if session.user:
            # Busca informações adicionais do usuário na tabela 'usuarios'
            user_id = session.user.id
            user_data = supabase.table('usuarios').select("*").eq('id', user_id).single().execute()

            if user_data.data:
                st.session_state['user_id'] = user_id
                st.session_state['user_email'] = session.user.email
                st.session_state['user_info'] = user_data.data
                st.session_state['logged_in'] = True
                return True
            else:
                st.error("Usuário autenticado, mas não encontrado no banco de dados.")
                return False
        return False
    except Exception as e:
        st.error("E-mail ou senha incorretos. Por favor, tente novamente.")
        # st.error(f"Detalhe do erro: {e}") # Descomente para depuração
        return False

def logout():
    """Limpa o estado da sessão para deslogar o usuário."""
    # supabase.auth.sign_out() # Opcional, invalida o token no servidor
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- Interface de Login ---
def show_login_page():
    st.image("https://placehold.co/400x100/FFFFFF/000000?text=Logo+da+Empresa", width=200)
    st.title("Login - Sistema de Check-List Veicular")
    st.write("Por favor, insira suas credenciais para acessar o sistema.")

    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Senha", type="password", key="login_password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not email or not password:
                st.warning("Por favor, preencha todos os campos.")
            else:
                with st.spinner("Autenticando..."):
                    if login_user(email, password):
                        st.success("Login realizado com sucesso! Redirecionando...")
                        time.sleep(1)
                        st.switch_page("pages/2_Dashboard.py")
                    # Mensagens de erro são tratadas dentro da função login_user

# --- Lógica Principal ---
if 'logged_in' in st.session_state and st.session_state.logged_in:
    
    with st.sidebar:
        st.subheader(f"Bem-vindo(a), {st.session_state.user_info.get('nome', 'Usuário')}!")
        st.write(f"**Nível:** {st.session_state.user_info.get('nivel_acesso', 'N/A').capitalize()}")
        if st.button("Logout"):
            logout()
    
    st.title("Você já está logado.")
    st.write("Navegue pelas páginas na barra lateral.")
    if st.button("Ir para o Dashboard"):
        st.switch_page("pages/2_Dashboard.py")

else:
    show_login_page()
