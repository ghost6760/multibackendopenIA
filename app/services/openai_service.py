# app/services/openai_service.py
from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from flask import current_app
import requests
import tempfile
import os
import logging
from typing import Optional, Dict, Any, List
from PIL import Image
import io

logger = logging.getLogger(__name__)


def init_openai(app):
    """Initialize OpenAI configuration (test connection)."""
    try:
        api_key = app.config.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in configuration")

        # Test connection
        client = OpenAI(api_key=api_key)
        # Simple test call (list models)
        client.models.list()

        logger.info("✅ OpenAI connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ OpenAI initialization failed: {e}", exc_info=True)
        raise


class OpenAIService:
    """Service for OpenAI API interactions.

    Important: This service *exposes* LangChain / OpenAI clients for compatibility,
    but **the execution of the LLM must be performed by a graph node** that builds
    the `messages: List[Dict]` payload and calls one of the methods below
    (generate_response / chat_completion / invoke_with_messages).
    DO NOT use `(prompt | model)` chaining in business logic; do prompt construction
    in graph nodes and call this service with the messages array.
    """

    def __init__(self):
        self.api_key = current_app.config.get('OPENAI_API_KEY', '')
        self.model_name = current_app.config.get('MODEL_NAME', 'gpt-4.1-mini-2025-04-14')
        self.embedding_model = current_app.config.get('EMBEDDING_MODEL', 'text-embedding-3-small')
        self.max_tokens = current_app.config.get('MAX_TOKENS', 1500)
        self.temperature = current_app.config.get('TEMPERATURE', 0.7)

        # New OpenAI client (official)
        self.client = OpenAI(api_key=self.api_key)

        # Voice and image enabled flags
        self.voice_enabled = current_app.config.get('VOICE_ENABLED', False)
        self.image_enabled = current_app.config.get('IMAGE_ENABLED', False)

        logger.debug(f"[OpenAIService] Initialized with model={self.model_name} embeddings={self.embedding_model}")

    # ---------------------------------------------------------------------
    # Compatibility helpers (LangChain client object if someone needs it)
    # ---------------------------------------------------------------------
    def get_chat_model(self, model_name: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        """
        Get LangChain ChatOpenAI model.

        NOTE: returning this object for compatibility only. Prefer calling
        generate_response/invoke_with_messages/chat_completion from graph nodes.
        """
        model_to_use = model_name or self.model_name
        logger.debug(f"[OpenAIService] get_chat_model -> {model_to_use}")
        return ChatOpenAI(
            api_key=self.api_key,
            model=model_to_use,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature
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
            logger.error(f"OpenAI connection test failed: {e}", exc_info=True)
            raise

    def validate_openai_setup(self) -> bool:
        """Validar configuración completa de OpenAI (test chat completion)."""
        try:
            # Use fallback model in case config empty
            model_to_use = self.model_name or "gpt-4-1-mini"
            self.client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI validation failed: {e}", exc_info=True)
            return False

    # ---------------------------------------------------------------------
    # Core: generate / invoke wrappers
    # ---------------------------------------------------------------------
    def generate_response(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Generate a chat response using the OpenAI Chat API.

        Always ensures a valid model parameter is passed to the client
        (kwargs['model'] overrides service config).
        Returns the textual content of the response (best-effort extraction).
        """
        try:
            model_to_use = kwargs.get('model') or self.model_name
            if not model_to_use:
                # Safeguard fallback
                model_to_use = "gpt-4.1-mini-2025-04-14"

            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature)
            )

            # Robust extraction of text content (different SDK shapes)
            try:
                # New shape: response.choices[0].message.content
                return response.choices[0].message.content
            except Exception:
                try:
                    # Older shape: response.choices[0].text
                    return response.choices[0].text
                except Exception:
                    try:
                        # Another fallback: response.get('text') or str(response)
                        return getattr(response, "text", None) or str(response)
                    except Exception:
                        return str(response)

        except Exception as e:
            # Log full stack for debugging
            logger.error(f"Error generating OpenAI response: {e}", exc_info=True)
            raise

    def invoke_with_messages(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Alias / compatibility wrapper that normalizes messages and calls generate_response.

        Accepts LangChain-style messages or plain dicts.
        """
        normalized_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                # assume already in {role, content}
                normalized_messages.append(msg)
            elif hasattr(msg, 'type') and hasattr(msg, 'content'):
                normalized_messages.append({
                    "role": msg.type if msg.type in ['system', 'user', 'assistant'] else 'user',
                    "content": msg.content
                })
            else:
                logger.warning(f"[OpenAIService] Unknown message format: {type(msg)}")
                normalized_messages.append({"role": "user", "content": str(msg)})

        return self.generate_response(normalized_messages, **kwargs)

    def chat_completion(self, messages: List[Dict[str, Any]], model: Optional[str] = None, **kwargs) -> str:
        """
        Backwards-compatible method used by some nodes (router_node earlier).
        Delegates to generate_response. Avoid passing model=None; if omitted,
        service default model is used.
        """
        return self.generate_response(messages, model=model, **kwargs)

    # ---------------------------------------------------------------------
    # Transcription / Vision / TTS
    # ---------------------------------------------------------------------
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

            logger.info(f"Audio transcribed successfully")
            # SDK shapes vary: try to return text attr
            return getattr(response, "text", str(response))

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            raise

    def transcribe_audio_from_url(self, audio_url: str) -> str:
        """Transcribe audio from URL"""
        if not self.voice_enabled:
            raise ValueError("Voice processing is not enabled")

        temp_path = None
        try:
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name

            result = self.transcribe_audio(temp_path)
            return result

        except Exception as e:
            logger.error(f"Error transcribing audio from URL: {e}", exc_info=True)
            raise

        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not cleanup temp file: {cleanup_error}")

    def analyze_image(self, image_file) -> str:
        """Analyze image using OpenAI Vision API"""
        if not self.image_enabled:
            raise ValueError("Image processing is not enabled")

        try:
            if hasattr(image_file, 'read'):
                image_data = image_file.read()
            else:
                with open(image_file, 'rb') as f:
                    image_data = f.read()

            import base64
            base64_image = base64.b64encode(image_data).decode('utf-8')

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe esta imagen en detalle en español, enfocándote en aspectos relevantes para un centro estético."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=300
            )

            try:
                return response.choices[0].message.content
            except Exception:
                return getattr(response, "text", str(response))

        except Exception as e:
            logger.error(f"Error analyzing image: {e}", exc_info=True)
            raise

    def analyze_image_from_url(self, image_url: str) -> str:
        """Analyze image from URL"""
        if not self.image_enabled:
            raise ValueError("Image processing is not enabled")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe esta imagen en detalle en español, enfocándote en aspectos relevantes para un centro estético."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=300
            )

            try:
                return response.choices[0].message.content
            except Exception:
                return getattr(response, "text", str(response))

        except Exception as e:
            logger.error(f"Error analyzing image from URL: {e}", exc_info=True)
            raise

    def text_to_speech(self, text: str) -> str:
        """Convert text to speech and return file path"""
        if not self.voice_enabled:
            raise ValueError("Voice processing is not enabled")

        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text[:1000]
            )

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            # response.content may be bytes or sdk-specific object
            try:
                temp_file.write(response.content)
            except Exception:
                # fallback: str conversion
                temp_file.write(str(response).encode('utf-8'))
            temp_file.close()

            logger.info(f"Text-to-speech generated: {temp_file.name}")
            return temp_file.name

        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            raise

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
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

            # Robust extraction
            try:
                return response.data[0].embedding
            except Exception:
                # fallback: try attribute access or raise
                if hasattr(response, "data") and len(response.data) > 0:
                    return response.data[0].embedding
                raise
        except Exception as e:
            logger.error(f"Error creating embedding: {e}", exc_info=True)
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

