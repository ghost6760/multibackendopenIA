# app/models/prompt_models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class PromptModel(BaseModel):
    """Modelo para prompts personalizados"""
    company_id: str = Field(..., description="ID de la empresa")
    agent_name: str = Field(..., description="Nombre del agente")
    template: str = Field(..., description="Template del prompt")
    is_active: bool = Field(True, description="Si está activo")
    version: int = Field(1, description="Versión del prompt")
    created_by: str = Field("admin", description="Creado por")
    modified_by: str = Field("admin", description="Modificado por")
    
    @validator('template')
    def template_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Template cannot be empty')
        return v

class PromptVersionModel(BaseModel):
    """Modelo para versiones de prompts"""
    prompt_id: int = Field(..., description="ID del prompt")
    company_id: str = Field(..., description="ID de la empresa")
    agent_name: str = Field(..., description="Nombre del agente")
    template: str = Field(..., description="Template del prompt")
    version: int = Field(..., description="Versión")
    action: str = Field(..., description="Acción realizada")
    created_by: str = Field("admin", description="Creado por")
    notes: Optional[str] = Field(None, description="Notas adicionales")

class DefaultPromptModel(BaseModel):
    """Modelo para prompts por defecto"""
    agent_name: str = Field(..., description="Nombre del agente")
    template: str = Field(..., description="Template por defecto")
    description: Optional[str] = Field(None, description="Descripción")

class PromptSearchModel(BaseModel):
    """Modelo para búsqueda de prompts"""
    company_id: Optional[str] = Field(None, description="Filtrar por empresa")
    agent_name: Optional[str] = Field(None, description="Filtrar por agente")
    is_custom: Optional[bool] = Field(None, description="Solo personalizados")
    modified_after: Optional[datetime] = Field(None, description="Modificados después de")
    
class PromptStatsModel(BaseModel):
    """Modelo para estadísticas de prompts"""
    total_companies: int = Field(..., description="Total de empresas")
    total_custom_prompts: int = Field(..., description="Total de prompts personalizados")
    recent_modifications: int = Field(..., description="Modificaciones recientes")
    top_companies: List[Dict[str, Any]] = Field(default_factory=list, description="Empresas más activas")
