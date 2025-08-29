from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_config, CompanyConfig
from datetime import datetime
import hashlib
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class DocumentManager:
    """Manager for document operations - Multi-Company"""
    
    def __init__(self, company_id: str = "default"):
        self.redis_client = get_redis_client()
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.redis_prefix = self.company_config.redis_prefix
        self.change_tracker = DocumentChangeTracker(self.redis_client, company_id)
    
    def _get_document_key(self, doc_id: str) -> str:
        """Get Redis key for document with company prefix"""
        return f"{self.redis_prefix}document:{doc_id}"
    
    def add_document(self, content: str, metadata: Dict[str, Any], 
                    vectorstore_service) -> Tuple[str, int]:
        """Add a single document with company isolation"""
        # Generate doc_id with company prefix for uniqueness
        content_hash = hashlib.md5(content.encode()).hexdigest()
        doc_id = f"{self.company_id}_{content_hash}"
        
        # Add company metadata
        metadata.update({
            'doc_id': doc_id,
            'company_id': self.company_id,
            'company_name': self.company_config.company_name
        })
        
        # Create chunks
        texts, chunk_metadatas = vectorstore_service.create_chunks(content)
        
        # Add doc_id and company info to all chunk metadata
        for i, chunk_meta in enumerate(chunk_metadatas):
            chunk_meta.update(metadata)
            chunk_meta['chunk_index'] = i
        
        # Add to vectorstore
        vectorstore_service.add_texts(texts, chunk_metadatas)
        
        # Save document in Redis with company prefix
        doc_key = self._get_document_key(doc_id)
        doc_data = {
            'doc_id': doc_id,
            'content': content,
            'metadata': json.dumps(metadata),
            'created_at': datetime.utcnow().isoformat(),
            'chunk_count': str(len(texts)),
            'company_id': self.company_id,
            'company_name': self.company_config.company_name
        }
        
        self.redis_client.hset(doc_key, mapping=doc_data)
        
        # Track change
        self.change_tracker.register_document_change(doc_id, 'added')
        
        logger.info(f"Document {doc_id} added for company {self.company_id} with {len(texts)} chunks")
        return doc_id, len(texts)
    
    def bulk_add_documents(self, documents: List[Dict[str, Any]], 
                          vectorstore_service) -> Dict[str, Any]:
        """Bulk add multiple documents for this company"""
        added_docs = 0
        total_chunks = 0
        errors = []
        added_doc_ids = []
        
        for i, doc_data in enumerate(documents):
            try:
                content = doc_data.get('content', '').strip()
                metadata = doc_data.get('metadata', {})
                
                if not content:
                    raise ValueError("Content cannot be empty")
                
                # Ensure company metadata is set
                metadata.update({
                    'company_id': self.company_id,
                    'company_name': self.company_config.company_name,
                    'batch_index': i
                })
                
                doc_id, num_chunks = self.add_document(content, metadata, vectorstore_service)
                
                added_docs += 1
                total_chunks += num_chunks
                added_doc_ids.append(doc_id)
                
            except Exception as e:
                errors.append(f"Document {i}: {str(e)}")
                continue
        
        response_data = {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "documents_added": added_docs,
            "total_chunks": total_chunks,
            "message": f"Added {added_docs} documents with {total_chunks} chunks for {self.company_config.company_name}",
            "added_doc_ids": added_doc_ids
        }
        
        if errors:
            response_data["errors"] = errors
        
        return response_data
    
    def delete_document(self, doc_id: str, vectorstore_service) -> Dict[str, Any]:
        """Delete a document and its vectors (company-safe)"""
        doc_key = self._get_document_key(doc_id)
        
        # Verify document exists and belongs to this company
        if not self.redis_client.exists(doc_key):
            return {"found": False, "company_id": self.company_id}
        
        # Verify company ownership
        doc_data = self.redis_client.hgetall(doc_key)
        doc_company_id = doc_data.get('company_id', self.company_id)
        
        if doc_company_id != self.company_id:
            logger.warning(f"Attempted to delete document {doc_id} from wrong company. Doc belongs to {doc_company_id}, attempted by {self.company_id}")
            return {"found": False, "error": "Document not found or access denied", "company_id": self.company_id}
        
        # Find and delete vectors (company-safe)
        vectors = vectorstore_service.find_vectors_by_doc_id(doc_id)
        vectors_deleted = vectorstore_service.delete_vectors(vectors)
        
        # Delete document
        self.redis_client.delete(doc_key)
        
        # Track change
        self.change_tracker.register_document_change(doc_id, 'deleted')
        
        return {
            "found": True,
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "message": "Document deleted successfully",
            "vectors_deleted": vectors_deleted
        }
    
    def list_documents(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """List documents for this company with pagination"""
        doc_pattern = f"{self.redis_prefix}document:*"
        doc_keys = self.redis_client.keys(doc_pattern)
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_keys = doc_keys[start_idx:end_idx]
        
        documents = []
        for key in paginated_keys:
            try:
                doc_data = self.redis_client.hgetall(key)
                if not doc_data:
                    continue
                
                # Verify company ownership
                doc_company_id = doc_data.get('company_id', self.company_id)
                if doc_company_id != self.company_id:
                    continue
                
                doc_id = key.split(':', -1)[-1]  # Get last part after final ':'
                content = doc_data.get('content', '')
                metadata = json.loads(doc_data.get('metadata', '{}'))
                
                documents.append({
                    "id": doc_id,
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "metadata": metadata,
                    "created_at": doc_data.get('created_at'),
                    "chunk_count": int(doc_data.get('chunk_count', 0)),
                    "company_id": self.company_id,
                    "company_name": self.company_config.company_name
                })
                
            except Exception as e:
                logger.warning(f"Error parsing document {key}: {e}")
                continue
        
        return {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "total_documents": len(doc_keys),
            "page": page,
            "page_size": page_size,
            "documents": documents
        }
    
    def cleanup_orphaned_vectors(self, vectorstore_service, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up orphaned vectors for this company"""
        # Get all documents for this company
        doc_keys = self.redis_client.keys(f"{self.redis_prefix}document:*")
        existing_doc_ids = set()
        
        for key in doc_keys:
            try:
                doc_data = self.redis_client.hgetall(key)
                doc_company_id = doc_data.get('company_id', self.company_id)
                if doc_company_id == self.company_id:
                    doc_id = key.split(':', -1)[-1]
                    existing_doc_ids.add(doc_id)
            except:
                continue
        
        # Get all vectors for this company's index
        vector_pattern = f"{vectorstore_service.index_name}:*"
        vector_keys = self.redis_client.keys(vector_pattern)
        
        orphaned_vectors = []
        
        for vector_key in vector_keys:
            try:
                doc_id = None
                
                # Check direct field
                doc_id_direct = self.redis_client.hget(vector_key, 'doc_id')
                if doc_id_direct:
                    doc_id = doc_id_direct
                else:
                    # Check metadata
                    metadata_str = self.redis_client.hget(vector_key, 'metadata')
                    if metadata_str:
                        metadata = json.loads(metadata_str)
                        doc_id = metadata.get('doc_id')
                        
                        # Verify this vector belongs to our company
                        vector_company_id = metadata.get('company_id')
                        if vector_company_id and vector_company_id != self.company_id:
                            continue  # Skip vectors from other companies
                
                # Check if doc exists and is orphaned
                if doc_id and doc_id not in existing_doc_ids:
                    orphaned_vectors.append({
                        "vector_key": vector_key,
                        "doc_id": doc_id
                    })
                    
            except Exception as e:
                logger.warning(f"Error checking vector {vector_key}: {e}")
                continue
        
        # Delete if not dry run
        deleted_count = 0
        if not dry_run and orphaned_vectors:
            keys_to_delete = [v["vector_key"] for v in orphaned_vectors]
            deleted_count = vectorstore_service.delete_vectors(keys_to_delete)
        
        return {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "total_vectors_checked": len(vector_keys),
            "total_company_documents": len(existing_doc_ids),
            "orphaned_vectors_found": len(orphaned_vectors),
            "orphaned_vectors_deleted": deleted_count,
            "dry_run": dry_run,
            "orphaned_samples": orphaned_vectors[:10]
        }
    
    def get_diagnostics(self, vectorstore_service) -> Dict[str, Any]:
        """Get system diagnostics for this company"""
        doc_keys = self.redis_client.keys(f"{self.redis_prefix}document:*")
        vector_keys = self.redis_client.keys(f"{vectorstore_service.index_name}:*")
        
        # Filter documents by company
        company_doc_count = 0
        for key in doc_keys:
            try:
                doc_data = self.redis_client.hgetall(key)
                if doc_data.get('company_id', self.company_id) == self.company_id:
                    company_doc_count += 1
            except:
                continue
        
        # Analyze vectors for this company
        doc_id_counts = {}
        vectors_without_doc_id = 0
        company_vector_count = 0
        
        for vector_key in vector_keys:
            try:
                doc_id = None
                vector_company_id = None
                
                # Get doc_id from direct field
                doc_id_direct = self.redis_client.hget(vector_key, 'doc_id')
                if doc_id_direct:
                    doc_id = doc_id_direct
                
                # Get metadata
                metadata_str = self.redis_client.hget(vector_key, 'metadata')
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    if not doc_id:
                        doc_id = metadata.get('doc_id')
                    vector_company_id = metadata.get('company_id')
                
                # Only count vectors that belong to this company
                if vector_company_id == self.company_id or (not vector_company_id and doc_id and doc_id.startswith(f"{self.company_id}_")):
                    company_vector_count += 1
                    
                    if doc_id:
                        doc_id_counts[doc_id] = doc_id_counts.get(doc_id, 0) + 1
                    else:
                        vectors_without_doc_id += 1
                
            except Exception as e:
                logger.warning(f"Error analyzing vector: {e}")
                continue
        
        # Find orphaned documents (documents without vectors)
        orphaned_docs = []
        for key in doc_keys:
            try:
                doc_data = self.redis_client.hgetall(key)
                if doc_data.get('company_id', self.company_id) == self.company_id:
                    doc_id = key.split(':', -1)[-1]
                    if doc_id not in doc_id_counts:
                        orphaned_docs.append(doc_id)
            except:
                continue
        
        return {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "total_documents": company_doc_count,
            "total_company_vectors": company_vector_count,
            "vectors_without_doc_id": vectors_without_doc_id,
            "documents_with_vectors": len(doc_id_counts),
            "orphaned_documents": len(orphaned_docs),
            "avg_vectors_per_doc": round(sum(doc_id_counts.values()) / len(doc_id_counts), 2) if doc_id_counts else 0,
            "sample_doc_vector_counts": dict(list(doc_id_counts.items())[:10]),
            "orphaned_doc_samples": orphaned_docs[:5]
        }


class DocumentChangeTracker:
    """Track document changes for cache invalidation - Multi-Company"""
    
    def __init__(self, redis_client, company_id: str = "default"):
        self.redis_client = redis_client
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.redis_prefix = self.company_config.redis_prefix
        self.version_key = f"{self.redis_prefix}vectorstore_version"
        self.doc_hash_key = f"{self.redis_prefix}document_hashes"
    
    def get_current_version(self) -> int:
        """Get current version of vectorstore for this company"""
        try:
            version = self.redis_client.get(self.version_key)
            return int(version) if version else 0
        except:
            return 0
    
    def increment_version(self):
        """Increment version of vectorstore for this company"""
        try:
            self.redis_client.incr(self.version_key)
            logger.info(f"Vectorstore version incremented to {self.get_current_version()} for company {self.company_id}")
        except Exception as e:
            logger.error(f"Error incrementing version for company {self.company_id}: {e}")
    
    def register_document_change(self, doc_id: str, change_type: str):
        """Register document change for this company"""
        try:
            change_data = {
                'doc_id': doc_id,
                'change_type': change_type,
                'company_id': self.company_id,
                'company_name': self.company_config.company_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            change_key = f"{self.redis_prefix}doc_change:{doc_id}:{int(time.time())}"
            self.redis_client.setex(change_key, 3600, json.dumps(change_data))
            
            self.increment_version()
            
            logger.info(f"Document change registered for company {self.company_id}: {doc_id} - {change_type}")
            
        except Exception as e:
            logger.error(f"Error registering document change for company {self.company_id}: {e}")


class MultiCompanyDocumentManager:
    """Manager for documents across multiple companies"""
    
    def __init__(self):
        self.company_managers = {}
    
    def get_manager_for_company(self, company_id: str) -> DocumentManager:
        """Get document manager for specific company"""
        if company_id not in self.company_managers:
            self.company_managers[company_id] = DocumentManager(company_id)
        
        return self.company_managers[company_id]
    
    def get_global_document_stats(self) -> Dict[str, Any]:
        """Get document statistics across all companies"""
        global_stats = {
            "total_companies": len(self.company_managers),
            "companies": {},
            "global_totals": {
                "documents": 0,
                "chunks": 0,
                "companies_with_docs": 0
            }
        }
        
        for company_id, manager in self.company_managers.items():
            try:
                # Get basic document count for this company
                doc_pattern = f"{manager.redis_prefix}document:*"
                doc_keys = manager.redis_client.keys(doc_pattern)
                
                company_doc_count = 0
                total_chunks = 0
                
                for key in doc_keys:
                    try:
                        doc_data = manager.redis_client.hgetall(key)
                        if doc_data.get('company_id', company_id) == company_id:
                            company_doc_count += 1
                            total_chunks += int(doc_data.get('chunk_count', 0))
                    except:
                        continue
                
                company_stats = {
                    "company_id": company_id,
                    "company_name": manager.company_config.company_name,
                    "documents": company_doc_count,
                    "total_chunks": total_chunks
                }
                
                global_stats["companies"][company_id] = company_stats
                
                # Update global totals
                global_stats["global_totals"]["documents"] += company_doc_count
                global_stats["global_totals"]["chunks"] += total_chunks
                
                if company_doc_count > 0:
                    global_stats["global_totals"]["companies_with_docs"] += 1
                
            except Exception as e:
                logger.error(f"Error getting stats for company {company_id}: {e}")
                continue
        
        return global_stats
    
    def bulk_cleanup_all_companies(self, dry_run: bool = True) -> Dict[str, Any]:
        """Run cleanup across all companies"""
        cleanup_results = {
            "companies": {},
            "global_summary": {
                "total_orphaned_vectors": 0,
                "total_cleaned_vectors": 0,
                "companies_processed": 0,
                "companies_with_orphaned_data": 0
            }
        }
        
        for company_id, manager in self.company_managers.items():
            try:
                # Get vectorstore service for this company
                from app.services.vectorstore_service import VectorstoreService
                vectorstore_service = VectorstoreService(company_id)
                
                # Run cleanup
                cleanup_result = manager.cleanup_orphaned_vectors(vectorstore_service, dry_run)
                cleanup_results["companies"][company_id] = cleanup_result
                
                # Update global summary
                cleanup_results["global_summary"]["companies_processed"] += 1
                cleanup_results["global_summary"]["total_orphaned_vectors"] += cleanup_result.get("orphaned_vectors_found", 0)
                cleanup_results["global_summary"]["total_cleaned_vectors"] += cleanup_result.get("orphaned_vectors_deleted", 0)
                
                if cleanup_result.get("orphaned_vectors_found", 0) > 0:
                    cleanup_results["global_summary"]["companies_with_orphaned_data"] += 1
                
            except Exception as e:
                logger.error(f"Error during cleanup for company {company_id}: {e}")
                cleanup_results["companies"][company_id] = {
                    "error": str(e),
                    "company_id": company_id
                }
                continue
        
        return cleanup_results
