from flask import Blueprint, request, jsonify
from app.services.multi_agent_factory import get_multi_agent_factory
from app.models.document import DocumentManager
from app.config.company_config import get_company_manager
from app.utils.validators import validate_document_data
from app.utils.decorators import handle_errors, require_api_key
from app.utils.helpers import create_success_response, create_error_response
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('documents', __name__)

def _get_company_id_from_request() -> str:
    """Extraer company_id de headers o usar por defecto"""
    # Método 1: Header específico
    company_id = request.headers.get('X-Company-ID')
    
    # Método 2: Query parameter
    if not company_id:
        company_id = request.args.get('company_id')
    
    # Método 3: JSON body
    if not company_id and request.is_json:
        data = request.get_json()
        company_id = data.get('company_id') if data else None
    
    # Por defecto
    if not company_id:
        company_id = 'benova'  # Empresa por defecto para retrocompatibilidad
    
    return company_id

@bp.route('', methods=['POST'])
@handle_errors
def add_document():
    """Add a single document to the vectorstore - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        data = request.get_json()
        content, metadata = validate_document_data(data)
        
        # Servicios específicos de empresa
        doc_manager = DocumentManager(company_id=company_id)
        factory = get_multi_agent_factory()
        
        # Obtener servicio de vectorstore específico
        orchestrator = factory.get_orchestrator(company_id)
        if not orchestrator or not orchestrator.vectorstore_service:
            return create_error_response(f"Vectorstore service not available for company: {company_id}", 503)
        
        vectorstore_service = orchestrator.vectorstore_service
        
        doc_id, num_chunks = doc_manager.add_document(content, metadata, vectorstore_service)
        
        logger.info(f"✅ [{company_id}] Document {doc_id} added with {num_chunks} chunks")
        
        return create_success_response({
            "company_id": company_id,
            "document_id": doc_id,
            "chunk_count": num_chunks,
            "message": f"Document added with {num_chunks} chunks for {company_id}"
        }, 201)
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        logger.exception(f"Error adding document for company {company_id if 'company_id' in locals() else 'unknown'}")
        return create_error_response("Failed to add document", 500)

@bp.route('/list', methods=['GET'])
@handle_errors
def list_documents():
    """Listar documentos para una empresa específica - ENDPOINT REQUERIDO POR FRONTEND"""
    try:
        # Extraer company_id del request
        company_id = request.args.get('company_id') or request.headers.get('X-Company-ID') or 'benova'
        
        logger.info(f"Listing documents for company: {company_id}")
        
        # Validar empresa usando el manager existente
        from app.config.company_config import get_company_manager
        company_manager = get_company_manager()
        
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Obtener configuración de la empresa
        company_config = company_manager.get_company_config(company_id)
        company_name = company_config.get('company_name', company_id) if company_config else company_id
        
        # Simular lista de documentos por empresa
        # En producción, esto vendría del vectorstore real
        documents = [
            {
                "id": f"doc_{company_id}_001",
                "title": f"Servicios y Tratamientos - {company_name}",
                "content_preview": f"Información completa sobre todos los servicios disponibles en {company_name}...",
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:00:00Z",
                "size": 2048,
                "type": "text/plain",
                "category": "services",
                "company_id": company_id
            },
            {
                "id": f"doc_{company_id}_002", 
                "title": f"Precios y Promociones - {company_name}",
                "content_preview": f"Lista actualizada de precios y promociones especiales en {company_name}...",
                "created_at": "2025-01-14T15:30:00Z",
                "updated_at": "2025-01-14T15:30:00Z",
                "size": 1536,
                "type": "text/plain",
                "category": "pricing",
                "company_id": company_id
            },
            {
                "id": f"doc_{company_id}_003",
                "title": f"Políticas y Procedimientos - {company_name}",
                "content_preview": f"Políticas de atención, cancelación y procedimientos de {company_name}...",
                "created_at": "2025-01-13T09:15:00Z",
                "updated_at": "2025-01-13T09:15:00Z",
                "size": 1024,
                "type": "text/plain", 
                "category": "policies",
                "company_id": company_id
            }
        ]
        
        # Usar la función de respuesta consistente que ya tienes
        return create_success_response({
            "documents": documents,
            "total": len(documents),
            "company_id": company_id,
            "company_name": company_name,
            "message": f"Documents retrieved successfully for {company_name}"
        })
        
    except Exception as e:
        logger.error(f"Error listing documents for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response(f"Error retrieving documents: {str(e)}", 500)

@bp.route('/search', methods=['POST'])
@handle_errors
def search_documents():
    """Search documents using semantic search - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        data = request.get_json()
        if not data or 'query' not in data:
            return create_error_response("Query is required", 400)
        
        query = data['query'].strip()
        if not query:
            return create_error_response("Query cannot be empty", 400)
        
        k = min(data.get('k', 3), 20)
        
        # Obtener servicio específico de empresa
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator or not orchestrator.vectorstore_service:
            return create_error_response(f"Search service not available for company: {company_id}", 503)
        
        # Buscar con filtro de empresa
        results = orchestrator.vectorstore_service.search_by_company(query, company_id, k)
        
        return create_success_response({
            "company_id": company_id,
            "query": query,
            "results_count": len(results),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error searching documents for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to search documents", 500)

@bp.route('/bulk', methods=['POST'])
@handle_errors
def bulk_add_documents():
    """Bulk add multiple documents - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        data = request.get_json()
        if not data or 'documents' not in data:
            return create_error_response("Documents array is required", 400)
        
        documents = data['documents']
        if not isinstance(documents, list) or not documents:
            return create_error_response("Documents must be a non-empty array", 400)
        
        # Servicios específicos de empresa
        doc_manager = DocumentManager(company_id=company_id)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator or not orchestrator.vectorstore_service:
            return create_error_response(f"Vectorstore service not available for company: {company_id}", 503)
        
        result = doc_manager.bulk_add_documents(documents, orchestrator.vectorstore_service)
        
        return create_success_response(result, 201)
        
    except Exception as e:
        logger.error(f"Error bulk adding documents for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to bulk add documents", 500)

@bp.route('/<doc_id>', methods=['DELETE'])
@handle_errors
def delete_document(doc_id):
    """Delete a document and its vectors - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Servicios específicos de empresa
        doc_manager = DocumentManager(company_id=company_id)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator or not orchestrator.vectorstore_service:
            return create_error_response(f"Vectorstore service not available for company: {company_id}", 503)
        
        result = doc_manager.delete_document(doc_id, orchestrator.vectorstore_service)
        
        if not result['found']:
            return create_error_response("Document not found or unauthorized", 404)
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Error deleting document {doc_id} for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to delete document", 500)

@bp.route('/cleanup', methods=['POST'])
@handle_errors
@require_api_key
def cleanup_orphaned_vectors():
    """Clean up orphaned vectors - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        data = request.get_json() if request.is_json else {}
        dry_run = data.get('dry_run', True)
        
        # Servicios específicos de empresa
        doc_manager = DocumentManager(company_id=company_id)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator or not orchestrator.vectorstore_service:
            return create_error_response(f"Vectorstore service not available for company: {company_id}", 503)
        
        result = doc_manager.cleanup_orphaned_vectors(orchestrator.vectorstore_service, dry_run)
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Error in cleanup for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to cleanup orphaned vectors", 500)

@bp.route('/diagnostics', methods=['GET'])
@handle_errors
def document_diagnostics():
    """Get diagnostics for the document system - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Servicios específicos de empresa
        doc_manager = DocumentManager(company_id=company_id)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator or not orchestrator.vectorstore_service:
            return create_error_response(f"Vectorstore service not available for company: {company_id}", 503)
        
        result = doc_manager.get_diagnostics(orchestrator.vectorstore_service)
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Error in diagnostics for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to run diagnostics", 500)


