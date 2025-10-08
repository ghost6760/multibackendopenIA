# app/routes/documents.py - CORREGIDO COMPLETAMENTE
# Fixes: 1) Content-Type handling, 2) Búsqueda semántica, 3) Error handling

from flask import Blueprint, request, jsonify
from app.services.multi_agent_factory import get_multi_agent_factory
from app.models.document import DocumentManager
from app.config.company_config import get_company_manager
from app.utils.validators import validate_document_data
from app.utils.decorators import handle_errors, require_api_key
from app.utils.helpers import create_success_response, create_error_response
import json
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
    
    # Método 3: Form data
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

def _get_json_data_flexible():
    """
    🔧 NUEVO: Extrae JSON data de manera más flexible
    Maneja diferentes Content-Types y formatos de request
    """
    try:
        # Método 1: JSON directo (Content-Type: application/json)
        if request.is_json:
            return request.get_json()
        
        # Método 2: Content-Type text/plain con JSON en el body
        if request.content_type and 'text/' in request.content_type:
            try:
                text_data = request.get_data(as_text=True)
                if text_data.strip():
                    return json.loads(text_data)
            except json.JSONDecodeError:
                pass
        
        # Método 3: Form data con JSON string
        if request.form:
            json_str = request.form.get('json_data') or request.form.get('data')
            if json_str:
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # Método 4: Query parameters como fallback
        if request.args:
            query = request.args.get('query')
            if query:
                return {'query': query}
        
        return None
        
    except Exception as e:
        logger.warning(f"Error extracting JSON data: {e}")
        return None


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
                
        else:
            # 🔧 CORREGIDO: Usar método flexible para JSON
            data = _get_json_data_flexible()
            if not data:
                return create_error_response("Invalid or missing JSON data", 400)
        
        # Validar datos
        content, metadata = validate_document_data(data)
        
        # 🔧 CRÍTICO: Asegurar company_id en metadata
        metadata['company_id'] = company_id
        
        # Obtener servicios
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
    """🔧 CORREGIDO: List documents with proper company isolation"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        logger.info(f"[{company_id}] Listing documents for company")
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        doc_manager = DocumentManager(company_id=company_id)
        
        # Usar método que filtra por empresa
        result = doc_manager.list_documents(page, page_size)
        
        # Verificar que todos los documentos pertenecen a la empresa correcta
        if 'documents' in result:
            # Filtrar solo documentos de esta empresa
            filtered_docs = []
            for doc in result['documents']:
                # Verificar múltiples formas de identificar la empresa
                doc_company = (
                    doc.get('company_id') or 
                    doc.get('metadata', {}).get('company_id') or
                    (doc.get('id', '').split('_')[0] if '_' in doc.get('id', '') else None)
                )
                
                if doc_company == company_id:
                    filtered_docs.append(doc)
                else:
                    logger.warning(f"[{company_id}] Filtering out document {doc.get('id')} belonging to {doc_company}")
            
            result['documents'] = filtered_docs
            result['total_documents'] = len(filtered_docs)
            
            logger.info(f"[{company_id}] Returned {len(filtered_docs)} documents after filtering")
        
        return create_success_response(result)
        
    except Exception as e:
        logger.error(f"Error listing documents for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to list documents", 500)


@bp.route('/search', methods=['POST'])
@handle_errors
def search_documents():
    """🔧 CORREGIDO: Search documents with flexible Content-Type handling"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # 🔧 CRÍTICO: Usar método flexible para extraer JSON
        data = _get_json_data_flexible()
        
        if not data:
            logger.error(f"[{company_id}] No valid data received. Content-Type: {request.content_type}")
            return create_error_response(
                "No valid search data provided. Send JSON with 'query' field.", 
                400,
                {
                    "content_type_received": request.content_type,
                    "methods_tried": ["application/json", "text/plain", "form_data", "query_params"],
                    "example": {"query": "tu término de búsqueda"}
                }
            )
        
        if 'query' not in data:
            return create_error_response("Query field is required", 400)
        
        query = str(data['query']).strip()
        if not query:
            return create_error_response("Query cannot be empty", 400)
        
        k = min(data.get('k', 5), 20)  # Aumentar default de 3 a 5
        
        logger.info(f"[{company_id}] Searching documents: '{query}' (limit: {k})")
        
        # Obtener servicio específico de empresa
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            return create_error_response(f"Multi-agent system not available for company: {company_id}", 503)
        
        if not orchestrator.vectorstore_service:
            return create_error_response(f"Search service not available for company: {company_id}", 503)
        
        # 🔧 MEJORADO: Búsqueda con manejo de errores más robusto
        try:
            document_results = orchestrator.vectorstore_service.search_by_company(query, company_id, k)
            logger.info(f"[{company_id}] Found {len(document_results)} document results")
            
        except Exception as search_error:
            logger.error(f"[{company_id}] Vectorstore search failed: {search_error}")
            
            # Intentar búsqueda de fallback si está disponible
            try:
                # Búsqueda simple en Redis como fallback
                doc_manager = DocumentManager(company_id=company_id)
                fallback_results = doc_manager.simple_text_search(query, limit=k)
                logger.warning(f"[{company_id}] Using fallback search, found {len(fallback_results)} results")
                document_results = fallback_results
                
            except Exception as fallback_error:
                logger.error(f"[{company_id}] Fallback search also failed: {fallback_error}")
                return create_error_response(
                    f"Search failed: {str(search_error)}", 
                    503,
                    {
                        "primary_error": str(search_error),
                        "fallback_error": str(fallback_error),
                        "company_id": company_id,
                        "query": query
                    }
                )
        
        # Convertir resultados a formato API
        api_results = []
        for i, doc in enumerate(document_results):
            try:
                # Manejar diferentes tipos de objetos resultado
                if hasattr(doc, 'page_content'):
                    # Objeto Document de LangChain
                    content = getattr(doc, 'page_content', '')
                    metadata = getattr(doc, 'metadata', {})
                elif isinstance(doc, dict):
                    # Dict resultado de fallback
                    content = doc.get('content', '')
                    metadata = doc.get('metadata', {})
                else:
                    logger.warning(f"[{company_id}] Unknown document type: {type(doc)}")
                    content = str(doc)
                    metadata = {}
                
                # Crear resultado API estandarizado
                api_result = {
                    'id': metadata.get('doc_id', f'doc_{i}'),
                    'title': metadata.get('title') or metadata.get('name') or 'Sin título',
                    'content': content,
                    'excerpt': content[:200] + ('...' if len(content) > 200 else ''),
                    'metadata': metadata,
                    'relevance': metadata.get('score', 1.0),
                    'score': metadata.get('score', 1.0),
                    'type': metadata.get('file_type') or metadata.get('type') or 'text',
                    'chunk_index': metadata.get('chunk_index', 0),
                    'created_at': metadata.get('processed_at') or metadata.get('created_at', ''),
                    'company_id': metadata.get('company_id', company_id),
                    'doc_id': metadata.get('doc_id', f'doc_{i}'),
                    '_id': metadata.get('doc_id', f'doc_{i}')  # Para compatibilidad con frontend
                }
                api_results.append(api_result)
                
            except Exception as result_error:
                logger.warning(f"[{company_id}] Error processing search result {i}: {result_error}")
                continue
        
        logger.info(f"[{company_id}] Search completed: {len(api_results)} results processed")
        
        return create_success_response({
            "company_id": company_id,
            "query": query,
            "results_count": len(api_results),
            "results": api_results,
            "search_method": "vectorstore" if 'search_error' not in locals() else "fallback",
            "limit": k
        })
        
    except Exception as e:
        logger.error(f"Error searching documents for company {company_id if 'company_id' in locals() else 'unknown'}: {e}", exc_info=True)
        return create_error_response(
            f"Search failed: {str(e)}", 
            500,
            {
                "company_id": company_id if 'company_id' in locals() else 'unknown',
                "error_type": type(e).__name__
            }
        )


@bp.route('/<doc_id>', methods=['GET'])
@handle_errors  
def get_document(doc_id):
    """🔧 CORREGIDO: Get document with proper company isolation"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Mejor manejo de doc_id
        original_doc_id = str(doc_id).strip()
        logger.info(f"[{company_id}] Getting document: {original_doc_id}")
        
        # Probar diferentes formatos de doc_id
        possible_doc_ids = [
            original_doc_id,  # Como viene
            f"{company_id}_{original_doc_id}",  # Con prefijo de empresa
            original_doc_id.replace(f"{company_id}_", "")  # Sin prefijo si ya lo tiene
        ]
        
        # Remover duplicados manteniendo orden
        seen = set()
        unique_doc_ids = []
        for doc_id_variant in possible_doc_ids:
            if doc_id_variant not in seen:
                seen.add(doc_id_variant)
                unique_doc_ids.append(doc_id_variant)
        
        # Obtener manager y cliente Redis
        doc_manager = DocumentManager(company_id=company_id)
        redis_client = doc_manager.redis_client
        redis_prefix = doc_manager.redis_prefix
        
        # Intentar encontrar el documento con diferentes formatos
        doc_data = None
        found_doc_id = None
        
        for doc_id_variant in unique_doc_ids:
            doc_key = f"{redis_prefix}{doc_id_variant}"
            logger.debug(f"[{company_id}] Trying Redis key: {doc_key}")
            
            if redis_client.exists(doc_key):
                doc_data = redis_client.hgetall(doc_key)
                found_doc_id = doc_id_variant
                logger.info(f"[{company_id}] Document found with key: {doc_key}")
                break
        
        if not doc_data:
            logger.warning(f"[{company_id}] Document not found. Tried keys: {[f'{redis_prefix}{did}' for did in unique_doc_ids]}")
            return create_error_response("Document not found", 404)
        
        # Mejor procesamiento de datos Redis
        def decode_redis_value(value, default=''):
            """Decodifica valores de Redis manejando bytes y strings"""
            if value is None:
                return default
            if isinstance(value, bytes):
                return value.decode('utf-8')
            return str(value)
        
        # Extraer datos con decodificación segura
        content = decode_redis_value(doc_data.get('content'), '')
        metadata_str = decode_redis_value(doc_data.get('metadata'), '{}')
        created_at = decode_redis_value(doc_data.get('created_at'), '')
        
        # Parsear metadata JSON
        try:
            metadata = json.loads(metadata_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"[{company_id}] Invalid metadata JSON for document {found_doc_id}: {e}")
            metadata = {}
        
        # Verificar que el documento pertenece a la empresa correcta
        doc_company = metadata.get('company_id', '')
        if doc_company and doc_company != company_id:
            logger.warning(f"[{company_id}] Access denied: document {found_doc_id} belongs to {doc_company}")
            return create_error_response("Document not found", 404)  # No revelar que existe pero pertenece a otra empresa
        
        # Construir respuesta robusta
        document = {
            "id": found_doc_id,
            "_id": found_doc_id,
            "doc_id": found_doc_id,
            "title": metadata.get('title') or metadata.get('name') or 'Sin título',
            "content": content,
            "metadata": metadata,
            "created_at": created_at,
            "company_id": company_id,
            "type": metadata.get('file_type') or metadata.get('type') or 'text',
            "size": metadata.get('size', 0),
            
            # Campos adicionales para compatibilidad
            "name": metadata.get('title') or metadata.get('name') or 'Sin título',
            "filename": metadata.get('filename', ''),
            "document_type": metadata.get('file_type') or metadata.get('type') or 'text',
            "status": "active"
        }
        
        logger.info(f"[{company_id}] Document retrieved successfully: {found_doc_id} (title: {document['title']})")
        
        return create_success_response(document)
        
    except Exception as e:
        logger.error(f"Error getting document {doc_id}: {e}", exc_info=True)
        return create_error_response(f"Failed to get document: {str(e)}", 500)


# 🆕 NUEVO: Endpoint de diagnóstico para debugging
@bp.route('/<doc_id>/debug', methods=['GET'])
@handle_errors
def debug_document(doc_id):
    """Debug endpoint para investigar problemas con documentos"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        doc_manager = DocumentManager(company_id=company_id)
        redis_client = doc_manager.redis_client
        redis_prefix = doc_manager.redis_prefix
        
        # Generar variantes de doc_id
        original_doc_id = str(doc_id).strip()
        possible_doc_ids = [
            original_doc_id,
            f"{company_id}_{original_doc_id}",
            original_doc_id.replace(f"{company_id}_", "")
        ]
        
        # Información de diagnóstico
        debug_info = {
            "original_doc_id": original_doc_id,
            "company_id": company_id,
            "redis_prefix": redis_prefix,
            "possible_doc_ids": possible_doc_ids,
            "redis_keys_checked": [],
            "keys_found": [],
            "keys_not_found": [],
            "redis_connection": False,
            "sample_document_keys": []
        }
        
        try:
            # Test Redis connection
            redis_client.ping()
            debug_info["redis_connection"] = True
            
            # Check cada variante
            for doc_id_variant in possible_doc_ids:
                doc_key = f"{redis_prefix}{doc_id_variant}"
                debug_info["redis_keys_checked"].append(doc_key)
                
                if redis_client.exists(doc_key):
                    debug_info["keys_found"].append(doc_key)
                    
                    # Verificar company_id en metadata
                    doc_data = redis_client.hgetall(doc_key)
                    metadata_str = doc_data.get('metadata', '{}')
                    if isinstance(metadata_str, bytes):
                        metadata_str = metadata_str.decode('utf-8')
                    
                    try:
                        metadata = json.loads(metadata_str)
                        debug_info[f"company_in_metadata_{doc_id_variant}"] = metadata.get('company_id', 'NOT_SET')
                    except:
                        debug_info[f"company_in_metadata_{doc_id_variant}"] = 'INVALID_JSON'
                        
                else:
                    debug_info["keys_not_found"].append(doc_key)
            
            # Get sample document keys for this company
            pattern = f"{redis_prefix}*"
            sample_keys = redis_client.keys(pattern)[:10]  # Primeros 10
            debug_info["sample_document_keys"] = [key.decode() if isinstance(key, bytes) else key for key in sample_keys]
            
        except Exception as redis_error:
            debug_info["redis_error"] = str(redis_error)
        
        return create_success_response(debug_info)
        
    except Exception as e:
        return create_error_response(f"Debug failed: {str(e)}", 500)


# Resto de endpoints mantienen la misma estructura...
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
        
        # Usar método flexible para JSON
        data = _get_json_data_flexible()
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
        
        data = _get_json_data_flexible() or {}
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

# Resto de endpoints sin cambios...
@bp.route('/<doc_id>/vectors', methods=['GET'])
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
        
        # Simulación de vectores
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

@bp.route('/stats', methods=['GET'])
def get_documents_stats():
    """Obtener estadísticas REALES de documentos para una empresa"""
    try:
        company_id = request.args.get('company_id') or request.headers.get('X-Company-ID')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        logger.info(f"[{company_id}] Getting REAL document statistics")
        
        # ✅ OBTENER ESTADÍSTICAS REALES
        doc_manager = DocumentManager(company_id=company_id)
        
        # Obtener estadísticas completas
        real_stats = doc_manager.get_document_statistics()
        
        # Agregar company_id
        real_stats['company_id'] = company_id
        
        logger.info(f"[{company_id}] Stats calculated: {real_stats['total_documents']} docs, "
                   f"{real_stats['total_chunks']} chunks, {real_stats['storage_used']}")
        
        return create_success_response({
            "stats": real_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting REAL document stats for company {company_id}: {e}")
        return create_error_response(str(e), 500)
