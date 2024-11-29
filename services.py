import aiohttp
import base64
import aiofiles
from dotenv import load_dotenv
import os
from fastapi import HTTPException

# Carregar variáveis do .env
load_dotenv()


# Função assíncrona para converter base64 em arquivo temporário
async def convert_base64_to_file(base64_data):
    audio_data = base64.b64decode(base64_data)
    audio_file_path = "/tmp/audio_file.mp3"

    async with aiofiles.open(audio_file_path, "wb") as f:
        await f.write(audio_data)

    return audio_file_path


# Função assíncrona para resumir o texto se necessário
async def summarize_text_if_needed(text):

    url_completions = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json",
    }

    json_data = {
        "messages": [
            {
                "role": "user",
                "content": f"""
                    Entenda o contexto desse áudio e faça um resumo super enxuto sobre o que se trata.
                    Esse áudio foi enviado pelo whatsapp, de alguém, para Gabriel.  
                    Escreva APENAS o resumo do áudio como se fosse você que estivesse enviando 
                    essa mensagem!  Não comprimente, não de oi, não escreva nada antes nem depois 
                    do resumo, responda apenas um resumo enxuto do que foi falado no áudio.  
                    IMPORTANTE: Não faça esse resumo como se fosse um áudio que uma terceira 
                    pessoa enviou, não diga coisas como 'a pessoa está falando...' etc. 
                    Escreva o resumo com base nessa mensagem do áudio, 
                    como se você estivesse escrevendo esse resumo e enviando em 
                    texto pelo whatsapp: {text}""",
            }
        ],
        "model": "llama-3.2-90b-text-preview",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url_completions,
            headers=headers,
            json=json_data,
        ) as summary_response:
            if summary_response.status == 200:
                summary_result = await summary_response.json()
                summary_text = summary_result["choices"][0]["message"]["content"]
                return summary_text
            else:
                raise Exception("Erro ao resumir o texto")


# Função assíncrona para transcrever o áudio
async def transcribe_audio(audio_file):
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers=headers,
            data={
                "file": open(audio_file, "rb"),
                "model": "whisper-large-v3",
                "language": "pt",
            },
        ) as response:

            is_summary = False
            if response.status == 200:
                result = await response.json()
                message = result.get("text", "")

                if len(message) > 600:
                    is_summary = True
                    message = await summarize_text_if_needed(message)

                return message, is_summary
            else:
                raise Exception("Erro ao transcrever o áudio")


def get_body_message_to_whatsapp_v2(message, remote_jid, message_id):
    return {
        "number": remote_jid,
        "text": message,
        "quoted": {"key": {"remoteJid": remote_jid, "fromMe": False, "id": message_id}},
    }


def get_body_message_to_whatsapp_v1(message, remote_jid):
    return {
        "number": remote_jid,
        "options": {"delay": 1200, "presence": "composing", "linkPreview": False},
        "textMessage": {"text": message},
    }


async def call_whatsapp(url, body, headers):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as response:
            if response.status not in [200, 201]:
                print(f"Erro ao enviar mensagem via WhatsApp: {await response.text()}")
                return False


# Função assíncrona para enviar a mensagem de resumo via WhatsApp
async def send_message_to_whatsapp(
    server_url, instance, apikey, message, remote_jid, message_id
):
    url = f"{server_url}/message/sendText/{instance}"
    headers = {"apikey": apikey}

    # Tentar enviar na V1
    body = get_body_message_to_whatsapp_v1(message, remote_jid)
    result = await call_whatsapp(url, body, headers)

    # Se falhar, monta novo body na V2 e reenvia
    if not result:
        body = get_body_message_to_whatsapp_v2(message, remote_jid, message_id)
        await call_whatsapp(url, body, headers)


# Função para obter o áudio em Base64 via API do WhatsApp
async def get_audio_base64(server_url, instance, apikey, message_id):
    url = f"{server_url}/chat/getBase64FromMediaMessage/{instance}"
    headers = {"apikey": apikey}
    body = {"message": {"key": {"id": message_id}}, "convertToMp4": False}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as response:
            if response.status in [200, 201]:
                result = await response.json()
                return result.get("base64", "")
            else:
                raise HTTPException(
                    status_code=500, detail="Falha ao obter áudio em base64"
                )
