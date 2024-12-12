# Usar uma imagem oficial do Python como base
FROM python:3.10-slim

# Instalar dependências do sistema, incluindo redis-tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-tools \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho
WORKDIR /app

# Copiar o arquivo requirements.txt e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da aplicação
COPY . .

# Garantir que o diretório static existe
RUN mkdir -p /app/static

# Copiar arquivos estáticos para o diretório apropriado
COPY static/ /app/static/

# Garantir permissões de execução ao script inicial
COPY start.sh .
RUN chmod +x start.sh

# Converter possíveis caracteres de retorno de carro do Windows
RUN apt-get update && apt-get install -y dos2unix && dos2unix start.sh && apt-get remove -y dos2unix && apt-get autoremove -y && apt-get clean

# Expor as portas usadas pela aplicação
EXPOSE 8005 8501

# Definir o comando inicial
CMD ["/bin/bash", "/app/start.sh"]