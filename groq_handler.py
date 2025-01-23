import aiohttp
import json
from typing import Optional, Tuple
from datetime import datetime

async def test_groq_key(key: str) -> bool:
    """Teste se uma chave GROQ é válida e está funcionando."""
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {key}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return bool(data.get("data"))
                return False
    except Exception:
        return False

async def validate_transcription_response(response_text: str) -> bool:
    """Valide se a resposta da transcrição é significativa."""
    try:
        # Remove common whitespace and punctuation
        cleaned_text = response_text.strip()
        # Check minimum content length (adjustable threshold)
        return len(cleaned_text) >= 10
    except Exception:
        return False

async def get_working_groq_key(storage) -> Optional[str]:
    """Obtenha uma chave GROQ funcional do pool disponível."""
    keys = storage.get_groq_keys()
    
    for _ in range(len(keys)):  # Try each key once
        key = storage.get_next_groq_key()
        if key and await test_groq_key(key):
            return key
            
    storage.add_log("ERROR", "No working GROQ keys available")
    return None

async def handle_groq_request(url: str, headers: dict, data, storage, is_form_data: bool = False) -> Tuple[bool, dict, str]:
    """
    Handle GROQ API request with retries and key rotation.
    Suporta tanto JSON quanto FormData.
    Returns: (success, response_data, error_message)
    """
    max_retries = len(storage.get_groq_keys())
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                if is_form_data:
                    async with session.post(url, headers=headers, data=data) as response:
                        response_data = await response.json()
                else:
                    async with session.post(url, headers=headers, json=data) as response:
                        response_data = await response.json()
                
                if response.status == 200:
                    # Validate response content
                    if "choices" in response_data and response_data["choices"]:
                        content = response_data["choices"][0].get("message", {}).get("content")
                        if content and await validate_transcription_response(content):
                            return True, response_data, ""
                
                # Handle specific error cases
                error_msg = response_data.get("error", {}).get("message", "")
                if "organization_restricted" in error_msg or "invalid_api_key" in error_msg:
                    # Try next key
                    new_key = await get_working_groq_key(storage)
                    if new_key:
                        headers["Authorization"] = f"Bearer {new_key}"
                        storage.add_log("INFO", "Tentando nova chave GROQ após erro", {
                            "error": error_msg,
                            "attempt": attempt + 1
                        })
                        continue
                
                return False, {}, f"API Error: {error_msg}"
                
        except Exception as e:
            # Tratamento específico para erros de conexão
            if "Connection" in str(e) and attempt < max_retries - 1:
                storage.add_log("WARNING", "Erro de conexão, tentando novamente", {
                    "error": str(e),
                    "attempt": attempt + 1
                })
                await asyncio.sleep(1)  # Espera 1 segundo antes de retry
                continue
                
            # Se for última tentativa ou outro tipo de erro
            if attempt == max_retries - 1:
                storage.add_log("ERROR", "Todas tentativas falharam", {
                    "error": str(e),
                    "total_attempts": max_retries
                })
                return False, {}, f"Request failed: {str(e)}"
            continue
            
    storage.add_log("ERROR", "Todas as chaves GROQ falharam")
    return False, {}, "All GROQ keys exhausted"
