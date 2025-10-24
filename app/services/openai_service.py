from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from flask import current_app
import requests
import tempfile
import os
import logging
from typing import Optional, Dict, Any
from PIL import Image
import io

logger = logging.getLogger(__name__)

def init_openai(app):
    """Initialize OpenAI configuration"""
    try:
        api_key = app.config.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in configuration")
        
        # Test connection
        client = OpenAI(api_key=api_key)
        # Simple test call
        client.models.list()
        
        logger.info("✅ OpenAI connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ OpenAI initialization failed: {e}")
        raise

class OpenAIService:
    """Service for OpenAI API interactions"""
    
    def __init__(self):
        self.api_key = current_app.config['OPENAI_API_KEY']
        self.model_name = current_app.config.get('MODEL_NAME', 'gpt-4.1-mini-2025-04-14')
        self.embedding_model = current_app.config.get('EMBEDDING_MODEL', 'text-embedding-3-small')
        self.max_tokens = current_app.config.get('MAX_TOKENS', 1500)
        self.temperature = current_app.config.get('TEMPERATURE', 0.7)
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Voice and image enabled flags
        self.voice_enabled = current_app.config.get('VOICE_ENABLED', False)
        self.image_enabled = current_app.config.get('IMAGE_ENABLED', False)
    
    def get_chat_model(self):
        """Get LangChain ChatOpenAI model"""
        return ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
    
    def get_embeddings(self):
        """Get LangChain OpenAI embeddings"""
        return OpenAIEmbeddings(
            api_key=self.api_key,
            model=self.embedding_model
        )
    
    def test_connection(self):
        """Test OpenAI connection"""
        try:
            self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            raise


    def validate_openai_setup(self) -> bool:
        """Validar configuración completa de OpenAI (Responses API)."""
        try:
            # Prueba simple con Responses API
            resp = self.client.responses.create(
                model=self.model_name,
                input="test",
                max_output_tokens=1
            )
            # Si el cliente devolvió algo, consideramos OK
            return bool(resp and getattr(resp, "id", None))
        except Exception as e:
            logger.error(f"OpenAI validation failed (Responses): {e}")
            return False
    
    def generate_response(self, messages: list, **kwargs) -> str:
        """Generate response using OpenAI Responses API (minimal migration).

        - messages: lista de dicts {'role': 'user'|'assistant', 'content': '...'}
        - Conserva max_tokens/temperature como antes.
        """
        try:
            # Si te pasan un string directamente, usarlo
            if isinstance(messages, str):
                prompt = messages
            else:
                # Normalizar lista de mensajes a texto plano (cambio mínimo)
                parts = []
                for m in messages:
                    role = m.get("role", "user")
                    content = m.get("content", "")
                    # Si content es lista (ej. para images) intentar extraer texto partes
                    if isinstance(content, list):
                        # concatenar textos que encuentre en la estructura
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
                prompt = "\n".join(parts)

            resp = self.client.responses.create(
                model=self.model_name,
                input=prompt,
                max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature)
            )

            # Extraer texto de salida de forma robusta:
            text_out = ""
            try:
                # La Responses API puede contener .output con elementos content
                if hasattr(resp, "output"):
                    for out in getattr(resp, "output", []):
                        # cada out puede tener .content: lista de items con .type e .text/plain
                        content = out.get("content") if isinstance(out, dict) else getattr(out, "content", None)
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and "text" in c:
                                    text_out += c["text"]
                                elif isinstance(c, dict) and c.get("type") == "output_text" and "text" in c:
                                    text_out += c["text"]
                                elif isinstance(c, str):
                                    text_out += c
                # Fallback: algunos SDK exponen resp.output_text directamente
                if not text_out and hasattr(resp, "output_text"):
                    text_out = getattr(resp, "output_text")
            except Exception:
                # último recurso: convertir a str
                text_out = str(resp)

            return text_out.strip()

        except Exception as e:
            logger.error(f"Error generating OpenAI response (Responses API): {e}")
            raise

    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio file to text"""
        if not self.voice_enabled:
            raise ValueError("Voice processing is not enabled")
        
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es"
                )
            
            logger.info(f"Audio transcribed successfully: {len(response.text)} chars")
            return response.text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    def transcribe_audio_from_url(self, audio_url: str) -> str:
        """Transcribe audio from URL"""
        if not self.voice_enabled:
            raise ValueError("Voice processing is not enabled")
        
        temp_path = None
        try:
            # Download audio file
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            # Transcribe
            result = self.transcribe_audio(temp_path)
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio from URL: {e}")
            raise
        
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not cleanup temp file: {cleanup_error}")
                
    
    def analyze_image(self, image_file) -> str:
        """Analyze image using Responses API (fixed input types)."""
        if not self.image_enabled:
            raise ValueError("Image processing is not enabled")
    
        try:
            # Leer bytes
            if hasattr(image_file, "read"):
                image_bytes = image_file.read()
            else:
                with open(image_file, "rb") as f:
                    image_bytes = f.read()
    
            # Preferible: si imagen grande, subir a storage y usar URL pública.
            if len(image_bytes) > 300_000:
                logger.warning("Image size > 300KB — consider uploading to storage and passing a URL instead of data URI.")
    
            import base64, json
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            data_uri = f"data:image/jpeg;base64,{base64_image}"
    
            # Construir payload válido para Responses API
            message_item = {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "output_text",
                        "text": (
                            "Describe esta imagen en detalle en español, enfocándote en elementos relevantes "
                            "para una consulta de tratamientos estéticos o servicios médicos. Si es una promoción o anuncio, menciona los detalles principales."
                        )
                    }
                ]
            }
    
            image_item = {
                "type": "input_image",
                "image_url": {"url": data_uri}
            }
    
            input_payload = [message_item, image_item]
    
            # DEBUG: log payload (recorta para no llenar logs)
            try:
                logger.debug("OPENAI RESPONSES PAYLOAD (analyze_image): %s", json.dumps(input_payload)[:8000])
            except Exception:
                logger.debug("OPENAI RESPONSES PAYLOAD (analyze_image): (could not json.dumps)")
    
            resp = self.client.responses.create(
                model=self.model_name,
                input=input_payload,
                max_output_tokens=500,
                temperature=0.1
            )
    
            # Extraer texto robustamente (usa tu helper si ya existe)
            text_out = ""
            if hasattr(resp, "output"):
                for out in getattr(resp, "output", []):
                    content = out.get("content") if isinstance(out, dict) else getattr(out, "content", None)
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and "text" in c:
                                text_out += c["text"]
                            elif isinstance(c, str):
                                text_out += c
            if not text_out and hasattr(resp, "output_text"):
                text_out = getattr(resp, "output_text")
    
            return text_out.strip()
    
        except Exception as e:
            logger.error(f"Error analyzing image (Responses): {e}")
            # Log extra para debugging
            try:
                logger.debug("Exception details: %s", getattr(e, "args", e))
            except Exception:
                pass
            raise

    
    def analyze_image_from_url(self, image_url: str) -> str:
        """Analyze image from URL using Responses API (fixed input types)."""
        if not self.image_enabled:
            raise ValueError("Image processing is not enabled")
    
        try:
            logger.info(f"Downloading image from: {image_url}")
            headers = {"User-Agent": "Mozilla/5.0 (compatible; ChatbotImageAnalyzer/1.0)"}
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
    
            content_type = response.headers.get("content-type", "").lower()
            if not any(img_type in content_type for img_type in ["image/", "jpeg", "png", "gif", "webp"]):
                logger.warning(f"Content type might not be image: {content_type}")
    
            # Si la imagen es grande preferible subir a storage y usar URL pública,
            # pero para compatibilidad temporal delegamos al mismo analyze_image
            image_file = BytesIO(response.content)
    
            return self.analyze_image(image_file)
    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image: {e}")
            raise Exception(f"Error downloading image: {str(e)}")
        except Exception as e:
            logger.error(f"Error in image analysis from URL: {e}")
            raise

    def text_to_speech(self, text: str) -> str:
        """Convert text to speech and return file path"""
        if not self.voice_enabled:
            raise ValueError("Voice processing is not enabled")
        
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text[:1000]  # Limit text length
            )
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(response.content)
            temp_file.close()
            
            logger.info(f"Text-to-speech generated: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise



    def extract_file_extension(self, url: str, content_type: str = "") -> str:
        """Extract file extension from URL or content type"""
        content_type_lower = content_type.lower()
        
        if 'mp3' in content_type_lower or url.endswith('.mp3'):
            return '.mp3'
        elif 'wav' in content_type_lower or url.endswith('.wav'):
            return '.wav'
        elif 'm4a' in content_type_lower or url.endswith('.m4a'):
            return '.m4a'
        elif 'ogg' in content_type_lower or url.endswith('.ogg'):
            return '.ogg'
        elif 'jpeg' in content_type_lower or 'jpg' in content_type_lower:
            return '.jpg'
        elif 'png' in content_type_lower or url.endswith('.png'):
            return '.png'
        elif 'gif' in content_type_lower or url.endswith('.gif'):
            return '.gif'
        elif 'webp' in content_type_lower or url.endswith('.webp'):
            return '.webp'
        
        if 'audio' in content_type_lower:
            return '.mp3'
        elif 'image' in content_type_lower:
            return '.jpg'
        
        return ''
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def create_embedding(self, text: str) -> list:
        """Create embedding for text"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise

        
    def get_system_info(self) -> Dict[str, Any]:
        """Get OpenAI service system information"""
        return {
            "model_name": self.model_name,
            "embedding_model": self.embedding_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "voice_enabled": self.voice_enabled,
            "image_enabled": self.image_enabled,
            "api_key_configured": bool(self.api_key and self.api_key.strip())
        }
