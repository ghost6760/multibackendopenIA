from langchain_redis import RedisVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from app.services.redis_service import get_redis_client
from app.services.openai_service import OpenAIService
from app.config.company_config import get_company_config, CompanyConfig
from flask import current_app
import logging
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def init_vectorstore(app):
    """Initialize vectorstore configuration"""
    try:
        # This is mainly for validation at startup
        redis_url = app.config.get('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL not found in configuration")
        
        logger.info("✅ Vectorstore configuration validated")
        return True
    except Exception as e:
        logger.error(f"❌ Vectorstore initialization failed: {e}")
        raise

class VectorstoreService:
    """Service for managing vector storage and retrieval - Multi-Company"""
    
    def __init__(self, company_id: str = "default"):
        self.redis_client = get_redis_client()
        self.openai_service = OpenAIService()
        self.embeddings = self.openai_service.get_embeddings()
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.index_name = self.company_config.vectorstore_index
        self.vector_dim = 1536
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """Initialize the vectorstore with company-specific index"""
        try:
            self.vectorstore = RedisVectorStore(
                self.embeddings,
                redis_url=current_app.config['REDIS_URL'],
                index_name=self.index_name,
                vector_dim=self.vector_dim
            )
            logger.info(f"Vectorstore initialized for company {self.company_id} with index {self.index_name}")
        except Exception as e:
            logger.error(f"Error initializing vectorstore for company {self.company_id}: {e}")
            raise
    
    def get_retriever(self, k: int = 3):
        """Get retriever with specified k"""
        return self.vectorstore.as_retriever(search_kwargs={"k": k})
    
    def test_connection(self):
        """Test vectorstore connection"""
        try:
            self.vectorstore.similarity_search("test", k=1)
            return True
        except Exception as e:
            logger.error(f"Vectorstore connection test failed for company {self.company_id}: {e}")
            raise
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search for similar documents within company context"""
        try:
            docs = self.vectorstore.similarity_search(query, k=k)
            
            results = []
            for doc in docs:
                # Filter by company_id if metadata exists
                doc_metadata = getattr(doc, 'metadata', {})
                doc_company_id = doc_metadata.get('company_id', self.company_id)
                
                # Only return docs from this company
                if doc_company_id == self.company_id:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc_metadata,
                        "score": getattr(doc, 'score', None)
                    })
            
            logger.info(f"Search for company {self.company_id}: {len(results)} relevant docs found")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents for company {self.company_id}: {e}")
            raise
    
    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        """Add texts to vectorstore with company isolation"""
        try:
            # Ensure all metadata includes company_id
            if metadatas:
                for metadata in metadatas:
                    metadata['company_id'] = self.company_id
                    metadata['company_name'] = self.company_config.company_name
            else:
                metadatas = [{'company_id': self.company_id, 'company_name': self.company_config.company_name} for _ in texts]
            
            self.vectorstore.add_texts(texts, metadatas=metadatas)
            logger.info(f"Added {len(texts)} texts to vectorstore for company {self.company_id}")
        except Exception as e:
            logger.error(f"Error adding texts for company {self.company_id}: {e}")
            raise
    
    def create_chunks(self, text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Create chunks from text with advanced splitting"""
        try:
            # Create splitters
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[
                    ("##", "treatment"),
                    ("###", "detail"),
                ],
                strip_headers=False,
                return_each_line=False
            )
            
            fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""],
                length_function=len
            )
            
            # Normalize text
            normalized_text = self._normalize_text(text)
            
            # Try markdown splitting first
            try:
                chunks = markdown_splitter.split_text(normalized_text)
                
                if not chunks:
                    text_chunks = fallback_splitter.split_text(normalized_text)
                    chunks = [
                        type('Chunk', (), {
                            'page_content': chunk,
                            'metadata': {'section': f'chunk_{i}', 'treatment': 'general'}
                        })()
                        for i, chunk in enumerate(text_chunks)
                    ]
                    
            except Exception:
                text_chunks = fallback_splitter.split_text(normalized_text)
                chunks = [
                    type('Chunk', (), {
                        'page_content': chunk,
                        'metadata': {'section': f'chunk_{i}', 'treatment': 'general'}
                    })()
                    for i, chunk in enumerate(text_chunks)
                ]
            
            # Process chunks and generate metadata
            processed_texts = []
            metadatas = []
            
            for chunk in chunks:
                if chunk.page_content and chunk.page_content.strip():
                    processed_texts.append(chunk.page_content)
                    metadata = self._classify_chunk_metadata(chunk)
                    metadata['company_id'] = self.company_id
                    metadata['company_name'] = self.company_config.company_name
                    metadatas.append(metadata)
            
            return processed_texts, metadatas
            
        except Exception as e:
            logger.error(f"Error creating chunks for company {self.company_id}: {e}")
            return [], []
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text preserving structure"""
        if not text or not text.strip():
            return ""
        
        lines = text.split('\n')
        normalized_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                line = line.lower()
                line = ' '.join(line.split())
                normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def _classify_chunk_metadata(self, chunk) -> Dict[str, Any]:
        """Classify chunk metadata based on company business rules"""
        section = chunk.metadata.get("section", "").lower()
        treatment = chunk.metadata.get("treatment", "general")
        
        # Use company-specific business rules for classification
        business_rules = self.company_config.business_rules
        
        if any(word in section for word in ["funciona", "beneficio", "detalle"]):
            metadata_type = "general"
        elif any(word in section for word in ["precio", "oferta", "horario"]):
            metadata_type = "específico"
        elif any(word in section for word in ["contraindicación", "cuidado"]):
            metadata_type = "cuidados"
        else:
            metadata_type = "otro"
        
        return {
            "treatment": treatment,
            "type": metadata_type,
            "section": section,
            "chunk_length": len(chunk.page_content),
            "has_headers": str(bool(chunk.metadata)).lower(),
            "processed_at": datetime.utcnow().isoformat(),
            "company_id": self.company_id,
            "company_name": self.company_config.company_name
        }
    
    def find_vectors_by_doc_id(self, doc_id: str) -> List[str]:
        """Find all vectors for a document within company context"""
        pattern = f"{self.index_name}:*"
        keys = self.redis_client.keys(pattern)
        vectors_to_find = []
        
        for key in keys:
            try:
                # Check direct doc_id field
                doc_id_direct = self.redis_client.hget(key, 'doc_id')
                if doc_id_direct == doc_id:
                    # Verify company ownership
                    metadata_str = self.redis_client.hget(key, 'metadata')
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str)
                            if metadata.get('company_id') == self.company_id:
                                vectors_to_find.append(key)
                        except json.JSONDecodeError:
                            continue
                    else:
                        vectors_to_find.append(key)  # Fallback for docs without metadata
                    continue
                
                # Check metadata for doc_id
                metadata_str = self.redis_client.hget(key, 'metadata')
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                        if (metadata.get('doc_id') == doc_id and 
                            metadata.get('company_id') == self.company_id):
                            vectors_to_find.append(key)
                    except json.JSONDecodeError:
                        continue
                        
            except Exception as e:
                logger.warning(f"Error checking vector {key}: {e}")
                continue
        
        return vectors_to_find
    
    def delete_vectors(self, vector_keys: List[str]) -> int:
        """Delete specific vectors (company-safe)"""
        if not vector_keys:
            return 0
        
        # Verify all vectors belong to this company before deletion
        safe_to_delete = []
        for key in vector_keys:
            try:
                metadata_str = self.redis_client.hget(key, 'metadata')
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    if metadata.get('company_id') == self.company_id:
                        safe_to_delete.append(key)
                else:
                    # If no metadata, check if key belongs to company index
                    if key.startswith(f"{self.index_name}:"):
                        safe_to_delete.append(key)
            except Exception as e:
                logger.warning(f"Error verifying vector ownership {key}: {e}")
                continue
        
        if safe_to_delete:
            self.redis_client.delete(*safe_to_delete)
            logger.info(f"Deleted {len(safe_to_delete)} vectors for company {self.company_id}")
        
        return len(safe_to_delete)
    
    def get_document_vectors(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get detailed vector information for a document"""
        vectors = self.find_vectors_by_doc_id(doc_id)
        vector_details = []
        
        for vector_key in vectors:
            try:
                metadata_str = self.redis_client.hget(vector_key, 'metadata')
                doc_id_direct = self.redis_client.hget(vector_key, 'doc_id')
                
                vector_info = {
                    "vector_key": vector_key,
                    "doc_id_direct": doc_id_direct,
                    "has_metadata": bool(metadata_str),
                    "company_id": self.company_id
                }
                
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                        safe_metadata = {k: v for k, v in metadata.items() 
                                       if k not in ['embedding', 'vector']}
                        vector_info["metadata"] = safe_metadata
                    except json.JSONDecodeError:
                        vector_info["metadata_error"] = "Invalid JSON"
                
                vector_details.append(vector_info)
                
            except Exception as e:
                logger.warning(f"Error getting vector details: {e}")
                continue
        
        return vector_details
    
    def check_health(self) -> Dict[str, Any]:
        """Check vectorstore health for this company"""
        try:
            # Get index info
            info = self.redis_client.ft(self.index_name).info()
            doc_count = info.get('num_docs', 0)
            
            # Count stored documents for this company
            stored_keys = list(self.redis_client.scan_iter(match=f"{self.index_name}:*"))
            company_docs_count = 0
            
            for key in stored_keys:
                try:
                    metadata_str = self.redis_client.hget(key, 'metadata')
                    if metadata_str:
                        metadata = json.loads(metadata_str)
                        if metadata.get('company_id') == self.company_id:
                            company_docs_count += 1
                    else:
                        company_docs_count += 1  # Count docs without metadata as belonging to company
                except:
                    continue
            
            return {
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "index_name": self.index_name,
                "index_exists": True,
                "index_functional": doc_count > 0,
                "company_documents": company_docs_count,
                "total_index_docs": doc_count,
                "needs_recovery": doc_count == 0 and company_docs_count > 0,
                "healthy": company_docs_count > 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking vectorstore health for company {self.company_id}: {e}")
            return {
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "index_name": self.index_name,
                "index_exists": False,
                "index_functional": False,
                "company_documents": 0,
                "needs_recovery": True,
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def force_recovery(self) -> bool:
        """Force index recovery for this company"""
        try:
            logger.info(f"Starting index recovery for company {self.company_id}...")
            
            # Drop existing index
            try:
                self.redis_client.ft(self.index_name).dropindex(delete_documents=False)
            except:
                pass
            
            # Recreate vectorstore
            self._initialize_vectorstore()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in index recovery for company {self.company_id}: {e}")
            return False
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Get protection status for this company"""
        health = self.check_health()
        
        return {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "vectorstore_healthy": health.get("healthy", False),
            "index_exists": health.get("index_exists", False),
            "needs_recovery": health.get("needs_recovery", False),
            "protection_active": True,
            "auto_recovery_available": True
        }

class MultiCompanyVectorstoreService:
    """Service manager for multiple company vectorstores"""
    
    def __init__(self):
        self.company_services = {}
    
    def get_service_for_company(self, company_id: str) -> VectorstoreService:
        """Get vectorstore service for specific company"""
        if company_id not in self.company_services:
            self.company_services[company_id] = VectorstoreService(company_id)
        
        return self.company_services[company_id]
    
    def get_global_health(self) -> Dict[str, Any]:
        """Get health status for all companies"""
        global_health = {
            "total_companies": len(self.company_services),
            "companies": {},
            "global_summary": {
                "healthy_companies": 0,
                "total_documents": 0,
                "companies_needing_recovery": 0
            }
        }
        
        for company_id, service in self.company_services.items():
            try:
                company_health = service.check_health()
                global_health["companies"][company_id] = company_health
                
                # Update global summary
                if company_health.get("healthy", False):
                    global_health["global_summary"]["healthy_companies"] += 1
                
                if company_health.get("needs_recovery", False):
                    global_health["global_summary"]["companies_needing_recovery"] += 1
                
                global_health["global_summary"]["total_documents"] += company_health.get("company_documents", 0)
                
            except Exception as e:
                logger.error(f"Error getting health for company {company_id}: {e}")
                continue
        
        return global_health
