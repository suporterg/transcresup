#!/bin/bash

# Função para inicializar configurações no Redis se não existirem
initialize_redis_config() {
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET GROQ_API_KEY "sua_api_key_aqui" NX
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET BUSINESS_MESSAGE "*Impacte AI* Premium Services" NX
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET PROCESS_GROUP_MESSAGES "false" NX
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET PROCESS_SELF_MESSAGES "true" NX
    redis-cli -h $REDIS_HOST -p $REDIS_PORT SET API_DOMAIN "$API_DOMAIN" NX
}

# Aguardar o Redis estar pronto
echo "Aguardando o Redis ficar disponível..."
until redis-cli -h $REDIS_HOST -p $REDIS_PORT PING; do
  echo "Redis não está pronto - aguardando..."
  sleep 5
done

# Inicializar configurações no Redis (apenas se não existirem)
initialize_redis_config

# Iniciar o FastAPI em background
uvicorn main:app --host 0.0.0.0 --port 8005 &

# Iniciar o Streamlit
streamlit run manager.py --server.address 0.0.0.0 --server.port 8501

# Manter o script rodando
wait