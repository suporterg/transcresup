# Transcrição e Resumo de Áudios no WhatsApp usando Python

![ImpacteAI](./fluxo.png)

Este projeto permite transcrever e resumir áudios enviados pelo WhatsApp usando inteligência artificial e integração com APIs. Ideal para automatizar o processamento de mensagens de áudio, oferecendo um resumo claro e prático.

Contato de email: `impacte.ai@gmail.com`
---

## 📋 **Pré-requisitos**
Antes de começar, certifique-se de ter os seguintes requisitos:
- Python 3.10+ instalado ([Download](https://www.python.org/downloads/))
- Docker e Docker Compose instalados ([Instruções](https://docs.docker.com/get-docker/))
- Uma conta Evolution API com chave válida
- Uma conta GROQ API com chave válida (começa com 'gsk_')

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

### Configuração do Arquivo .env
Copie o arquivo `.env.example` para `.env` e configure suas variáveis:
```bash
cp .env.example .env
```
## 📖 **Configuração Detalhada das Variáveis**

### Variáveis Essenciais

| Variável               | Descrição                                                | Obrigatória | Exemplo                                                    |
|-----------------------|----------------------------------------------------------|-------------|----------------------------------------------------------|
| `GROQ_API_KEY`        | Chave da API GROQ (deve começar com 'gsk_')             | Sim         | `gsk_abc123...`                                           |

### Variáveis de Personalização

| Variável               | Descrição                                                | Padrão      | Exemplo                                                    |
|-----------------------|----------------------------------------------------------|-------------|----------------------------------------------------------|
| `BUSINESS_MESSAGE`    | Mensagem de rodapé após transcrição                      | Vazio       | `substitua_sua_mensagem_de_servico_aqui` |
| `PROCESS_GROUP_MESSAGES` | Habilita processamento de mensagens em grupos          | `false`     | `true` ou `false`                                          |

### Variáveis de Debug e Log

| Variável               | Descrição                                                | Padrão      | Valores Possíveis                                          |
|-----------------------|----------------------------------------------------------|-------------|----------------------------------------------------------|
| `DEBUG_MODE`          | Ativa logs detalhados para debugging                     | `false`     | `true` ou `false`                                          |
| `LOG_LEVEL`           | Define o nível de detalhamento dos logs                  | `INFO`      | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`            |

---

## 🚀 **Métodos de Execução**

### Execução Local
```bash
uvicorn main:app --host 0.0.0.0 --port 8005
```
### Endpoint para inserir no webhook da Evolution API para consumir o serviço
```bash
http://127.0.0.1:8005/transcreve-audios
```

### 🐳 Docker Compose Simples
```yaml
version: "3.7"
services:
  transcricaoaudio:
    image: impacteai/transcrevezap:latest
    ports:
      - 8005:8005
    environment:
      Uvicorn_port: 8005
      Uvicorn_host: 0.0.0.0
      Uvicorn_reload: "true"
      Uvicorn_workers: 1
      GROQ_API_KEY: "substitua_sua_chave_GROQ_aqui" #coloque sua chave GROQ aqui
      BUSINESS_MESSAGE: "substitua_sua_mensagem_de_servico_aqui" #coloque a mensagem que será enviada ao final da transcrição aqui
      PROCESS_GROUP_MESSAGES: "false" # Define se mensagens de grupos devem ser processadas
      DEBUG_MODE: "false"
      LOG_LEVEL: "INFO"
```

### 🌟 Docker Swarm com Traefik
```yaml
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
      GROQ_API_KEY: "substitua_sua_chave_GROQ_aqui" #coloque sua chave GROQ aqui
      BUSINESS_MESSAGE: "substitua_sua_mensagem_de_servico_aqui" #coloque a mensagem que será enviada ao final da transcrição aqui
      PROCESS_GROUP_MESSAGES: "false" # Define se mensagens de grupos devem ser processadas
      DEBUG_MODE: "false"
      LOG_LEVEL: "INFO"
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

### Endpoint para inserir no webhook da Evolution API para consumir o serviço
```bash
https://transcricaoaudio.seudominio.com.br/transcreve-audios

```
## 🔧 **Configuração do Traefik**

Para usar com Traefik, certifique-se de:
1. Ter o Traefik configurado em seu ambiente Docker Swarm
2. Configurar o DNS do seu domínio para apontar para o servidor
3. Ajustar as labels do Traefik conforme seu ambiente
4. Verificar se a rede externa existe no Docker Swarm

## 📝 **Notas Importantes**
- A GROQ_API_KEY deve começar com 'gsk_'
- O BUSINESS_MESSAGE suporta formatação do WhatsApp (*negrito*, _itálico_)
- Para quebras de linha no BUSINESS_MESSAGE, use \n
- Em produção, recomenda-se DEBUG_MODE=false
- Configure LOG_LEVEL=DEBUG apenas para troubleshooting

## 🔍 **Troubleshooting**
Se encontrar problemas:
1. Verifique se todas as variáveis obrigatórias estão configuradas
2. Ative DEBUG_MODE=true temporariamente
3. Verifique os logs do container
4. Certifique-se que as APIs estão acessíveis

## 📄 **Licença**
Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---
