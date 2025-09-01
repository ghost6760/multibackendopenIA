// scripts/documents.js - Document Management Module
'use strict';

/**
 * Document Management Module for Multi-Tenant Admin Panel
 * Handles document upload, search, listing, and management operations
 */
class DocumentsManager {
    constructor() {
        this.documents = [];
        this.searchResults = [];
        this.isInitialized = false;
        this.currentCompanyId = null;
        
        // File upload configuration
        this.maxFileSize = window.APP_CONFIG.UPLOAD.max_file_size;
        this.allowedTypes = window.APP_CONFIG.UPLOAD.allowed_types.documents;
        
        this.init = this.init.bind(this);
        this.onCompanyChange = this.onCompanyChange.bind(this);
    }

    /**
     * Initialize Documents Manager
     */
    async init() {
        if (this.isInitialized) return;

        try {
            this.setupEventListeners();
            this.setupFormValidation();
            this.setupFileDropZone();
            
            this.isInitialized = true;
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('📄 Documents Manager initialized');
            }
        } catch (error) {
            console.error('❌ Failed to initialize Documents Manager:', error);
            throw error;
        }
    }

    /**
     * Handle company change
     */
    async onCompanyChange(companyId) {
        this.currentCompanyId = companyId;
        
        // Clear previous data
        this.documents = [];
        this.searchResults = [];
        this.clearSearchResults();
        
        // Load documents for new company
        if (companyId) {
            await this.loadDocuments();
        } else {
            this.clearDocumentsList();
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Add document form
        const addDocForm = document.getElementById('addDocumentForm');
        if (addDocForm) {
            addDocForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addDocument();
            });
        }

        // Bulk upload form
        const bulkUploadForm = document.getElementById('bulkUploadForm');
        if (bulkUploadForm) {
            bulkUploadForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.bulkUploadDocuments();
            });
        }

        // Search form
        const searchForm = document.getElementById('searchDocumentsForm');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.searchDocuments();
            });
        }

        // Refresh documents button
        const refreshBtn = document.getElementById('refreshDocsList');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadDocuments();
            });
        }

        // File input changes
        const bulkFiles = document.getElementById('bulkFiles');
        if (bulkFiles) {
            bulkFiles.addEventListener('change', (e) => {
                this.validateFiles(e.target.files);
            });
        }

        // Real-time search if enabled
        const searchQuery = document.getElementById('searchQuery');
        if (searchQuery && window.APP_CONFIG.PERFORMANCE.debounce_search) {
            const debouncedSearch = window.UI.debounce(() => {
                if (searchQuery.value.trim().length >= 3) {
                    this.searchDocuments();
                }
            }, window.APP_CONFIG.UI.debounce_delay);
            
            searchQuery.addEventListener('input', debouncedSearch);
        }
    }

    /**
     * Setup form validation
     */
    setupFormValidation() {
        const docContent = document.getElementById('docContent');
        const docMetadata = document.getElementById('docMetadata');

        if (docContent) {
            docContent.addEventListener('input', () => {
                this.validateDocumentContent(docContent.value);
            });
        }

        if (docMetadata) {
            docMetadata.addEventListener('blur', () => {
                this.validateMetadata(docMetadata.value);
            });
        }
    }

    /**
     * Setup file drop zone
     */
    setupFileDropZone() {
        const bulkUploadForm = document.getElementById('bulkUploadForm');
        if (!bulkUploadForm) return;

        // Add drop zone styling
        bulkUploadForm.classList.add('drop-zone');

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            bulkUploadForm.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            bulkUploadForm.addEventListener(eventName, () => {
                bulkUploadForm.classList.add('drag-over');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            bulkUploadForm.addEventListener(eventName, () => {
                bulkUploadForm.classList.remove('drag-over');
            });
        });

        // Handle dropped files
        bulkUploadForm.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const bulkFiles = document.getElementById('bulkFiles');
                if (bulkFiles) {
                    bulkFiles.files = files;
                    this.validateFiles(files);
                    window.UI.showToast(`📁 ${files.length} archivo(s) seleccionado(s)`, 'info');
                }
            }
        });
    }

    /**
     * Load documents for current company
     */
    async loadDocuments() {
        if (!this.currentCompanyId) {
            this.clearDocumentsList();
            return;
        }

        try {
            window.UI.showLoading('Cargando documentos...');

            const response = await window.API.listDocuments();
            
            if (response.status === 'success' && response.documents) {
                this.documents = response.documents;
                this.updateDocumentsList();
                
                window.UI.showToast(`✅ ${this.documents.length} documentos cargados`, 'success');
            } else {
                throw new Error(response.message || 'Error cargando documentos');
            }

        } catch (error) {
            console.error('❌ Error loading documents:', error);
            window.UI.showToast('❌ Error cargando documentos: ' + error.message, 'error');
            this.clearDocumentsList();
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Add new document
     */
    async addDocument() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const content = document.getElementById('docContent').value.trim();
        const metadataStr = document.getElementById('docMetadata').value.trim();

        if (!content) {
            window.UI.showToast('❌ El contenido es requerido', 'error');
            document.getElementById('docContent').focus();
            return;
        }

        let metadata = {};
        if (metadataStr) {
            try {
                metadata = JSON.parse(metadataStr);
            } catch (error) {
                window.UI.showToast('❌ Metadata debe ser JSON válido', 'error');
                document.getElementById('docMetadata').focus();
                return;
            }
        }

        try {
            window.UI.showLoading('Agregando documento...');

            const response = await window.API.addDocument(content, metadata);
            
            if (response.status === 'success') {
                window.UI.showToast('✅ Documento agregado correctamente', 'success');
                
                // Clear form
                window.UI.clearForm('addDocumentForm');
                
                // Reload documents
                await this.loadDocuments();
                
            } else {
                throw new Error(response.message || 'Error agregando documento');
            }

        } catch (error) {
            console.error('❌ Error adding document:', error);
            window.UI.showToast('❌ Error agregando documento: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Bulk upload documents
     */
    async bulkUploadDocuments() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const fileInput = document.getElementById('bulkFiles');
        const files = fileInput.files;

        if (!files || files.length === 0) {
            window.UI.showToast('❌ Selecciona al menos un archivo', 'error');
            return;
        }

        // Validate files
        const validationResult = this.validateFiles(files);
        if (!validationResult.isValid) {
            window.UI.showToast(`❌ ${validationResult.error}`, 'error');
            return;
        }

        try {
            window.UI.showLoadingWithProgress('Subiendo archivos...', 0);

            let uploadedCount = 0;
            let failedCount = 0;

            // Upload files one by one to show progress
            for (let i = 0; i < files.length; i++) {
                try {
                    const progress = ((i + 1) / files.length) * 100;
                    window.UI.updateProgress(progress);

                    const response = await window.API.bulkUploadDocuments([files[i]]);
                    
                    if (response.status === 'success') {
                        uploadedCount++;
                    } else {
                        failedCount++;
                        console.warn(`Failed to upload ${files[i].name}:`, response.message);
                    }
                } catch (error) {
                    failedCount++;
                    console.error(`Error uploading ${files[i].name}:`, error);
                }
            }

            // Show results
            if (uploadedCount > 0) {
                window.UI.showToast(`✅ ${uploadedCount} archivos subidos correctamente`, 'success');
                
                // Clear form
                fileInput.value = '';
                
                // Reload documents
                await this.loadDocuments();
            }

            if (failedCount > 0) {
                window.UI.showToast(`⚠️ ${failedCount} archivos fallaron al subir`, 'warning');
            }

        } catch (error) {
            console.error('❌ Error in bulk upload:', error);
            window.UI.showToast('❌ Error en la subida masiva: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Search documents
     */
    async searchDocuments() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const query = document.getElementById('searchQuery').value.trim();
        const k = parseInt(document.getElementById('searchK').value) || 3;

        if (!query) {
            window.UI.showToast('❌ Ingresa un término de búsqueda', 'error');
            document.getElementById('searchQuery').focus();
            return;
        }

        try {
            window.UI.showLoading('Buscando documentos...');

            const response = await window.API.searchDocuments(query, k);
            
            if (response.status === 'success' && response.results) {
                this.searchResults = response.results;
                this.displaySearchResults();
                
                window.UI.showToast(`🔍 ${this.searchResults.length} resultados encontrados`, 'success');
            } else {
                throw new Error(response.message || 'Error en la búsqueda');
            }

        } catch (error) {
            console.error('❌ Error searching documents:', error);
            window.UI.showToast('❌ Error en la búsqueda: ' + error.message, 'error');
            this.clearSearchResults();
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Display search results
     */
    displaySearchResults() {
        const resultsContainer = document.getElementById('searchResults');
        if (!resultsContainer) return;

        if (this.searchResults.length === 0) {
            resultsContainer.innerHTML = `
                <div class="no-results">
                    <span class="placeholder-icon">🔍</span>
                    <p>No se encontraron documentos con ese término</p>
                </div>
            `;
            return;
        }

        let resultsHTML = '<h4>Resultados de la Búsqueda:</h4>';
        
        this.searchResults.forEach((result, index) => {
            const score = (result.score * 100).toFixed(1);
            const content = this.truncateText(result.content || result.text || '', 200);
            
            resultsHTML += `
                <div class="search-result" data-result-index="${index}">
                    <div class="search-result-header">
                        <span class="search-result-score">Relevancia: ${score}%</span>
                        ${result.metadata ? `<span class="search-result-source">${this.formatMetadata(result.metadata)}</span>` : ''}
                    </div>
                    <div class="search-result-content">${this.highlightSearchTerms(content, document.getElementById('searchQuery').value)}</div>
                    ${result.document_id ? `<div class="search-result-id">ID: ${result.document_id}</div>` : ''}
                </div>
            `;
        });

        resultsContainer.innerHTML = resultsHTML;
    }

    /**
     * Clear search results
     */
    clearSearchResults() {
        const resultsContainer = document.getElementById('searchResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
        this.searchResults = [];
    }

    /**
     * Update documents list
     */
    updateDocumentsList() {
        const listContainer = document.getElementById('documentsList');
        if (!listContainer) return;

        if (this.documents.length === 0) {
            listContainer.innerHTML = `
                <div class="list-placeholder">
                    <span class="placeholder-icon">📄</span>
                    <p>No hay documentos almacenados</p>
                    <small>Agrega documentos usando los formularios de arriba</small>
                </div>
            `;
            return;
        }

        let listHTML = '';
        
        this.documents.forEach((doc, index) => {
            const createdDate = doc.created_at ? window.UI.formatDate(doc.created_at) : 'Fecha desconocida';
            const docSize = doc.size ? window.UI.formatFileSize(doc.size) : '';
            const docType = this.getDocumentType(doc);
            
            listHTML += `
                <div class="document-item" data-doc-id="${doc.id || index}">
                    <div class="document-info">
                        <div class="document-title">${docType} ${doc.title || doc.name || `Documento ${index + 1}`}</div>
                        <div class="document-meta">
                            <span>📅 ${createdDate}</span>
                            ${docSize ? `<span>📊 ${docSize}</span>` : ''}
                            ${doc.chunks ? `<span>🧩 ${doc.chunks} fragmentos</span>` : ''}
                        </div>
                        ${doc.metadata ? `<div class="document-metadata">${this.formatMetadata(doc.metadata)}</div>` : ''}
                    </div>
                    <div class="document-actions">
                        <button class="btn btn-sm btn-secondary" onclick="window.DocumentsManager.viewDocument('${doc.id || index}')">
                            <span class="btn-icon">👁️</span>
                            Ver
                        </button>
                        <button class="btn btn-sm btn-info" onclick="window.DocumentsManager.viewDocumentVectors('${doc.id || index}')">
                            <span class="btn-icon">🔍</span>
                            Vectores
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="window.DocumentsManager.deleteDocument('${doc.id || index}')">
                            <span class="btn-icon">🗑️</span>
                            Eliminar
                        </button>
                    </div>
                </div>
            `;
        });

        listContainer.innerHTML = listHTML;
    }

    /**
     * Clear documents list
     */
    clearDocumentsList() {
        const listContainer = document.getElementById('documentsList');
        if (listContainer) {
            listContainer.innerHTML = `
                <div class="list-placeholder">
                    <span class="placeholder-icon">🏢</span>
                    <p>Selecciona una empresa para ver sus documentos</p>
                </div>
            `;
        }
    }

    /**
     * View document details
     */
    async viewDocument(docId) {
        const doc = this.documents.find(d => (d.id || this.documents.indexOf(d).toString()) === docId.toString());
        if (!doc) {
            window.UI.showToast('❌ Documento no encontrado', 'error');
            return;
        }

        const content = `
            <div class="document-details">
                <h4>${doc.title || doc.name || `Documento ${docId}`}</h4>
                
                <div class="document-info-grid">
                    <div class="info-item">
                        <strong>ID:</strong> ${doc.id || docId}
                    </div>
                    <div class="info-item">
                        <strong>Creado:</strong> ${doc.created_at ? window.UI.formatDate(doc.created_at) : 'Desconocido'}
                    </div>
                    <div class="info-item">
                        <strong>Tamaño:</strong> ${doc.size ? window.UI.formatFileSize(doc.size) : 'N/A'}
                    </div>
                    <div class="info-item">
                        <strong>Tipo:</strong> ${this.getDocumentType(doc)}
                    </div>
                    ${doc.chunks ? `<div class="info-item"><strong>Fragmentos:</strong> ${doc.chunks}</div>` : ''}
                </div>

                ${doc.metadata ? `
                    <div class="document-metadata-section">
                        <h5>Metadata:</h5>
                        <pre class="metadata-json">${JSON.stringify(doc.metadata, null, 2)}</pre>
                    </div>
                ` : ''}

                ${doc.content ? `
                    <div class="document-content-section">
                        <h5>Contenido:</h5>
                        <div class="document-content-preview">${this.truncateText(doc.content, 500)}</div>
                    </div>
                ` : ''}

                <div class="document-actions-section">
                    <button class="btn btn-primary" onclick="window.UI.copyToClipboard('${doc.id || docId}')">
                        <span class="btn-icon">📋</span>
                        Copiar ID
                    </button>
                    ${doc.content ? `
                        <button class="btn btn-secondary" onclick="window.UI.copyToClipboard(\`${doc.content.replace(/`/g, '\\`')}\`)">
                            <span class="btn-icon">📄</span>
                            Copiar Contenido
                        </button>
                    ` : ''}
                </div>
            </div>
        `;

        window.UI.showModal('📄 Detalles del Documento', content, {
            maxWidth: '800px'
        });
    }

    /**
     * View document vectors
     */
    async viewDocumentVectors(docId) {
        window.UI.showToast(`🔍 Visualización de vectores para documento ${docId} - Función en desarrollo`, 'info');
    }

    /**
     * Delete document
     */
    async deleteDocument(docId) {
        const doc = this.documents.find(d => (d.id || this.documents.indexOf(d).toString()) === docId.toString());
        const docName = doc ? (doc.title || doc.name || `Documento ${docId}`) : docId;

        const confirmed = await this.showConfirmDialog(
            '🗑️ Eliminar Documento',
            `¿Estás seguro de que quieres eliminar <strong>${docName}</strong>?<br><br>
            Esta acción no se puede deshacer y eliminará todos los vectores asociados.`
        );

        if (!confirmed) return;

        try {
            window.UI.showLoading('Eliminando documento...');

            const response = await window.API.deleteDocument(docId);
            
            if (response.status === 'success') {
                window.UI.showToast(`✅ Documento eliminado: ${docName}`, 'success');
                
                // Remove from local array
                this.documents = this.documents.filter(d => 
                    (d.id || this.documents.indexOf(d).toString()) !== docId.toString()
                );
                
                // Update UI
                this.updateDocumentsList();
                
            } else {
                throw new Error(response.message || 'Error eliminando documento');
            }

        } catch (error) {
            console.error('❌ Error deleting document:', error);
            window.UI.showToast('❌ Error eliminando documento: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Validate files before upload
     */
    validateFiles(files) {
        const errors = [];
        let totalSize = 0;

        for (let file of files) {
            // Check file type
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            if (!this.allowedTypes.includes(fileExtension)) {
                errors.push(`Tipo de archivo no permitido: ${file.name}`);
                continue;
            }

            // Check file size
            if (file.size > this.maxFileSize) {
                const maxSizeMB = Math.round(this.maxFileSize / 1024 / 1024);
                errors.push(`Archivo muy grande: ${file.name} (máximo ${maxSizeMB}MB)`);
                continue;
            }

            totalSize += file.size;
        }

        // Check total size
        const maxTotalSize = this.maxFileSize * 5; // Allow 5x max for batch
        if (totalSize > maxTotalSize) {
            const maxTotalMB = Math.round(maxTotalSize / 1024 / 1024);
            errors.push(`Tamaño total muy grande (máximo ${maxTotalMB}MB)`);
        }

        return {
            isValid: errors.length === 0,
            errors,
            error: errors.join(', ')
        };
    }

    /**
     * Validate document content
     */
    validateDocumentContent(content) {
        const contentEl = document.getElementById('docContent');
        if (!contentEl) return true;

        if (!content.trim()) {
            contentEl.classList.add('is-invalid');
            return false;
        }

        if (content.length < 10) {
            contentEl.classList.add('is-invalid');
            window.UI.showToast('⚠️ El contenido debe tener al menos 10 caracteres', 'warning');
            return false;
        }

        contentEl.classList.remove('is-invalid');
        contentEl.classList.add('is-valid');
        return true;
    }

    /**
     * Validate metadata JSON
     */
    validateMetadata(metadataStr) {
        const metadataEl = document.getElementById('docMetadata');
        if (!metadataEl) return true;

        if (!metadataStr.trim()) {
            metadataEl.classList.remove('is-invalid', 'is-valid');
            return true;
        }

        try {
            JSON.parse(metadataStr);
            metadataEl.classList.remove('is-invalid');
            metadataEl.classList.add('is-valid');
            return true;
        } catch (error) {
            metadataEl.classList.add('is-invalid');
            return false;
        }
    }

    /**
     * Get document type from filename or metadata
     */
    getDocumentType(doc) {
        if (doc.type) return doc.type;
        if (doc.name) {
            const extension = doc.name.split('.').pop().toLowerCase();
            const typeMap = {
                'txt': '📝 Texto',
                'md': '📝 Markdown',
                'docx': '📘 Word',
                'pdf': '📕 PDF',
                'json': '🔧 JSON',
                'xml': '🔧 XML'
            };
            return typeMap[extension] || '📄 Documento';
        }
        return '📄 Documento';
    }

    /**
     * Format metadata for display
     */
    formatMetadata(metadata) {
        if (!metadata || typeof metadata !== 'object') return '';
        
        const entries = Object.entries(metadata).slice(0, 3); // Show first 3 entries
        const formatted = entries.map(([key, value]) => `${key}: ${value}`).join(', ');
        
        return entries.length < Object.keys(metadata).length 
            ? formatted + '...' 
            : formatted;
    }

    /**
     * Truncate text for display
     */
    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Highlight search terms in text
     */
    highlightSearchTerms(text, searchQuery) {
        if (!searchQuery) return text;
        
        const terms = searchQuery.split(/\s+/).filter(term => term.length > 2);
        let highlightedText = text;
        
        terms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi');
            highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
        });
        
        return highlightedText;
    }

    /**
     * Show confirmation dialog
     */
    showConfirmDialog(title, message) {
        return new Promise((resolve) => {
            window.UI.showConfirmModal(
                title,
                message,
                () => resolve(true),
                () => resolve(false)
            );
        });
    }

    /**
     * Get documents count
     */
    getDocumentsCount() {
        return this.documents.length;
    }

    /**
     * Get search results count
     */
    getSearchResultsCount() {
        return this.searchResults.length;
    }

    /**
     * Export documents list
     */
    exportDocumentsList() {
        if (this.documents.length === 0) {
            window.UI.showToast('⚠️ No hay documentos para exportar', 'warning');
            return;
        }

        const exportData = this.documents.map(doc => ({
            id: doc.id,
            title: doc.title || doc.name,
            type: this.getDocumentType(doc),
            size: doc.size,
            created_at: doc.created_at,
            chunks: doc.chunks,
            metadata: doc.metadata
        }));

        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `documents_${this.currentCompanyId}_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        window.UI.showToast('✅ Lista de documentos exportada', 'success');
    }

    /**
     * Clear all data
     */
    clearAll() {
        this.documents = [];
        this.searchResults = [];
        this.clearSearchResults();
        this.clearDocumentsList();
        
        // Clear forms
        window.UI.clearForm('addDocumentForm');
        window.UI.clearForm('bulkUploadForm');
        window.UI.clearForm('searchDocumentsForm');
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.clearAll();
        this.isInitialized = false;
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🧹 Documents Manager cleaned up');
        }
    }
}

// Create global instance
window.DocumentsManager = new DocumentsManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DocumentsManager;
}
