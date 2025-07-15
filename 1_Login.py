import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import time

# --- Configuração da Página ---
st.set_page_config(
    page_title="Check-List Veicular",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Funções de Autenticação e Firebase ---

# Inicializa o Firebase apenas uma vez
@st.cache_resource
def init_firebase():
    try:
        # Tenta usar as credenciais dos segredos do Streamlit
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds, {
            'storageBucket': creds_dict['storage_bucket']
        })
        print("Firebase App inicializado com sucesso.")
    except Exception as e:
        # Fallback para caso não encontre as credenciais (ou já inicializado)
        if not firebase_admin._apps:
            print(f"Erro ao inicializar Firebase: {e}. Verifique o seu arquivo secrets.toml")
    return firestore.client()

db = init_firebase()

def login_user(email, password):
    """
    Autentica o usuário com email e senha usando Firebase Auth.
    Retorna o UID do usuário em caso de sucesso, None caso contrário.
    """
    try:
        # ATENÇÃO: Firebase Admin SDK não tem um método direto de login com senha.
        # A maneira correta é usar a API REST do Firebase ou o SDK do cliente (JavaScript).
        # Esta função SIMULA o login buscando o usuário pelo email.
        # Para um app de produção, a autenticação DEVE ser feita no lado do cliente.
        user = auth.get_user_by_email(email)
        
        # A verificação de senha não é possível aqui.
        # Apenas confirmamos que o usuário existe.
        if user:
            st.session_state['user_uid'] = user.uid
            st.session_state['user_email'] = user.email
            
            # Busca informações adicionais do usuário no Firestore
            user_info_ref = db.collection('usuarios').document(user.uid)
            user_info_doc = user_info_ref.get()
            if user_info_doc.exists:
                st.session_state['user_info'] = user_info_doc.to_dict()
                st.session_state['logged_in'] = True
                return True
            else:
                st.error("Usuário autenticado, mas não encontrado no banco de dados.")
                return False
        return False
    except auth.UserNotFoundError:
        st.error("Usuário não encontrado. Verifique o e-mail.")
        return False
    except Exception as e:
        st.error(f"Ocorreu um erro durante o login: {e}")
        return False

def logout():
    """Limpa o estado da sessão para deslogar o usuário."""
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
                        # Redireciona para a primeira página após o login
                        st.switch_page("pages/2_Dashboard.py")
                    # Mensagens de erro são tratadas dentro da função login_user

# --- Lógica Principal ---
# Verifica se o usuário já está logado
if 'logged_in' in st.session_state and st.session_state.logged_in:
    
    # Se estiver logado, mostra a barra lateral com informações e botão de logout
    with st.sidebar:
        st.subheader(f"Bem-vindo(a), {st.session_state.user_info.get('nome', 'Usuário')}!")
        st.write(f"**Nível:** {st.session_state.user_info.get('nivel_acesso', 'N/A').capitalize()}")
        if st.button("Logout"):
            logout()
    
    # Se o usuário está logado mas na página de login, redireciona para o dashboard
    st.title("Você já está logado.")
    st.write("Navegue pelas páginas na barra lateral.")
    if st.button("Ir para o Dashboard"):
        st.switch_page("pages/2_Dashboard.py")

else:
    # Se não estiver logado, mostra a página de login
    show_login_page()

