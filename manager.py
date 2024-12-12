import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from storage import StorageHandler
import plotly.express as px
import os
import redis


# Conectar ao Redis
redis_client = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6380)), decode_responses=True)

# Função para salvar configurações no Redis
def save_to_redis(key, value):
    try:
        redis_client.set(key, value)
        st.success(f"Configuração {key} salva com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar no Redis: {key} -> {e}")

# Função para buscar configurações no Redis
def get_from_redis(key, default=None):
    try:
        value = redis_client.get(key)
        return value if value is not None else default
    except Exception as e:
        st.error(f"Erro ao buscar no Redis: {key} -> {e}")
        return default
# Função para buscar grupos do Whatsapp
def fetch_whatsapp_groups(server_url, instance, api_key):
    url = f"{server_url}/group/fetchAllGroups/{instance}"
    headers = {"apikey": api_key}
    params = {"getParticipants": "false"}  # Adicionando o parâmetro de query
    
    try:
        st.write(f"Requisição para URL: {url}")  # Debug para URL
        st.write(f"Cabeçalhos: {headers}")  # Debug para headers
        st.write(f"Parâmetros: {params}")  # Debug para parâmetros
        
        response = requests.get(url, headers=headers, params=params)
        st.write(f"Status Code: {response.status_code}")  # Debug para status HTTP
        
        response.raise_for_status()  # Levanta exceções HTTP
        return response.json()  # Retorna o JSON da resposta
    except requests.RequestException as e:
        st.error(f"Erro ao buscar grupos: {str(e)}")
        if response.text:
            st.error(f"Resposta do servidor: {response.text}")
        return []
    
# Configuração da página
st.set_page_config(
    page_title="TranscreveZAP by Impacte AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        font-size: 16px;
    }
    h1, h2, h3 {
        margin-bottom: 1rem;
    }
    .sidebar-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #000000;
        color: #ffffff;
        text-align: center;
        padding: 10px 0;
        font-size: 14px;
    }
    .footer a {
        color: #ffffff;
        text-decoration: underline;
    }
    @media (max-width: 768px) {
        .main > div {
            padding-top: 1rem;
        }
        .sidebar-header {
            font-size: 1.2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Configuração do storage
storage = StorageHandler()

# Função para carregar configurações do Redis para o Streamlit
def load_settings():
    try:
        st.session_state.settings = {
            "GROQ_API_KEY": get_from_redis("GROQ_API_KEY", "default_key"),
            "BUSINESS_MESSAGE": get_from_redis("BUSINESS_MESSAGE", "*Impacte AI* Premium Services"),
            "PROCESS_GROUP_MESSAGES": get_from_redis("PROCESS_GROUP_MESSAGES", "false"),
            "PROCESS_SELF_MESSAGES": get_from_redis("PROCESS_SELF_MESSAGES", "true"),
        }
    except Exception as e:
        st.error(f"Erro ao carregar configurações do Redis: {e}")

# Carregar configurações na sessão, se necessário
if "settings" not in st.session_state:
    load_settings()

# Função para salvar configurações do Streamlit no Redis
def save_settings():
    try:
        save_to_redis("GROQ_API_KEY", st.session_state.groq_api_key)
        save_to_redis("BUSINESS_MESSAGE", st.session_state.business_message)
        save_to_redis("PROCESS_GROUP_MESSAGES", st.session_state.process_group_messages)
        save_to_redis("PROCESS_SELF_MESSAGES", st.session_state.process_self_messages)
        st.success("Configurações salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar configurações: {e}")

def show_logo():
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "static", "fluxo.png")
        if os.path.exists(logo_path):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(logo_path, width=400, use_column_width=True)  # Aumentado e responsivo
        else:
            st.warning("Logo não encontrada.")
    except Exception as e:
        st.error(f"Erro ao carregar logo: {e}")

def show_footer():
    st.markdown(
        """
        <div class="footer" style="text-align: center; margin-top: 50px;">
            <p>Desenvolvido por <a href="https://impacte.ai" target="_blank">Impacte AI</a> | 
            Código fonte no <a href="https://github.com/impacte-ai/transcrevezap" target="_blank">GitHub</a></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def login_page():
    show_logo()
    st.markdown("<h3 style='text-align: center; margin-bottom: 1rem; font-size: 1.2em;'>TranscreveZAP</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<h2 style='text-align: center; margin-bottom: 1rem;'>Login</h2>", unsafe_allow_html=True)
            username = st.text_input('Usuário', key='username')
            password = st.text_input('Senha', type='password', key='password')
            submit_button = st.form_submit_button('Entrar')
            if submit_button:
                if username == os.getenv('MANAGER_USER') and password == os.getenv('MANAGER_PASSWORD'):
                    st.session_state.authenticated = True
                    st.experimental_rerun()
                else:
                    st.error('Credenciais inválidas')

def dashboard():
    show_logo()
    st.sidebar.markdown('<div class="sidebar-header">TranscreveZAP - Menu</div>', unsafe_allow_html=True)
    page = st.sidebar.radio(
        "Navegação",
        ["📊 Painel de Controle", "👥 Gerenciar Grupos", "🚫 Gerenciar Bloqueios", "⚙️ Configurações"]
    )
    if st.sidebar.button("Sair"):
        st.session_state.authenticated = False
        st.experimental_rerun()

    if page == "📊 Painel de Controle":
        show_statistics()
    elif page == "👥 Gerenciar Grupos":
        manage_groups()
    elif page == "🚫 Gerenciar Bloqueios":
        manage_blocks()
    elif page == "⚙️ Configurações":
        manage_settings()

def show_statistics():
    st.title("📊 Painel de Controle")
    try:
        stats = storage.get_statistics()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Áudios Processados", stats.get("total_processed", 0))
        with col2:
            last_processed = stats.get("last_processed", "Nunca")
            st.metric("Último Processamento", last_processed)
        with col3:
            total_groups = len(storage.get_allowed_groups())
            st.metric("Grupos Permitidos", total_groups)

        daily_data = stats["stats"]["daily_count"]
        if daily_data:
            df = pd.DataFrame(list(daily_data.items()), columns=['Data', 'Processamentos'])
            df['Data'] = pd.to_datetime(df['Data'])
            fig = px.line(df, x='Data', y='Processamentos', title='Processamentos por Dia')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ainda não há dados de processamento disponíveis.")

        # Adicionar informações sobre o endpoint da API
        st.subheader("Endpoint da API")
        api_domain = get_from_redis("API_DOMAIN", "seu.dominio.com")
        api_endpoint = f"https://{api_domain}/transcreve-audios"
        st.code(api_endpoint, language="text")

        if st.button("ℹ️ Instruções de Uso"):
            st.info(
                "Para utilizar o serviço de transcrição, siga estas etapas:\n\n"
                "1. Copie a URL completa acima.\n"
                "2. Na configuração de webhook da Evolution API:\n"
                "   - Cole a URL no campo apropriado.\n"
                "   - Ative o webhook.\n"
                "   - Marque as opções 'Webhook Base64' e o Evento 'MESSAGES_UPSERT'.\n\n"
                "Isso permitirá que a Evolution API envie as mensagens de áudio para o nosso serviço de transcrição."
            )

    except Exception as e:
        st.error(f"Erro ao carregar estatísticas: {e}")

def manage_groups():
    st.title("👥 Gerenciar Grupos")

    # Campos para inserção dos dados da API
    st.subheader("Configuração da API Evolution")
    col1, col2, col3 = st.columns(3)
    with col1:
        server_url = st.text_input("URL do Servidor", value=get_from_redis("EVOLUTION_API_URL", ""))
    with col2:
        instance = st.text_input("Instância", value=get_from_redis("EVOLUTION_INSTANCE", ""))
    with col3:
        api_key = st.text_input("API Key", value=get_from_redis("EVOLUTION_API_KEY", ""), type="password")

    if st.button("Salvar Configurações da API"):
        save_to_redis("EVOLUTION_API_URL", server_url)
        save_to_redis("EVOLUTION_INSTANCE", instance)
        save_to_redis("EVOLUTION_API_KEY", api_key)
        st.success("Configurações da API salvas com sucesso!")

    # Busca e exibição de grupos do WhatsApp
    if server_url and instance and api_key:
        if st.button("Buscar Grupos do WhatsApp"):
            with st.spinner('Buscando grupos...'):
                groups = fetch_whatsapp_groups(server_url, instance, api_key)
                if groups:
                    st.session_state.whatsapp_groups = groups
                    st.success(f"{len(groups)} grupos carregados com sucesso!")
                else:
                    st.warning("Nenhum grupo encontrado ou erro ao buscar grupos.")

        if 'whatsapp_groups' in st.session_state:
            st.subheader("Grupos do WhatsApp")
            search_term = st.text_input("Buscar grupos", "")
            filtered_groups = [group for group in st.session_state.whatsapp_groups if search_term.lower() in group['subject'].lower()]
            
            for group in filtered_groups:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text(f"{group['subject']} ({group['id']})")
                with col2:
                    is_allowed = group['id'] in storage.get_allowed_groups()
                    if st.checkbox("Permitir", value=is_allowed, key=f"allow_{group['id']}"):
                        if not is_allowed:
                            storage.add_allowed_group(group['id'])
                            st.success(f"Grupo {group['subject']} permitido!")
                    else:
                        if is_allowed:
                            storage.remove_allowed_group(group['id'])
                            st.success(f"Grupo {group['subject']} removido!")
    else:
        st.info("Por favor, insira as configurações da API Evolution para buscar os grupos.")

    # Adicionar grupo manualmente
    st.subheader("Adicionar Grupo Manualmente")
    new_group = st.text_input("Número do Grupo", placeholder="Ex: 5521999999999")
    if st.button("Adicionar"):
        formatted_group = f"{new_group}@g.us"
        storage.add_allowed_group(formatted_group)
        st.success(f"Grupo {formatted_group} adicionado com sucesso!")
        st.experimental_rerun()

    # Lista de grupos permitidos
    st.subheader("Grupos Permitidos")
    allowed_groups = storage.get_allowed_groups()
    if allowed_groups:
        for group in allowed_groups:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(group)
            with col2:
                if st.button("Remover", key=f"remove_{group}"):
                    storage.remove_allowed_group(group)
                    st.success(f"Grupo {group} removido!")
                    st.experimental_rerun()
    else:
        st.info("Nenhum grupo permitido.")

def manage_blocks():
    st.title("🚫 Gerenciar Bloqueios")
    st.subheader("Bloquear Usuário")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_user = st.text_input("Número do Usuário", placeholder="Ex: 5521999999999")
    with col2:
        if st.button("Bloquear"):
            formatted_user = f"{new_user}@s.whatsapp.net"
            storage.add_blocked_user(formatted_user)
            st.success(f"Usuário {formatted_user} bloqueado!")
            st.experimental_rerun()

    st.subheader("Usuários Bloqueados")
    blocked_users = storage.get_blocked_users()
    if blocked_users:
        for user in blocked_users:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(user)
            with col2:
                if st.button("Desbloquear", key=f"unblock_{user}"):
                    storage.remove_blocked_user(user)
                    st.success(f"Usuário {user} desbloqueado!")
                    st.experimental_rerun()
    else:
        st.info("Nenhum usuário bloqueado.")

def manage_settings():
    st.title("⚙️ Configurações")
    st.subheader("Configurações do Sistema")
    st.text_input("GROQ_API_KEY", value=st.session_state.settings["GROQ_API_KEY"], key="groq_api_key")
    st.text_input("Mensagem de Serviço no Rodapé", value=st.session_state.settings["BUSINESS_MESSAGE"], key="business_message")
    st.selectbox("Processar Mensagens em Grupos", options=["true", "false"], index=["true", "false"].index(st.session_state.settings["PROCESS_GROUP_MESSAGES"]), key="process_group_messages")
    st.selectbox("Processar Mensagens Próprias", options=["true", "false"], index=["true", "false"].index(st.session_state.settings["PROCESS_SELF_MESSAGES"]), key="process_self_messages")
    if st.button("Salvar Configurações"):
        save_settings()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    dashboard()
else:
    login_page()

show_footer()