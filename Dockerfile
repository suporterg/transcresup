# Usar uma imagem oficial do Python como base
FROM python:3.10-slim

# Definir o diretório de trabalho
WORKDIR /app

# Copiar o requirements.txt e instalar dependências
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código para dentro do contêiner
COPY . .

# Expor a porta onde o FastAPI vai rodar
EXPOSE 8005

# Comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
