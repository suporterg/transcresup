## Conversão Fluxo de Transcrição e Resumo de Audios do N8N para Python usando FastAPI

![Fluxo N8N para Python](./fluxo.png)

### Setup Local
```bash
# Linux ou Mac
virtualenv venv
source ./venv/bin/activate 
pip install -r requirements.txt

 # Windows
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```
para sair do venv é deactivate
### Como Executar localmente
Rode o Comando
```bash
uvicorn main:app --host 0.0.0.0 --port 8005
```
### Endpoint de uso para inserir na sua Evolution api como webhook
```bash
curl --location 'http://127.0.0.1:8005/transcreve-audios'
```
### Para instalar com Docker Swarm e Traefik use o .yaml abaixo como referencia
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
      WHATSAPP_API_KEY: "substitua_sua_chave_aqui"
      WHATSAPP_API_URL: "https://suaevolutionapi.sedominio.com.br/"
      WHATSAPP_INSTANCE: "substitua_sua_instancia_aqui"
      GROQ_API_KEY: "substitua_sua_chave_GROQ_aqui"
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