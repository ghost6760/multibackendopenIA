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
    
    # Método 3: Form data (NUEVO)
    if not company_id and request.form:
        company_id = request.form.get('company_id')
    
    # Método 4: JSON body
    if not company_id and request.is_json:
        data = request.get_json()
        company_id = data.get('company_id') if data else None
    
    # Por defecto
    if not company_id:
        company_id = 'benova'
    
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
        
        # 🔧 CORRECCIÓN: Detectar tipo de contenido
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Manejar FormData (con archivos)
            data = {
                'title': request.form.get('title'),
                'content': request.form.get('content', ''),
                'company_id': request.form.get('company_id', company_id)
            }
            
            # Manejar archivo si existe
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename:
                # Procesar el archivo
                file_content = uploaded_file.read().decode('utf-8', errors='ignore')
                # Combinar contenido del archivo con el contenido del form
                if file_content.strip():
                    data['content'] = file_content if not data['content'] else data['content'] + '\n\n' + file_content
                
                # Agregar metadatos del archivo
                data['filename'] = uploaded_file.filename
                data['file_type'] = uploaded_file.content_type
                
        elif request.is_json:
            # Manejar JSON (sin archivos) - comportamiento original
            data = request.get_json()
            
        else:
            return create_error_response("Unsupported content type. Use application/json or multipart/form-data", 400)
        
        # Validar datos (esto debería funcionar con ambos formatos)
        content, metadata = validate_document_data(data)
        
        # Resto del código original continúa igual...
        doc_manager = DocumentManager(company_id=company_id)
        factory = get_multi_agent_factory()
        
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
            "message": f"Document added with {num_chunks} chunks for {company_id}",
            "filename": data.get('filename'),  # Incluir info del archivo si existe
            "file_type": data.get('file_type')
        }, 201)
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        logger.exception(f"Error adding document for company {company_id if 'company_id' in locals() else 'unknown'}")
        return create_error_response("Failed to add document", 500)
        

@bp.route('', methods=['GET'])
@handle_errors
def list_documents():
    """List all documents with pagination - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        doc_manager = DocumentManager(company_id=company_id)
        result = doc_manager.list_documents(page, page_size)
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Error listing documents for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to list documents", 500)

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
