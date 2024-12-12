#!/bin/bash

# Função para inicializar configurações no Redis
initialize_redis_config() {
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET GROQ_API_KEY "sua_api_key_aqui"
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET BUSINESS_MESSAGE "*Impacte AI* Premium Services"
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET PROCESS_GROUP_MESSAGES "false"
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET PROCESS_SELF_MESSAGES "true"
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET DEBUG_MODE "false"
}

# Inicializar configurações no Redis
initialize_redis_config

# Iniciar o FastAPI em background
uvicorn main:app --host 0.0.0.0 --port 8005 &

# Iniciar o Streamlit
streamlit run manager.py --server.address 0.0.0.0 --server.port 8501

# Manter o script rodando
wait