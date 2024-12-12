from fastapi import FastAPI, Request, HTTPException
from services import (
    convert_base64_to_file,
    transcribe_audio,
    send_message_to_whatsapp,
    get_audio_base64,
    summarize_text_if_needed,
)
from models import WebhookRequest
from config import logger, settings, redis_client
from storage import StorageHandler
import traceback
import os

app = FastAPI()
storage = StorageHandler()
@app.on_event("startup")
async def startup_event():
    api_domain = os.getenv("API_DOMAIN", "seu.dominio.com")
    redis_client.set("API_DOMAIN", api_domain)
# Função para buscar configurações do Redis com fallback para valores padrão
def get_config(key, default=None):
    try:
        value = redis_client.get(key)
        if value is None:
            logger.warning(f"Configuração '{key}' não encontrada no Redis. Usando padrão: {default}")
            return default
        return value
    except Exception as e:
        logger.error(f"Erro ao acessar Redis: {e}")
        return default

# Carregando configurações dinâmicas do Redis
def load_dynamic_settings():
    return {
        "GROQ_API_KEY": get_config("GROQ_API_KEY", "default_key"),
        "BUSINESS_MESSAGE": get_config("BUSINESS_MESSAGE", "*Impacte AI* Premium Services"),
        "PROCESS_GROUP_MESSAGES": get_config("PROCESS_GROUP_MESSAGES", "false") == "true",
        "PROCESS_SELF_MESSAGES": get_config("PROCESS_SELF_MESSAGES", "true") == "true",
        "DEBUG_MODE": get_config("DEBUG_MODE", "false") == "true",
    }

@app.post("/transcreve-audios")
async def transcreve_audios(request: Request):
    try:
        body = await request.json()
        dynamic_settings = load_dynamic_settings()

        # Log inicial da requisição
        storage.add_log("INFO", "Nova requisição de transcrição recebida", {
            "instance": body.get("instance"),
            "event": body.get("event")
        })

        if dynamic_settings["DEBUG_MODE"]:
            storage.add_log("DEBUG", "Payload completo recebido", {
                "body": body
            })

        # Extraindo informações
        server_url = body["server_url"]
        instance = body["instance"]
        apikey = body["apikey"]
        audio_key = body["data"]["key"]["id"]
        from_me = body["data"]["key"]["fromMe"]
        remote_jid = body["data"]["key"]["remoteJid"]
        message_type = body["data"]["messageType"]

        # Verificação de tipo de mensagem
        if "audioMessage" not in message_type:
            storage.add_log("INFO", "Mensagem ignorada - não é áudio", {
                "message_type": message_type,
                "remote_jid": remote_jid
            })
            return {"message": "Mensagem recebida não é um áudio"}

        # Verificação de permissões
        if not storage.can_process_message(remote_jid):
            is_group = "@g.us" in remote_jid
            storage.add_log("INFO", 
                "Mensagem não autorizada para processamento",
                {
                    "remote_jid": remote_jid,
                    "tipo": "grupo" if is_group else "usuário",
                    "motivo": "grupo não permitido" if is_group else "usuário bloqueado"
                }
            )
            return {"message": "Mensagem não autorizada para processamento"}

        if from_me and not dynamic_settings["PROCESS_SELF_MESSAGES"]:
            storage.add_log("INFO", "Mensagem própria ignorada", {
                "remote_jid": remote_jid
            })
            return {"message": "Mensagem enviada por mim, sem operação"}

        # Obter áudio
        try:
            if "mediaUrl" in body["data"]["message"]:
                audio_source = body["data"]["message"]["mediaUrl"]
                storage.add_log("DEBUG", "Usando mediaUrl para áudio", {
                    "mediaUrl": audio_source
                })
            else:
                storage.add_log("DEBUG", "Obtendo áudio via base64")
                base64_audio = await get_audio_base64(server_url, instance, apikey, audio_key)
                audio_source = await convert_base64_to_file(base64_audio)
                storage.add_log("DEBUG", "Áudio convertido", {
                    "source": audio_source
                })

            # Transcrever áudio
            storage.add_log("INFO", "Iniciando transcrição")
            transcription_text, _ = await transcribe_audio(audio_source)
            
            # Resumir se necessário
            summary_text = await summarize_text_if_needed(transcription_text)
            
            # Formatar mensagem
            summary_message = (
                f"🤖 *Resumo do áudio:*\n\n"
                f"{summary_text}\n\n"
                f"🔊 *Transcrição do áudio:*\n\n"
                f"{transcription_text}\n\n"
                f"{dynamic_settings['BUSINESS_MESSAGE']}"
            )

            # Enviar resposta
            await send_message_to_whatsapp(
                server_url,
                instance,
                apikey,
                summary_message,
                remote_jid,
                audio_key,
            )

            # Registrar sucesso
            storage.record_processing(remote_jid)
            storage.add_log("INFO", "Áudio processado com sucesso", {
                "remote_jid": remote_jid,
                "transcription_length": len(transcription_text),
                "summary_length": len(summary_text)
            })

            return {"message": "Áudio transcrito e resposta enviada com sucesso"}

        except Exception as e:
            storage.add_log("ERROR", f"Erro ao processar áudio: {str(e)}", {
                "error_type": type(e).__name__,
                "remote_jid": remote_jid,
                "traceback": traceback.format_exc()
            })
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao processar áudio: {str(e)}"
            )

    except Exception as e:
        storage.add_log("ERROR", f"Erro na requisição: {str(e)}", {
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar a requisição: {str(e)}"
        )