# app/services/vectorstore_service.py
# MIGRADO A LANGGRAPH - Retrieval explícito pre-prompt

from langchain_redis import RedisVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from app.services.redis_service import get_redis_client
from app.services.openai_service import OpenAIService
from app.config.company_config import get_company_config
from flask import current_app
import logging
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class VectorstoreService:
    """
    Servicio de vectorstore multi-tenant - Compatible con LangGraph
    
    🆕 CAMBIOS PARA LANGGRAPH:
    - Retrieval debe hacerse ANTES de ejecutar PromptNode
    - El agente llama a similarity_search_for_graph() explícitamente
    - Los resultados se pasan como 'context' en extra_vars
    - No más integración automática en prompts
    """
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id or "default"
        self.company_config = get_company_config(self.company_id)
        
        if not self.company_config:
            logger.warning(f"No config found for company {self.company_id}, using default")
            from app.config.company_config import CompanyConfig
            self.company_config = CompanyConfig(
                company_id=self.company_id,
                company_name="Default Company",
                redis_prefix=f"{self.company_id}:",
                vectorstore_index=f"{self.company_id}_documents",
                schedule_service_url="http://127.0.0.1:4040",
                sales_agent_name="Asistente",
                services="servicios generales"
            )
        
        self.redis_client = get_redis_client()
        self.openai_service = OpenAIService()
        self.embeddings = self.openai_service.get_embeddings()
        
        # Configuración específica de la empresa
        self.index_name = self.company_config.vectorstore_index
        self.vector_dim = 1536
        
        self._initialize_vectorstore()
        
        logger.info(f"VectorstoreService initialized for company: {self.company_id} with index: {self.index_name}")
    
    def _initialize_vectorstore(self):
        """Inicializar vectorstore específico de la empresa"""
        try:
            self.vectorstore = RedisVectorStore(
                self.embeddings,
                redis_url=current_app.config['REDIS_URL'],
                index_name=self.index_name,
                vector_dim=self.vector_dim
            )
            logger.info(f"Vectorstore initialized for {self.company_id}: {self.index_name}")
        except Exception as e:
            logger.error(f"Error initializing vectorstore for {self.company_id}: {e}")
            raise
    
    # ========================================================================
    # 🆕 MÉTODOS PARA LANGGRAPH
    # ========================================================================
    
    def similarity_search_for_graph(
        self, 
        query: str, 
        k: int = 3,
        return_format: str = "context_string"
    ) -> Any:
        """
        🆕 MÉTODO PRINCIPAL PARA LANGGRAPH
        
        Realiza búsqueda de similitud y retorna resultados en formato
        listo para pasar a PromptNode como extra_vars.
        
        Args:
            query: Consulta de búsqueda
            k: Número de documentos a retornar
            return_format: 
                - "context_string": String concatenado listo para prompt
                - "context_list": Lista de diccionarios con metadata
                - "documents": Objetos Document originales de LangChain
        
        Returns:
            Según return_format:
            - String formateado para inyectar en prompt
            - Lista de diccionarios con content y metadata
            - Lista de objetos Document
        """
        try:
            logger.info(f"🔍 [{self.company_id}] RAG SEARCH FOR LANGGRAPH:")
            logger.info(f"   → Query: {query[:100]}...")
            logger.info(f"   → K: {k}")
            logger.info(f"   → Return format: {return_format}")
            
            # Realizar búsqueda usando método interno
            docs = self.search_by_company(query, company_id=self.company_id, k=k)
            
            if not docs:
                logger.warning(f"   → No documents found")
                if return_format == "context_string":
                    return ""
                elif return_format == "context_list":
                    return []
                else:
                    return []
            
            logger.info(f"   → Documents found: {len(docs)}")
            
            # Formatear según el formato solicitado
            if return_format == "context_string":
                return self._format_docs_as_context_string(docs)
            
            elif return_format == "context_list":
                return self._format_docs_as_context_list(docs)
            
            elif return_format == "documents":
                return docs
            
            else:
                logger.warning(f"   → Unknown format: {return_format}, returning context_string")
                return self._format_docs_as_context_string(docs)
                
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Error in similarity_search_for_graph: {e}")
            if return_format == "context_string":
                return ""
            elif return_format == "context_list":
                return []
            else:
                return []
    
    def _format_docs_as_context_string(self, docs: List[Any]) -> str:
        """
        Formatea documentos como un string concatenado listo para inyectar en prompt
        """
        if not docs:
            return ""
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            metadata = getattr(doc, 'metadata', {})
            
            # Incluir información de metadata si está disponible
            source_info = ""
            if metadata.get('treatment'):
                source_info = f"[Tratamiento: {metadata['treatment']}] "
            elif metadata.get('section'):
                source_info = f"[Sección: {metadata['section']}] "
            
            context_parts.append(f"Documento {i}: {source_info}{content}")
        
        formatted_context = "\n\n---\n\n".join(context_parts)
        
        logger.debug(f"   → Formatted context: {len(formatted_context)} chars")
        return formatted_context
    
    def _format_docs_as_context_list(self, docs: List[Any]) -> List[Dict[str, Any]]:
        """
        Formatea documentos como lista de diccionarios con content y metadata
        """
        if not docs:
            return []
        
        context_list = []
        for doc in docs:
            content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            metadata = getattr(doc, 'metadata', {})
            
            context_list.append({
                "content": content,
                "metadata": metadata,
                "length": len(content)
            })
        
        logger.debug(f"   → Formatted context list: {len(context_list)} items")
        return context_list
    
    def prepare_retrieval_context(
        self, 
        query: str, 
        k: int = 3,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        🆕 Prepara contexto de retrieval completo para pasar a LangGraph state
        
        Útil para nodos de retrieval que necesitan metadata adicional
        además del contexto del documento.
        
        Returns:
            {
                "context": str,  # Texto formateado
                "documents": List[Dict],  # Lista estructurada
                "metadata": {
                    "query": str,
                    "documents_found": int,
                    "company_id": str
                }
            }
        """
        try:
            docs = self.search_by_company(query, company_id=self.company_id, k=k)
            
            result = {
                "context": self._format_docs_as_context_string(docs),
                "documents": self._format_docs_as_context_list(docs) if include_metadata else [],
                "metadata": {
                    "query": query,
                    "documents_found": len(docs),
                    "company_id": self.company_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"✅ [{self.company_id}] Retrieval context prepared: {len(docs)} docs")
            return result
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Error preparing retrieval context: {e}")
            return {
                "context": "",
                "documents": [],
                "metadata": {
                    "query": query,
                    "documents_found": 0,
                    "company_id": self.company_id,
                    "error": str(e)
                }
            }
    
    # ========================================================================
    # MÉTODOS LEGACY (mantener compatibilidad)
    # ========================================================================
    
    def get_retriever(self, k: int = 3):
        """
        ⚠️ LEGACY - Para compatibilidad con código antiguo
        En LangGraph, preferir usar similarity_search_for_graph()
        """
        logger.warning(f"[{self.company_id}] Using legacy get_retriever() - consider migrating to similarity_search_for_graph()")
        return self.vectorstore.as_retriever(search_kwargs={"k": k})
    
    def search_by_company(self, query: str, company_id: str = None, k: int = 3) -> List[Any]:
        """
        Buscar documentos filtrados por empresa
        MANTIENE FUNCIONALIDAD ORIGINAL - devolver objetos Document de LangChain
        """
        try:
            target_company = company_id or self.company_id
            logger.info(f"🔍 [{target_company}] RAG SEARCH START:")
            logger.info(f"   → Query: {query[:100]}...")
            logger.info(f"   → Requested documents: {k}")
            logger.info(f"   → Target company: {target_company}")
            logger.info(f"   → Current company: {self.company_id}")
            
            # Verificar que coincida la empresa
            if target_company != self.company_id:
                logger.warning(f"❌ [{target_company}] Company ID mismatch: {target_company} != {self.company_id}")
                return []
            
            if not self.vectorstore:
                logger.warning(f"   → Vectorstore not available for {target_company}")
                return []
            
            # Realizar búsqueda usando el vectorstore directamente
            logger.info(f"   → Executing similarity search...")
            docs = self.vectorstore.similarity_search(query, k=k)
            
            logger.info(f"   → Initial documents retrieved: {len(docs)}")
            
            # Filtrar por empresa pero mantener objetos Document de LangChain
            filtered_docs = []
            for doc in docs:
                metadata = getattr(doc, 'metadata', {})
                
                # Filtrar por empresa si está especificado en metadata
                doc_company = metadata.get('company_id', self.company_id)
                if doc_company == self.company_id:
                    filtered_docs.append(doc)
            
            # Logs de resultados
            logger.info(f"📄 [{self.company_id}] RAG RESULTS:")
            logger.info(f"   → Documents found after filtering: {len(filtered_docs)}")
            
            for i, doc in enumerate(filtered_docs):
                doc_preview = doc.page_content[:100].replace('\n', ' ') if hasattr(doc, 'page_content') else 'No content'
                metadata = getattr(doc, 'metadata', {})
                logger.info(f"   → Doc {i+1}: {doc_preview}...")
                logger.info(f"      Metadata: {metadata}")
            
            logger.info(f"✅ [{self.company_id}] RAG search completed successfully")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"❌ [{target_company if 'target_company' in locals() else 'unknown'}] RAG search error: {e}")
            return []
    
    # ========================================================================
    # MÉTODOS DE INDEXACIÓN (sin cambios)
    # ========================================================================
    
    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        """Agregar textos con metadata de empresa"""
        try:
            # Enriquecer metadata con información de empresa
            if metadatas is None:
                metadatas = [{} for _ in texts]
            
            enhanced_metadatas = []
            for metadata in metadatas:
                enhanced_metadata = metadata.copy()
                enhanced_metadata.update({
                    'company_id': self.company_id,
                    'company_name': self.company_config.company_name,
                    'index_name': self.index_name
                })
                enhanced_metadatas.append(enhanced_metadata)
            
            self.vectorstore.add_texts(texts, metadatas=enhanced_metadatas)
            logger.info(f"Added {len(texts)} texts for company {self.company_id}")
            
        except Exception as e:
            logger.error(f"Error adding texts for {self.company_id}: {e}")
            raise
    
    def create_chunks(self, text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Crear chunks con metadata específica de empresa"""
        try:
            processed_texts, metadatas = self._create_chunks_internal(text)
            
            # Enriquecer metadata
            enhanced_metadatas = []
            for metadata in metadatas:
                enhanced_metadata = metadata.copy()
                enhanced_metadata.update({
                    'company_id': self.company_id,
                    'company_name': self.company_config.company_name
                })
                enhanced_metadatas.append(enhanced_metadata)
            
            return processed_texts, enhanced_metadatas
            
        except Exception as e:
            logger.error(f"Error creating chunks for {self.company_id}: {e}")
            return [], []
    
    def _create_chunks_internal(self, text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Lógica interna de chunking (sin cambios)"""
        try:
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
            
            normalized_text = self._normalize_text(text)
            
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
            
            processed_texts = []
            metadatas = []
            
            for chunk in chunks:
                if chunk.page_content and chunk.page_content.strip():
                    processed_texts.append(chunk.page_content)
                    metadata = self._classify_chunk_metadata(chunk)
                    metadatas.append(metadata)
            
            return processed_texts, metadatas
            
        except Exception as e:
            logger.error(f"Error in internal chunking: {e}")
            return [], []
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto preservando estructura"""
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
        """Clasificar metadata del chunk"""
        section = chunk.metadata.get("section", "").lower()
        treatment = chunk.metadata.get("treatment", "general")
        
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
            "processed_at": datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # MÉTODOS DE GESTIÓN (sin cambios)
    # ========================================================================
    
    def find_vectors_by_doc_id(self, doc_id: str) -> List[str]:
        """Encontrar vectores por doc_id específicos de la empresa"""
        pattern = f"{self.index_name}:*"
        keys = self.redis_client.keys(pattern)
        vectors_to_find = []
        
        for key in keys:
            try:
                doc_id_direct = self.redis_client.hget(key, 'doc_id')
                if doc_id_direct == doc_id:
                    vectors_to_find.append(key)
                    continue
                
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
        """Eliminar vectores específicos"""
        if vector_keys:
            self.redis_client.delete(*vector_keys)
            logger.info(f"Deleted {len(vector_keys)} vectors for company {self.company_id}")
            return len(vector_keys)
        return 0
    
    def check_health(self) -> Dict[str, Any]:
        """Verificar salud del vectorstore específico de empresa"""
        try:
            info = self.redis_client.ft(self.index_name).info()
            doc_count = info.get('num_docs', 0)
            
            stored_keys = list(self.redis_client.scan_iter(match=f"{self.index_name}:*"))
            stored_count = len(stored_keys)
            
            return {
                "company_id": self.company_id,
                "index_name": self.index_name,
                "index_exists": True,
                "index_functional": doc_count > 0,
                "stored_documents": stored_count,
                "index_doc_count": doc_count,
                "needs_recovery": doc_count == 0 and stored_count > 0,
                "healthy": doc_count > 0 and stored_count > 0
            }
            
        except Exception as e:
            logger.error(f"Error checking vectorstore health for {self.company_id}: {e}")
            return {
                "company_id": self.company_id,
                "index_name": self.index_name,
                "index_exists": False,
                "index_functional": False,
                "stored_documents": 0,
                "needs_recovery": True,
                "healthy": False,
                "error": str(e)
            }


def init_vectorstore(app):
    """Initialize vectorstore system for multi-tenant Flask app"""
    try:
        from app.config.company_config import get_company_manager
        
        company_manager = get_company_manager()
        companies = company_manager.get_all_companies()
        
        logger.info(f"Vectorstore system initialized for {len(companies)} companies (multi-tenant mode)")
        return True
        
    except Exception as e:
        logger.error(f"Vectorstore initialization failed: {e}")
        raise
