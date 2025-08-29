import os
import requests
import tempfile
from io import BytesIO
from typing import Dict, Any, Optional, Union, BinaryIO
import logging
from flask import current_app
from app.services.openai_service import OpenAIService
from app.config.company_config import get_company_config

logger = logging.getLogger(__name__)

class MultimediaService:
    """Service for processing multimedia content (audio, images) with multi-company support"""
    
    def __init__(self, company_id: str = "default"):
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.openai_service = OpenAIService()
        
        # Configuración específica de empresa
        self.voice_enabled = current_app.config.get('VOICE_ENABLED', False)
        self.image_enabled = current_app.config.get('IMAGE_ENABLED', False)
        self.max_file_size = current_app.config.get('MAX_FILE_SIZE', 25 * 1024 * 1024)  # 25MB
        
        # Formatos soportados por empresa
        self.supported_audio_formats = ['.ogg', '.mp3', '.wav', '.m4a', '.aac', '.flac']
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        
        logger.info(f"MultimediaService initialized for company {self.company_config.company_name}")
    
    def transcribe_audio_from_url(self, audio_url: str) -> Dict[str, Any]:
        """
        Transcribe audio from URL with comprehensive error handling
        """
        if not self.voice_enabled:
            return {
                "success": False,
                "error": f"Audio transcription is disabled for {self.company_config.company_name}",
                "company_id": self.company_id
            }
        
        try:
            logger.info(f"Starting audio transcription for company {self.company_config.company_name} from URL: {audio_url}")
            
            # Download audio file
            download_result = self._download_audio_file(audio_url)
            if not download_result["success"]:
                return download_result
            
            temp_path = download_result["temp_path"]
            file_info = download_result["file_info"]
            
            try:
                # Transcribe using OpenAI
                transcription = self.openai_service.transcribe_audio(temp_path)
                
                result = {
                    "success": True,
                    "transcription": transcription,
                    "company_id": self.company_id,
                    "company_name": self.company_config.company_name,
                    "file_info": file_info,
                    "character_count": len(transcription),
                    "service": "whisper"
                }
                
                logger.info(f"Audio transcription successful for {self.company_config.company_name}: {len(transcription)} characters")
                return result
                
            finally:
                # Clean up temporary file
                self._cleanup_temp_file(temp_path)
                
        except Exception as e:
            logger.error(f"Error in audio transcription for company {self.company_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_id": self.company_id,
                "company_name": self.company_config.company_name
            }
    
    def transcribe_audio_from_file(self, file_data: Union[bytes, BinaryIO], 
                                  filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio from file data or file object
        """
        if not self.voice_enabled:
            return {
                "success": False,
                "error": f"Audio transcription is disabled for {self.company_config.company_name}",
                "company_id": self.company_id
            }
        
        try:
            # Validate file
            validation_result = self._validate_audio_file(file_data, filename)
            if not validation_result["success"]:
                return validation_result
            
            # Create temporary file
            temp_path = self._create_temp_audio_file(file_data, filename)
            
            try:
                # Transcribe
                transcription = self.openai_service.transcribe_audio(temp_path)
                
                result = {
                    "success": True,
                    "transcription": transcription,
                    "company_id": self.company_id,
                    "company_name": self.company_config.company_name,
                    "character_count": len(transcription),
                    "service": "whisper"
                }
                
                logger.info(f"Audio file transcription successful for {self.company_config.company_name}: {len(transcription)} characters")
                return result
                
            finally:
                self._cleanup_temp_file(temp_path)
                
        except Exception as e:
            logger.error(f"Error in audio file transcription for company {self.company_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_id": self.company_id,
                "company_name": self.company_config.company_name
            }
    
    def analyze_image_from_url(self, image_url: str, 
                              analysis_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze image from URL using GPT-4 Vision
        """
        if not self.image_enabled:
            return {
                "success": False,
                "error": f"Image analysis is disabled for {self.company_config.company_name}",
                "company_id": self.company_id
            }
        
        try:
            logger.info(f"Starting image analysis for company {self.company_config.company_name} from URL: {image_url}")
            
            # Download and validate image
            download_result = self._download_image_file(image_url)
            if not download_result["success"]:
                return download_result
            
            image_data = download_result["image_data"]
            file_info = download_result["file_info"]
            
            # Use company-specific analysis prompt if not provided
            if not analysis_prompt:
                analysis_prompt = self._get_default_image_analysis_prompt()
            
            # Analyze image
            analysis = self.openai_service.analyze_image(image_data, prompt=analysis_prompt)
            
            result = {
                "success": True,
                "analysis": analysis,
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "file_info": file_info,
                "character_count": len(analysis),
                "service": "gpt-4-vision",
                "prompt_used": analysis_prompt
            }
            
            logger.info(f"Image analysis successful for {self.company_config.company_name}: {len(analysis)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error in image analysis for company {self.company_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_id": self.company_id,
                "company_name": self.company_config.company_name
            }
    
    def analyze_image_from_file(self, file_data: Union[bytes, BinaryIO], 
                               filename: Optional[str] = None,
                               analysis_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze image from file data or file object
        """
        if not self.image_enabled:
            return {
                "success": False,
                "error": f"Image analysis is disabled for {self.company_config.company_name}",
                "company_id": self.company_id
            }
        
        try:
            # Validate file
            validation_result = self._validate_image_file(file_data, filename)
            if not validation_result["success"]:
                return validation_result
            
            # Convert to BytesIO if needed
            if isinstance(file_data, bytes):
                image_file = BytesIO(file_data)
            else:
                image_file = file_data
            
            # Use company-specific analysis prompt if not provided
            if not analysis_prompt:
                analysis_prompt = self._get_default_image_analysis_prompt()
            
            # Analyze image
            analysis = self.openai_service.analyze_image(image_file, prompt=analysis_prompt)
            
            result = {
                "success": True,
                "analysis": analysis,
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "character_count": len(analysis),
                "service": "gpt-4-vision",
                "prompt_used": analysis_prompt
            }
            
            logger.info(f"Image file analysis successful for {self.company_config.company_name}: {len(analysis)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error in image file analysis for company {self.company_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "company_id": self.company_id,
                "company_name": self.company_config.company_name
            }
    
    def _download_audio_file(self, audio_url: str) -> Dict[str, Any]:
        """Download audio file from URL with validation"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; MultimediaService/1.0)',
                'Accept': 'audio/*,*/*;q=0.9'
            }
            
            response = requests.get(audio_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_file_size:
                return {
                    "success": False,
                    "error": f"Audio file too large: {content_length} bytes (max: {self.max_file_size})"
                }
            
            # Determine file extension
            content_type = response.headers.get('content-type', '').lower()
            extension = self._get_audio_extension_from_content_type(content_type, audio_url)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                total_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > self.max_file_size:
                        os.unlink(temp_file.name)
                        return {
                            "success": False,
                            "error": f"Audio file too large during download: {total_size} bytes"
                        }
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            file_info = {
                "content_type": content_type,
                "extension": extension,
                "size_bytes": total_size,
                "url": audio_url
            }
            
            return {
                "success": True,
                "temp_path": temp_path,
                "file_info": file_info
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error downloading audio file: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error downloading audio: {str(e)}"
            }
    
    def _download_image_file(self, image_url: str) -> Dict[str, Any]:
        """Download image file from URL with validation"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; MultimediaService/1.0)',
                'Accept': 'image/*,*/*;q=0.9'
            }
            
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Check file size
            if len(response.content) > self.max_file_size:
                return {
                    "success": False,
                    "error": f"Image file too large: {len(response.content)} bytes"
                }
            
            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
                return {
                    "success": False,
                    "error": f"Invalid content type: {content_type}"
                }
            
            image_data = BytesIO(response.content)
            
            file_info = {
                "content_type": content_type,
                "size_bytes": len(response.content),
                "url": image_url
            }
            
            return {
                "success": True,
                "image_data": image_data,
                "file_info": file_info
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error downloading image file: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error downloading image: {str(e)}"
            }
    
    def _validate_audio_file(self, file_data: Union[bytes, BinaryIO], 
                           filename: Optional[str] = None) -> Dict[str, Any]:
        """Validate audio file data"""
        try:
            # Check file size
            if isinstance(file_data, bytes):
                file_size = len(file_data)
            else:
                file_data.seek(0, 2)  # Seek to end
                file_size = file_data.tell()
                file_data.seek(0)  # Reset position
            
            if file_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"Audio file too large: {file_size} bytes"
                }
            
            # Check extension if filename provided
            if filename:
                extension = os.path.splitext(filename.lower())[1]
                if extension not in self.supported_audio_formats:
                    return {
                        "success": False,
                        "error": f"Unsupported audio format: {extension}"
                    }
            
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error validating audio file: {str(e)}"
            }
    
    def _validate_image_file(self, file_data: Union[bytes, BinaryIO], 
                           filename: Optional[str] = None) -> Dict[str, Any]:
        """Validate image file data"""
        try:
            # Check file size
            if isinstance(file_data, bytes):
                file_size = len(file_data)
            else:
                file_data.seek(0, 2)  # Seek to end
                file_size = file_data.tell()
                file_data.seek(0)  # Reset position
            
            if file_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"Image file too large: {file_size} bytes"
                }
            
            # Check extension if filename provided
            if filename:
                extension = os.path.splitext(filename.lower())[1]
                if extension not in self.supported_image_formats:
                    return {
                        "success": False,
                        "error": f"Unsupported image format: {extension}"
                    }
            
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error validating image file: {str(e)}"
            }
    
    def _create_temp_audio_file(self, file_data: Union[bytes, BinaryIO], 
                               filename: Optional[str] = None) -> str:
        """Create temporary audio file from data"""
        # Determine extension
        extension = '.ogg'  # Default
        if filename:
            extension = os.path.splitext(filename.lower())[1] or '.ogg'
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            if isinstance(file_data, bytes):
                temp_file.write(file_data)
            else:
                file_data.seek(0)
                temp_file.write(file_data.read())
            
            return temp_file.name
    
    def _get_audio_extension_from_content_type(self, content_type: str, url: str) -> str:
        """Determine audio file extension from content type or URL"""
        if 'mp3' in content_type or url.endswith('.mp3'):
            return '.mp3'
        elif 'wav' in content_type or url.endswith('.wav'):
            return '.wav'
        elif 'm4a' in content_type or url.endswith('.m4a'):
            return '.m4a'
        elif 'aac' in content_type or url.endswith('.aac'):
            return '.aac'
        elif 'flac' in content_type or url.endswith('.flac'):
            return '.flac'
        else:
            return '.ogg'  # Default for Chatwoot and web audio
    
    def _get_default_image_analysis_prompt(self) -> str:
        """Get default image analysis prompt based on company configuration"""
        # Personalizar prompt según la industria de la empresa
        if self.company_config.industry_type == "estética":
            return f"""Analiza esta imagen en el contexto de {self.company_config.company_name}, un centro estético.
            
Describe:
1. ¿Qué se muestra en la imagen?
2. ¿Es relevante para tratamientos estéticos o consultas de belleza?
3. ¿Hay alguna condición de piel o área que podría beneficiarse de nuestros servicios?
4. ¿Qué información útil puedes proporcionar?

Responde de manera profesional y útil."""
        
        else:
            return f"""Analiza esta imagen en el contexto de {self.company_config.company_name}.
            
Describe:
1. ¿Qué se muestra en la imagen?
2. ¿Es relevante para nuestros servicios: {self.company_config.services}?
3. ¿Qué información útil puedes proporcionar?
4. ¿Hay alguna acción recomendada?

Responde de manera profesional y útil."""
    
    def _cleanup_temp_file(self, temp_path: str):
        """Clean up temporary file safely"""
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
        except Exception as e:
            logger.warning(f"Could not clean up temporary file {temp_path}: {e}")
    
    def get_service_capabilities(self) -> Dict[str, Any]:
        """Get service capabilities for this company"""
        return {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "capabilities": {
                "audio_transcription": self.voice_enabled,
                "image_analysis": self.image_enabled,
                "max_file_size_mb": self.max_file_size / (1024 * 1024),
                "supported_audio_formats": self.supported_audio_formats,
                "supported_image_formats": self.supported_image_formats
            },
            "services": {
                "transcription_service": "openai-whisper",
                "image_analysis_service": "openai-gpt4-vision"
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            # Test OpenAI service
            openai_healthy = self.openai_service.health_check()
            
            return {
                "service": "multimedia",
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "healthy": openai_healthy,
                "voice_enabled": self.voice_enabled,
                "image_enabled": self.image_enabled,
                "openai_service": openai_healthy
            }
            
        except Exception as e:
            logger.error(f"Health check failed for multimedia service (company {self.company_id}): {e}")
            return {
                "service": "multimedia",
                "company_id": self.company_id,
                "healthy": False,
                "error": str(e)
            }


class MultiCompanyMultimediaService:
    """Manager for multimedia services across multiple companies"""
    
    def __init__(self):
        self.company_services = {}
    
    def get_service_for_company(self, company_id: str) -> MultimediaService:
        """Get multimedia service for specific company"""
        if company_id not in self.company_services:
            self.company_services[company_id] = MultimediaService(company_id)
        
        return self.company_services[company_id]
    
    def get_global_capabilities(self) -> Dict[str, Any]:
        """Get capabilities across all companies"""
        global_capabilities = {
            "total_companies": len(self.company_services),
            "companies": {},
            "global_summary": {
                "companies_with_audio": 0,
                "companies_with_images": 0,
                "total_services": len(self.company_services)
            }
        }
        
        for company_id, service in self.company_services.items():
            try:
                company_capabilities = service.get_service_capabilities()
                global_capabilities["companies"][company_id] = company_capabilities
                
                # Update global summary
                if company_capabilities["capabilities"]["audio_transcription"]:
                    global_capabilities["global_summary"]["companies_with_audio"] += 1
                
                if company_capabilities["capabilities"]["image_analysis"]:
                    global_capabilities["global_summary"]["companies_with_images"] += 1
                
            except Exception as e:
                logger.error(f"Error getting capabilities for company {company_id}: {e}")
                continue
        
        return global_capabilities
    
    def get_global_health_status(self) -> Dict[str, Any]:
        """Get health status across all companies"""
        global_health = {
            "total_companies": len(self.company_services),
            "companies": {},
            "global_summary": {
                "healthy_companies": 0,
                "total_companies": len(self.company_services)
            }
        }
        
        for company_id, service in self.company_services.items():
            try:
                company_health = service.health_check()
                global_health["companies"][company_id] = company_health
                
                if company_health.get("healthy", False):
                    global_health["global_summary"]["healthy_companies"] += 1
                
            except Exception as e:
                logger.error(f"Error getting health for company {company_id}: {e}")
                global_health["companies"][company_id] = {
                    "company_id": company_id,
                    "healthy": False,
                    "error": str(e)
                }
                continue
        
        return global_health
