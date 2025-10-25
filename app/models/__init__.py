"""Models package initialization - Enhanced for Multi-tenant"""

from .conversation import ConversationManager
from .document import DocumentManager, DocumentChangeTracker
from .audit_trail import AuditManager, AuditEntry
from .schemas import *

__all__ = [
    'ConversationManager',
    'DocumentManager',
    'DocumentChangeTracker',
    'AuditManager',
    'AuditEntry'
    # schemas se exportan automáticamente con *
]

# Helper function for creating company-specific managers
def get_conversation_manager(company_id: str) -> ConversationManager:
    """Get conversation manager for specific company"""
    return ConversationManager(company_id=company_id)

def get_document_manager(company_id: str) -> DocumentManager:
    """Get document manager for specific company"""
    return DocumentManager(company_id=company_id)

def get_audit_manager(company_id: str) -> AuditManager:
    """Get audit manager for specific company"""
    return AuditManager(company_id=company_id)
