from fastapi import FastAPI, Request, HTTPException
from services import (
    convert_base64_to_file,
    transcribe_audio,
    send_message_to_whatsapp,
    get_audio_base64,
)
from models import WebhookRequest
import aiohttp
from dotenv import load_dotenv
import os

# Carregar variáveis do .env
load_dotenv()

app = FastAPI()


@app.post("/transcreve-audios")
async def transcreve_audios(request: Request):
    try:
        # Receber o corpo do webhook
        body = await request.json()

        # Extraindo informações necessárias do JSON
        server_url = body["server_url"]
        instance = body["instance"]  # os.getenv("WHATSAPP_INSTANCE")
        apikey = body["apikey"]  # os.getenv("WHATSAPP_API_KEY")
        audio_key = body["data"]["key"]["id"]
        from_me = body["data"]["key"]["fromMe"]
        remote_jid = body["data"]["key"]["remoteJid"]

        # Verificar se a mensagem foi enviada por mim
        if from_me:
            return {"message": "Mensagem enviada por mim, sem operação"}

        # Verifica se a mensagem é de um grupo
        if "@g.us" in remote_jid:
            return {"message": "Mensagem enviada por um grupo, sem operação"}

        if "base64" not in body:

            # Pega o áudio em Base64
            base64_audio = await get_audio_base64(
                server_url, instance, apikey, audio_key
            )

        else:
            base64_audio = body["data"]["message"]["base64"]

        # Converter Base64 para arquivo de áudio
        audio_file = await convert_base64_to_file(base64_audio)

        # Transcrever o áudio usando o modelo da API externa
        transcription_text, is_summary = await transcribe_audio(audio_file)

        header_message = (
            "*Resumo do áudio:*\n\n" if is_summary else "*Transcrição desse áudio:*\n\n"
        )

        # Formatar o conteúdo da mensagem
        summary_message = f"{header_message}{transcription_text}"

        # Enviar o resumo transcrito de volta via WhatsApp

        await send_message_to_whatsapp(
            server_url,
            instance,
            apikey,
            summary_message,
            body["data"]["key"]["remoteJid"],
            audio_key,
        )

        return {"message": "Áudio transcrito e resposta enviada com sucesso"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar a requisição: {str(e)}"
        )
