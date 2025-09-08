# app/config/constants.py
"""Application constants - Enhanced for Multi-tenant"""

# Bot status constants (compartidas entre empresas)
BOT_ACTIVE_STATUSES = ["open"]
BOT_INACTIVE_STATUSES = ["pending", "resolved", "snoozed"]

# Redis key patterns (ahora con prefijos dinámicos por empresa)
REDIS_KEY_PATTERNS = {
    "conversation": "{company_prefix}conversation:",
    "document": "{company_prefix}document:",
    "bot_status": "{company_prefix}bot_status:",
    "processed_message": "{company_prefix}processed_message:",
    "chat_history": "chat_history:",  # LangChain maneja esto automáticamente
    "cache": "cache:",
    "doc_change": "{company_prefix}doc_change:",
    "vectorstore_version": "{company_id}:vectorstore_version",
    "document_hashes": "{company_id}:document_hashes",
    # Nuevas keys para prompts
    "prompts": "{company_id}:prompts:",
    "default_prompts": "default_prompts:",
    "prompts_version": "prompts_version:",
    "prompts_backup": "{company_id}:prompts_backup:"
}

# Redis TTL values (in seconds) - compartidas
REDIS_TTL = {
    "bot_status": 86400,      # 24 hours
    "processed_message": 3600, # 1 hour
    "conversation": 604800,    # 7 days
    "cache": 300,             # 5 minutes
    "doc_change": 3600,       # 1 hour
    # TTL para prompts - Sin expiración
    "prompts": None,          # Sin TTL - persistencia permanente
    "default_prompts": None,  # Sin TTL - persistencia permanente
    "prompts_backup": None    # Sin TTL - persistencia permanente
}

# Multimedia constants (compartidas)
SUPPORTED_IMAGE_TYPES = ['jpg', 'jpeg', 'png', 'gif', 'webp']
SUPPORTED_AUDIO_TYPES = ['mp3', 'wav', 'ogg', 'm4a', 'aac']

# Chunking constants (compartidas)
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MAX_CHUNK_SIZE = 2000

# Search constants (compartidas)
DEFAULT_SEARCH_K = 3
MAX_SEARCH_K = 20

# Pagination constants (compartidas)
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

# Agent types (compartidas)
AGENT_TYPES = ["router", "emergency", "sales", "support", "schedule", "availability"]

# Default treatment durations (fallback si no está en config de empresa)
DEFAULT_TREATMENT_DURATIONS = {
    "consulta general": 30,
    "procedimiento básico": 60,
    "tratamiento avanzado": 90,
    "cirugía menor": 120,
    "sesión de terapia": 45
}

# Default keywords (fallback si no está en config de empresa)
DEFAULT_SCHEDULE_KEYWORDS = [
    "agendar", "reservar", "programar", "cita", "appointment",
    "agenda", "disponibilidad", "horario", "fecha", "hora"
]

DEFAULT_EMERGENCY_KEYWORDS = [
    "dolor intenso", "sangrado", "emergencia", "urgencia",
    "reacción alérgica", "inflamación severa"
]

DEFAULT_SALES_KEYWORDS = [
    "precio", "costo", "inversión", "promoción",
    "tratamiento", "procedimiento", "beneficio", "servicio"
]

# Multi-tenant specific constants
COMPANY_ID_VALIDATION_PATTERN = r'^[a-zA-Z0-9_-]+$'
MAX_COMPANIES = 50  # Límite de empresas por instancia
DEFAULT_COMPANY_ID = 'benova'

# Header names for company identification
COMPANY_HEADER_NAMES = [
    'X-Company-ID',
    'X-Client-ID', 
    'Company-ID',
    'Client-ID'
]
