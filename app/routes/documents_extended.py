from flask import Blueprint, request, jsonify
from app.config.company_config import get_company_manager
from app.utils.helpers import create_success_response, create_error_response
import logging

logger = logging.getLogger(__name__)

# Este blueprint se debe registrar en __init__.py
documents_extended_bp = Blueprint('documents_extended', __name__, url_prefix='/api/documents')

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

@documents_extended_bp.route('/search', methods=['POST'])
def search_documents():
    """Buscar documentos por similitud"""
    try:
        data = request.get_json()
        company_id = data.get('company_id') or request.headers.get('X-Company-ID')
        query = data.get('query')
        limit = data.get('limit', 10)
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        if not query:
            return create_error_response("query is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Búsqueda simulada
        search_results = [
            {
                "document_id": f"doc_{i}",
                "title": f"Documento {i}",
                "content_preview": f"Contenido relacionado con '{query}' en documento {i}...",
                "similarity_score": 0.9 - (i * 0.1),
                "chunk_index": i,
                "metadata": {
                    "category": "general",
                    "file_type": "application/pdf",
                    "company_id": company_id
                }
            }
            for i in range(1, min(limit + 1, 6))
        ]
        
        return create_success_response({
            "results": search_results,
            "query": query,
            "total_results": len(search_results),
            "company_id": company_id
        })
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return create_error_response(str(e), 500)
