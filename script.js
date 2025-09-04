

// script.js - Frontend Multi-Tenant Benova - Funcionalidad Completa
// ============================================================================
// CONFIGURACIÓN Y VARIABLES GLOBALES
// ============================================================================

// Configuración de la API
const API_BASE_URL = window.location.origin;
const DEFAULT_COMPANY_ID = 'benova';

// Estado global de la aplicación
let currentCompanyId = '';
let monitoringInterval = null;
let systemLog = [];

// Cache para optimizar requests
const cache = {
    companies: null,
    systemInfo: null,
    lastUpdate: {}
};

// ============================================================================
// UTILIDADES Y HELPERS
// ============================================================================

/**
 * Realiza una petición HTTP con manejo de errores y headers multi-tenant
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Headers por defecto
    const defaultHeaders = {
        'Content-Type': 'application/json'
    };
    
    // Agregar company_id si está seleccionado
    if (currentCompanyId) {
        defaultHeaders['X-Company-ID'] = currentCompanyId;
    }
    
    // Combinar headers
    const headers = { ...defaultHeaders, ...(options.headers || {}) };
    
    // Configuración de la petición
    const config = {
        method: options.method || 'GET',
        headers,
        ...options
    };
    
    // Agregar body si existe y no es FormData
    if (options.body && !(options.body instanceof FormData)) {
        config.body = JSON.stringify(options.body);
    } else if (options.body instanceof FormData) {
        // Para FormData, remover Content-Type para que el browser lo maneje
        delete config.headers['Content-Type'];
        config.body = options.body;
    }
    
    try {
        addToLog(`API Request: ${config.method} ${endpoint}`, 'info');
        
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        addToLog(`API Response: ${endpoint} - Success`, 'info');
        return data;
        
    } catch (error) {
        addToLog(`API Error: ${endpoint} - ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Muestra una notificación al usuario
 */
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notificationContainer');
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Mostrar con animación
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    // Ocultar después del tiempo especificado
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (container.contains(notification)) {
                container.removeChild(notification);
            }
        }, 300);
    }, duration);
}

/**
 * Agrega una entrada al log del sistema
 */
function addToLog(message, level = 'info') {
    const timestamp = new Date().toISOString().substring(0, 19).replace('T', ' ');
    const logEntry = {
        timestamp,
        level,
        message
    };
    
    systemLog.push(logEntry);
    
    // Mantener solo los últimos 100 logs
    if (systemLog.length > 100) {
        systemLog.shift();
    }
    
    // Actualizar UI del log
    updateLogDisplay();
}

/**
 * Actualiza la visualización del log en la UI
 */
function updateLogDisplay() {
    const logContainer = document.getElementById('systemLog');
    if (!logContainer) return;
    
    const logHTML = systemLog.map(entry => `
        <div class="log-entry">
            <span class="log-timestamp">[${entry.timestamp}]</span>
            <span class="log-level-${entry.level}">[${entry.level.toUpperCase()}]</span>
            ${entry.message}
        </div>
    `).join('');
    
    logContainer.innerHTML = logHTML;
    
    // Scroll automático al final
    logContainer.scrollTop = logContainer.scrollHeight;
}

/**
 * Muestra/oculta el overlay de carga
 */
function toggleLoadingOverlay(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

/**
 * Formatea JSON para mostrar en la UI
 */
function formatJSON(obj) {
    return JSON.stringify(obj, null, 2);
}

/**
 * Valida si hay una empresa seleccionada
 */
function validateCompanySelection() {
    if (!currentCompanyId) {
        showNotification('Por favor selecciona una empresa primero', 'warning');
        return false;
    }
    return true;
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// GESTIÓN DE TABS
// ============================================================================

/**
 * Cambia entre tabs
 */
function switchTab(tabName) {
    // Remover clase active de todos los tabs y contenidos
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Activar el tab seleccionado
    const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    const activeContent = document.getElementById(tabName);
    if (activeContent) {
        activeContent.classList.add('active');
    }
    
    addToLog(`Switched to tab: ${tabName}`, 'info');
    
    // Cargar datos específicos del tab si es necesario
    if (tabName === 'dashboard') {
        loadDashboardData();
    }
}

// ============================================================================
// GESTIÓN DE EMPRESAS - CORREGIDO
// ============================================================================

/**
 * Carga la lista de empresas disponibles - CORREGIDO
 */
async function loadCompanies() {
    try {
        if (cache.companies && Array.isArray(cache.companies)) {
            console.log('Using cached companies:', cache.companies);
            return cache.companies;
        }
        
        console.log('Loading companies from API...');
        
        // Intentar primero el endpoint /api/companies
        try {
            const response = await apiRequest('/api/companies');
            console.log('Response from /api/companies:', response);
            
            // El endpoint devuelve: { status: "success", data: { companies: {...}, total_companies: N } }
            if (response.data && response.data.companies) {
                const companiesObj = response.data.companies;
                
                // Convertir objeto de empresas a array
                cache.companies = Object.keys(companiesObj).map(companyId => {
                    const companyData = companiesObj[companyId];
                    return {
                        id: companyId,
                        name: companyData.company_name || companyId
                    };
                });
                
                console.log('Converted companies from /api/companies:', cache.companies);
                updateCompanySelector();
                return cache.companies;
            }
            
        } catch (error) {
            console.log('Fallback to /api/health/companies due to:', error.message);
            
            // Fallback: usar health/companies
            const response = await apiRequest('/api/health/companies');
            console.log('Raw response from /api/health/companies:', response);
            
            // Convertir el objeto de empresas a array
            if (response.companies && typeof response.companies === 'object') {
                cache.companies = Object.keys(response.companies).map(companyId => {
                    const companyData = response.companies[companyId];
                    return {
                        id: companyId,
                        name: companyData.company_name || companyId
                    };
                });
                
                console.log('Converted companies from health endpoint:', cache.companies);
                updateCompanySelector();
                return cache.companies;
            }
        }
        
        // Si todo falla, devolver array vacío
        console.error('No companies data available');
        cache.companies = [];
        return [];
        
    } catch (error) {
        console.error('Error loading companies:', error);
        showNotification('Error al cargar empresas: ' + error.message, 'error');
        cache.companies = [];
        return [];
    }
}

/**
 * Actualiza el selector de empresas en la UI - CORREGIDO
 */
function updateCompanySelector() {
    const selector = document.getElementById('companySelect');
    if (!selector) {
        console.error('Company selector element not found');
        return;
    }
    
    if (!cache.companies || !Array.isArray(cache.companies)) {
        console.warn('No valid companies data available for selector');
        return;
    }
    
    console.log('Updating company selector with companies:', cache.companies);
    
    // Limpiar opciones existentes (excepto la primera opción "Seleccionar empresa...")
    while (selector.children.length > 1) {
        selector.removeChild(selector.lastChild);
    }
    
    // Agregar cada empresa como opción
    cache.companies.forEach((company, index) => {
        try {
            const option = document.createElement('option');
            option.value = company.id;
            option.textContent = company.name;
            selector.appendChild(option);
            console.log(`Added company option ${index + 1}: ${company.name} (${company.id})`);
        } catch (error) {
            console.error('Error adding company option:', company, error);
        }
    });
    
    console.log(`Company selector updated with ${cache.companies.length} companies`);
}

/**
 * Maneja el cambio de empresa seleccionada
 */
function handleCompanyChange(companyId) {
    currentCompanyId = companyId;
    addToLog(`Company changed to: ${companyId}`, 'info');
    
    if (companyId) {
        showNotification(`Empresa cambiada a: ${companyId}`, 'success', 3000);
        
        // Limpiar cache relacionado con empresas
        cache.lastUpdate = {};
        
        // Recargar datos del dashboard si estamos en él
        const dashboardTab = document.getElementById('dashboard');
        if (dashboardTab && dashboardTab.classList.contains('active')) {
            loadDashboardData();
        }
    }
}

// ============================================================================
// DASHBOARD - FUNCIONES PRINCIPALES
// ============================================================================

/**
 * Carga todos los datos del dashboard
 */
async function loadDashboardData() {
    await Promise.all([
        loadSystemInfo(),
        loadCompaniesStatus(),
        updateStats()
    ]);
}

/**
 * Carga información del sistema
 */
async function loadSystemInfo() {
    try {
        const response = await apiRequest('/api/system/info');
        
        cache.systemInfo = response;
        
        const container = document.getElementById('systemInfo');
        if (container) {
            container.innerHTML = `
                <div class="result-container result-success">
                    <h4>🚀 Sistema Multi-Tenant Activo</h4>
                    <p><strong>Versión:</strong> ${response.version || '1.0.0'}</p>
                    <p><strong>Tipo:</strong> ${response.system_type || 'multi-tenant-multi-agent'}</p>
                    <p><strong>Empresas configuradas:</strong> ${response.companies_configured || 0}</p>
                    <p><strong>Características:</strong></p>
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        ${(response.features || []).map(feature => `<li>${feature}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Actualizar estadísticas
        document.getElementById('totalCompanies').textContent = response.companies_configured || 0;
        
    } catch (error) {
        console.error('Error loading system info:', error);
        const container = document.getElementById('systemInfo');
        if (container) {
            container.innerHTML = `
                <div class="result-container result-error">
                    <p>❌ Error al cargar información del sistema</p>
                    <p>${escapeHTML(error.message)}</p>
                </div>
            `;
        }
    }
}

/**
 * Carga el estado de todas las empresas
 */
async function loadCompaniesStatus() {
    try {
        const response = await apiRequest('/api/health/companies');
        console.log('Companies health response:', response); // Debug
        
        const container = document.getElementById('companiesStatus');
        if (container && response.companies) {
            let statusHTML = '';
            
            Object.entries(response.companies).forEach(([companyId, status]) => {
                // Verificar si el campo existe en el objeto status
                let isHealthy = false;
                if (status.system_healthy !== undefined) {
                    isHealthy = status.system_healthy === true;
                } else {
                    // Si no hay system_healthy, asumimos que está saludable si tiene información
                    isHealthy = true;
                }
                
                const statusClass = isHealthy ? 'healthy' : 'error';
                const statusIcon = isHealthy ? '✅' : '❌';
                const statusText = isHealthy ? 'ONLINE' : 'ERROR';
                const companyName = status.company_name || companyId;
                
                statusHTML += `
                    <div class="health-status ${statusClass}">
                        <span class="status-indicator status-${isHealthy ? 'healthy' : 'error'}"></span>
                        ${statusIcon} <strong>${companyName}</strong>
                        <span class="badge badge-${isHealthy ? 'success' : 'error'}">
                            ${statusText}
                        </span>
                    </div>
                `;
            });
            
            container.innerHTML = statusHTML;
        }
        
    } catch (error) {
        console.error('Error loading companies status:', error);
        const container = document.getElementById('companiesStatus');
        if (container) {
            container.innerHTML = `
                <div class="result-container result-error">
                    <p>❌ Error al cargar estado de empresas</p>
                    <p>${escapeHTML(error.message)}</p>
                </div>
            `;
        }
    }
}


/**
 * Actualiza las estadísticas del dashboard
 */
async function updateStats() {
    if (!validateCompanySelection()) return;
    
    try {
        // Cargar estadísticas básicas
        const [documentsResponse, conversationsResponse] = await Promise.all([
            apiRequest('/api/documents').catch(() => ({ data: [] })),
            apiRequest('/api/conversations').catch(() => ({ data: [] }))
        ]);
        
        // Actualizar contadores
        document.getElementById('totalDocuments').textContent = 
            documentsResponse.data?.length || documentsResponse.total || 0;
        
        document.getElementById('totalConversations').textContent = 
            conversationsResponse.data?.length || conversationsResponse.total || 0;
        
        document.getElementById('systemStatus').textContent = '🟢';
        
    } catch (error) {
        console.error('Error updating stats:', error);
        document.getElementById('systemStatus').textContent = '🔴';
    }
}

// ============================================================================
// GESTIÓN DE DOCUMENTOS
// ============================================================================

/**
 * Sube un documento al sistema
 */
async function uploadDocument() {
    if (!validateCompanySelection()) return;
    
    const title = document.getElementById('documentTitle').value.trim();
    const content = document.getElementById('documentContent').value.trim();
    const fileInput = document.getElementById('documentFile');
    
    if (!title) {
        showNotification('Por favor ingresa un título para el documento', 'warning');
        return;
    }
    
    if (!content && !fileInput.files[0]) {
        showNotification('Por favor ingresa contenido o selecciona un archivo', 'warning');
        return;
    }
    
    try {
        toggleLoadingOverlay(true);
        
        let documentData = {
            title: title,
            company_id: currentCompanyId
        };
        
        if (content) {
            documentData.content = content;
        }
        
        if (fileInput.files[0]) {
            // Si hay archivo, leer su contenido
            const fileContent = await readFileContent(fileInput.files[0]);
            documentData.content = fileContent;
            documentData.file_name = fileInput.files[0].name;
        }
        
        const response = await apiRequest('/api/documents', {
            method: 'POST',
            body: documentData
        });
        
        showNotification('Documento subido exitosamente', 'success');
        
        // Limpiar formulario
        document.getElementById('documentTitle').value = '';
        document.getElementById('documentContent').value = '';
        document.getElementById('documentFile').value = '';
        
        // Recargar lista de documentos
        await loadDocuments();
        
    } catch (error) {
        console.error('Error uploading document:', error);
        showNotification('Error al subir documento: ' + error.message, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Lee el contenido de un archivo
 */
function readFileContent(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

/**
 * Carga la lista de documentos
 */
async function loadDocuments() {
    if (!validateCompanySelection()) return;
    
    try {
        const response = await apiRequest('/api/documents');
        const documents = response.data || response.documents || [];
        
        const container = document.getElementById('documentsList');
        if (!container) return;
        
        if (documents.length === 0) {
            container.innerHTML = `
                <p style="padding: 20px; text-align: center; color: #718096;">
                    No hay documentos para la empresa ${currentCompanyId}
                </p>
            `;
            return;
        }
        
        const documentsHTML = documents.map(doc => `
            <div class="data-item">
                <div class="data-item-header">
                    <div class="data-item-title">📄 ${escapeHTML(doc.title || doc.name || 'Sin título')}</div>
                    <div class="data-item-meta">
                        ${doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Fecha desconocida'}
                    </div>
                </div>
                <div class="data-item-content">
                    ${doc.content ? escapeHTML(doc.content.substring(0, 150)) + '...' : 'Sin contenido'}
                </div>
                <div class="data-item-actions">
                    <button class="btn btn-secondary" onclick="viewDocument('${doc.id}')">
                        👁️ Ver
                    </button>
                    <button class="btn btn-danger" onclick="deleteDocument('${doc.id}')">
                        🗑️ Eliminar
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = documentsHTML;
        
    } catch (error) {
        console.error('Error loading documents:', error);
        const container = document.getElementById('documentsList');
        if (container) {
            container.innerHTML = `
                <div class="result-container result-error">
                    <p>❌ Error al cargar documentos</p>
                    <p>${escapeHTML(error.message)}</p>
                </div>
            `;
        }
    }
}

/**
 * Busca documentos
 */
async function searchDocuments() {
    if (!validateCompanySelection()) return;
    
    const query = document.getElementById('searchQuery').value.trim();
    if (!query) {
        showNotification('Por favor ingresa una consulta de búsqueda', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest('/api/documents/search', {
            method: 'POST',
            body: {
                query: query,
                company_id: currentCompanyId
            }
        });
        
        const results = response.data || response.results || [];
        const container = document.getElementById('searchResults');
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="result-container result-warning">
                    <p>🔍 No se encontraron resultados para "${escapeHTML(query)}"</p>
                </div>
            `;
            return;
        }
        
        const resultsHTML = `
            <div class="result-container result-success">
                <h4>🔍 Resultados de búsqueda (${results.length})</h4>
                ${results.map(result => `
                    <div class="search-result" style="border-left: 3px solid #667eea; padding-left: 15px; margin: 10px 0;">
                        <h5>${escapeHTML(result.title || result.document_title || 'Sin título')}</h5>
                        <p>${escapeHTML(result.content || result.text || 'Sin contenido').substring(0, 200)}...</p>
                        ${result.score ? `<small>Relevancia: ${Math.round(result.score * 100)}%</small>` : ''}
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = resultsHTML;
        
    } catch (error) {
        console.error('Error searching documents:', error);
        const container = document.getElementById('searchResults');
        if (container) {
            container.innerHTML = `
                <div class="result-container result-error">
                    <p>❌ Error en la búsqueda</p>
                    <p>${escapeHTML(error.message)}</p>
                </div>
            `;
        }
    }
}

/**
 * Ve un documento específico
 */
async function viewDocument(docId) {
    try {
        const response = await apiRequest(`/api/documents/${docId}`);
        const doc = response.data || response;
        
        // Crear modal para mostrar el documento
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); max-width: 80%; max-height: 80%; overflow-y: auto; z-index: 10000;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px;">
                    <h3>📄 ${escapeHTML(doc.title || 'Documento')}</h3>
                    <button class="btn btn-secondary" onclick="closeModal()" style="padding: 8px 12px;">✕</button>
                </div>
                <div class="modal-body">
                    <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: 'Segoe UI', sans-serif; line-height: 1.6;">${escapeHTML(doc.content || 'Sin contenido')}</pre>
                </div>
            </div>
            <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 9999;" onclick="closeModal()"></div>
        `;
        
        document.body.appendChild(modal);
        
    } catch (error) {
        console.error('Error viewing document:', error);
        showNotification('Error al ver documento: ' + error.message, 'error');
    }
}

/**
 * Cierra el modal
 */
function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        document.body.removeChild(modal);
    }
}

/**
 * Elimina un documento
 */
async function deleteDocument(docId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este documento?')) {
        return;
    }
    
    try {
        await apiRequest(`/api/documents/${docId}`, {
            method: 'DELETE'
        });
        
        showNotification('Documento eliminado exitosamente', 'success');
        await loadDocuments();
        
    } catch (error) {
        console.error('Error deleting document:', error);
        showNotification('Error al eliminar documento: ' + error.message, 'error');
    }
}

// ============================================================================
// GESTIÓN DE CONVERSACIONES
// ============================================================================

/**
 * Prueba una conversación
 */
async function testConversation() {
    if (!validateCompanySelection()) return;
    
    const userId = document.getElementById('testUserId').value.trim();
    const message = document.getElementById('testMessage').value.trim();
    
    if (!userId || !message) {
        showNotification('Por favor completa todos los campos', 'warning');
        return;
    }
    
    try {
        toggleLoadingOverlay(true);
        
        // Crear AbortController para timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 segundos timeout
        
        console.log(`Testing conversation for user: ${userId}, company: ${currentCompanyId}`);
        console.log(`Message: ${message}`);
        
        const response = await fetch(`${API_BASE_URL}/api/conversations/${userId}/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Company-ID': currentCompanyId
            },
            body: JSON.stringify({
                message: message,
                company_id: currentCompanyId
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: `HTTP ${response.status}` }));
            throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        const container = document.getElementById('conversationResult');
        container.innerHTML = `
            <div class="result-container result-success">
                <h4>💬 Respuesta del Bot</h4>
                <p><strong>Usuario:</strong> ${escapeHTML(message)}</p>
                <p><strong>Bot:</strong> ${escapeHTML(data.bot_response || data.response || data.message || 'Sin respuesta')}</p>
                <p><strong>Agente usado:</strong> ${data.agent_used || data.agent || 'Desconocido'}</p>
                <p><strong>Empresa:</strong> ${data.company_id || currentCompanyId}</p>
                ${data.processing_time ? `<p><strong>Tiempo de procesamiento:</strong> ${data.processing_time}ms</p>` : ''}
            </div>
        `;
        
        showNotification('Conversación probada exitosamente', 'success');
        
    } catch (error) {
        console.error('Error testing conversation:', error);
        
        let errorMessage = error.message;
        
        if (error.name === 'AbortError') {
            errorMessage = 'La solicitud tardó demasiado en responder (timeout de 30 segundos)';
        }
        
        const container = document.getElementById('conversationResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al probar conversación</p>
                <p><strong>Error:</strong> ${escapeHTML(errorMessage)}</p>
                <p><strong>Usuario:</strong> ${escapeHTML(userId)}</p>
                <p><strong>Mensaje enviado:</strong> ${escapeHTML(message)}</p>
                <p><strong>Empresa:</strong> ${currentCompanyId}</p>
                <small>Revisa los logs del servidor para más detalles</small>
            </div>
        `;
        
        showNotification('Error al probar conversación: ' + errorMessage, 'error');
        
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Obtiene una conversación específica
 */
async function getConversation() {
    if (!validateCompanySelection()) return;
    
    const userId = document.getElementById('manageUserId').value.trim();
    if (!userId) {
        showNotification('Por favor ingresa un ID de usuario', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest(`/api/conversations/${userId}`);
        const conversation = response.data || response;
        
        const container = document.getElementById('conversationDetails');
        container.innerHTML = `
            <div class="result-container result-info">
                <h4>👤 Conversación de ${escapeHTML(userId)}</h4>
                <div class="conversation-history" style="max-height: 300px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px;">
                    ${conversation.history ? conversation.history.map(msg => `
                        <div class="message" style="margin-bottom: 15px; padding: 10px; border-radius: 8px; background: ${msg.role === 'user' ? '#f0fff4' : '#ebf8ff'};">
                            <strong>${msg.role === 'user' ? '👤 Usuario' : '🤖 Bot'}:</strong> ${escapeHTML(msg.content)}
                            <br><small style="color: #718096;">${msg.timestamp || 'Sin fecha'}</small>
                        </div>
                    `).join('') : '<p>No hay historial disponible</p>'}
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Error getting conversation:', error);
        const container = document.getElementById('conversationDetails');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al obtener conversación</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}

/**
 * Elimina una conversación
 */
async function deleteConversation() {
    if (!validateCompanySelection()) return;
    
    const userId = document.getElementById('manageUserId').value.trim();
    if (!userId) {
        showNotification('Por favor ingresa un ID de usuario', 'warning');
        return;
    }
    
    if (!confirm(`¿Estás seguro de que quieres eliminar la conversación de ${userId}?`)) {
        return;
    }
    
    try {
        await apiRequest(`/api/conversations/${userId}`, {
            method: 'DELETE'
        });
        
        showNotification('Conversación eliminada exitosamente', 'success');
        
        // Limpiar detalles mostrados
        const container = document.getElementById('conversationDetails');
        container.innerHTML = '';
        
        // Recargar lista
        await loadConversations();
        
    } catch (error) {
        console.error('Error deleting conversation:', error);
        showNotification('Error al eliminar conversación: ' + error.message, 'error');
    }

/**
 * Carga la lista de conversaciones
 */
async function loadConversations() {
    if (!validateCompanySelection()) return;
    
    try {
        const response = await apiRequest('/api/conversations');
        const conversations = response.data || response.conversations || [];
        
        const container = document.getElementById('conversationsList');
        if (!container) return;
        
        if (conversations.length === 0) {
            container.innerHTML = `
                <p style="padding: 20px; text-align: center; color: #718096;">
                    No hay conversaciones para la empresa ${currentCompanyId}
                </p>
            `;
            return;
        }
        
        const conversationsHTML = conversations.map(conv => `
            <div class="data-item">
                <div class="data-item-header">
                    <div class="data-item-title">👤 ${escapeHTML(conv.user_id || conv.id)}</div>
                    <div class="data-item-meta">
                        ${conv.last_message_at ? new Date(conv.last_message_at).toLocaleDateString() : 'Sin fecha'}
                    </div>
                </div>
                <div class="data-item-content">
                    Mensajes: ${conv.message_count || 0} | 
                    Estado: ${conv.status || 'Activo'}
                </div>
                <div class="data-item-actions">
                    <button class="btn btn-primary" onclick="viewConversationDetail('${conv.user_id || conv.id}')">
                        👁️ Ver
                    </button>
                    <button class="btn btn-danger" onclick="deleteConversationFromList('${conv.user_id || conv.id}')">
                        🗑️ Eliminar
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = conversationsHTML;
        
    } catch (error) {
        console.error('Error loading conversations:', error);
        const container = document.getElementById('conversationsList');
        if (container) {
            container.innerHTML = `
                <div class="result-container result-error">
                    <p>❌ Error al cargar conversaciones</p>
                    <p>${escapeHTML(error.message)}</p>
                </div>
            `;
        }
    }
}

/**
 * Ve detalles de una conversación desde la lista
 */
function viewConversationDetail(userId) {
    document.getElementById('manageUserId').value = userId;
    getConversation();
}

/**
 * Elimina una conversación desde la lista
 */
function deleteConversationFromList(userId) {
    document.getElementById('manageUserId').value = userId;
    deleteConversation();
}

// ============================================================================
// GESTIÓN DE MULTIMEDIA
// ============================================================================

/**
 * Procesa un archivo de audio
 */
async function processAudio() {
    if (!validateCompanySelection()) return;
    
    const audioFile = document.getElementById('audioFile').files[0];
    const userId = document.getElementById('audioUserId').value.trim();
    
    if (!audioFile) {
        showNotification('Por favor selecciona un archivo de audio', 'warning');
        return;
    }
    
    if (!userId) {
        showNotification('Por favor ingresa un ID de usuario', 'warning');
        return;
    }
    
    try {
        toggleLoadingOverlay(true);
        
        const formData = new FormData();
        formData.append('audio', audioFile);
        formData.append('user_id', userId);
        formData.append('company_id', currentCompanyId);
        
        const response = await apiRequest('/api/multimedia/process-voice', {
            method: 'POST',
            body: formData
        });
        
        const container = document.getElementById('audioResult');
        container.innerHTML = `
            <div class="result-container result-success">
                <h4>🎵 Procesamiento de Audio Completado</h4>
                <p><strong>Transcripción:</strong></p>
                <div class="code-block">${escapeHTML(response.transcript || 'Sin transcripción')}</div>
                ${response.bot_response ? `
                    <p><strong>Respuesta del Bot:</strong></p>
                    <div class="code-block">${escapeHTML(response.bot_response)}</div>
                ` : ''}
                <p><strong>Empresa:</strong> ${response.company_id || currentCompanyId}</p>
            </div>
        `;
        
        showNotification('Audio procesado exitosamente', 'success');
        
    } catch (error) {
        console.error('Error processing audio:', error);
        const container = document.getElementById('audioResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al procesar audio</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Procesa una imagen
 */
async function processImage() {
    if (!validateCompanySelection()) return;
    
    const imageFile = document.getElementById('imageFile').files[0];
    const userId = document.getElementById('imageUserId').value.trim();
    
    if (!imageFile) {
        showNotification('Por favor selecciona una imagen', 'warning');
        return;
    }
    
    if (!userId) {
        showNotification('Por favor ingresa un ID de usuario', 'warning');
        return;
    }
    
    try {
        toggleLoadingOverlay(true);
        
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('user_id', userId);
        formData.append('company_id', currentCompanyId);
        
        const response = await apiRequest('/api/multimedia/process-image', {
            method: 'POST',
            body: formData
        });
        
        const container = document.getElementById('imageResult');
        container.innerHTML = `
            <div class="result-container result-success">
                <h4>📸 Procesamiento de Imagen Completado</h4>
                <p><strong>Análisis:</strong></p>
                <div class="code-block">${escapeHTML(response.analysis || response.description || 'Sin análisis')}</div>
                ${response.bot_response ? `
                    <p><strong>Respuesta del Bot:</strong></p>
                    <div class="code-block">${escapeHTML(response.bot_response)}</div>
                ` : ''}
                <p><strong>Empresa:</strong> ${response.company_id || currentCompanyId}</p>
            </div>
        `;
        
        showNotification('Imagen procesada exitosamente', 'success');
        
    } catch (error) {
        console.error('Error processing image:', error);
        const container = document.getElementById('imageResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al procesar imagen</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Prueba la integración multimedia
 */
async function testMultimediaIntegration() {
    if (!validateCompanySelection()) return;
    
    try {
        const response = await apiRequest('/api/admin/multimedia/test', {
            method: 'POST',
            body: {
                company_id: currentCompanyId
            }
        });
        
        const container = document.getElementById('multimediaTestResult');
        const integration = response.multimedia_integration || {};
        
        container.innerHTML = `
            <div class="result-container result-success">
                <h4>🧪 Test de Integración Multimedia</h4>
                <div class="health-status ${integration.fully_integrated ? 'healthy' : 'warning'}">
                    <span class="status-indicator status-${integration.fully_integrated ? 'healthy' : 'warning'}"></span>
                    Integración completa: ${integration.fully_integrated ? '✅' : '❌'}
                </div>
                <div class="health-status ${integration.transcribe_audio_from_url ? 'healthy' : 'error'}">
                    <span class="status-indicator status-${integration.transcribe_audio_from_url ? 'healthy' : 'error'}"></span>
                    Transcripción de audio: ${integration.transcribe_audio_from_url ? '✅' : '❌'}
                </div>
                <div class="health-status ${integration.analyze_image_from_url ? 'healthy' : 'error'}">
                    <span class="status-indicator status-${integration.analyze_image_from_url ? 'healthy' : 'error'}"></span>
                    Análisis de imagen: ${integration.analyze_image_from_url ? '✅' : '❌'}
                </div>
                <div class="health-status ${integration.process_attachment ? 'healthy' : 'error'}">
                    <span class="status-indicator status-${integration.process_attachment ? 'healthy' : 'error'}"></span>
                    Procesamiento de archivos: ${integration.process_attachment ? '✅' : '❌'}
                </div>
                <p><strong>OpenAI disponible:</strong> ${response.openai_service_available ? '✅' : '❌'}</p>
                <p><strong>Empresa:</strong> ${response.company_id}</p>
            </div>
        `;
        
        showNotification('Test de integración completado', 'success');
        
    } catch (error) {
        console.error('Error testing multimedia integration:', error);
        const container = document.getElementById('multimediaTestResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error en test de integración</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}

// ============================================================================
// ADMINISTRACIÓN
// ============================================================================

/**
 * Actualiza la configuración de Google Calendar
 */
async function updateGoogleCalendarConfig() {
    if (!validateCompanySelection()) return;
    
    const url = document.getElementById('googleCalendarUrl').value.trim();
    if (!url) {
        showNotification('Por favor ingresa una URL de Google Calendar', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest('/api/admin/config/google-calendar', {
            method: 'POST',
            body: {
                company_id: currentCompanyId,
                google_calendar_url: url
            }
        });
        
        showNotification('Configuración de Google Calendar actualizada', 'success');
        
        // Mostrar resultado en la sección de administración
        const container = document.getElementById('adminResults');
        container.innerHTML = `
            <div class="result-container result-success">
                <h4>📅 Google Calendar Configurado</h4>
                <p><strong>Empresa:</strong> ${response.company_id}</p>
                <p><strong>URL:</strong> ${escapeHTML(url)}</p>
                <p><strong>Estado:</strong> Configurado exitosamente</p>
            </div>
        `;
        
    } catch (error) {
        console.error('Error updating Google Calendar config:', error);
        showNotification('Error al actualizar Google Calendar: ' + error.message, 'error');
        
        const container = document.getElementById('adminResults');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al configurar Google Calendar</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}

/**
 * Recarga la configuración de empresas
 */
async function reloadCompaniesConfig() {
    try {
        const response = await apiRequest('/api/admin/companies/reload-config', {
            method: 'POST'
        });
        
        showNotification('Configuración de empresas recargada', 'success');
        
        // Limpiar cache de empresas
        cache.companies = null;
        
        // Recargar empresas
        await loadCompanies();
        
        const container = document.getElementById('adminResults');
        container.innerHTML = `
            <div class="result-container result-success">
                <h4>🔄 Configuración Recargada</h4>
                <p><strong>Empresas cargadas:</strong> ${response.companies_loaded}</p>
                <p><strong>Empresas:</strong> ${response.companies.join(', ')}</p>
                <p><strong>Timestamp:</strong> ${new Date(response.timestamp * 1000).toLocaleString()}</p>
            </div>
        `;
        
    } catch (error) {
        console.error('Error reloading companies config:', error);
        showNotification('Error al recargar configuración: ' + error.message, 'error');
        
        const container = document.getElementById('adminResults');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al recargar configuración</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}

/**
 * Ejecuta diagnósticos del sistema
 */
async function runSystemDiagnostics() {
    try {
        toggleLoadingOverlay(true);
        
        const response = await apiRequest('/api/admin/diagnostics');
        
        const container = document.getElementById('adminResults');
        container.innerHTML = `
            <div class="result-container result-info">
                <h4>🔍 Diagnósticos del Sistema</h4>
                <div class="json-container">
                    <pre>${formatJSON(response)}</pre>
                </div>
            </div>
        `;
        
        showNotification('Diagnósticos ejecutados exitosamente', 'success');
        
    } catch (error) {
        console.error('Error running diagnostics:', error);
        showNotification('Error al ejecutar diagnósticos: ' + error.message, 'error');
        
        const container = document.getElementById('adminResults');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al ejecutar diagnósticos</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    } finally {
        toggleLoadingOverlay(false);
    }
}

// ============================================================================
// HEALTH CHECK Y MONITOREO
// ============================================================================

/**
 * Realiza un health check general
 */
async function performHealthCheck() {
    try {
        const response = await apiRequest('/api/health');
        
        const container = document.getElementById('generalHealthResult');
        const status = response.status;
        const statusClass = status === 'healthy' ? 'success' : 
                           status === 'partial' ? 'warning' : 'error';
        
        container.innerHTML = `
            <div class="result-container result-${statusClass}">
                <h4>🏥 Health Check General</h4>
                <div class="health-status ${status === 'healthy' ? 'healthy' : 'warning'}">
                    <span class="status-indicator status-${status === 'healthy' ? 'healthy' : 'warning'}"></span>
                    Estado: ${status.toUpperCase()}
                </div>
                <p><strong>Timestamp:</strong> ${response.timestamp}</p>
                <p><strong>Ambiente:</strong> ${response.environment || 'Desconocido'}</p>
                
                ${response.services ? `
                    <h5>Servicios:</h5>
                    ${Object.entries(response.services).map(([service, healthy]) => `
                        <div class="health-status ${healthy ? 'healthy' : 'error'}">
                            <span class="status-indicator status-${healthy ? 'healthy' : 'error'}"></span>
                            ${service}: ${healthy ? '✅' : '❌'}
                        </div>
                    `).join('')}
                ` : ''}
                
                ${response.companies ? `
                    <p><strong>Empresas configuradas:</strong> ${response.companies.total}</p>
                ` : ''}
            </div>
        `;
        
        showNotification(`Health check completado: ${status}`, status === 'healthy' ? 'success' : 'warning');
        
    } catch (error) {
        console.error('Error performing health check:', error);
        const container = document.getElementById('generalHealthResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error en health check</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}

/**
 * Realiza health check por empresa
 */
async function performCompanyHealthCheck() {
    try {
        const response = await apiRequest('/api/health/companies');
        
        const container = document.getElementById('companyHealthResult');
        
        if (!response.companies) {
            container.innerHTML = `
                <div class="result-container result-warning">
                    <p>⚠️ No se encontró información de health por empresa</p>
                </div>
            `;
            return;
        }
        
        let healthHTML = '<div class="result-container result-info"><h4>🏢 Health por Empresa</h4>';
        
        Object.entries(response.companies).forEach(([companyId, health]) => {
            const isHealthy = health.system_healthy;
            healthHTML += `
                <div class="health-status ${isHealthy ? 'healthy' : 'error'}">
                    <span class="status-indicator status-${isHealthy ? 'healthy' : 'error'}"></span>
                    <strong>${companyId}:</strong> ${isHealthy ? 'HEALTHY' : 'UNHEALTHY'}
                    ${health.orchestrator ? `(Agentes: ${health.orchestrator.agents_available?.length || 0})` : ''}
                </div>
            `;
        });
        
        healthHTML += '</div>';
        container.innerHTML = healthHTML;
        
        showNotification('Health check por empresa completado', 'success');
        
    } catch (error) {
        console.error('Error performing company health check:', error);
        const container = document.getElementById('companyHealthResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error en health check de empresas</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}
/**
 * Verifica el estado de los servicios
 */
async function checkServicesStatus() {
    try {
        const response = await apiRequest('/api/health/status/services');
        
        const container = document.getElementById('servicesStatusResult');
        
        if (!response.services) {
            container.innerHTML = `
                <div class="result-container result-warning">
                    <p>⚠️ No se encontró información de servicios</p>
                </div>
            `;
            return;
        }
        
        let servicesHTML = '<div class="result-container result-info"><h4>⚙️ Estado de Servicios</h4>';
        
        Object.entries(response.services).forEach(([serviceName, serviceInfo]) => {
            const status = serviceInfo.status;
            const isHealthy = status === 'healthy';
            const isAvailable = status !== 'unavailable';
            
            servicesHTML += `
                <div class="health-status ${isHealthy ? 'healthy' : isAvailable ? 'warning' : 'error'}">
                    <span class="status-indicator status-${isHealthy ? 'healthy' : isAvailable ? 'warning' : 'error'}"></span>
                    <strong>${serviceName}:</strong> ${status.toUpperCase()}
                    ${serviceInfo.endpoint ? `<br><small>Endpoint: ${serviceInfo.endpoint}</small>` : ''}
                    ${serviceInfo.description ? `<br><small>${serviceInfo.description}</small>` : ''}
                </div>
            `;
        });
        
        servicesHTML += `<p><strong>Timestamp:</strong> ${response.timestamp}</p></div>`;
        container.innerHTML = servicesHTML;
        
        showNotification('Verificación de servicios completada', 'success');
        
    } catch (error) {
        console.error('Error checking services status:', error);
        const container = document.getElementById('servicesStatusResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al verificar servicios</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}

/**
 * Ejecuta diagnósticos automáticos
 */
async function runAutoDiagnostics() {
    try {
        toggleLoadingOverlay(true);
        
        // Ejecutar múltiples diagnósticos en paralelo
        const [healthResponse, companiesResponse, servicesResponse] = await Promise.all([
            apiRequest('/api/health').catch(e => ({ error: e.message })),
            apiRequest('/api/health/companies').catch(e => ({ error: e.message })),
            apiRequest('/api/health/status/services').catch(e => ({ error: e.message }))
        ]);
        
        const container = document.getElementById('monitoringResults');
        
        let diagnosticsHTML = '<div class="result-container result-info"><h4>🚀 Auto-Diagnósticos del Sistema</h4>';
        
        // Health general
        if (healthResponse.error) {
            diagnosticsHTML += `
                <div class="health-status error">
                    <span class="status-indicator status-error"></span>
                    <strong>Health General:</strong> ERROR - ${escapeHTML(healthResponse.error)}
                </div>
            `;
        } else {
            const status = healthResponse.status;
            diagnosticsHTML += `
                <div class="health-status ${status === 'healthy' ? 'healthy' : 'warning'}">
                    <span class="status-indicator status-${status === 'healthy' ? 'healthy' : 'warning'}"></span>
                    <strong>Health General:</strong> ${status.toUpperCase()}
                </div>
            `;
        }
        
        // Companies health
        if (companiesResponse.error) {
            diagnosticsHTML += `
                <div class="health-status error">
                    <span class="status-indicator status-error"></span>
                    <strong>Health Empresas:</strong> ERROR - ${escapeHTML(companiesResponse.error)}
                </div>
            `;
        } else if (companiesResponse.companies) {
            const healthyCompanies = Object.values(companiesResponse.companies).filter(c => c.system_healthy).length;
            const totalCompanies = Object.keys(companiesResponse.companies).length;
            diagnosticsHTML += `
                <div class="health-status ${healthyCompanies === totalCompanies ? 'healthy' : 'warning'}">
                    <span class="status-indicator status-${healthyCompanies === totalCompanies ? 'healthy' : 'warning'}"></span>
                    <strong>Empresas Saludables:</strong> ${healthyCompanies}/${totalCompanies}
                </div>
            `;
        }
        
        // Services status
        if (servicesResponse.error) {
            diagnosticsHTML += `
                <div class="health-status error">
                    <span class="status-indicator status-error"></span>
                    <strong>Estado Servicios:</strong> ERROR - ${escapeHTML(servicesResponse.error)}
                </div>
            `;
        } else if (servicesResponse.services) {
            const healthyServices = Object.values(servicesResponse.services).filter(s => s.status === 'healthy').length;
            const totalServices = Object.keys(servicesResponse.services).length;
            diagnosticsHTML += `
                <div class="health-status ${healthyServices === totalServices ? 'healthy' : 'warning'}">
                    <span class="status-indicator status-${healthyServices === totalServices ? 'healthy' : 'warning'}"></span>
                    <strong>Servicios Saludables:</strong> ${healthyServices}/${totalServices}
                </div>
            `;
        }
        
        diagnosticsHTML += `
            <p><strong>Diagnóstico completado:</strong> ${new Date().toLocaleString()}</p>
            </div>
        `;
        
        container.innerHTML = diagnosticsHTML;
        showNotification('Auto-diagnósticos completados', 'success');
        
    } catch (error) {
        console.error('Error running auto diagnostics:', error);
        const container = document.getElementById('monitoringResults');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error en auto-diagnósticos</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Inicia monitoreo en tiempo real
 */
function startRealTimeMonitoring() {
    if (monitoringInterval) {
        showNotification('El monitoreo ya está activo', 'warning');
        return;
    }
    
    showNotification('Iniciando monitoreo en tiempo real...', 'info');
    addToLog('Real-time monitoring started', 'info');
    
    // Ejecutar monitoreo cada 30 segundos
    monitoringInterval = setInterval(async () => {
        try {
            const container = document.getElementById('monitoringResults');
            if (!container) return;
            
            // Obtener métricas básicas
            const healthResponse = await apiRequest('/api/health').catch(() => null);
            
            let monitoringHTML = `
                <div class="result-container result-info">
                    <h4>📊 Monitoreo en Tiempo Real</h4>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 100%;">
                            Monitoreando... ${new Date().toLocaleTimeString()}
                        </div>
                    </div>
            `;
            
            if (healthResponse) {
                const status = healthResponse.status;
                monitoringHTML += `
                    <div class="health-status ${status === 'healthy' ? 'healthy' : 'warning'}">
                        <span class="status-indicator status-${status === 'healthy' ? 'healthy' : 'warning'}"></span>
                        Sistema: ${status.toUpperCase()}
                    </div>
                `;
            } else {
                monitoringHTML += `
                    <div class="health-status error">
                        <span class="status-indicator status-error"></span>
                        Sistema: DESCONECTADO
                    </div>
                `;
            }
            
            // Actualizar estadísticas si hay empresa seleccionada
            if (currentCompanyId) {
                const statsResponse = await Promise.all([
                    apiRequest('/api/documents').catch(() => ({ data: [] })),
                    apiRequest('/api/conversations').catch(() => ({ data: [] }))
                ]);
                
                const docs = statsResponse[0].data?.length || 0;
                const convs = statsResponse[1].data?.length || 0;
                
                monitoringHTML += `
                    <p><strong>Empresa Activa:</strong> ${currentCompanyId}</p>
                    <p><strong>Documentos:</strong> ${docs} | <strong>Conversaciones:</strong> ${convs}</p>
                `;
            }
            
            monitoringHTML += `
                <p><strong>Última actualización:</strong> ${new Date().toLocaleString()}</p>
                </div>
            `;
            
            container.innerHTML = monitoringHTML;
            
        } catch (error) {
            console.error('Error in monitoring:', error);
            addToLog(`Monitoring error: ${error.message}`, 'error');
        }
    }, 30000);
    
    // Ejecutar inmediatamente la primera vez
    runAutoDiagnostics();
}

/**
 * Detiene el monitoreo en tiempo real
 */
function stopRealTimeMonitoring() {
    if (!monitoringInterval) {
        showNotification('El monitoreo no está activo', 'warning');
        return;
    }
    
    clearInterval(monitoringInterval);
    monitoringInterval = null;
    
    showNotification('Monitoreo en tiempo real detenido', 'success');
    addToLog('Real-time monitoring stopped', 'info');
    
    const container = document.getElementById('monitoringResults');
    if (container) {
        container.innerHTML = `
            <div class="result-container result-warning">
                <h4>⏹️ Monitoreo Detenido</h4>
                <p>El monitoreo en tiempo real ha sido detenido.</p>
                <p><strong>Detenido en:</strong> ${new Date().toLocaleString()}</p>
            </div>
        `;
    }
}

/**
 * Limpia el log del sistema
 */
function clearSystemLog() {
    systemLog = [];
    updateLogDisplay();
    addToLog('System log cleared', 'info');
    showNotification('Log del sistema limpiado', 'success');
}


// ============================================================================
// INICIALIZACIÓN Y EVENT LISTENERS
// ============================================================================

/**
 * Inicializa la aplicación cuando se carga la página
 */
document.addEventListener('DOMContentLoaded', async function() {
    addToLog('Application initializing...', 'info');
    
    try {
        // Configurar event listeners para tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.getAttribute('data-tab');
                if (tabName) {
                    switchTab(tabName);
                }
            });
        });
        
        // Configurar event listener para selector de empresa
        const companySelect = document.getElementById('companySelect');
        if (companySelect) {
            companySelect.addEventListener('change', (e) => {
                handleCompanyChange(e.target.value);
            });
        }
        
        // Cargar datos iniciales
        await loadCompanies();
        await loadSystemInfo();
        
        // Cargar tab inicial (dashboard)
        switchTab('dashboard');
        
        addToLog('Application initialized successfully', 'info');
        showNotification('Sistema inicializado correctamente', 'success', 3000);
        
    } catch (error) {
        console.error('Error initializing application:', error);
        addToLog(`Initialization error: ${error.message}`, 'error');
        showNotification('Error al inicializar la aplicación', 'error');
    }
});

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA EL HTML
// ============================================================================

// Hacer las funciones disponibles globalmente para los onclick del HTML
window.switchTab = switchTab;
window.loadSystemInfo = loadSystemInfo;
window.loadCompaniesStatus = loadCompaniesStatus;
window.uploadDocument = uploadDocument;
window.loadDocuments = loadDocuments;
window.searchDocuments = searchDocuments;
window.viewDocument = viewDocument;
window.deleteDocument = deleteDocument;
window.closeModal = closeModal;
window.testConversation = testConversation;
window.getConversation = getConversation;
window.deleteConversation = deleteConversation;
window.loadConversations = loadConversations;
window.viewConversationDetail = viewConversationDetail;
window.deleteConversationFromList = deleteConversationFromList;
window.processAudio = processAudio;
window.processImage = processImage;
window.testMultimediaIntegration = testMultimediaIntegration;
window.updateGoogleCalendarConfig = updateGoogleCalendarConfig;
window.reloadCompaniesConfig = reloadCompaniesConfig;
window.runSystemDiagnostics = runSystemDiagnostics;
window.performHealthCheck = performHealthCheck;
window.performCompanyHealthCheck = performCompanyHealthCheck;
window.checkServicesStatus = checkServicesStatus;
window.runAutoDiagnostics = runAutoDiagnostics;
window.startRealTimeMonitoring = startRealTimeMonitoring;
window.stopRealTimeMonitoring = stopRealTimeMonitoring;
window.clearSystemLog = clearSystemLog;

