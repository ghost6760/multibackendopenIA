# app/services/multimedia_service.py

import os
import tempfile
import requests
import base64
from io import BytesIO
from openai import OpenAI
from typing import Optional
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class MultimediaService:
    def __init__(self):
        # Inicializar cliente OpenAI (usar la misma configuración que el resto de la app)
        self.client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'])

    # ---------------------------
    # Helpers
    # ---------------------------
    def _extract_response_text(self, resp) -> str:
        """Extrae texto de una respuesta de Responses API de forma tolerante."""
        text_parts = []

        try:
            out = getattr(resp, "output", None)
            if isinstance(out, list):
                for item in out:
                    # item puede ser dict o un objeto; normalizar a dict-accessible
                    content = item.get("content") if isinstance(item, dict) else getattr(item, "content", None)
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict):
                                # formatos: {'type':'output_text','text': '...'} o {'text': '...'}
                                if "text" in c:
                                    text_parts.append(c["text"])
                            elif isinstance(c, str):
                                text_parts.append(c)
        except Exception:
            # no rompemos, iremos a fallbacks
            pass

        # fallback común: output_text
        if not text_parts and hasattr(resp, "output_text"):
            try:
                text_parts.append(getattr(resp, "output_text"))
            except Exception:
                pass

        if text_parts:
            return "".join(text_parts).strip()

        # último recurso: stringify
        try:
            return str(resp)
        except Exception:
            return ""

    def _messages_to_prompt(self, messages) -> str:
        """Convierta la lista de mensajes (role/content) a un prompt simple."""
        if isinstance(messages, str):
            return messages

        parts = []
        for m in messages:
            role = m.get("role", "user") if isinstance(m, dict) else "user"
            content = m.get("content", "") if isinstance(m, dict) else str(m)
            if isinstance(content, list):
                subparts = []
                for c in content:
                    if isinstance(c, dict) and "text" in c:
                        subparts.append(c["text"])
                    elif isinstance(c, str):
                        subparts.append(c)
                content_text = " ".join(subparts)
            else:
                content_text = str(content)
            parts.append(f"{role.upper()}: {content_text}")
        return "\n".join(parts)

    # ---------------------------
    # Audio / Transcription
    # ---------------------------
    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio to text using Whisper with Spanish language."""
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es",
                    response_format="text"
                )

            return transcript.text if hasattr(transcript, "text") else str(transcript)

        except Exception as e:
            logger.error(f"Error in audio transcription: {e}")
            raise

    def transcribe_audio_from_url(self, audio_url: str) -> str:
        """Download audio and transcribe it (with safe temp-file handling)."""
        try:
            logger.info(f"Downloading audio from: {audio_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ChatbotAudioTranscriber/1.0)",
                "Accept": "audio/*,*/*;q=0.9",
            }

            response = requests.get(audio_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            logger.info(f"Audio content-type: {content_type}")

            extension = ".ogg"
            if "mp3" in content_type or audio_url.endswith(".mp3"):
                extension = ".mp3"
            elif "wav" in content_type or audio_url.endswith(".wav"):
                extension = ".wav"
            elif "m4a" in content_type or audio_url.endswith(".m4a"):
                extension = ".m4a"

            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                temp_path = tmp.name

            logger.info(f"Audio saved to temp file: {temp_path} (size: {os.path.getsize(temp_path)} bytes)")

            try:
                result = self.transcribe_audio(temp_path)
                logger.info(f"Transcription successful: {len(result)} characters")
                return result
            finally:
                try:
                    os.unlink(temp_path)
                    logger.info(f"Temporary file deleted: {temp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_path}: {cleanup_error}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading audio: {e}")
            raise Exception(f"Error downloading audio: {str(e)}")
        except Exception as e:
            logger.error(f"Error in audio transcription from URL: {e}")
            raise

    # ---------------------------
    # Image analysis (Responses API)
    # ---------------------------
    def analyze_image(self, image_file) -> str:
        """Analyze image using Responses API (robust and size-aware)."""
        try:
            # Leer bytes
            if hasattr(image_file, "read"):
                image_bytes = image_file.read()
            else:
                with open(image_file, "rb") as f:
                    image_bytes = f.read()

            # Aviso si la imagen es grande: preferible subir a storage y pasar URL
            if len(image_bytes) > 300_000:  # ~300 KB threshold (ajustable)
                logger.warning("Image size > 300KB — consider uploading to storage and passing a URL instead of data URI.")

            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            data_uri = f"data:image/jpeg;base64,{base64_image}"

            # Construir input mixto para Responses API
            prompt_parts = [
                {"type": "text", "text": "Describe esta imagen en detalle en español, enfocándote en elementos relevantes para una consulta de tratamientos estéticos o servicios médicos. Si es una promoción o anuncio, menciona los detalles principales."},
                {"type": "image_url", "image_url": {"url": data_uri}}
            ]

            resp = self.client.responses.create(
                model="gpt-4.1-mini-2025-04-14",
                input=prompt_parts,
                max_output_tokens=500,
                temperature=0.1
            )

            return self._extract_response_text(resp)

        except Exception as e:
            logger.error(f"Error analyzing image (Responses API): {e}")
            raise

    def analyze_image_from_url(self, image_url: str) -> str:
        """Download image and analyze it (delegates to analyze_image)."""
        try:
            logger.info(f"Downloading image from: {image_url}")
            headers = {"User-Agent": "Mozilla/5.0 (compatible; ChatbotImageAnalyzer/1.0)"}
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            if not any(img_type in content_type for img_type in ["image/", "jpeg", "png", "gif", "webp"]):
                logger.warning(f"Content type might not be image: {content_type}")

            image_file = BytesIO(response.content)
            return self.analyze_image(image_file)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image: {e}")
            raise Exception(f"Error downloading image: {str(e)}")
        except Exception as e:
            logger.error(f"Error in image analysis from URL: {e}")
            raise

    # ---------------------------
    # Text-to-speech
    # ---------------------------
    def text_to_speech(self, text: str) -> str:
        """Convert text to audio using OpenAI TTS"""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )

            # Algunos SDKs exponen método para guardar/stream; usamos fallback a archivo temporal
            temp_path = "/tmp/response.mp3"
            try:
                # Si existe método stream_to_file
                if hasattr(response, "stream_to_file"):
                    response.stream_to_file(temp_path)
                else:
                    # intentar obtener bytes en .content o .audio
                    content = getattr(response, "content", None) or getattr(response, "audio", None)
                    if isinstance(content, (bytes, bytearray)):
                        with open(temp_path, "wb") as f:
                            f.write(content)
                    else:
                        # fallback a str(resp)
                        with open(temp_path, "wb") as f:
                            f.write(str(response).encode("utf-8"))
            except Exception:
                # Si falló el guardado específico, intentar cast simple
                with open(temp_path, "wb") as f:
                    f.write(str(response).encode("utf-8"))

            return temp_path
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            raise
