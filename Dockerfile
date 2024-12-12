# Usar uma imagem oficial do Python como base
FROM python:3.10-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
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
RUN chmod +x start.sh

# Expor as portas usadas pela aplicação
EXPOSE 8005 8501

# Definir o comando inicial
CMD ["./start.sh"]