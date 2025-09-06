
// script.js - Frontend Multi-Tenant Benova - Funcionalidad Completa
// ============================================================================
// CONFIGURACIÓN Y VARIABLES GLOBALES
// ============================================================================

// Configuración de la API
const API_BASE_URL = window.location.origin;
const DEFAULT_COMPANY_ID = 'benova';

// Estado global de la aplicación
let currentCompanyId = DEFAULT_COMPANY_ID; // Cambiar de '' a DEFAULT_COMPANY_ID
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
 * Cambia entre tabs con validaciones y carga de datos específicos
 * @param {string} tabName - Nombre del tab a activar
 * @returns {void}
 */
function switchTab(tabName) {
    // Validación especial para tabs que requieren empresa seleccionada
    const requiresCompany = ['prompts', 'documents', 'conversations'];
    
    if (requiresCompany.includes(tabName) && !currentCompanyId) {
        showNotification('⚠️ Por favor selecciona una empresa primero', 'warning');
        
        // Hacer focus en el selector de empresas
        const companySelect = document.getElementById('companySelect');
        if (companySelect) {
            companySelect.focus();
            // Añadir clase temporal para resaltar
            companySelect.classList.add('highlight');
            setTimeout(() => companySelect.classList.remove('highlight'), 2000);
        }
        
        // Log del intento
        addToLog(`Tab switch blocked: ${tabName} requires company selection`, 'warning');
        return;
    }
    
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
    
    // Log del cambio de tab
    addToLog(`Switched to tab: ${tabName}`, 'info');
    
    // Cargar datos específicos del tab según el caso
    loadTabContent(tabName);
}

/**
 * Carga el contenido específico de cada tab
 * @param {string} tabName - Nombre del tab activo
 */
async function loadTabContent(tabName) {
    try {
        // Mostrar indicador de carga si es necesario
        const shouldShowLoader = ['dashboard', 'prompts', 'documents', 'conversations', 'health'].includes(tabName);
        
        if (shouldShowLoader) {
            toggleLoadingOverlay(true);
        }
        
        switch(tabName) {
            case 'dashboard':
                await loadDashboardData();
                break;
                
            case 'prompts':
                await loadPromptsTab();
                break;
                
            case 'documents':
                await loadDocumentsTab();
                break;
                
            case 'conversations':
                await loadConversationsTab();
                break;
                
            case 'multimedia':
                await loadMultimediaTab();
                break;
                
            case 'admin':
                await loadAdminTab();
                break;
                
            case 'health':
                await loadHealthCheckTab();
                break;
                
            default:
                console.log(`No specific loader for tab: ${tabName}`);
        }
        
    } catch (error) {
        console.error(`Error loading tab content for ${tabName}:`, error);
        showNotification(`Error al cargar ${tabName}: ${error.message}`, 'error');
        addToLog(`Error loading tab ${tabName}: ${error.message}`, 'error');
        
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Carga el contenido del tab de documentos
 */
async function loadDocumentsTab() {
    if (!currentCompanyId) {
        const container = document.getElementById('documentsTabContent');
        if (container) {
            container.innerHTML = `
                <div class="warning-message">
                    <h3>⚠️ Empresa no seleccionada</h3>
                    <p>Selecciona una empresa para gestionar sus documentos.</p>
                </div>
            `;
        }
        return;
    }
    
    addToLog(`Loading documents for company: ${currentCompanyId}`, 'info');
    await loadDocuments();
}

/**
 * Carga el contenido del tab de conversaciones
 */
async function loadConversationsTab() {
    if (!currentCompanyId) {
        const container = document.getElementById('conversationsTabContent');
        if (container) {
            container.innerHTML = `
                <div class="warning-message">
                    <h3>⚠️ Empresa no seleccionada</h3>
                    <p>Selecciona una empresa para ver sus conversaciones.</p>
                </div>
            `;
        }
        return;
    }
    
    addToLog(`Loading conversations for company: ${currentCompanyId}`, 'info');
    await loadConversations();
}

/**
 * Carga el contenido del tab multimedia
 */
async function loadMultimediaTab() {
    const container = document.getElementById('multimediaTabContent');
    if (container && !container.hasChildNodes()) {
        // Solo cargar si el contenido no existe ya
        container.innerHTML = `
            <div class="multimedia-section">
                <h3>🎤 Procesamiento Multimedia</h3>
                <p>Funciones de audio e imagen disponibles para ${currentCompanyId || 'todas las empresas'}</p>
                <!-- Aquí va el contenido multimedia -->
            </div>
        `;
    }
    
    addToLog('Multimedia tab loaded', 'info');
}

/**
 * Carga el contenido del tab de administración
 */
async function loadAdminTab() {
    const container = document.getElementById('adminTabContent');
    if (container) {
        try {
            // Cargar configuración actual
            const config = await apiRequest('/api/admin/config');
            
            container.innerHTML = `
                <div class="admin-section">
                    <h3>🔧 Panel de Administración</h3>
                    <div class="admin-info">
                        <p><strong>Empresa activa:</strong> ${currentCompanyId || 'Ninguna'}</p>
                        <p><strong>Total empresas:</strong> ${config.total_companies || 0}</p>
                        <p><strong>Modo:</strong> ${config.mode || 'Multi-tenant'}</p>
                    </div>
                    <div class="admin-actions">
                        <button onclick="reloadCompaniesConfig()" class="btn-primary">
                            🔄 Recargar Configuración
                        </button>
                        <button onclick="runSystemDiagnostics()" class="btn-secondary">
                            🔍 Ejecutar Diagnóstico
                        </button>
                    </div>
                </div>
            `;
            
        } catch (error) {
            container.innerHTML = `
                <div class="error-message">
                    <h3>❌ Error al cargar administración</h3>
                    <p>${error.message}</p>
                </div>
            `;
        }
    }
    
    addToLog('Admin tab loaded', 'info');
}

/**
 * Carga el contenido del tab de health check
 */
async function loadHealthCheckTab() {
    const container = document.getElementById('healthTabContent');
    if (container) {
        container.innerHTML = `
            <div class="health-section">
                <h3>🏥 Health Check del Sistema</h3>
                <div id="healthStatus">
                    <div class="loading">Verificando estado del sistema...</div>
                </div>
            </div>
        `;
        
        // Ejecutar health check
        await performHealthCheck();
    }
    
    addToLog('Health check tab loaded', 'info');
}

/**
 * Inicializa los event listeners para los tabs
 */
function initializeTabs() {
    // Agregar event listeners a todos los botones de tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            if (tabName) {
                switchTab(tabName);
            }
        });
    });
    
    // Verificar si hay un tab por defecto en la URL
    const urlParams = new URLSearchParams(window.location.search);
    const defaultTab = urlParams.get('tab');
    
    if (defaultTab && document.querySelector(`[data-tab="${defaultTab}"]`)) {
        switchTab(defaultTab);
    } else {
        // Cargar dashboard por defecto
        switchTab('dashboard');
    }
    
    addToLog('Tabs initialized', 'info');
}

/**
 * Actualiza el contador de notificaciones en un tab
 * @param {string} tabName - Nombre del tab
 * @param {number} count - Número de notificaciones
 */
function updateTabNotificationCount(tabName, count) {
    const tab = document.querySelector(`[data-tab="${tabName}"]`);
    if (!tab) return;
    
    // Remover badge existente
    const existingBadge = tab.querySelector('.tab-badge');
    if (existingBadge) {
        existingBadge.remove();
    }
    
    // Agregar nuevo badge si count > 0
    if (count > 0) {
        const badge = document.createElement('span');
        badge.className = 'tab-badge';
        badge.textContent = count > 99 ? '99+' : count;
        tab.appendChild(badge);
    }
}

/**
 * Verifica si un tab requiere empresa seleccionada
 * @param {string} tabName - Nombre del tab
 * @returns {boolean}
 */
function tabRequiresCompany(tabName) {
    const requiresCompany = ['prompts', 'documents', 'conversations'];
    return requiresCompany.includes(tabName);
}

/**
 * Obtiene el tab activo actual
 * @returns {string|null} Nombre del tab activo o null
 */
function getActiveTab() {
    const activeTab = document.querySelector('.tab.active');
    return activeTab ? activeTab.getAttribute('data-tab') : null;
}

/**
 * Recarga el contenido del tab activo actual
 */
async function refreshActiveTab() {
    const activeTab = getActiveTab();
    if (activeTab) {
        addToLog(`Refreshing active tab: ${activeTab}`, 'info');
        await loadTabContent(activeTab);
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
            
            // Verificar si las empresas están directamente en response.companies
            if (response.companies && typeof response.companies === 'object') {
                const companiesObj = response.companies;
                
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
            // Fallback: verificar si están en response.data.companies (formato alternativo)
            else if (response.data && response.data.companies) {
                const companiesObj = response.data.companies;
                
                // Convertir objeto de empresas a array
                cache.companies = Object.keys(companiesObj).map(companyId => {
                    const companyData = companiesObj[companyId];
                    return {
                        id: companyId,
                        name: companyData.company_name || companyId
                    };
                });
                
                console.log('Converted companies from /api/companies (data format):', cache.companies);
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
        
        // Recargar la pestaña activa actual
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab) {
            const tabId = activeTab.id;
            
            // Recargar contenido según la pestaña activa
            switch(tabId) {
                case 'dashboard':
                    loadDashboardData();
                    break;
                case 'prompts':
                    loadPromptsTab();
                    break;
                case 'documents':
                    loadDocuments();
                    break;
                case 'conversations':
                    loadConversations();
                    break;
            }
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
} // <- Esta llave de cierre faltaba

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
// GESTIÓN DE MULTIMEDIA - FUNCIONES CORREGIDAS Y NUEVAS
// ============================================================================

/**
 * Variables para grabación de voz
 */
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

/**
 * Procesa un archivo de audio - CORREGIDO para mostrar respuesta del bot
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
        
        console.log('Full audio response:', response); // Debug
        
        const container = document.getElementById('audioResult');
        
        // Extraer los campos de la respuesta de manera más robusta
        const transcript = response.transcript || response.transcription || 'Sin transcripción';
        const botResponse = response.bot_response || response.response || response.message || null;
        const companyId = response.company_id || currentCompanyId;
        const processingTime = response.processing_time || response.time || null;
        
        let resultHTML = `
            <div class="result-container result-success">
                <h4>🎵 Procesamiento de Audio Completado</h4>
                <p><strong>Transcripción:</strong></p>
                <div class="code-block">${escapeHTML(transcript)}</div>
        `;
        
        if (botResponse) {
            resultHTML += `
                <p><strong>Respuesta del Bot:</strong></p>
                <div class="code-block">${escapeHTML(botResponse)}</div>
            `;
        }
        
        resultHTML += `
                <p><strong>Empresa:</strong> ${companyId}</p>
        `;
        
        if (processingTime) {
            resultHTML += `<p><strong>Tiempo:</strong> ${processingTime}ms</p>`;
        }
        
        resultHTML += `</div>`;
        
        container.innerHTML = resultHTML;
        showNotification('Audio procesado exitosamente', 'success');
        
    } catch (error) {
        console.error('Error processing audio:', error);
        const container = document.getElementById('audioResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al procesar audio</p>
                <p><strong>Error:</strong> ${escapeHTML(error.message)}</p>
                <p><strong>Usuario:</strong> ${escapeHTML(userId)}</p>
                <p><strong>Empresa:</strong> ${currentCompanyId}</p>
            </div>
        `;
        showNotification('Error al procesar audio: ' + error.message, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Procesa una imagen - CORREGIDO para mostrar respuesta del bot
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
        
        console.log('Full image response:', response); // Debug
        
        const container = document.getElementById('imageResult');
        
        // Extraer los campos de la respuesta de manera más robusta
        const analysis = response.analysis || response.description || response.image_analysis || 'Sin análisis';
        const botResponse = response.bot_response || response.response || response.message || null;
        const companyId = response.company_id || currentCompanyId;
        const processingTime = response.processing_time || response.time || null;
        
        let resultHTML = `
            <div class="result-container result-success">
                <h4>📸 Procesamiento de Imagen Completado</h4>
                <p><strong>Análisis:</strong></p>
                <div class="code-block">${escapeHTML(analysis)}</div>
        `;
        
        if (botResponse) {
            resultHTML += `
                <p><strong>Respuesta del Bot:</strong></p>
                <div class="code-block">${escapeHTML(botResponse)}</div>
            `;
        }
        
        resultHTML += `
                <p><strong>Empresa:</strong> ${companyId}</p>
        `;
        
        if (processingTime) {
            resultHTML += `<p><strong>Tiempo:</strong> ${processingTime}ms</p>`;
        }
        
        resultHTML += `</div>`;
        
        container.innerHTML = resultHTML;
        showNotification('Imagen procesada exitosamente', 'success');
        
    } catch (error) {
        console.error('Error processing image:', error);
        const container = document.getElementById('imageResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al procesar imagen</p>
                <p><strong>Error:</strong> ${escapeHTML(error.message)}</p>
                <p><strong>Usuario:</strong> ${escapeHTML(userId)}</p>
                <p><strong>Empresa:</strong> ${currentCompanyId}</p>
            </div>
        `;
        showNotification('Error al procesar imagen: ' + error.message, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * NUEVA: Captura pantalla y la envía
 */
async function captureScreen() {
    if (!validateCompanySelection()) return;
    
    const userId = document.getElementById('imageUserId').value.trim();
    if (!userId) {
        showNotification('Por favor ingresa un ID de usuario', 'warning');
        return;
    }
    
    try {
        showNotification('Solicitando permisos de captura de pantalla...', 'info');
        
        const stream = await navigator.mediaDevices.getDisplayMedia({
            video: {
                mediaSource: 'screen',
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            }
        });
        
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play();
        
        video.addEventListener('loadedmetadata', () => {
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            
            // Detener el stream
            stream.getTracks().forEach(track => track.stop());
            
            showNotification('Captura realizada, procesando...', 'info');
            
            // Convertir a blob y procesar
            canvas.toBlob(async (blob) => {
                try {
                    await processImageBlob(blob, userId, 'Captura de pantalla');
                } catch (error) {
                    console.error('Error processing screen capture:', error);
                    showNotification('Error al procesar captura de pantalla: ' + error.message, 'error');
                }
            }, 'image/png', 0.9);
        });
        
    } catch (error) {
        console.error('Error capturing screen:', error);
        if (error.name === 'NotAllowedError') {
            showNotification('Permisos de captura de pantalla denegados', 'warning');
        } else {
            showNotification('Error al capturar pantalla: ' + error.message, 'error');
        }
    }
}

/**
 * NUEVA: Procesa blob de imagen (para capturas de pantalla)
 */
async function processImageBlob(blob, userId, description = 'Imagen') {
    try {
        toggleLoadingOverlay(true);
        
        const formData = new FormData();
        formData.append('image', blob, `${description.toLowerCase().replace(/\s+/g, '_')}.png`);
        formData.append('user_id', userId);
        formData.append('company_id', currentCompanyId);
        
        const response = await apiRequest('/api/multimedia/process-image', {
            method: 'POST',
            body: formData
        });
        
        console.log('Image blob response:', response); // Debug
        
        const container = document.getElementById('imageResult');
        
        // Extraer campos de manera robusta
        const analysis = response.analysis || response.description || response.image_analysis || 'Sin análisis';
        const botResponse = response.bot_response || response.response || response.message || null;
        const companyId = response.company_id || currentCompanyId;
        
        let resultHTML = `
            <div class="result-container result-success">
                <h4>📸 ${description} Procesada</h4>
                <p><strong>Análisis:</strong></p>
                <div class="code-block">${escapeHTML(analysis)}</div>
        `;
        
        if (botResponse) {
            resultHTML += `
                <p><strong>Respuesta del Bot:</strong></p>
                <div class="code-block">${escapeHTML(botResponse)}</div>
            `;
        }
        
        resultHTML += `
                <p><strong>Empresa:</strong> ${companyId}</p>
            </div>
        `;
        
        container.innerHTML = resultHTML;
        showNotification(`${description} procesada exitosamente`, 'success');
        
    } catch (error) {
        console.error(`Error processing ${description.toLowerCase()}:`, error);
        showNotification(`Error al procesar ${description.toLowerCase()}: ${error.message}`, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * NUEVA: Inicia/detiene grabación de voz
 */
async function toggleVoiceRecording() {
    if (!validateCompanySelection()) return;
    
    const userId = document.getElementById('audioUserId').value.trim();
    if (!userId) {
        showNotification('Por favor ingresa un ID de usuario', 'warning');
        return;
    }
    
    const button = document.getElementById('recordVoiceButton');
    
    try {
        if (!isRecording) {
            // Iniciar grabación
            showNotification('Solicitando permisos de micrófono...', 'info');
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            });
            
            // Verificar soporte de MediaRecorder
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
                ? 'audio/webm;codecs=opus' 
                : 'audio/webm';
            
            mediaRecorder = new MediaRecorder(stream, { mimeType });
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: mimeType });
                audioChunks = [];
                
                try {
                    await processAudioBlob(audioBlob, userId);
                } catch (error) {
                    showNotification('Error al procesar grabación: ' + error.message, 'error');
                }
                
                // Detener todos los tracks
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
            isRecording = true;
            
            button.textContent = '🛑 Detener Grabación';
            button.classList.remove('btn-primary');
            button.classList.add('btn-danger');
            
            showNotification('Grabación iniciada... Habla ahora', 'success');
            
        } else {
            // Detener grabación
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
            }
            isRecording = false;
            
            button.textContent = '🎤 Grabar Voz';
            button.classList.remove('btn-danger');
            button.classList.add('btn-primary');
            
            showNotification('Procesando grabación...', 'info');
        }
        
    } catch (error) {
        console.error('Error with voice recording:', error);
        
        if (error.name === 'NotAllowedError') {
            showNotification('Permisos de micrófono denegados', 'warning');
        } else {
            showNotification('Error con la grabación: ' + error.message, 'error');
        }
        
        // Resetear estado
        isRecording = false;
        button.textContent = '🎤 Grabar Voz';
        button.classList.remove('btn-danger');
        button.classList.add('btn-primary');
    }
}

/**
 * NUEVA: Procesa blob de audio grabado
 */
async function processAudioBlob(blob, userId) {
    try {
        toggleLoadingOverlay(true);
        
        const formData = new FormData();
        formData.append('audio', blob, 'voice_recording.webm');
        formData.append('user_id', userId);
        formData.append('company_id', currentCompanyId);
        
        const response = await apiRequest('/api/multimedia/process-voice', {
            method: 'POST',
            body: formData
        });
        
        console.log('Voice recording response:', response); // Debug
        
        const container = document.getElementById('audioResult');
        
        // Extraer campos de manera robusta
        const transcript = response.transcript || response.transcription || 'Sin transcripción';
        const botResponse = response.bot_response || response.response || response.message || null;
        const companyId = response.company_id || currentCompanyId;
        
        let resultHTML = `
            <div class="result-container result-success">
                <h4>🎵 Grabación de Voz Procesada</h4>
                <p><strong>Transcripción:</strong></p>
                <div class="code-block">${escapeHTML(transcript)}</div>
        `;
        
        if (botResponse) {
            resultHTML += `
                <p><strong>Respuesta del Bot:</strong></p>
                <div class="code-block">${escapeHTML(botResponse)}</div>
            `;
        }
        
        resultHTML += `
                <p><strong>Empresa:</strong> ${companyId}</p>
            </div>
        `;
        
        container.innerHTML = resultHTML;
        showNotification('Grabación procesada exitosamente', 'success');
        
    } catch (error) {
        console.error('Error processing voice recording:', error);
        const container = document.getElementById('audioResult');
        container.innerHTML = `
            <div class="result-container result-error">
                <p>❌ Error al procesar grabación</p>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
        showNotification('Error al procesar grabación: ' + error.message, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}

/**
 * Prueba la integración multimedia - MANTENIDO
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
                e.preventDefault();
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
        
        // Configurar drag and drop para archivos
        setupFileUploadHandlers();
        
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

/**
 * Configura los manejadores de drag and drop para archivos
 */
function setupFileUploadHandlers() {
    const fileUploadElements = document.querySelectorAll('.file-upload');
    
    fileUploadElements.forEach(element => {
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            element.classList.add('dragover');
        });
        
        element.addEventListener('dragleave', (e) => {
            e.preventDefault();
            element.classList.remove('dragover');
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            element.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const input = element.querySelector('input[type="file"]');
                if (input) {
                    input.files = files;
                    showNotification(`Archivo seleccionado: ${files[0].name}`, 'success', 3000);
                }
            }
        });
    });
}


// ============================================================================
// GESTIÓN DE PROMPTS PERSONALIZADOS
// ============================================================================
async function loadPromptsTab() {
    const container = document.getElementById('promptsTabContent');
    
    // Validar que hay una empresa seleccionada
    if (!currentCompanyId) {
        container.innerHTML = `
            <div class="warning-message">
                <h3>⚠️ Selecciona una empresa</h3>
                <p>Por favor, selecciona una empresa del menú desplegable superior para gestionar sus prompts.</p>
            </div>
        `;
        return;
    }
    
    const agentNames = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent'];
    
    let html = `
        <div class="prompts-management">
            <h3>🤖 Gestión de Prompts - ${currentCompanyId}</h3>
            <div class="prompts-grid">
    `;
    
    for (const agentName of agentNames) {
        const displayName = agentName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        html += `
            <div class="prompt-card" data-agent="${agentName}">
                <h4>${displayName}</h4>
                <div class="prompt-status" id="status-${agentName}">Cargando...</div>
                <textarea class="prompt-editor" id="prompt-${agentName}" rows="8" placeholder="Cargando prompt..."></textarea>
                <div class="prompt-actions">
                    <button onclick="updatePrompt('${agentName}')" class="btn-primary">Actualizar</button>
                    <button onclick="resetPrompt('${agentName}')" class="btn-secondary">Restaurar</button>
                    <button onclick="previewPrompt('${agentName}')" class="btn-info">Vista Previa</button>
                </div>
            </div>
        `;
    }
    
    html += `
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Cargar prompts actuales
    await loadCurrentPrompts();
}

async function loadCurrentPrompts() {
    // Validar empresa seleccionada
    if (!currentCompanyId) {
        showNotification('Por favor selecciona una empresa primero', 'warning');
        return;
    }
    
    try {
        addToLog(`Loading prompts for company: ${currentCompanyId}`, 'info');
        const response = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId}`);
        
        if (!response || !response.agents) {
            throw new Error('Invalid response format');
        }
        
        for (const [agentName, promptData] of Object.entries(response.agents)) {
            const textarea = document.getElementById(`prompt-${agentName}`);
            const status = document.getElementById(`status-${agentName}`);
            
            if (textarea && promptData) {
                textarea.value = promptData.current_prompt || '';
                
                if (status) {
                    status.innerHTML = promptData.is_custom 
                        ? `<span class="custom">✏️ Personalizado</span>`
                        : `<span class="default">🔧 Por defecto</span>`;
                }
            }
        }
        
        showNotification('Prompts cargados exitosamente', 'success');
        
    } catch (error) {
        console.error('Error loading prompts:', error);
        showNotification('Error al cargar prompts: ' + error.message, 'error');
        
        // Mostrar mensaje de error en cada textarea
        document.querySelectorAll('.prompt-editor').forEach(textarea => {
            textarea.value = 'Error al cargar el prompt. Por favor, verifica la conexión.';
            textarea.disabled = true;
        });
    }
}

async function updatePrompt(agentName) {
    if (!currentCompanyId) {
        showNotification('Por favor selecciona una empresa primero', 'warning');
        return;
    }
    
    const textarea = document.getElementById(`prompt-${agentName}`);
    const promptTemplate = textarea.value.trim();
    
    if (!promptTemplate) {
        showNotification('El prompt no puede estar vacío', 'error');
        return;
    }
    
    try {
        toggleLoadingOverlay(true);
        addToLog(`Updating prompt for ${agentName} in company ${currentCompanyId}`, 'info');
        
        const response = await apiRequest(`/api/admin/prompts/${agentName}`, {
            method: 'PUT',
            body: JSON.stringify({
                company_id: currentCompanyId,
                prompt_template: promptTemplate
            })
        });
        
        showNotification(`Prompt de ${agentName} actualizado exitosamente`, 'success');
        await loadCurrentPrompts(); // Recargar estado
        
    } catch (error) {
        console.error('Error updating prompt:', error);
        showNotification('Error al actualizar prompt: ' + error.message, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}

async function resetPrompt(agentName) {
    if (!currentCompanyId) {
        showNotification('Por favor selecciona una empresa primero', 'warning');
        return;
    }
    
    if (!confirm(`¿Estás seguro de restaurar el prompt por defecto para ${agentName}?`)) {
        return;
    }
    
    try {
        toggleLoadingOverlay(true);
        addToLog(`Resetting prompt for ${agentName} in company ${currentCompanyId}`, 'info');
        
        const response = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${currentCompanyId}`, {
            method: 'DELETE'
        });
        
        showNotification(`Prompt de ${agentName} restaurado al valor por defecto`, 'success');
        await loadCurrentPrompts();
        
    } catch (error) {
        console.error('Error resetting prompt:', error);
        showNotification('Error al restaurar prompt: ' + error.message, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}


async function previewPrompt(agentName) {
    if (!currentCompanyId) {
        showNotification('Por favor selecciona una empresa primero', 'warning');
        return;
    }
    
    const textarea = document.getElementById(`prompt-${agentName}`);
    const promptTemplate = textarea.value.trim();
    
    if (!promptTemplate) {
        showNotification('El prompt no puede estar vacío', 'error');
        return;
    }
    
    const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?');
    if (!testMessage) return;
    
    try {
        toggleLoadingOverlay(true);
        addToLog(`Previewing prompt for ${agentName} in company ${currentCompanyId}`, 'info');
        
        const response = await apiRequest('/api/admin/prompts/preview', {
            method: 'POST',
            body: JSON.stringify({
                company_id: currentCompanyId,
                agent_name: agentName,
                prompt_template: promptTemplate,
                test_message: testMessage
            })
        });
        
        // Mostrar preview en modal
        showPreviewModal(agentName, testMessage, response.preview_response);
        
    } catch (error) {
        console.error('Error in preview:', error);
        showNotification('Error en vista previa: ' + error.message, 'error');
    } finally {
        toggleLoadingOverlay(false);
    }
}

function showPreviewModal(agentName, testMessage, previewResponse) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>🔍 Vista Previa - ${agentName}</h3>
            <div class="preview-content">
                <p><strong>Mensaje de prueba:</strong></p>
                <div class="test-message">${escapeHTML(testMessage)}</div>
                
                <p><strong>Respuesta simulada:</strong></p>
                <div class="preview-response">${escapeHTML(previewResponse)}</div>
            </div>
            <button onclick="closeModal()" class="btn-primary">Cerrar</button>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.onclick = (e) => { if (e.target === modal) closeModal(); };
}

document.addEventListener('DOMContentLoaded', function() {
    // Configurar el selector de empresas
    const companySelect = document.getElementById('companySelect');
    if (companySelect) {
        // Establecer valor por defecto si existe
        if (DEFAULT_COMPANY_ID) {
            companySelect.value = DEFAULT_COMPANY_ID;
            currentCompanyId = DEFAULT_COMPANY_ID;
        }
        
        // Escuchar cambios
        companySelect.addEventListener('change', (e) => {
            handleCompanyChange(e.target.value);
        });
    }
    
    // Cargar empresas disponibles
    loadCompanies();
    
    // Cargar dashboard inicial
    loadDashboardData();
});

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA EL HTML
// ============================================================================

// Hacer las funciones disponibles globalmente para los onclick del HTML
window.captureScreen = captureScreen;
window.toggleVoiceRecording = toggleVoiceRecording;
window.switchTab = switchTab;
window.loadTabContent = loadTabContent;
window.initializeTabs = initializeTabs;
window.updateTabNotificationCount = updateTabNotificationCount;
window.refreshActiveTab = refreshActiveTab;
window.getActiveTab = getActiveTab;
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

// 🆕 AGREGAR ESTAS LÍNEAS PARA GESTIÓN DE PROMPTS
window.loadPromptsTab = loadPromptsTab;
window.loadCurrentPrompts = loadCurrentPrompts;
window.updatePrompt = updatePrompt;
window.resetPrompt = resetPrompt;
window.previewPrompt = previewPrompt;
window.showPreviewModal = showPreviewModal;
window.closeModal = closeModal; // Ya existe, pero importante para el modal de prompts

// Log final de inicialización del script
addToLog('Script loaded successfully', 'info');



