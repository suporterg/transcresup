import os
from dotenv import load_dotenv
import logging
from pathlib import Path

# Configuração de logging com cores e formatação melhorada
class ColoredFormatter(logging.Formatter):
    """Formatter personalizado que adiciona cores aos logs"""
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.blue + self.fmt + self.reset,
            logging.INFO: self.grey + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Configuração inicial do logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Carregar variáveis de ambiente
env_path = Path('.env')
if env_path.exists():
    logger.debug(f"Arquivo .env encontrado em: {env_path.absolute()}")
    load_dotenv(override=True)
else:
    logger.warning("Arquivo .env não encontrado! Usando variáveis de ambiente do sistema.")

class Settings:
    def __init__(self):
        logger.debug("Iniciando carregamento das configurações...")
        
        # Carregamento das variáveis com logs detalhados
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        logger.debug(f"DEBUG_MODE configurado como: {self.DEBUG_MODE}")
        
        self.GROQ_API_KEY = os.getenv('GROQ_API_KEY')
        if self.GROQ_API_KEY:
            masked_key = f"{self.GROQ_API_KEY[:10]}...{self.GROQ_API_KEY[-4:]}"
            logger.debug(f"GROQ_API_KEY carregada: {masked_key}")
        else:
            logger.error("GROQ_API_KEY não encontrada!")
        
        self.BUSINESS_MESSAGE = os.getenv('BUSINESS_MESSAGE', '*Impacte AI* Premium Services')
        logger.debug(f"BUSINESS_MESSAGE configurada como: {self.BUSINESS_MESSAGE}")
        
        self.PROCESS_GROUP_MESSAGES = os.getenv('PROCESS_GROUP_MESSAGES', 'false').lower() == 'true'
        logger.debug(f"PROCESS_GROUP_MESSAGES configurado como: {self.PROCESS_GROUP_MESSAGES}")
        
        self.PROCESS_SELF_MESSAGES = os.getenv('PROCESS_SELF_MESSAGES', 'false').lower() == 'true'
        logger.debug(f"PROCESS_SELF_MESSAGES configurado como: {self.PROCESS_SELF_MESSAGES}")

        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        logger.debug(f"LOG_LEVEL configurado como: {self.LOG_LEVEL}")

    def validate(self):
        """Validação detalhada das configurações críticas"""
        logger.debug("Iniciando validação das configurações...")
        
        validation_errors = []
        
        if not self.GROQ_API_KEY:
            validation_errors.append("GROQ_API_KEY não está definida")
        elif not self.GROQ_API_KEY.startswith('gsk_'):
            validation_errors.append("GROQ_API_KEY inválida: deve começar com 'gsk_'")

        if validation_errors:
            for error in validation_errors:
                logger.error(f"Erro de validação: {error}")
            return False
            
        logger.info("Todas as configurações foram validadas com sucesso!")
        return True

# Criar instância das configurações
settings = Settings()

# Validar configurações
if not settings.validate():
    logger.critical("Configurações inválidas detectadas. A aplicação pode não funcionar corretamente!")

# Ajustar nível de log
log_level = logging.DEBUG if settings.DEBUG_MODE else getattr(logging, settings.LOG_LEVEL.upper())
logger.setLevel(log_level)
logger.info(f"Nível de log definido como: {logging.getLevelName(log_level)}")