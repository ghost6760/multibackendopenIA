from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_config
from datetime import datetime
import hashlib
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manager for document operations multi-tenant"""
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id or "default"
        self.company_config = get_company_config(self.company_id)
        
        # Configurar prefijo específico de empresa
        if self.company_config:
            self.redis_prefix = self.company_config.redis_prefix + "document:"
        else:
            self.redis_prefix = f"{self.company_id}:document:"
        
        self.redis_client = get_redis_client()
        self.change_tracker = DocumentChangeTracker(self.redis_client, self.company_id)
        
        logger.info(f"DocumentManager initialized for company: {self.company_id}")
    
    def add_document(self, content: str, metadata: Dict[str, Any], 
                    vectorstore_service) -> Tuple[str, int]:
        """Add a single document with company isolation"""
        # Generate doc_id with company prefix
        base_doc_id = hashlib.md5(content.encode()).hexdigest()
        doc_id = f"{self.company_id}_{base_doc_id}"
        
        # Enrich metadata with company info
        metadata.update({
            'doc_id': doc_id,
            'company_id': self.company_id,
            'company_name': self.company_config.company_name if self.company_config else self.company_id
        })
        
        # Create chunks
        texts, chunk_metadatas = vectorstore_service.create_chunks(content)
        
        # Add doc_id and company info to all chunk metadata
        for i, chunk_meta in enumerate(chunk_metadatas):
            chunk_meta.update(metadata)
            chunk_meta['chunk_index'] = i
        
        # Add to vectorstore
        vectorstore_service.add_texts(texts, chunk_metadatas)
        
        # Save document in Redis with company-specific key
        doc_key = f"{self.redis_prefix}{doc_id}"
        doc_data = {
            'content': content,
            'metadata': json.dumps(metadata),
            'company_id': self.company_id,
            'created_at': datetime.utcnow().isoformat(),
            'chunk_count': str(len(texts))
        }
        
        self.redis_client.hset(doc_key, mapping=doc_data)
        
        # Track change
        self.change_tracker.register_document_change(doc_id, 'added')
        
        logger.info(f"[{self.company_id}] Document {doc_id} added with {len(texts)} chunks")
        return doc_id, len(texts)
    
    def bulk_add_documents(self, documents: List[Dict[str, Any]], 
                          vectorstore_service) -> Dict[str, Any]:
        """Bulk add multiple documents with company isolation"""
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
                
                doc_id, num_chunks = self.add_document(content, metadata, vectorstore_service)
                
                added_docs += 1
                total_chunks += num_chunks
                added_doc_ids.append(doc_id)
                
            except Exception as e:
                errors.append(f"Document {i}: {str(e)}")
                continue
        
        response_data = {
            "company_id": self.company_id,
            "documents_added": added_docs,
            "total_chunks": total_chunks,
            "message": f"Added {added_docs} documents with {total_chunks} chunks for {self.company_id}"
        }
        
        if errors:
            response_data["errors"] = errors
        
        return response_data
    
    def delete_document(self, doc_id: str, vectorstore_service) -> Dict[str, Any]:
        """Delete a document and its vectors with company verification"""
        # Ensure company prefix
        if not doc_id.startswith(f"{self.company_id}_"):
            doc_id = f"{self.company_id}_{doc_id}"
        
        doc_key = f"{self.redis_prefix}{doc_id}"
        
        if not self.redis_client.exists(doc_key):
            return {"found": False, "company_id": self.company_id}
        
        # Verify company ownership
        doc_data = self.redis_client.hgetall(doc_key)
        doc_company_id = doc_data.get('company_id', '').decode() if isinstance(doc_data.get('company_id'), bytes) else doc_data.get('company_id', '')
        
        if doc_company_id != self.company_id:
            logger.warning(f"Attempt to delete document {doc_id} from wrong company {self.company_id} (owner: {doc_company_id})")
            return {"found": False, "error": "Unauthorized", "company_id": self.company_id}
        
        # Find and delete vectors
        vectors = vectorstore_service.find_vectors_by_doc_id(doc_id)
        vectors_deleted = vectorstore_service.delete_vectors(vectors)
        
        # Delete document
        self.redis_client.delete(doc_key)
        
        # Track change
        self.change_tracker.register_document_change(doc_id, 'deleted')
        
        logger.info(f"[{self.company_id}] Document {doc_id} deleted with {vectors_deleted} vectors")
        
        return {
            "found": True,
            "message": "Document deleted successfully",
            "vectors_deleted": vectors_deleted,
            "company_id": self.company_id
        }
    
    def list_documents(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """List documents with pagination and company isolation"""
        doc_pattern = f"{self.redis_prefix}*"
        doc_keys = self.redis_client.keys(doc_pattern)
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_keys = doc_keys[start_idx:end_idx]
        
        documents = []
        for key in paginated_keys:
            try:
                doc_data = self.redis_client.hgetall(key)
                if doc_data:
                    # Extract doc_id (remove company prefix for display)
                    full_doc_id = key.decode() if isinstance(key, bytes) else key
                    doc_id = full_doc_id.split(':', -1)[-1]  # Get last part after colon
                    
                    content = doc_data.get('content', '')
                    if isinstance(content, bytes):
                        content = content.decode()
                    
                    metadata_str = doc_data.get('metadata', '{}')
                    if isinstance(metadata_str, bytes):
                        metadata_str = metadata_str.decode()
                    
                    try:
                        metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        metadata = {}
                    
                    chunk_count = doc_data.get('chunk_count', '0')
                    if isinstance(chunk_count, bytes):
                        chunk_count = chunk_count.decode()
                    
                    documents.append({
                        "id": doc_id,
                        "content": content[:200] + "..." if len(content) > 200 else content,
                        "metadata": metadata,
                        "created_at": doc_data.get('created_at', '').decode() if isinstance(doc_data.get('created_at'), bytes) else doc_data.get('created_at', ''),
                        "chunk_count": int(chunk_count),
                        "company_id": self.company_id
                    })
                    
            except Exception as e:
                logger.warning(f"[{self.company_id}] Error parsing document {key}: {e}")
                continue
        
        return {
            "company_id": self.company_id,
            "total_documents": len(doc_keys),
            "page": page,
            "page_size": page_size,
            "documents": documents
        }
    
    def cleanup_orphaned_vectors(self, vectorstore_service, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up orphaned vectors for this company only"""
        # Get all documents for this company
        doc_keys = self.redis_client.keys(f"{self.redis_prefix}*")
        existing_doc_ids = set()
        
        for key in doc_keys:
            doc_id = key.decode() if isinstance(key, bytes) else key
            doc_id = doc_id.split(':', -1)[-1]  # Get last part after colon
            existing_doc_ids.add(doc_id)
        
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
                    if isinstance(doc_id_direct, bytes):
                        doc_id_direct = doc_id_direct.decode()
                    doc_id = doc_id_direct
                else:
                    # Check metadata
                    metadata_str = self.redis_client.hget(vector_key, 'metadata')
                    if metadata_str:
                        if isinstance(metadata_str, bytes):
                            metadata_str = metadata_str.decode()
                        try:
                            metadata = json.loads(metadata_str)
                            doc_id = metadata.get('doc_id')
                            vector_company_id = metadata.get('company_id')
                            
                            # Skip if not from this company
                            if vector_company_id != self.company_id:
                                continue
                        except json.JSONDecodeError:
                            continue
                
                if doc_id and doc_id not in existing_doc_ids:
                    # Additional check: verify it belongs to this company
                    if doc_id.startswith(f"{self.company_id}_"):
                        orphaned_vectors.append({
                            "vector_key": vector_key,
                            "doc_id": doc_id
                        })
                    
            except Exception as e:
                logger.warning(f"[{self.company_id}] Error checking vector {vector_key}: {e}")
                continue
        
        # Delete if not dry run
        deleted_count = 0
        if not dry_run and orphaned_vectors:
            keys_to_delete = [v["vector_key"] for v in orphaned_vectors]
            deleted_count = vectorstore_service.delete_vectors(keys_to_delete)
        
        return {
            "company_id": self.company_id,
            "total_vectors": len(vector_keys),
            "total_documents": len(existing_doc_ids),
            "orphaned_vectors_found": len(orphaned_vectors),
            "orphaned_vectors_deleted": deleted_count,
            "dry_run": dry_run,
            "orphaned_samples": orphaned_vectors[:10]
        }
    
    def get_diagnostics(self, vectorstore_service) -> Dict[str, Any]:
        """Get system diagnostics for this company"""
        doc_keys = self.redis_client.keys(f"{self.redis_prefix}*")
        vector_keys = self.redis_client.keys(f"{vectorstore_service.index_name}:*")
        
        # Filter vectors by company
        company_vectors = []
        doc_id_counts = {}
        vectors_without_doc_id = 0
        
        for vector_key in vector_keys:
            try:
                doc_id = None
                vector_company_id = None
                
                doc_id_direct = self.redis_client.hget(vector_key, 'doc_id')
                if doc_id_direct:
                    if isinstance(doc_id_direct, bytes):
                        doc_id_direct = doc_id_direct.decode()
                    doc_id = doc_id_direct
                else:
                    metadata_str = self.redis_client.hget(vector_key, 'metadata')
                    if metadata_str:
                        if isinstance(metadata_str, bytes):
                            metadata_str = metadata_str.decode()
                        try:
                            metadata = json.loads(metadata_str)
                            doc_id = metadata.get('doc_id')
                            vector_company_id = metadata.get('company_id')
                        except json.JSONDecodeError:
                            continue
                
                # Only count vectors from this company
                if vector_company_id == self.company_id or (doc_id and doc_id.startswith(f"{self.company_id}_")):
                    company_vectors.append(vector_key)
                    
                    if doc_id:
                        doc_id_counts[doc_id] = doc_id_counts.get(doc_id, 0) + 1
                    else:
                        vectors_without_doc_id += 1
                    
            except Exception as e:
                logger.warning(f"[{self.company_id}] Error analyzing vector: {e}")
                continue
        
        orphaned_docs = []
        for doc_key in doc_keys:
            doc_id = doc_key.decode() if isinstance(doc_key, bytes) else doc_key
            doc_id = doc_id.split(':', -1)[-1]  # Get last part after colon
            if doc_id not in doc_id_counts:
                orphaned_docs.append(doc_id)
        
        return {
            "company_id": self.company_id,
            "total_documents": len(doc_keys),
            "total_company_vectors": len(company_vectors),
            "vectors_without_doc_id": vectors_without_doc_id,
            "documents_with_vectors": len(doc_id_counts),
            "orphaned_documents": len(orphaned_docs),
            "avg_vectors_per_doc": round(sum(doc_id_counts.values()) / len(doc_id_counts), 2) if doc_id_counts else 0,
            "sample_doc_vector_counts": dict(list(doc_id_counts.items())[:10]),
            "orphaned_doc_samples": orphaned_docs[:5]
        }

    # ============================================================================
    # ✅ AGREGAR AQUÍ - NUEVOS MÉTODOS DE ESTADÍSTICAS
    # ============================================================================
    
    def get_document_statistics(self) -> dict:
        """
        Obtener estadísticas REALES de documentos para la empresa
        
        Returns:
            dict: Estadísticas completas con datos reales de Redis y vectorstore
        """
        try:
            # Inicializar estadísticas
            stats = {
                "total_documents": 0,
                "total_chunks": 0,
                "total_vectors": 0,
                "storage_used": "0 B",
                "storage_bytes": 0,
                "categories": {},
                "file_types": {},
                "last_updated": None,
                "documents_by_month": {},
                "avg_chunks_per_document": 0,
                "oldest_document": None,
                "newest_document": None
            }
            
            # Obtener TODOS los documentos de Redis
            document_pattern = f"{self.redis_prefix}*"
            all_keys = self.redis_client.keys(document_pattern)
            
            # Filtrar solo keys de documentos (no conversations, bot_status, etc)
            document_keys = [
                key for key in all_keys 
                if not any(x in str(key) for x in ['conversation:', 'bot_status:', 'cache:'])
            ]
            
            logger.info(f"[{self.company_id}] Found {len(document_keys)} document keys")
            
            total_size_bytes = 0
            total_chunks = 0
            documents_processed = 0
            
            earliest_date = None
            latest_date = None
            
            # Procesar cada documento
            for key in document_keys:
                try:
                    # Obtener datos del documento
                    doc_data = self.redis_client.hgetall(key)
                    
                    if not doc_data:
                        continue
                    
                    documents_processed += 1
                    
                    # Decodificar valores
                    def decode_value(value, default=''):
                        if value is None:
                            return default
                        if isinstance(value, bytes):
                            return value.decode('utf-8')
                        return str(value)
                    
                    # Obtener metadata
                    metadata_str = decode_value(doc_data.get('metadata'), '{}')
                    try:
                        metadata = json.loads(metadata_str)
                    except:
                        metadata = {}
                    
                    # Calcular tamaño del contenido
                    content = decode_value(doc_data.get('content'), '')
                    content_size = len(content.encode('utf-8'))
                    total_size_bytes += content_size
                    
                    # Contar chunks (desde metadata o doc_data directamente)
                    chunk_count_str = decode_value(doc_data.get('chunk_count'), '0')
                    try:
                        chunk_count = int(chunk_count_str)
                    except:
                        chunk_count = metadata.get('chunk_count', 0)
                    
                    if chunk_count:
                        total_chunks += chunk_count
                    
                    # Extraer categorías de metadata
                    category = metadata.get('category') or metadata.get('type') or 'general'
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1
                    
                    # Tipos de archivo
                    file_type = metadata.get('file_type') or metadata.get('type') or 'text'
                    stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
                    
                    # Fecha de creación
                    created_at = decode_value(doc_data.get('created_at'))
                    if created_at:
                        try:
                            doc_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            
                            # Tracking de fechas
                            if earliest_date is None or doc_date < earliest_date:
                                earliest_date = doc_date
                            if latest_date is None or doc_date > latest_date:
                                latest_date = doc_date
                            
                            # Documentos por mes
                            month_key = doc_date.strftime('%Y-%m')
                            stats['documents_by_month'][month_key] = stats['documents_by_month'].get(month_key, 0) + 1
                        except:
                            pass
                    
                except Exception as e:
                    logger.warning(f"[{self.company_id}] Error processing document key {key}: {e}")
                    continue
            
            # Actualizar stats finales
            stats['total_documents'] = documents_processed
            stats['total_chunks'] = total_chunks
            stats['storage_bytes'] = total_size_bytes
            stats['storage_used'] = self._format_storage_size(total_size_bytes)
            
            # Calcular promedio de chunks por documento
            if documents_processed > 0:
                stats['avg_chunks_per_document'] = round(total_chunks / documents_processed, 2)
            
            # Fechas
            if latest_date:
                stats['last_updated'] = latest_date.isoformat()
                stats['newest_document'] = latest_date.isoformat()
            
            if earliest_date:
                stats['oldest_document'] = earliest_date.isoformat()
            
            # Obtener conteo de vectores desde vectorstore si está disponible
            try:
                from app.services.multi_agent_factory import get_multi_agent_factory
                
                factory = get_multi_agent_factory()
                orchestrator = factory.get_orchestrator(self.company_id)
                
                if orchestrator and orchestrator.vectorstore_service:
                    # Intentar obtener conteo de vectores
                    index = orchestrator.vectorstore_service.redis_client.ft(
                        orchestrator.vectorstore_service.index_name
                    )
                    info = index.info()
                    
                    # El conteo total de documentos en el índice
                    total_vectors = info.get('num_docs', total_chunks)
                    stats['total_vectors'] = total_vectors
                else:
                    # Fallback: asumir 1 vector por chunk
                    stats['total_vectors'] = total_chunks
                    
            except Exception as e:
                logger.warning(f"[{self.company_id}] Could not get vector count: {e}")
                stats['total_vectors'] = total_chunks
            
            logger.info(f"[{self.company_id}] Statistics calculated successfully: "
                       f"{stats['total_documents']} docs, {stats['total_chunks']} chunks, "
                       f"{stats['storage_used']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error calculating statistics: {e}")
            
            # Retornar estadísticas mínimas en caso de error
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "total_vectors": 0,
                "storage_used": "0 B",
                "storage_bytes": 0,
                "categories": {},
                "file_types": {},
                "last_updated": None,
                "error": str(e)
            }
    
    def _format_storage_size(self, bytes_size: int) -> str:
        """
        Formatear tamaño de almacenamiento de forma legible
        
        Args:
            bytes_size: Tamaño en bytes
            
        Returns:
            str: Tamaño formateado (ej: "24.5 MB")
        """
        if bytes_size == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(bytes_size)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        # Formatear con 1-2 decimales
        if size < 10:
            return f"{size:.2f} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"


class DocumentChangeTracker:
    """Track document changes for cache invalidation - Multi-tenant"""
    
    def __init__(self, redis_client, company_id: str):
        self.redis_client = redis_client
        self.company_id = company_id
        self.version_key = f"{company_id}:vectorstore_version"
        self.doc_hash_key = f"{company_id}:document_hashes"
    
    def get_current_version(self) -> int:
        """Get current version of vectorstore for company"""
        try:
            version = self.redis_client.get(self.version_key)
            return int(version) if version else 0
        except:
            return 0
    
    def increment_version(self):
        """Increment version of vectorstore for company"""
        try:
            self.redis_client.incr(self.version_key)
            logger.info(f"[{self.company_id}] Vectorstore version incremented to {self.get_current_version()}")
        except Exception as e:
            logger.error(f"[{self.company_id}] Error incrementing version: {e}")
    
    def register_document_change(self, doc_id: str, change_type: str):
        """Register document change for company"""
        try:
            change_data = {
                'company_id': self.company_id,
                'doc_id': doc_id,
                'change_type': change_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            change_key = f"{self.company_id}:doc_change:{doc_id}:{int(time.time())}"
            self.redis_client.setex(change_key, 3600, json.dumps(change_data))
            
            self.increment_version()
            
            logger.info(f"[{self.company_id}] Document change registered: {doc_id} - {change_type}")
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error registering document change: {e}")
