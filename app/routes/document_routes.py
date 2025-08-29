from flask import Blueprint, request, jsonify, current_app
from app.models.document import MultiCompanyDocumentManager
from app.services.vectorstore_service import MultiCompanyVectorstoreService
from app.config.company_config import get_company_config_manager, get_company_config
import logging
import json
from datetime import datetime
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Initialize multi-company services
multi_company_documents = MultiCompanyDocumentManager()
multi_company_vectorstore = MultiCompanyVectorstoreService()

document_bp = Blueprint('documents', __name__)

@document_bp.route('/documents', methods=['POST'])
def add_documents():
    """Add documents with multi-company support"""
    
    start_time = time.time()
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "No data provided"
            }), 400
        
        # Extract or determine company_id
        company_id = data.get('company_id')
        if not company_id:
            # Try to infer from request headers or use default
            company_id = request.headers.get('X-Company-ID', 'default')
        
        logger.info(f"Adding documents for company: {company_id}")
        
        # Validate company exists
        company_config_manager = get_company_config_manager()
        if not company_config_manager.validate_company_config(company_id):
            return jsonify({
                "status": "error",
                "error": f"Invalid company_id: {company_id}"
            }), 400
        
        # Get company-specific services
        document_manager = multi_company_documents.get_manager_for_company(company_id)
        vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
        company_config = get_company_config(company_id)
        
        # Extract documents
        documents = data.get('documents', [])
        if not documents:
            return jsonify({
                "status": "error",
                "error": "No documents provided"
            }), 400
        
        # Validate documents format
        for i, doc in enumerate(documents):
            if not isinstance(doc, dict):
                return jsonify({
                    "status": "error",
                    "error": f"Document {i} must be an object"
                }), 400
            
            if not doc.get('content'):
                return jsonify({
                    "status": "error",
                    "error": f"Document {i} missing required 'content' field"
                }), 400
        
        # Process documents
        result = document_manager.bulk_add_documents(documents, vectorstore_service)
        
        processing_time = time.time() - start_time
        result.update({
            "processing_time": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Documents added for company {company_id}: {result.get('documents_added', 0)} docs in {processing_time:.2f}s")
        
        return jsonify(result), 200
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception(f"Error adding documents after {processing_time:.2f}s")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "processing_time": round(processing_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/<company_id>', methods=['GET'])
def list_company_documents(company_id: str):
    """List documents for a specific company"""
    
    try:
        # Validate company
        company_config_manager = get_company_config_manager()
        if not company_config_manager.validate_company_config(company_id):
            return jsonify({
                "status": "error",
                "error": f"Invalid company_id: {company_id}"
            }), 400
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        # Validate pagination
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 50
        
        # Get company-specific document manager
        document_manager = multi_company_documents.get_manager_for_company(company_id)
        
        # List documents
        result = document_manager.list_documents(page=page, page_size=page_size)
        result["timestamp"] = datetime.utcnow().isoformat()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.exception(f"Error listing documents for company {company_id}")
        
        return jsonify({
            "status": "error",
            "company_id": company_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents', methods=['GET'])
def list_all_documents():
    """List documents across all companies"""
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        # Get optional company filter
        company_filter = request.args.get('company_id')
        
        if company_filter:
            # List documents for specific company
            return list_company_documents(company_filter)
        
        # Get global document statistics
        global_stats = multi_company_documents.get_global_document_stats()
        
        # Add pagination info (for future implementation of cross-company pagination)
        global_stats.update({
            "pagination": {
                "page": page,
                "page_size": page_size,
                "note": "Cross-company pagination not implemented. Use /documents/{company_id} for company-specific pagination."
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return jsonify(global_stats), 200
        
    except Exception as e:
        logger.exception("Error listing all documents")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/<company_id>/<doc_id>', methods=['DELETE'])
def delete_document(company_id: str, doc_id: str):
    """Delete a specific document from a company"""
    
    try:
        # Validate company
        company_config_manager = get_company_config_manager()
        if not company_config_manager.validate_company_config(company_id):
            return jsonify({
                "status": "error",
                "error": f"Invalid company_id: {company_id}"
            }), 400
        
        # Get company-specific services
        document_manager = multi_company_documents.get_manager_for_company(company_id)
        vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
        
        # Delete document
        result = document_manager.delete_document(doc_id, vectorstore_service)
        result["timestamp"] = datetime.utcnow().isoformat()
        
        if result.get("found"):
            logger.info(f"Document deleted: {doc_id} from company {company_id}")
            return jsonify(result), 200
        else:
            logger.warning(f"Document not found: {doc_id} in company {company_id}")
            return jsonify(result), 404
            
    except Exception as e:
        logger.exception(f"Error deleting document {doc_id} from company {company_id}")
        
        return jsonify({
            "status": "error",
            "company_id": company_id,
            "doc_id": doc_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/search', methods=['POST'])
def search_documents():
    """Search documents with multi-company support"""
    
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "No data provided"
            }), 400
        
        # Extract search parameters
        query = data.get('query')
        if not query or not query.strip():
            return jsonify({
                "status": "error",
                "error": "Query parameter is required"
            }), 400
        
        company_id = data.get('company_id')
        if not company_id:
            return jsonify({
                "status": "error",
                "error": "company_id parameter is required"
            }), 400
        
        k = data.get('k', 5)  # Number of results to return
        
        # Validate company
        company_config_manager = get_company_config_manager()
        if not company_config_manager.validate_company_config(company_id):
            return jsonify({
                "status": "error",
                "error": f"Invalid company_id: {company_id}"
            }), 400
        
        # Get company-specific vectorstore service
        vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
        company_config = get_company_config(company_id)
        
        # Perform search
        start_time = time.time()
        search_results = vectorstore_service.search(query, k=k)
        search_time = time.time() - start_time
        
        result = {
            "status": "success",
            "company_id": company_id,
            "company_name": company_config.company_name,
            "query": query,
            "results_count": len(search_results),
            "results": search_results,
            "search_time": round(search_time, 3),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Document search completed for company {company_id}: {len(search_results)} results in {search_time:.3f}s")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.exception("Error in document search")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/diagnostics/<company_id>', methods=['GET'])
def get_company_diagnostics(company_id: str):
    """Get diagnostics for a specific company's documents and vectors"""
    
    try:
        # Validate company
        company_config_manager = get_company_config_manager()
        if not company_config_manager.validate_company_config(company_id):
            return jsonify({
                "status": "error",
                "error": f"Invalid company_id: {company_id}"
            }), 400
        
        # Get company-specific services
        document_manager = multi_company_documents.get_manager_for_company(company_id)
        vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
        
        # Get diagnostics
        diagnostics = document_manager.get_diagnostics(vectorstore_service)
        diagnostics["timestamp"] = datetime.utcnow().isoformat()
        
        return jsonify(diagnostics), 200
        
    except Exception as e:
        logger.exception(f"Error getting diagnostics for company {company_id}")
        
        return jsonify({
            "status": "error",
            "company_id": company_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/cleanup', methods=['POST'])
def cleanup_documents():
    """Clean up orphaned vectors with multi-company support"""
    
    try:
        # Get request data
        data = request.get_json() or {}
        
        # Extract parameters
        company_id = data.get('company_id')
        dry_run = data.get('dry_run', True)
        
        if company_id:
            # Clean up specific company
            company_config_manager = get_company_config_manager()
            if not company_config_manager.validate_company_config(company_id):
                return jsonify({
                    "status": "error",
                    "error": f"Invalid company_id: {company_id}"
                }), 400
            
            # Get company-specific services
            document_manager = multi_company_documents.get_manager_for_company(company_id)
            vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
            
            # Run cleanup
            result = document_manager.cleanup_orphaned_vectors(vectorstore_service, dry_run=dry_run)
            result["timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Cleanup completed for company {company_id}: {result.get('orphaned_vectors_deleted', 0)} vectors deleted (dry_run: {dry_run})")
            
            return jsonify(result), 200
        
        else:
            # Clean up all companies
            result = multi_company_documents.bulk_cleanup_all_companies(dry_run=dry_run)
            result["timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Global cleanup completed: {result.get('global_summary', {}).get('total_cleaned_vectors', 0)} vectors deleted (dry_run: {dry_run})")
            
            return jsonify(result), 200
            
    except Exception as e:
        logger.exception("Error in document cleanup")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/vectorstore/health', methods=['GET'])
def vectorstore_health():
    """Get vectorstore health status across all companies"""
    
    try:
        # Get optional company filter
        company_id = request.args.get('company_id')
        
        if company_id:
            # Check specific company
            company_config_manager = get_company_config_manager()
            if not company_config_manager.validate_company_config(company_id):
                return jsonify({
                    "status": "error",
                    "error": f"Invalid company_id: {company_id}"
                }), 400
            
            vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
            health_result = vectorstore_service.check_health()
            
            return jsonify(health_result), 200
        
        else:
            # Get global health status
            global_health = multi_company_vectorstore.get_global_health()
            
            return jsonify(global_health), 200
            
    except Exception as e:
        logger.exception("Error checking vectorstore health")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/vectorstore/recovery/<company_id>', methods=['POST'])
def force_vectorstore_recovery(company_id: str):
    """Force vectorstore index recovery for a specific company"""
    
    try:
        # Validate company
        company_config_manager = get_company_config_manager()
        if not company_config_manager.validate_company_config(company_id):
            return jsonify({
                "status": "error",
                "error": f"Invalid company_id: {company_id}"
            }), 400
        
        # Get company-specific vectorstore service
        vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
        company_config = get_company_config(company_id)
        
        # Attempt recovery
        start_time = time.time()
        success = vectorstore_service.force_recovery()
        recovery_time = time.time() - start_time
        
        result = {
            "status": "success" if success else "error",
            "company_id": company_id,
            "company_name": company_config.company_name,
            "recovery_successful": success,
            "recovery_time": round(recovery_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            logger.info(f"Vectorstore recovery successful for company {company_id} in {recovery_time:.2f}s")
            
            # Get updated health status
            health_result = vectorstore_service.check_health()
            result["health_after_recovery"] = health_result
            
            return jsonify(result), 200
        else:
            logger.error(f"Vectorstore recovery failed for company {company_id}")
            result["error"] = "Recovery failed"
            return jsonify(result), 500
            
    except Exception as e:
        logger.exception(f"Error in vectorstore recovery for company {company_id}")
        
        return jsonify({
            "status": "error",
            "company_id": company_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/stats', methods=['GET'])
def document_statistics():
    """Get comprehensive document statistics across all companies"""
    
    try:
        # Get global document statistics
        doc_stats = multi_company_documents.get_global_document_stats()
        
        # Get global vectorstore health
        vectorstore_health = multi_company_vectorstore.get_global_health()
        
        # Combine statistics
        combined_stats = {
            "overview": {
                "total_companies": doc_stats.get("total_companies", 0),
                "total_documents": doc_stats.get("global_totals", {}).get("documents", 0),
                "total_chunks": doc_stats.get("global_totals", {}).get("chunks", 0),
                "companies_with_docs": doc_stats.get("global_totals", {}).get("companies_with_docs", 0),
                "healthy_vectorstores": vectorstore_health.get("global_summary", {}).get("healthy_companies", 0)
            },
            "documents": doc_stats,
            "vectorstore": vectorstore_health,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return jsonify(combined_stats), 200
        
    except Exception as e:
        logger.exception("Error getting document statistics")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@document_bp.route('/documents/companies', methods=['GET'])
def list_document_companies():
    """List all companies with document data"""
    
    try:
        company_config_manager = get_company_config_manager()
        all_companies = company_config_manager.get_all_companies()
        
        companies_info = []
        for company_id, config in all_companies.items():
            try:
                # Get document manager for company
                document_manager = multi_company_documents.get_manager_for_company(company_id)
                vectorstore_service = multi_company_vectorstore.get_service_for_company(company_id)
                
                # Get basic stats
                doc_list = document_manager.list_documents(page=1, page_size=1)
                health_check = vectorstore_service.check_health()
                
                companies_info.append({
                    "company_id": company_id,
                    "company_name": config.company_name,
                    "industry_type": config.industry_type,
                    "vectorstore_index": config.vectorstore_index,
                    "total_documents": doc_list.get("total_documents", 0),
                    "vectorstore_healthy": health_check.get("healthy", False),
                    "company_documents": health_check.get("company_documents", 0)
                })
                
            except Exception as e:
                logger.warning(f"Error getting info for company {company_id}: {e}")
                companies_info.append({
                    "company_id": company_id,
                    "company_name": config.company_name,
                    "industry_type": config.industry_type,
                    "vectorstore_index": config.vectorstore_index,
                    "error": str(e)
                })
        
        return jsonify({
            "total_companies": len(companies_info),
            "companies": companies_info,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception("Error listing document companies")
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# Error handlers
@document_bp.errorhandler(400)
def handle_bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        "status": "error",
        "error": "Bad request",
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }), 400

@document_bp.errorhandler(404)
def handle_not_found(error):
    """Handle not found errors"""
    return jsonify({
        "status": "error",
        "error": "Endpoint not found",
        "message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }), 404

@document_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle internal server errors"""
    logger.exception("Internal server error in document routes")
    return jsonify({
        "status": "error",
        "error": "Internal server error",
        "timestamp": datetime.utcnow().isoformat()
    }), 500
