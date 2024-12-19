# TranscreveZAP 2.0
## Transcrição e Resumo de Áudios no WhatsApp usando Python com interface em Streamlit

![ImpacteAI](./fluxo.png)

Este projeto permite transcrever e resumir áudios enviados pelo WhatsApp usando inteligência artificial e integração com APIs. Ideal para automatizar o processamento de mensagens de áudio, oferecendo um resumo claro e prático.

Contato de email: contato@impacte.ai
([ACESSE NOSSO SITE](https://impacte.ai/))

Nosso Grupo do Whatsapp: ([Entre no GRUPO AQUI](https://chat.whatsapp.com/L9jB1SlcmQFIVxzN71Y6KG)) 
---

## 📋 **Pré-requisitos**
Antes de começar, certifique-se de ter os seguintes requisitos:
- Python 3.10+ instalado ([Download](https://www.python.org/downloads/))
- Docker e Docker Compose instalados ([Instruções](https://docs.docker.com/get-docker/))
- Uma conta Evolution API com chave válida
- Uma conta GROQ API com chave válida (começa com 'gsk_') ([Crie sua CONTA](https://console.groq.com/login))
* Em caso de uso com Proxy Reverso Aponte um Subdomínio para a API e outro para o MANAGER da aplicação
---

## 🚀 **Instalação e Configuração**

### 🐳 Docker Compose
1. Clone o repositório:
```bash
   git clone https://github.com/seu-usuario/transcrevezap.git
   cd transcrevezap
```
2. Configure o arquivo docker-compose.yaml:

```yaml
    version: "3.7"
    services:
      tcaudio:
        image: impacteai/transcrevezap:latest
        ports:
          - 8005:8005  # Porta para FastAPI
          - 8501:8501  # Porta para Streamlit
        environment:
          - REDIS_HOST=redis
          - REDIS_PORT=6380
          - API_DOMAIN=seu-ip 
          - DEBUG_MODE=false
          - LOG_LEVEL=INFO
          - MANAGER_USER=admin
          - MANAGER_PASSWORD=sua_senha_aqui
        depends_on:
          - redis
      
      redis:
        image: redis:6
        command: redis-server --port 6380 --appendonly yes
        volumes:
          - redis_data:/data

    volumes:
      redis_data:
```

3. Inicie os serviços:
```bash
docker-compose up -d
```

## 📖 Configuração da Interface

Acesse a interface de gerenciamento em http://seu-ip:8501.
Faça login com as credenciais definidas em MANAGER_USER e MANAGER_PASSWORD.
Na seção "Configurações", defina:

1. GROQ_API_KEY: Sua chave da API GROQ
2. BUSINESS_MESSAGE: Mensagem de rodapé após transcrição
3. PROCESS_GROUP_MESSAGES: Habilitar processamento de mensagens em grupos
4. PROCESS_SELF_MESSAGES: Habilitar processamento de mensagens próprias

## 🔧 Uso
Endpoint para Webhook da Evolution API
Configure o webhook da Evolution API para apontar para:
```bash
http://seu-ip:8005/transcreve-audios
```
## 🔍 Troubleshooting
Se encontrar problemas:

1. Verifique os logs dos containers:
```bash
docker-compose logs
```
2. Certifique-se de que o Redis está rodando e acessível.
3. Verifique se todas as configurações foram salvas corretamente na interface.


## 📖 **Configuração Detalhada das Variáveis**

### Variáveis Essenciais

| Variável               | Descrição                                                | Obrigatória | Exemplo                                                    |
|-----------------------|----------------------------------------------------------|-------------|----------------------------------------------------------|
| `GROQ_API_KEY`        | Chave da API GROQ (deve começar com 'gsk_')             | Sim         | `gsk_abc123...`                                           |

### Variáveis de Personalização

| Variável               | Descrição                                                | Padrão      | Exemplo                                                    |
|-----------------------|----------------------------------------------------------|-------------|----------------------------------------------------------|
| `BUSINESS_MESSAGE`    | Mensagem de rodapé após transcrição                      | Vazio       | `substitua_sua_mensagem_de_servico_aqui` |
| `PROCESS_GROUP_MESSAGES` | Habilita processamento de mensagens em grupos          | `false`     | `true` ou `false`
| `PROCESS_SELF_MESSAGES` | Habilita processamento de mensagens enviadas por você    | `true`     | `true` ou `false`                                                      |

### Variáveis de Debug e Log

| Variável               | Descrição                                                | Padrão      | Valores Possíveis                                          |
|-----------------------|----------------------------------------------------------|-------------|----------------------------------------------------------|
| `DEBUG_MODE`          | Ativa logs detalhados para debugging                     | `false`     | `true` ou `false`                                          |
| `LOG_LEVEL`           | Define o nível de detalhamento dos logs                  | `INFO`      | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`            |

---

## 🚀 **Métodos de Execução**
Usar sempre ao final do endereço definido o endpoint `/transcreve-audios` para que a API funcione.
### Execução Local
```bash
uvicorn main:app --host 0.0.0.0 --port 8005
```
### Endpoint para inserir no webhook da Evolution API para consumir o serviço
```bash
http://127.0.0.1:8005/transcreve-audios
```
1. Aponte um subomínio com o IP do seu servidor para a API da TranscreveZAP
2. Aponte um subomínio com o IP do seu servidor para o MANAGER da TranscreveZAP

### 🌟 Docker Swarm com Traefik
```yaml
version: "3.7"

services:
  tcaudio:
    image: impacteai/transcrevezap:latest
    networks:
      - sua_rede_externa # Substitua pelo nome da sua rede externa
    ports:
      - 8005:8005  # Porta para FastAPI
      - 8501:8501  # Porta para Streamlit
    environment:
      - UVICORN_PORT=8005
      - UVICORN_HOST=0.0.0.0
      - UVICORN_RELOAD=true
      - UVICORN_WORKERS=1
      - API_DOMAIN=seu.dominio.com   #coloque seu subdominio da API apontado aqui
      - DEBUG_MODE=false
      - LOG_LEVEL=INFO
      - MANAGER_USER=seu_usuario_admin   # Defina Usuário do Manager
      - MANAGER_PASSWORD=sua_senha_segura   # Defina Senha do Manager
      - REDIS_HOST=redis-transcrevezap
      - REDIS_PORT=6380 # Porta personalizada para o Redis do TranscreveZAP
    depends_on:
      - redis-transcrevezap
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      labels:
        - traefik.enable=true
        - traefik.http.routers.tcaudio.rule=Host(`seu.dominio.com`)   #coloque seu subdominio da API apontado aqui
        - traefik.http.routers.tcaudio.entrypoints=websecure
        - traefik.http.routers.tcaudio.tls.certresolver=letsencryptresolver
        - traefik.http.services.tcaudio.loadbalancer.server.port=8005
        - traefik.http.services.tcaudio.loadbalancer.passHostHeader=true
        - traefik.http.routers.tcaudio.service=tcaudio
        - traefik.http.middlewares.traefik-compress.compress=true
        - traefik.http.routers.tcaudio.middlewares=traefik-compress
        # Configuração do Streamlit
        - traefik.http.routers.tcaudio-manager.rule=Host(`manager.seu.dominio.com`)   #coloque seu subdominio do Manager apontado aqui
        - traefik.http.routers.tcaudio-manager.entrypoints=websecure
        - traefik.http.routers.tcaudio-manager.tls.certresolver=letsencryptresolver
        - traefik.http.services.tcaudio-manager.loadbalancer.server.port=8501
        - traefik.http.routers.tcaudio-manager.service=tcaudio-manager
    command: ./start.sh

  redis-transcrevezap:
    image: redis:6
    command: redis-server --port 6380 --appendonly yes
    volumes:
      - redis_transcrevezap_data:/data
    networks:
      - sua_rede_externa # Substitua pelo nome da sua rede externa

networks:
  sua_rede_externa:  # Substitua pelo nome da sua rede externa
    external: true
    name: sua_rede_externa  # Substitua pelo nome da sua rede externa

volumes:
  redis_transcrevezap_data:
    driver: local
```

### Endpoint para inserir no webhook da Evolution API para consumir o serviço
```bash
https://transcricaoaudio.seudominio.com.br/transcreve-audios

```
## 🔧 **Configuração do Traefik**

Para usar com Traefik, certifique-se de:
1. Ter o Traefik configurado em seu ambiente Docker Swarm
2. Configurar 2 DNS do seu domínio para apontar para a API e para o MANAGER
3. Ajustar as labels do Traefik conforme seu ambiente
4. Verificar se a rede externa existe no Docker Swarm
5. Utilize a stack de exemplo contida no projeto para guiar a instalação

## 📝 **Notas Importantes**
- A GROQ_API_KEY deve começar com 'gsk_'
- O BUSINESS_MESSAGE suporta formatação do WhatsApp (*negrito*, _itálico_)
- Para quebras de linha no BUSINESS_MESSAGE, use \n
- Em produção, recomenda-se DEBUG_MODE=false
- Configure LOG_LEVEL=DEBUG apenas para troubleshooting

## ✨ Novos Recursos na v2.1

### 🌍 Suporte Multilíngue
- Transcrição e resumo em 10+ idiomas
- Mudança instantânea de idioma
- Interface intuitiva para seleção de idioma
- Mantém consistência entre transcrição e resumo

### 🔄 Sistema Inteligente de Rodízio de Chaves
- Suporte a múltiplas chaves GROQ
- Balanceamento automático de carga
- Maior redundância e disponibilidade
- Gestão simplificada de chaves via interface

## 🌍 Sistema de Idiomas
O TranscreveZAP agora suporta transcrição e resumo em múltiplos idiomas. Na seção "Configurações", você pode:

1. Selecionar o idioma principal para transcrição e resumo
2. O sistema manterá Português como padrão se nenhum outro for selecionado
3. A mudança de idioma é aplicada instantaneamente após salvar

Idiomas suportados:
- 🇧🇷 Português (padrão)
- 🇺🇸 Inglês
- 🇪🇸 Espanhol
- 🇫🇷 Francês
- 🇩🇪 Alemão
- 🇮🇹 Italiano
- 🇯🇵 Japonês
- 🇰🇷 Coreano
- 🇨🇳 Chinês
- 🇷🇺 Russo

## 🔄 Sistema de Rodízio de Chaves GROQ
O TranscreveZAP agora suporta múltiplas chaves GROQ com sistema de rodízio automático para melhor distribuição de carga e redundância.

### Funcionalidades:
1. Adicione múltiplas chaves GROQ para distribuição de carga
2. O sistema alterna automaticamente entre as chaves disponíveis
3. Se uma chave falhar, o sistema usa a próxima disponível
4. Visualize todas as chaves configuradas no painel
5. Adicione ou remova chaves sem interromper o serviço

### Como Configurar:
1. Acesse a seção "Configurações"
2. Na área "🔑 Gerenciamento de Chaves GROQ":
   - Adicione a chave principal
   - Use "Adicionar Nova Chave GROQ" para incluir chaves adicionais
   - O sistema começará a usar todas as chaves em rodízio automaticamente

### Boas Práticas:
- Mantenha pelo menos duas chaves ativas para redundância
- Monitore o uso das chaves pelo painel administrativo
- Remova chaves expiradas ou inválidas
- Todas as chaves devem começar com 'gsk_'

## 🔍 **Troubleshooting**
Se encontrar problemas:
1. Verifique se todas as variáveis obrigatórias estão configuradas
2. Ative DEBUG_MODE=true temporariamente
3. Verifique os logs do container
4. Certifique-se que as APIs estão acessíveis

### Problemas com Múltiplas Chaves GROQ:
1. Verifique se todas as chaves começam com 'gsk_'
2. Confirme se as chaves estão ativas na console GROQ
3. Monitore os logs para identificar falhas específicas de chaves
4. Mantenha pelo menos uma chave válida no sistema

### Problemas com Idiomas:
1. Verifique se o idioma está corretamente selecionado nas configurações
2. Confirme se a configuração foi salva com sucesso
3. Reinicie o serviço se as alterações não forem aplicadas
4. Verifique os logs para confirmar o idioma em uso

## 📄 **Licença**
Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---
### AJUDE CONTRIBUINDO COM O PROJETO, FAÇA O PIX NO QR CODE
![PIX](./pix.jpeg)
---