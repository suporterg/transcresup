import aiohttp
import base64
import aiofiles
from fastapi import HTTPException
from config import settings, logger

async def convert_base64_to_file(base64_data):
    """Converte dados base64 em arquivo temporário"""
    try:
        logger.debug("Iniciando conversão de base64 para arquivo")
        audio_data = base64.b64decode(base64_data)
        audio_file_path = "/tmp/audio_file.mp3"

        async with aiofiles.open(audio_file_path, "wb") as f:
            await f.write(audio_data)
        
        logger.debug(f"Arquivo temporário criado em: {audio_file_path}")
        return audio_file_path
    except Exception as e:
        logger.error(f"Erro na conversão base64: {str(e)}", exc_info=settings.DEBUG_MODE)
        raise

async def summarize_text_if_needed(text):
    """Resumir texto usando a API GROQ"""
    logger.debug("Iniciando processo de resumo do texto")
    
    url_completions = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    json_data = {
        "messages": [{
            "role": "user",
            "content": f"""
                Entenda o contexto desse áudio e faça um resumo super enxuto sobre o que se trata, coloque os pontos relevantes e mais importantes no resumo de forma muito curta.
                Esse áudio foi enviado pelo whatsapp, de alguém, para Gabriel.  
                Escreva APENAS o resumo do áudio como se fosse você que estivesse enviando 
                essa mensagem!  Não comprimente, não de oi, não escreva nada antes nem depois 
                do resumo, responda apenas um resumo enxuto do que foi falado no áudio.  
                IMPORTANTE: Não faça esse resumo como se fosse um áudio que uma terceira 
                pessoa enviou, não diga coisas como 'a pessoa está falando...' etc. 
                Escreva o resumo com base nessa mensagem do áudio, 
                como se você estivesse escrevendo esse resumo e enviando em 
                texto pelo whatsapp: {text}""",
        }],
        "model": "llama-3.2-90b-vision-preview",
    }

    try:
        async with aiohttp.ClientSession() as session:
            logger.debug("Enviando requisição para API GROQ")
            async with session.post(url_completions, headers=headers, json=json_data) as summary_response:
                if summary_response.status == 200:
                    summary_result = await summary_response.json()
                    summary_text = summary_result["choices"][0]["message"]["content"]
                    logger.info("Resumo gerado com sucesso")
                    logger.debug(f"Resumo: {summary_text[:100]}...")
                    return summary_text
                else:
                    error_text = await summary_response.text()
                    logger.error(f"Erro na API GROQ: {error_text}")
                    raise Exception(f"Erro ao resumir o texto: {error_text}")
    except Exception as e:
        logger.error(f"Erro no processo de resumo: {str(e)}", exc_info=settings.DEBUG_MODE)
        raise

async def transcribe_audio(audio_source, apikey=None):
    """Transcreve áudio usando a API GROQ"""
    logger.info("Iniciando processo de transcrição")
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    groq_headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            # Se o audio_source for uma URL
            if isinstance(audio_source, str) and audio_source.startswith('http'):
                logger.debug(f"Baixando áudio da URL: {audio_source}")
                download_headers = {"apikey": apikey} if apikey else {}
                
                async with session.get(audio_source, headers=download_headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Erro no download do áudio: Status {response.status}, Resposta: {error_text}")
                        raise Exception(f"Erro ao baixar áudio: {error_text}")
                    
                    audio_data = await response.read()
                    temp_file = "/tmp/audio_from_url.mp3"
                    async with aiofiles.open(temp_file, "wb") as f:
                        await f.write(audio_data)
                    audio_source = temp_file
                    logger.debug(f"Áudio salvo temporariamente em: {temp_file}")

            # Preparar dados para transcrição
            data = aiohttp.FormData()
            data.add_field('file', open(audio_source, 'rb'), filename='audio.mp3')
            data.add_field('model', 'whisper-large-v3')
            data.add_field('language', 'pt')

            logger.debug("Enviando áudio para transcrição")
            async with session.post(url, headers=groq_headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    message = result.get("text", "")
                    logger.info("Transcrição concluída com sucesso")
                    logger.debug(f"Texto transcrito: {message[:100]}...")

                    is_summary = False
                    if len(message) > 1000:
                        logger.debug("Texto longo detectado, iniciando resumo")
                        is_summary = True
                        message = await summarize_text_if_needed(message)

                    return message, is_summary
                else:
                    error_text = await response.text()
                    logger.error(f"Erro na transcrição: {error_text}")
                    raise Exception(f"Erro na transcrição: {error_text}")

    except Exception as e:
        logger.error(f"Erro no processo de transcrição: {str(e)}", exc_info=settings.DEBUG_MODE)
        raise

async def send_message_to_whatsapp(server_url, instance, apikey, message, remote_jid, message_id):
    """Envia mensagem via WhatsApp"""
    logger.debug(f"Preparando envio de mensagem para: {remote_jid}")
    url = f"{server_url}/message/sendText/{instance}"
    headers = {"apikey": apikey}

    try:
        # Tentar enviar na V1
        body = get_body_message_to_whatsapp_v1(message, remote_jid)
        logger.debug("Tentando envio no formato V1")
        result = await call_whatsapp(url, body, headers)

        # Se falhar, tenta V2
        if not result:
            logger.debug("Formato V1 falhou, tentando formato V2")
            body = get_body_message_to_whatsapp_v2(message, remote_jid, message_id)
            await call_whatsapp(url, body, headers)
            
        logger.info("Mensagem enviada com sucesso")
    except Exception as e:
        logger.error(f"Erro no envio da mensagem: {str(e)}", exc_info=settings.DEBUG_MODE)
        raise

def get_body_message_to_whatsapp_v1(message, remote_jid):
    """Formata mensagem no formato V1"""
    return {
        "number": remote_jid,
        "options": {"delay": 1200, "presence": "composing", "linkPreview": False},
        "textMessage": {"text": message},
    }

def get_body_message_to_whatsapp_v2(message, remote_jid, message_id):
    """Formata mensagem no formato V2"""
    return {
        "number": remote_jid,
        "text": message,
        "quoted": {"key": {"remoteJid": remote_jid, "fromMe": False, "id": message_id}},
    }

async def call_whatsapp(url, body, headers):
    """Realiza chamada à API do WhatsApp"""
    try:
        async with aiohttp.ClientSession() as session:
            logger.debug(f"Enviando requisição para: {url}")
            async with session.post(url, json=body, headers=headers) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.error(f"Erro na API do WhatsApp: Status {response.status}, Resposta: {error_text}")
                    return False
                logger.debug("Requisição bem-sucedida")
                return True
    except Exception as e:
        logger.error(f"Erro na chamada WhatsApp: {str(e)}", exc_info=settings.DEBUG_MODE)
        return False

async def get_audio_base64(server_url, instance, apikey, message_id):
    """Obtém áudio em Base64 via API do WhatsApp"""
    logger.debug(f"Obtendo áudio base64 para mensagem: {message_id}")
    url = f"{server_url}/chat/getBase64FromMediaMessage/{instance}"
    headers = {"apikey": apikey}
    body = {"message": {"key": {"id": message_id}}, "convertToMp4": False}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info("Áudio base64 obtido com sucesso")
                    return result.get("base64", "")
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao obter áudio base64: {error_text}")
                    raise HTTPException(status_code=500, detail="Falha ao obter áudio em base64")
    except Exception as e:
        logger.error(f"Erro na obtenção do áudio base64: {str(e)}", exc_info=settings.DEBUG_MODE)
        raise