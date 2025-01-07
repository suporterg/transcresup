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

async def get_groq_key():
    """Obtém a próxima chave GROQ do sistema de rodízio."""
    key = storage.get_next_groq_key()
    if not key:
        raise HTTPException(
            status_code=500,
            detail="Nenhuma chave GROQ configurada. Configure pelo menos uma chave no painel administrativo."
        )
    return key

async def summarize_text_if_needed(text):
    """Resumir texto usando a API GROQ com sistema de rodízio de chaves"""
    storage.add_log("DEBUG", "Iniciando processo de resumo", {
        "text_length": len(text)
    })
    
    # Obter idioma configurado
    language = redis_client.get("TRANSCRIPTION_LANGUAGE") or "pt"
    storage.add_log("DEBUG", "Idioma configurado para resumo", {
    "language": language,
    "redis_value": redis_client.get("TRANSCRIPTION_LANGUAGE")
    })
    url_completions = "https://api.groq.com/openai/v1/chat/completions"
    groq_key = await get_groq_key()
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
    }
    
    # Adaptar o prompt para considerar o idioma
    prompt_by_language = {
        "pt": """
            Entenda o contexto desse áudio e faça um resumo super enxuto sobre o que se trata.
            Esse áudio foi enviado pelo whatsapp, de alguém, para Fabio.  
            Escreva APENAS o resumo do áudio como se fosse você que estivesse enviando 
            essa mensagem! Não cumprimente, não de oi, não escreva nada antes nem depois 
            do resumo, responda apenas um resumo enxuto do que foi falado no áudio.
            """,
        "en": """
            Understand the context of this audio and make a very concise summary of what it's about.
            This audio was sent via WhatsApp, from someone, to Fabio.
            Write ONLY the summary of the audio as if you were sending this message yourself!
            Don't greet, don't say hi, don't write anything before or after the summary,
            respond with just a concise summary of what was said in the audio.
            """,
        "es": """
            Entiende el contexto de este audio y haz un resumen muy conciso sobre de qué se trata. 
            Este audio fue enviado por WhatsApp, de alguien, para Fabio. 
            Escribe SOLO el resumen del audio como si tú estuvieras enviando este mensaje. 
            No saludes, no escribas nada antes ni después del resumen, responde únicamente un resumen conciso de lo dicho en el audio.
            """,
        "fr": """
            Comprenez le contexte de cet audio et faites un résumé très concis de ce dont il s'agit. 
            Cet audio a été envoyé via WhatsApp, par quelqu'un, à Fabio. 
            Écrivez UNIQUEMENT le résumé de l'audio comme si c'était vous qui envoyiez ce message. 
            Ne saluez pas, n'écrivez rien avant ou après le résumé, répondez seulement par un résumé concis de ce qui a été dit dans l'audio.
            """,
        "de": """
            Verstehen Sie den Kontext dieses Audios und erstellen Sie eine sehr kurze Zusammenfassung, worum es geht. 
            Dieses Audio wurde über WhatsApp von jemandem an Fabio gesendet. 
            Schreiben Sie NUR die Zusammenfassung des Audios, als ob Sie diese Nachricht senden würden. 
            Grüßen Sie nicht, schreiben Sie nichts vor oder nach der Zusammenfassung, antworten Sie nur mit einer kurzen Zusammenfassung dessen, was im Audio gesagt wurde.
            """,
        "it": """
            Comprendi il contesto di questo audio e fai un riassunto molto conciso di cosa si tratta. 
            Questo audio è stato inviato tramite WhatsApp, da qualcuno, a Fabio. 
            Scrivi SOLO il riassunto dell'audio come se fossi tu a inviare questo messaggio. 
            Non salutare, non scrivere nulla prima o dopo il riassunto, rispondi solo con un riassunto conciso di ciò che è stato detto nell'audio.
            """,
        "ja": """
            この音声の内容を理解し、それが何について話されているのかを非常に簡潔に要約してください。
            この音声は、誰かがWhatsAppでファビオに送ったものです。
            あなたがそのメッセージを送っているように、音声の要約だけを記述してください。
            挨拶や前置き、後書きは書かず、音声で話された内容の簡潔な要約のみを返信してください。
            """,
        "ko": """
            이 오디오의 맥락을 이해하고, 무엇에 관한 것인지 매우 간략하게 요약하세요.
            이 오디오는 누군가가 WhatsApp을 통해 Fabio에게 보낸 것입니다.
            마치 당신이 메시지를 보내는 것처럼 오디오의 요약만 작성하세요.
            인사하거나, 요약 전후로 아무것도 쓰지 말고, 오디오에서 말한 내용을 간략하게 요약한 답변만 하세요.
            """,
        "zh": """
            理解这个音频的上下文，并简洁地总结它的内容。
            这个音频是某人通过WhatsApp发送给Fabio的。
            请仅以摘要的形式回答，就好像是你在发送这条消息。
            不要问候，也不要在摘要前后写任何内容，只需用一句简短的话总结音频中所说的内容。
            """,
        "ro": """
            Înțelege contextul acestui audio și creează un rezumat foarte concis despre ce este vorba. 
            Acest audio a fost trimis prin WhatsApp, de cineva, către Fabio. 
            Scrie DOAR rezumatul audio-ului ca și cum tu ai trimite acest mesaj. 
            Nu saluta, nu scrie nimic înainte sau după rezumat, răspunde doar cu un rezumat concis despre ce s-a spus în audio.
            """,

        "ru": """
            Поймите контекст этого аудио и сделайте очень краткое резюме, о чем идет речь. 
            Это аудио было отправлено через WhatsApp кем-то Фабио. 
            Напишите ТОЛЬКО резюме аудио, как будто вы отправляете это сообщение. 
            Не приветствуйте, не пишите ничего до или после резюме, ответьте только кратким резюме того, что говорилось в аудио.
            """
    }
    
    # Usar o prompt do idioma configurado ou fallback para português
    base_prompt = prompt_by_language.get(language, prompt_by_language["pt"])
    json_data = {
        "messages": [{
            "role": "user",
            "content": f"{base_prompt}\n\nTexto para resumir: {text}",
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
                        "summary_length": len(summary_text),
                        "language": language
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
    """
    Transcreve áudio usando a API GROQ com sistema de rodízio de chaves.
    
    Args:
        audio_source: Caminho do arquivo de áudio ou URL
        apikey: Chave da API opcional para download de áudio
        
    Returns:
        tuple: (texto_transcrito, False)
    """
    storage.add_log("INFO", "Iniciando processo de transcrição")
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    groq_key = await get_groq_key()
    groq_headers = {"Authorization": f"Bearer {groq_key}"}
    
    # Obter idioma configurado
    language = redis_client.get("TRANSCRIPTION_LANGUAGE") or "pt"
    storage.add_log("DEBUG", "Idioma configurado para transcrição", {
        "language": language,
        "redis_value": redis_client.get("TRANSCRIPTION_LANGUAGE")
    })
    
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
            data.add_field('language', language)

            storage.add_log("DEBUG", "Enviando áudio para transcrição")
            async with session.post(url, headers=groq_headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    transcription = result.get("text", "")
                    storage.add_log("INFO", "Transcrição concluída com sucesso", {
                        "text_length": len(transcription)
                    })
                    
                    return transcription, False
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