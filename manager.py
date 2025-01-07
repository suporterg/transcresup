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
            "TRANSCRIPTION_LANGUAGE": get_from_redis("TRANSCRIPTION_LANGUAGE", "pt"),
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

# manager.py - Adicionar na seção de configurações
def message_settings_section():
    st.subheader("📝 Configurações de Mensagem")
    
    # Carregar configurações atuais
    message_settings = storage.get_message_settings()
    
    # Headers personalizados
    col1, col2 = st.columns(2)
    with col1:
        summary_header = st.text_input(
            "Cabeçalho do Resumo",
            value=message_settings["summary_header"],
            help="Formato do cabeçalho para o resumo do áudio"
        )
    with col2:
        transcription_header = st.text_input(
            "Cabeçalho da Transcrição",
            value=message_settings["transcription_header"],
            help="Formato do cabeçalho para a transcrição do áudio"
        )
    
    # Modo de saída
    output_mode = st.selectbox(
        "Modo de Saída",
        options=["both", "summary_only", "transcription_only", "smart"],
        format_func=lambda x: {
            "both": "Resumo e Transcrição",
            "summary_only": "Apenas Resumo",
            "transcription_only": "Apenas Transcrição",
            "smart": "Modo Inteligente (baseado no tamanho)"
        }[x],
        value=message_settings["output_mode"]
    )
    
    # Configuração do limite de caracteres (visível apenas no modo inteligente)
    if output_mode == "smart":
        character_limit = st.number_input(
            "Limite de Caracteres para Modo Inteligente",
            min_value=100,
            max_value=5000,
            value=int(message_settings["character_limit"]),
            help="Se a transcrição exceder este limite, será enviado apenas o resumo"
        )
    else:
        character_limit = message_settings["character_limit"]
    
    # Botão de salvar
    if st.button("💾 Salvar Configurações de Mensagem"):
        try:
            new_settings = {
                "summary_header": summary_header,
                "transcription_header": transcription_header,
                "output_mode": output_mode,
                "character_limit": character_limit
            }
            storage.save_message_settings(new_settings)
            st.success("Configurações de mensagem salvas com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar configurações: {str(e)}")

def manage_settings():
    st.title("⚙️ Configurações")
    
    # Criar tabs para melhor organização
    tab1, tab2, tab3 = st.tabs(["🔑 Chaves API", "🌐 Configurações Gerais", "📝 Formatação de Mensagens"])
    
    with tab1:
        st.subheader("Gerenciamento de Chaves GROQ")
    # Campo para gerenciamento de chaves GROQ
        main_key = st.text_input(
            "GROQ API Key Principal",
            value=st.session_state.settings["GROQ_API_KEY"],
            key="groq_api_key",
            type="password",
            help="Chave GROQ principal do sistema"
        )

        # Seção de chaves adicionais
        st.markdown("---")
        st.subheader("Chaves GROQ Adicionais (Sistema de Rodízio)")
    
        # Exibir chaves existentes
        groq_keys = storage.get_groq_keys()
        if groq_keys:
            st.write("Chaves configuradas para rodízio:")
            for key in groq_keys:
                col1, col2 = st.columns([4, 1])
                with col1:
                    masked_key = f"{key[:10]}...{key[-4:]}"
                    st.code(masked_key, language=None)
                with col2:
                    if st.button("🗑️", key=f"remove_{key}", help="Remover esta chave"):
                        storage.remove_groq_key(key)
                        st.success(f"Chave removida do rodízio!")
                        st.experimental_rerun()

        # Adicionar nova chave
        new_key = st.text_input(
            "Adicionar Nova Chave GROQ",
            key="new_groq_key",
            type="password",
            help="Insira uma nova chave GROQ para adicionar ao sistema de rodízio"
        )
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button("➕ Adicionar ao Rodízio", help="Adicionar esta chave ao sistema de rodízio"):
                if new_key:
                    if new_key.startswith("gsk_"):
                        storage.add_groq_key(new_key)
                        st.success("Nova chave adicionada ao sistema de rodízio!")
                        st.experimental_rerun()
                    else:
                        st.error("Chave inválida! A chave deve começar com 'gsk_'")
                else:
                    st.warning("Por favor, insira uma chave válida")
        pass
    
    with tab2:
        st.subheader("Configurações do Sistema")
    
        # Business Message
        st.text_input(
            "Mensagem de Serviço no Rodapé",
            value=st.session_state.settings["BUSINESS_MESSAGE"],
            key="business_message"
        )
        
        # Process Group Messages
        st.selectbox(
            "Processar Mensagens em Grupos",
            options=["true", "false"],
            index=["true", "false"].index(st.session_state.settings["PROCESS_GROUP_MESSAGES"]),
            key="process_group_messages"
        )
        
        # Process Self Messages
        st.selectbox(
            "Processar Mensagens Próprias",
            options=["true", "false"],
            index=["true", "false"].index(st.session_state.settings["PROCESS_SELF_MESSAGES"]),
            key="process_self_messages"
        )

        st.subheader("🔄 Modo de Processamento")
        # Obter o modo atual do Redis
        current_mode = storage.get_process_mode()
        # Definir as opções e seus rótulos
        mode_options = ["all", "groups_only"]
        mode_labels = {
            "all": "Todos (Grupos e Privado)",
            "groups_only": "Apenas Grupos"
        }
        # Calcular o índice atual baseado no valor do Redis
        current_index = mode_options.index(current_mode) if current_mode in mode_options else 0

        process_mode = st.selectbox(
            "Processar mensagens de:",
            options=mode_options,
            format_func=lambda x: mode_labels[x],
            index=current_index,
            key="process_mode",
            help="Escolha se deseja processar mensagens de todos os contatos ou apenas de grupos"
        )

        # Configuração de idioma
        st.markdown("---")
        st.subheader("🌐 Idioma")
    
        # Dicionário de idiomas em português
        IDIOMAS = {
            "pt": "Português",
            "en": "Inglês",
            "es": "Espanhol",
            "fr": "Francês",
            "de": "Alemão",
            "it": "Italiano",
            "ja": "Japonês",
            "ko": "Coreano",
            "zh": "Chinês",
            "ro": "Romeno",
            "ru": "Russo",
            "ar": "Árabe",
            "hi": "Hindi",
            "nl": "Holandês",
            "pl": "Polonês",
            "tr": "Turco"
        }
        
        # Carregar configuração atual de idioma
        current_language = get_from_redis("TRANSCRIPTION_LANGUAGE", "pt")
        
        # Seleção de idioma
        selected_language = st.selectbox(
            "Idioma para Transcrição e Resumo",
            options=list(IDIOMAS.keys()),
            format_func=lambda x: IDIOMAS[x],
            index=list(IDIOMAS.keys()).index(current_language) if current_language in IDIOMAS else 0,
            help="Selecione o idioma para transcrição dos áudios e geração dos resumos",
            key="transcription_language"
        )
        pass
    
    with tab3:
        st.subheader("Formatação de Mensagens")
        
        # Headers personalizados
        col1, col2 = st.columns(2)
        with col1:
            summary_header = st.text_input(
                "Cabeçalho do Resumo",
                value=get_from_redis("summary_header", "🤖 *Resumo do áudio:*"),
                key="summary_header",
                help="Formato do cabeçalho para o resumo do áudio"
            )
        with col2:
            transcription_header = st.text_input(
                "Cabeçalho da Transcrição",
                value=get_from_redis("transcription_header", "🔊 *Transcrição do áudio:*"),
                key="transcription_header",
                help="Formato do cabeçalho para a transcrição do áudio"
            )
        
        # Modo de saída - Corrigido para usar index
        output_modes = ["both", "summary_only", "transcription_only", "smart"]
        output_mode_labels = {
            "both": "Resumo e Transcrição",
            "summary_only": "Apenas Resumo",
            "transcription_only": "Apenas Transcrição",
            "smart": "Modo Inteligente (baseado no tamanho)"
        }
        
        current_mode = get_from_redis("output_mode", "both")
        mode_index = output_modes.index(current_mode) if current_mode in output_modes else 0
        
        output_mode = st.selectbox(
            "Modo de Saída",
            options=output_modes,
            format_func=lambda x: output_mode_labels[x],
            index=mode_index,
            key="output_mode",
            help="Selecione como deseja que as mensagens sejam enviadas"
        )
        
        if output_mode == "smart":
            character_limit = st.number_input(
                "Limite de Caracteres para Modo Inteligente",
                min_value=100,
                max_value=5000,
                value=int(get_from_redis("character_limit", "500")),
                help="Se a transcrição exceder este limite, será enviado apenas o resumo"
            )

    # Botão de salvar unificado
    if st.button("💾 Salvar Todas as Configurações"):
        try:
            # Salvar configurações existentes
            save_settings()
            
            # Salvar novas configurações de mensagem
            save_to_redis("summary_header", summary_header)
            save_to_redis("transcription_header", transcription_header)
            save_to_redis("output_mode", output_mode)
            if output_mode == "smart":
                save_to_redis("character_limit", str(character_limit))
                
            # Se há uma chave principal, adicionar ao sistema de rodízio
            if main_key and main_key.startswith("gsk_"):
                storage.add_groq_key(main_key)
            
            # Salvar configuração de idioma
            save_to_redis("TRANSCRIPTION_LANGUAGE", selected_language)
            
            # Salvamento do modo de processamento
            storage.redis.set(storage._get_redis_key("process_mode"), process_mode)
            
            st.success("✅ Todas as configurações foram salvas com sucesso!")
            
            # Mostrar resumo
            total_keys = len(storage.get_groq_keys())
            st.info(f"""Sistema configurado com {total_keys} chave(s) GROQ no rodízio
                    Idioma definido: {IDIOMAS[selected_language]}
                    Modo de saída: {output_mode_labels[output_mode]}""")
            
        except Exception as e:
            st.error(f"Erro ao salvar configurações: {str(e)}")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    dashboard()
else:
    login_page()

show_footer()