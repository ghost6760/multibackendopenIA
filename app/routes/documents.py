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
        
        # Detectar tipo de contenido y extraer datos
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Manejar FormData (con archivos)
            title = request.form.get('title', '').strip()
            form_content = request.form.get('content', '').strip()
            
            # Procesar archivo si existe
            file_content = ''
            filename = None
            file_type = None
            
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename:
                try:
                    # Leer contenido del archivo
                    file_content = uploaded_file.read().decode('utf-8', errors='ignore').strip()
                    filename = uploaded_file.filename
                    file_type = uploaded_file.content_type
                except Exception as e:
                    return create_error_response(f"Error reading file: {str(e)}", 400)
            
            # Combinar contenidos
            final_content = []
            if title:
                final_content.append(f"# {title}")
            if form_content:
                final_content.append(form_content)
            if file_content:
                final_content.append(file_content)
            
            if not final_content:
                return create_error_response("Either content or file is required", 400)
            
            # Preparar datos para validación
            data = {
                'content': '\n\n'.join(final_content),
                'metadata': {
                    'title': title,
                    'source': 'user_upload',
                    'company_id': company_id
                }
            }
            
            # Agregar metadatos del archivo si existe
            if filename:
                data['metadata']['filename'] = filename
            if file_type:
                data['metadata']['file_type'] = file_type
                
        elif request.is_json:
            # Manejar JSON (comportamiento original)
            data = request.get_json()
            if not data:
                return create_error_response("Invalid JSON data", 400)
                
        else:
            return create_error_response("Unsupported content type. Use application/json or multipart/form-data", 400)
        
        # Validar datos (ahora debería funcionar con ambos formatos)
        content, metadata = validate_document_data(data)
        
        # Resto del código original...
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
            "title": metadata.get('title'),
            "filename": metadata.get('filename'),
            "file_type": metadata.get('file_type')
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
        company_id = _get_company_id_from_request()  # Corregir el typo
        
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
        
        # Buscar con filtro de empresa (devuelve objetos Document)
        document_results = orchestrator.vectorstore_service.search_by_company(query, company_id, k)
        
        # NUEVA LÓGICA: Convertir objetos Document a diccionarios JSON serializables
        api_results = []
        for doc in document_results:
            metadata = getattr(doc, 'metadata', {})
            
            api_result = {
                'id': metadata.get('doc_id', ''),
                'title': metadata.get('title', 'Sin título'),
                'content': getattr(doc, 'page_content', ''),
                'excerpt': getattr(doc, 'page_content', '')[:200] + ('...' if len(getattr(doc, 'page_content', '')) > 200 else ''),
                'metadata': metadata,
                'relevance': 1.0,  # Placeholder - podrías calcular relevancia real más tarde
                'score': 1.0,
                'treatment': metadata.get('treatment', 'general'),
                'type': metadata.get('type', 'otro'),
                'chunk_index': metadata.get('chunk_index', 0),
                'created_at': metadata.get('processed_at', ''),
                'company_id': metadata.get('company_id', company_id),
                'doc_id': metadata.get('doc_id', ''),
                '_id': metadata.get('doc_id', '')  # Para compatibilidad con frontend
            }
            api_results.append(api_result)
        
        return create_success_response({
            "company_id": company_id,
            "query": query,
            "results_count": len(api_results),
            "results": api_results  # Ahora son diccionarios JSON serializables
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


@bp.route('/<doc_id>', methods=['GET'])
@handle_errors  
def get_document(doc_id):
    """Get a single document by ID - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Asegurar prefijo de empresa
        if not doc_id.startswith(f"{company_id}_"):
            doc_id = f"{company_id}_{doc_id}"
        
        # Obtener documento
        doc_manager = DocumentManager(company_id=company_id)
        doc_key = f"{doc_manager.redis_prefix}{doc_id}"
        
        if not doc_manager.redis_client.exists(doc_key):
            return create_error_response("Document not found", 404)
        
        doc_data = doc_manager.redis_client.hgetall(doc_key)
        
        # Procesar datos (conversión de bytes, etc.)
        content = doc_data.get('content', '').decode() if isinstance(doc_data.get('content'), bytes) else doc_data.get('content', '')
        metadata_str = doc_data.get('metadata', '{}').decode() if isinstance(doc_data.get('metadata'), bytes) else doc_data.get('metadata', '{}')
        
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            metadata = {}
        
        document = {
            "id": doc_id,
            "_id": doc_id,
            "title": metadata.get('title', 'Sin título'),
            "content": content,
            "metadata": metadata,
            "created_at": doc_data.get('created_at', '').decode() if isinstance(doc_data.get('created_at'), bytes) else doc_data.get('created_at', ''),
            "company_id": company_id,
            "type": metadata.get('file_type', 'text')
        }
        
        return create_success_response(document)
        
    except Exception as e:
        logger.error(f"Error getting document {doc_id}: {e}")
        return create_error_response("Failed to get document", 500)


@documents_extended_bp.route('/<doc_id>/vectors', methods=['GET'])
def get_document_vectors(doc_id):
    """Obtener vectores de un documento específico"""
    try:
        company_id = request.args.get('company_id') or request.headers.get('X-Company-ID')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Obtener vectores (simulado por ahora)
        # En implementación real, consultaría el vectorstore
        vectors_data = {
            "document_id": doc_id,
            "company_id": company_id,
            "vectors": [
                {
                    "id": f"vec_{i}",
                    "text_chunk": f"Chunk {i} content for document {doc_id}...",
                    "embedding_size": 1536,
                    "metadata": {
                        "chunk_index": i,
                        "document_id": doc_id,
                        "company_id": company_id
                    }
                }
                for i in range(1, 6)  # Simulamos 5 vectores
            ]
        }
        
        return create_success_response({
            "vectors": vectors_data["vectors"],
            "total_vectors": len(vectors_data["vectors"]),
            "document_id": doc_id,
            "company_id": company_id
        })
        
    except Exception as e:
        logger.error(f"Error getting vectors for document {doc_id}: {e}")
        return create_error_response(str(e), 500)


@documents_extended_bp.route('/stats', methods=['GET'])
def get_documents_stats():
    """Obtener estadísticas de documentos para una empresa"""
    try:
        company_id = request.args.get('company_id') or request.headers.get('X-Company-ID')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Obtener estadísticas (simulado por ahora)
        stats = {
            "company_id": company_id,
            "total_documents": 15,
            "total_chunks": 342,
            "total_vectors": 342,
            "storage_used": "24.5 MB",
            "categories": {
                "general": 5,
                "faq": 3,
                "procedures": 4,
                "policies": 2,
                "training": 1
            },
            "last_updated": "2025-01-15T10:30:00Z"
        }
        
        return create_success_response({
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting document stats for company {company_id}: {e}")
        return create_error_response(str(e), 500)

