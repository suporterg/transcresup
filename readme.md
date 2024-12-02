# Transcrição e Resumo de Áudios no WhatsApp usando Python

![ImpacteAI](./fluxo.png)

Este projeto permite transcrever e resumir áudios enviados pelo WhatsApp usando inteligência artificial e integração com APIs. Ideal para automatizar o processamento de mensagens de áudio, oferecendo um resumo claro e prático.

---

## 📋 **Pré-requisitos**
Antes de começar, certifique-se de ter os seguintes requisitos:
- Python 3.10+ instalado ([Download](https://www.python.org/downloads/))
- Docker e Docker Compose instalados ([Instruções](https://docs.docker.com/get-docker/))
- Uma conta Evolution API com chave válida
- Uma conta GROQ API com chave válida

---

## ⚙️ **Setup Local**

### Ambiente Virtual
Configure o ambiente virtual para instalar as dependências do projeto:

#### **Linux ou macOS**
```bash
virtualenv venv
source ./venv/bin/activate 
pip install -r requirements.txt
```
#### **Windows**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```
Para sair do ambiente virtual, use:
```bash
deactivate
```
### 🚀 Como Executar Localmente
Certifique-se de que todas as dependências foram instaladas.
Rode o comando abaixo para iniciar o servidor:
```bash
uvicorn main:app --host 0.0.0.0 --port 8005
```
Acesse o serviço localmente em: http://127.0.0.1:8005.

### 🌐 Configuração de Webhook na Evolution API
Endpoint para Webhook
Use o seguinte endpoint para configurar seu webhook na Evolution API:
```bash
https://transcricaoaudio.seudominio.com.br/transcreve-audios
```
### Testando Localmente
Se estiver rodando localmente, use o comando curl para testar:
```bash
curl --location 'http://127.0.0.1:8005/transcreve-audios'
```
### 🐳 Instalação com Docker Swarm e Traefik
Se preferir rodar o projeto em um ambiente de produção com Docker Swarm e Traefik, use o arquivo de configuração abaixo como referência.

docker-compose.yaml
```bash
version: "3.7"

services:
  transcricaoaudio:
    image: impacteai/transcrevezap:latest
    build: .
    networks:
      - suarededocker #troque pela sua rede do docker
    ports:
      - 8005:8005
    environment:
      Uvicorn_port: 8005
      Uvicorn_host: 0.0.0.0
      Uvicorn_reload: "true"
      Uvicorn_workers: 1
      WHATSAPP_API_KEY: "substitua_sua_chave_aqui" #coloque sua api key evolution aqui
      WHATSAPP_API_URL: "https://suaevolutionapi.sedominio.com.br/" #coloque sua url evolution aqui
      WHATSAPP_INSTANCE: "substitua_sua_instancia_aqui" #coloque nome da sua instancia evolution aqui
      GROQ_API_KEY: "substitua_sua_chave_GROQ_aqui" #coloque sua chave GROQ aqui
      BUSINESS_MESSAGE: "substitua_sua_mensagem_de_servico_aqui" #coloque a mensagem que será enviada ao final da transcrição aqui
      PROCESS_GROUP_MESSAGES: "false" # Define se mensagens de grupos devem ser processadas
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      labels:
        - traefik.enable=true
        - traefik.http.routers.transcricaoaudio.rule=Host(`transcricaoaudio.seudominio.com.br`) #coloque seu subdominio apontado aqui
        - traefik.http.routers.transcricaoaudio.entrypoints=websecure
        - traefik.http.routers.transcricaoaudio.tls.certresolver=letsencryptresolver
        - traefik.http.services.transcricaoaudio.loadbalancer.server.port=8005
        - traefik.http.services.transcricaoaudio.loadbalancer.passHostHeader=true
        - traefik.http.routers.transcricaoaudio.service=transcricaoaudio
        - traefik.http.middlewares.traefik-compress.compress=true
        - traefik.http.routers.transcricaoaudio.middlewares=traefik-compress
      resources:
        limits:
          cpus: "1"
          memory: 1024M

networks:
  suarededocker: #troque pela sua rede do docker
    external: true
    name: suarededocker #troque pela sua rede do docker
```
---

## 📖 **Configuração das Variáveis de Ambiente**
Ao usar o Docker Compose, configure as seguintes variáveis de ambiente no arquivo `docker-compose.yaml`:

| Variável               | Descrição                                                                                  |
|------------------------|--------------------------------------------------------------------------------------------|
| `WHATSAPP_API_KEY`     | Chave da API Evolution para integração com o WhatsApp.                                     |
| `WHATSAPP_API_URL`     | URL da sua instância da Evolution API.                                                     |
| `WHATSAPP_INSTANCE`    | Nome da instância configurada na Evolution API.                                            |
| `GROQ_API_KEY`         | Chave da API GROQ para realizar transcrições e resumos de áudios.                          |
| `BUSINESS_MESSAGE`     | Mensagem de divulgação que será adicionada ao final das transcrições.                      |
| `PROCESS_GROUP_MESSAGES` | Define se mensagens enviadas em grupos devem ser processadas (`true`) ou ignoradas (`false`). |

---