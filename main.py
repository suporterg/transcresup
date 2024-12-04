from fastapi import FastAPI, Request, HTTPException
from services import (
    convert_base64_to_file,
    transcribe_audio,
    send_message_to_whatsapp,
    get_audio_base64,
)
from models import WebhookRequest
import aiohttp
from config import settings, logger

app = FastAPI()

@app.post("/transcreve-audios")
async def transcreve_audios(request: Request):
    try:
        logger.info("Iniciando processamento de áudio")
        body = await request.json()
        
        if settings.DEBUG_MODE:
            logger.debug(f"Payload recebido: {body}")

        # Extraindo informações
        server_url = body["server_url"]
        instance = body["instance"]
        apikey = body["apikey"]
        audio_key = body["data"]["key"]["id"]
        from_me = body["data"]["key"]["fromMe"]
        remote_jid = body["data"]["key"]["remoteJid"]
        message_type = body["data"]["messageType"]
        
        if "audioMessage" not in message_type:
            logger.info("Mensagem recebida não é um áudio, ignorando")
            return {"message": "Mensagem recebida não é um áudio"}

        if from_me:
            logger.info("Mensagem enviada pelo próprio usuário, ignorando")
            return {"message": "Mensagem enviada por mim, sem operação"}

        if "@g.us" in remote_jid and not settings.PROCESS_GROUP_MESSAGES:
            logger.info("Mensagem de grupo ignorada conforme configuração")
            return {"message": "Mensagem enviada por um grupo, sem operação"}

        # Verificar se temos mediaUrl ou precisamos pegar o base64
        if "mediaUrl" in body["data"]["message"]:
            audio_source = body["data"]["message"]["mediaUrl"]
            logger.debug(f"Usando mediaUrl: {audio_source}")
        else:
            logger.debug("MediaUrl não encontrada, obtendo áudio via base64")
            base64_audio = await get_audio_base64(server_url, instance, apikey, audio_key)
            audio_source = await convert_base64_to_file(base64_audio)
            logger.debug(f"Áudio convertido e salvo em: {audio_source}")

        # Transcrever o áudio
        transcription_text, is_summary = await transcribe_audio(audio_source)

        header_message = (
            "*Resumo do áudio:*\n\n" if is_summary else "*Transcrição desse áudio:*\n\n"
        )

        # Formatar o conteúdo da mensagem
        summary_message = f"{header_message}{transcription_text}\n\n{settings.BUSINESS_MESSAGE}"
        logger.debug(f"Mensagem formatada: {summary_message[:100]}...")

        # Enviar o resumo transcrito de volta via WhatsApp
        await send_message_to_whatsapp(
            server_url,
            instance,
            apikey,
            summary_message,
            remote_jid,
            audio_key,
        )

        logger.info("Áudio processado e resposta enviada com sucesso")
        return {"message": "Áudio transcrito e resposta enviada com sucesso"}

    except Exception as e:
        logger.error(f"Erro ao processar áudio: {str(e)}", exc_info=settings.DEBUG_MODE)
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao processar a requisição: {str(e)}"
        )
