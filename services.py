import aiohttp
import base64
import aiofiles
from fastapi import HTTPException
from config import settings, logger, redis_client
from storage import StorageHandler
import os
import json
import tempfile

# Inicializa o storage handler
storage = StorageHandler()

async def convert_base64_to_file(base64_data):
    """Converte dados base64 em arquivo temporário"""
    try:
        storage.add_log("DEBUG", "Iniciando conversão de base64 para arquivo")
        audio_data = base64.b64decode(base64_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(audio_data)
            audio_file_path = temp_file.name
        
        storage.add_log("DEBUG", "Arquivo temporário criado", {
            "path": audio_file_path
        })
        return audio_file_path
    except Exception as e:
        storage.add_log("ERROR", "Erro na conversão base64", {
            "error": str(e),
            "type": type(e).__name__
        })
        raise

async def summarize_text_if_needed(text):
    """Resumir texto usando a API GROQ"""
    storage.add_log("DEBUG", "Iniciando processo de resumo", {
        "text_length": len(text)
    })
    
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
        "model": "llama-3.3-70b-versatile",
    }

    try:
        async with aiohttp.ClientSession() as session:
            storage.add_log("DEBUG", "Enviando requisição para API GROQ")
            async with session.post(url_completions, headers=headers, json=json_data) as summary_response:
                if summary_response.status == 200:
                    summary_result = await summary_response.json()
                    summary_text = summary_result["choices"][0]["message"]["content"]
                    storage.add_log("INFO", "Resumo gerado com sucesso", {
                        "original_length": len(text),
                        "summary_length": len(summary_text)
                    })
                    return summary_text
                else:
                    error_text = await summary_response.text()
                    storage.add_log("ERROR", "Erro na API GROQ", {
                        "error": error_text,
                        "status": summary_response.status
                    })
                    raise Exception(f"Erro ao resumir o texto: {error_text}")
    except Exception as e:
        storage.add_log("ERROR", "Erro no processo de resumo", {
            "error": str(e),
            "type": type(e).__name__
        })
        raise

async def transcribe_audio(audio_source, apikey=None):
    """Transcreve áudio usando a API GROQ"""
    storage.add_log("INFO", "Iniciando processo de transcrição")
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    groq_headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

    try:
        async with aiohttp.ClientSession() as session:
            # Se o audio_source for uma URL
            if isinstance(audio_source, str) and audio_source.startswith('http'):
                storage.add_log("DEBUG", "Baixando áudio da URL", {
                    "url": audio_source
                })
                download_headers = {"apikey": apikey} if apikey else {}
                
                async with session.get(audio_source, headers=download_headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        storage.add_log("ERROR", "Erro no download do áudio", {
                            "status": response.status,
                            "error": error_text
                        })
                        raise Exception(f"Erro ao baixar áudio: {error_text}")
                    
                    audio_data = await response.read()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                        temp_file.write(audio_data)
                        audio_source = temp_file.name
                    storage.add_log("DEBUG", "Áudio salvo temporariamente", {
                        "path": audio_source
                    })

            # Preparar dados para transcrição
            data = aiohttp.FormData()
            data.add_field('file', open(audio_source, 'rb'), filename='audio.mp3')
            data.add_field('model', 'whisper-large-v3')
            data.add_field('language', 'pt')

            storage.add_log("DEBUG", "Enviando áudio para transcrição")
            async with session.post(url, headers=groq_headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    message = result.get("text", "")
                    storage.add_log("INFO", "Transcrição concluída com sucesso", {
                        "text_length": len(message)
                    })

                    is_summary = False
                    if len(message) > 1000:
                        storage.add_log("DEBUG", "Texto longo detectado, iniciando resumo", {
                            "text_length": len(message)
                        })
                        is_summary = True
                        message = await summarize_text_if_needed(message)

                    return message, is_summary
                else:
                    error_text = await response.text()
                    storage.add_log("ERROR", "Erro na transcrição", {
                        "error": error_text,
                        "status": response.status
                    })
                    raise Exception(f"Erro na transcrição: {error_text}")

    except Exception as e:
        storage.add_log("ERROR", "Erro no processo de transcrição", {
            "error": str(e),
            "type": type(e).__name__
        })
        raise
    finally:
        # Limpar arquivos temporários
        if isinstance(audio_source, str) and os.path.exists(audio_source):
            os.unlink(audio_source)

async def send_message_to_whatsapp(server_url, instance, apikey, message, remote_jid, message_id):
    """Envia mensagem via WhatsApp"""
    storage.add_log("DEBUG", "Preparando envio de mensagem", {
        "remote_jid": remote_jid,
        "instance": instance
    })
    url = f"{server_url}/message/sendText/{instance}"
    headers = {"apikey": apikey}

    try:
        # Tentar enviar na V1
        body = get_body_message_to_whatsapp_v1(message, remote_jid)
        storage.add_log("DEBUG", "Tentando envio no formato V1")
        result = await call_whatsapp(url, body, headers)

        # Se falhar, tenta V2
        if not result:
            storage.add_log("DEBUG", "Formato V1 falhou, tentando formato V2")
            body = get_body_message_to_whatsapp_v2(message, remote_jid, message_id)
            await call_whatsapp(url, body, headers)
            
        storage.add_log("INFO", "Mensagem enviada com sucesso", {
            "remote_jid": remote_jid
        })
    except Exception as e:
        storage.add_log("ERROR", "Erro no envio da mensagem", {
            "error": str(e),
            "type": type(e).__name__,
            "remote_jid": remote_jid
        })
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
            storage.add_log("DEBUG", "Enviando requisição para WhatsApp", {
                "url": url
            })
            async with session.post(url, json=body, headers=headers) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    storage.add_log("ERROR", "Erro na API do WhatsApp", {
                        "status": response.status,
                        "error": error_text
                    })
                    return False
                storage.add_log("DEBUG", "Requisição bem-sucedida")
                return True
    except Exception as e:
        storage.add_log("ERROR", "Erro na chamada WhatsApp", {
            "error": str(e),
            "type": type(e).__name__
        })
        return False

async def get_audio_base64(server_url, instance, apikey, message_id):
    """Obtém áudio em Base64 via API do WhatsApp"""
    storage.add_log("DEBUG", "Obtendo áudio base64", {
        "message_id": message_id,
        "instance": instance
    })
    url = f"{server_url}/chat/getBase64FromMediaMessage/{instance}"
    headers = {"apikey": apikey}
    body = {"message": {"key": {"id": message_id}}, "convertToMp4": False}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    storage.add_log("INFO", "Áudio base64 obtido com sucesso")
                    return result.get("base64", "")
                else:
                    error_text = await response.text()
                    storage.add_log("ERROR", "Erro ao obter áudio base64", {
                        "status": response.status,
                        "error": error_text
                    })
                    raise HTTPException(status_code=500, detail="Falha ao obter áudio em base64")
    except Exception as e:
        storage.add_log("ERROR", "Erro na obtenção do áudio base64", {
            "error": str(e),
            "type": type(e).__name__,
            "message_id": message_id
        })
        raise