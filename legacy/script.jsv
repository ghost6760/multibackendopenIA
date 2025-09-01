// Multi-Tenant Chatbot Frontend
const API_BASE = window.location.origin + '/';

// Global state
let currentCompanyId = 'benova'; // Default
let companies = {};
let mediaRecorder;
let audioChunks = [];
let cameraStream;

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    loadCompanies();
    setupEventListeners();
    showLoading('Inicializando sistema multi-tenant...');
});

// ==================== COMPANY MANAGEMENT ====================

async function loadCompanies() {
    try {
        showLoading('Cargando empresas configuradas...');
        const response = await fetch(`${API_BASE}companies`);
        const data = await response.json();
        
        if (data.status === 'success') {
            companies = data.companies;
            populateCompanySelector();
            updateCompanyIndicators();
            loadSystemOverview();
            hideLoading();
            showToast('✅ Empresas cargadas correctamente', 'success');
        } else {
            throw new Error(data.message || 'Error cargando empresas');
        }
    } catch (error) {
        console.error('Error loading companies:', error);
        hideLoading();
        showToast('❌ Error cargando empresas: ' + error.message, 'error');
    }
}

function populateCompanySelector() {
    const selector = document.getElementById('currentCompany');
    selector.innerHTML = '';
    
    Object.keys(companies).forEach(companyId => {
        const option = document.createElement('option');
        option.value = companyId;
        option.textContent = `${companies[companyId].company_name} (${companyId})`;
        selector.appendChild(option);
    });
    
    // Set default
    if (Object.keys(companies).includes(currentCompanyId)) {
        selector.value = currentCompanyId;
    } else {
        currentCompanyId = Object.keys(companies)[0] || 'benova';
        selector.value = currentCompanyId;
    }
    
    updateCompanyContext();
}

function updateCompanyIndicators() {
    const currentCompany = companies[currentCompanyId];
    if (!currentCompany) return;
    
    // Update all company indicators
    const indicators = [
        'docCompanyIndicator', 'bulkCompanyIndicator', 
        'searchCompanyIndicator', 'chatCompanyName'
    ];
    
    indicators.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = currentCompany.company_name;
        }
    });
    
    // Update chat services
    const servicesElement = document.getElementById('chatCompanyServices');
    if (servicesElement && currentCompany.services) {
        servicesElement.textContent = `Servicios: ${currentCompany.services}`;
    }
    
    // Update camera modal
    const cameraCompany = document.getElementById('cameraCompany');
    if (cameraCompany) {
        cameraCompany.textContent = currentCompany.company_name;
    }
    
    // Update recording status
    const recordingCompany = document.getElementById('recordingCompany');
    if (recordingCompany) {
        recordingCompany.textContent = currentCompany.company_name;
    }
}

async function updateCompanyContext() {
    updateCompanyIndicators();
    await loadCompanyInfo();
    clearPreviousData();
}

async function loadCompanyInfo() {
    try {
        const response = await fetch(`${API_BASE}company/${currentCompanyId}/status`);
        const data = await response.json();
        
        const infoDiv = document.getElementById('companyInfo');
        
        if (data.status === 'success') {
            const info = data.data;
            infoDiv.innerHTML = `
                <div class="company-details">
                    <h3>${info.company_name} (${info.company_id})</h3>
                    <div class="company-stats">
                        <span class="stat">📍 Servicios: ${info.services}</span>
                        <span class="stat ${info.orchestrator_ready ? 'status-healthy' : 'status-error'}">
                            🤖 Orquestador: ${info.orchestrator_ready ? 'Listo' : 'No disponible'}
                        </span>
                        <span class="stat ${info.system_healthy ? 'status-healthy' : 'status-warning'}">
                            🩺 Estado: ${info.system_healthy ? 'Saludable' : 'Requiere atención'}
                        </span>
                    </div>
                    <div class="technical-info">
                        <small>📊 Índice: ${info.vectorstore_index}</small>
                        <small>🔑 Prefijo: ${info.redis_prefix}</small>
                    </div>
                </div>
            `;
        } else {
            infoDiv.innerHTML = `<div class="error-info">❌ Error cargando información de ${currentCompanyId}</div>`;
        }
    } catch (error) {
        console.error('Error loading company info:', error);
        document.getElementById('companyInfo').innerHTML = 
            `<div class="error-info">❌ Error de conexión</div>`;
    }
}

async function loadSystemOverview() {
    try {
        const response = await fetch(`${API_BASE}health`);
        const data = await response.json();
        
        const overviewDiv = document.getElementById('systemOverview');
        
        if (data.companies) {
            const healthData = data.companies.health || {};
            const statsData = data.companies.stats || {};
            
            let overviewHTML = '';
            Object.keys(companies).forEach(companyId => {
                const company = companies[companyId];
                const health = healthData[companyId] || {};
                const stats = statsData[companyId] || {};
                
                const isHealthy = health.system_healthy || false;
                const conversations = stats.conversations || 0;
                const documents = stats.documents || 0;
                
                overviewHTML += `
                    <div class="company-overview-card ${companyId === currentCompanyId ? 'active' : ''}" 
                         data-company="${companyId}">
                        <h4>${company.company_name}</h4>
                        <div class="overview-stats">
                            <span class="${isHealthy ? 'status-healthy' : 'status-error'}">
                                ${isHealthy ? '✅' : '❌'} ${isHealthy ? 'Saludable' : 'Error'}
                            </span>
                            <span>💬 ${conversations} conversaciones</span>
                            <span>📄 ${documents} documentos</span>
                        </div>
                        <button onclick="selectCompany('${companyId}')" class="btn-small">
                            ${companyId === currentCompanyId ? '✓ Activa' : 'Seleccionar'}
                        </button>
                    </div>
                `;
            });
            
            overviewDiv.innerHTML = overviewHTML;
        } else {
            overviewDiv.innerHTML = '<p>No se pudo cargar la vista general del sistema</p>';
        }
    } catch (error) {
        console.error('Error loading system overview:', error);
        document.getElementById('systemOverview').innerHTML = 
            '<p>❌ Error cargando vista general</p>';
    }
}

function selectCompany(companyId) {
    if (companies[companyId]) {
        currentCompanyId = companyId;
        document.getElementById('currentCompany').value = companyId;
        updateCompanyContext();
        loadSystemOverview();
        showToast(`🏢 Empresa cambiada a: ${companies[companyId].company_name}`, 'info');
    }
}

function clearPreviousData() {
    // Clear documents list
    document.getElementById('documentsList').innerHTML = '';
    // Clear conversations list  
    document.getElementById('conversationsList').innerHTML = '';
    // Clear search results
    document.getElementById('searchResults').innerHTML = '';
    // Clear chat history
    document.getElementById('chatHistory').innerHTML = '';
}

// ==================== EVENT LISTENERS ====================

function setupEventListeners() {
    // Company selector
    document.getElementById('currentCompany').addEventListener('change', (e) => {
        currentCompanyId = e.target.value;
        updateCompanyContext();
        loadSystemOverview();
    });
    
    // Refresh companies
    document.getElementById('refreshCompanies').addEventListener('click', loadCompanies);
    
    // Company actions
    document.getElementById('checkHealthBtn').addEventListener('click', checkCompanyHealth);
    document.getElementById('viewStatsBtn').addEventListener('click', viewCompanyStats);
    document.getElementById('resetCacheBtn').addEventListener('click', resetCompanyCache);
    document.getElementById('viewAllCompanies').addEventListener('click', viewAllCompanies);
    
    // Document management
    document.getElementById('addDocumentForm').addEventListener('submit', addDocument);
    document.getElementById('bulkUploadForm').addEventListener('submit', bulkUploadDocuments);
    document.getElementById('searchDocumentsForm').addEventListener('submit', searchDocuments);
    document.getElementById('listDocumentsBtn').addEventListener('click', listDocuments);
    document.getElementById('cleanupVectorsBtn').addEventListener('click', cleanupVectors);
    document.getElementById('diagnosticsBtn').addEventListener('click', runDiagnostics);
    
    // Conversation management
    document.getElementById('listConversationsBtn').addEventListener('click', listConversations);
    document.getElementById('conversationStatsBtn').addEventListener('click', viewConversationStats);
    
    // Chat testing
    document.getElementById('chatForm').addEventListener('submit', sendChatMessage);
    
    // Multimedia
    document.getElementById('recordVoiceBtn').addEventListener('click', startVoiceRecording);
    document.getElementById('stopRecordingBtn').addEventListener('click', stopVoiceRecording);
    document.getElementById('captureImageBtn').addEventListener('click', startCameraCapture);
    document.getElementById('takePictureBtn').addEventListener('click', takePicture);
    document.getElementById('closeCameraBtn').addEventListener('click', closeCameraModal);
    document.getElementById('cancelCameraBtn').addEventListener('click', closeCameraModal);
    
    // File uploads
    document.getElementById('voiceFile').addEventListener('change', handleVoiceFile);
    document.getElementById('imageFile').addEventListener('change', handleImageFile);
    
    // System administration
    document.getElementById('systemHealthBtn').addEventListener('click', checkSystemHealth);
    document.getElementById('reloadConfigBtn').addEventListener('click', reloadConfiguration);
    document.getElementById('systemStatsBtn').addEventListener('click', viewSystemStats);
    document.getElementById('multimediaTestBtn').addEventListener('click', testMultimedia);
    document.getElementById('vectorRecoveryBtn').addEventListener('click', forceVectorRecovery);
    document.getElementById('protectionStatusBtn').addEventListener('click', checkProtectionStatus);
    document.getElementById('exportConfigBtn').addEventListener('click', exportConfiguration);
    document.getElementById('migrationToolBtn').addEventListener('click', showMigrationTool);
}

// ==================== COMPANY ACTIONS ====================

async function checkCompanyHealth() {
    try {
        showLoading(`Verificando salud de ${companies[currentCompanyId].company_name}...`);
        
        const response = await fetch(`${API_BASE}health/company/${currentCompanyId}`);
        const data = await response.json();
        
        hideLoading();
        
        const isHealthy = data.system_healthy;
        const statusText = isHealthy ? '✅ Sistema saludable' : '❌ Sistema con problemas';
        
        let detailsHTML = `
            <h3>${statusText}</h3>
            <div class="health-details">
                <p><strong>Empresa:</strong> ${data.company_name} (${data.company_id})</p>
                <p><strong>Vectorstore:</strong> ${data.vectorstore_connected ? '✅ Conectado' : '❌ Desconectado'}</p>
        `;
        
        if (data.agents_available) {
            detailsHTML += `<p><strong>Agentes disponibles:</strong> ${data.agents_available.join(', ')}</p>`;
        }
        
        detailsHTML += '</div>';
        
        showModal('🩺 Health Check - ' + companies[currentCompanyId].company_name, detailsHTML);
        
    } catch (error) {
        hideLoading();
        showToast('❌ Error verificando salud: ' + error.message, 'error');
    }
}

async function viewCompanyStats() {
    try {
        showLoading('Cargando estadísticas...');
        
        const response = await fetch(`${API_BASE}admin/status?company_id=${currentCompanyId}`);
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            const stats = data.statistics || {};
            let statsHTML = `
                <h3>📊 Estadísticas de ${data.company_name}</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value">${stats.conversations || 0}</span>
                        <span class="stat-label">Conversaciones</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${stats.documents || 0}</span>
                        <span class="stat-label">Documentos</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${stats.bot_statuses || 0}</span>
                        <span class="stat-label">Estados Bot</span>
                    </div>
                </div>
            `;
            
            if (data.configuration) {
                statsHTML += `
                    <div class="config-section">
                        <h4>⚙️ Configuración</h4>
                        <p><strong>Servicios:</strong> ${data.configuration.services}</p>
                        <p><strong>Índice Vectorstore:</strong> ${data.configuration.vectorstore_index}</p>
                        <p><strong>URL Agendamiento:</strong> ${data.configuration.schedule_service_url}</p>
                    </div>
                `;
            }
            
            showModal('📊 Estadísticas', statsHTML);
        } else {
            throw new Error(data.message || 'Error cargando estadísticas');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error cargando estadísticas: ' + error.message, 'error');
    }
}

async function resetCompanyCache() {
    if (!confirm(`¿Estás seguro de que quieres limpiar el cache de ${companies[currentCompanyId].company_name}?`)) {
        return;
    }
    
    try {
        showLoading('Limpiando cache...');
        
        const response = await fetch(`${API_BASE}admin/system/reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Company-ID': currentCompanyId
            },
            body: JSON.stringify({
                reset_all: false
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            showToast(`✅ Cache limpiado: ${data.keys_cleared} claves eliminadas`, 'success');
        } else {
            throw new Error(data.message || 'Error limpiando cache');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error limpiando cache: ' + error.message, 'error');
    }
}

// ==================== DOCUMENT MANAGEMENT ====================

async function addDocument(e) {
    e.preventDefault();
    
    const content = document.getElementById('docContent').value.trim();
    const metadataStr = document.getElementById('docMetadata').value.trim();
    
    if (!content) {
        showToast('❌ El contenido es requerido', 'error');
        return;
    }
    
    let metadata = {};
    if (metadataStr) {
        try {
            metadata = JSON.parse(metadataStr);
        } catch (error) {
            showToast('❌ Metadata debe ser JSON válido', 'error');
            return;
        }
    }
    
    try {
        showLoading(`Agregando documento a ${companies[currentCompanyId].company_name}...`);
        
        const response = await fetch(`${API_BASE}documents`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Company-ID': currentCompanyId
            },
            body: JSON.stringify({
                content: content,
                metadata: metadata
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            showToast(`✅ Documento agregado: ${data.chunk_count} chunks creados`, 'success');
            document.getElementById('addDocumentForm').reset();
            // Refresh documents list if visible
            if (document.getElementById('documentsList').children.length > 0) {
                listDocuments();
            }
        } else {
            throw new Error(data.message || 'Error agregando documento');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error agregando documento: ' + error.message, 'error');
    }
}

async function bulkUploadDocuments(e) {
    e.preventDefault();
    
    const files = document.getElementById('bulkFiles').files;
    if (!files || files.length === 0) {
        showToast('❌ Selecciona al menos un archivo', 'error');
        return;
    }
    
    try {
        showLoading(`Procesando ${files.length} archivos para ${companies[currentCompanyId].company_name}...`);
        
        const documents = [];
        
        for (const file of files) {
            const content = await file.text();
            documents.push({
                content: content,
                metadata: {
                    filename: file.name,
                    type: file.type,
                    size: file.size
                }
            });
        }
        
        const response = await fetch(`${API_BASE}documents/bulk`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Company-ID': currentCompanyId
            },
            body: JSON.stringify({
                documents: documents
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            let message = `✅ ${data.documents_added} documentos agregados, ${data.total_chunks} chunks creados`;
            if (data.errors && data.errors.length > 0) {
                message += `\n⚠️ ${data.errors.length} errores encontrados`;
            }
            showToast(message, 'success');
            document.getElementById('bulkUploadForm').reset();
        } else {
            throw new Error(data.message || 'Error en subida masiva');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error en subida masiva: ' + error.message, 'error');
    }
}

async function searchDocuments(e) {
    e.preventDefault();
    
    const query = document.getElementById('searchQuery').value.trim();
    const k = parseInt(document.getElementById('searchK').value) || 3;
    
    if (!query) {
        showToast('❌ Ingresa una consulta de búsqueda', 'error');
        return;
    }
    
    try {
        showLoading(`Buscando en documentos de ${companies[currentCompanyId].company_name}...`);
        
        const response = await fetch(`${API_BASE}documents/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Company-ID': currentCompanyId
            },
            body: JSON.stringify({
                query: query,
                k: k
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            displaySearchResults(data.results, query);
            showToast(`🔍 ${data.results_count} resultados encontrados`, 'info');
        } else {
            throw new Error(data.message || 'Error en búsqueda');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error en búsqueda: ' + error.message, 'error');
    }
}

function displaySearchResults(results, query) {
    const container = document.getElementById('searchResults');
    
    if (!results || results.length === 0) {
        container.innerHTML = '<p class="no-results">No se encontraron resultados</p>';
        return;
    }
    
    let resultsHTML = `<h4>🔍 Resultados para: "${query}"</h4>`;
    
    results.forEach((result, index) => {
        const content = result.content.length > 200 ? 
            result.content.substring(0, 200) + '...' : result.content;
        
        resultsHTML += `
            <div class="search-result">
                <div class="result-content">
                    <p><strong>Resultado ${index + 1}:</strong></p>
                    <p>${content}</p>
                </div>
                <div class="result-metadata">
                    ${result.score ? `<span class="score">Score: ${result.score.toFixed(4)}</span>` : ''}
                    <span class="company">Empresa: ${result.company_id || currentCompanyId}</span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = resultsHTML;
}

async function listDocuments() {
    try {
        showLoading(`Cargando documentos de ${companies[currentCompanyId].company_name}...`);
        
        const response = await fetch(`${API_BASE}documents?company_id=${currentCompanyId}&page=1&page_size=20`);
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            displayDocumentsList(data);
            showToast(`📄 ${data.total_documents} documentos encontrados`, 'info');
        } else {
            throw new Error(data.message || 'Error listando documentos');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error listando documentos: ' + error.message, 'error');
    }
}

function displayDocumentsList(data) {
    const container = document.getElementById('documentsList');
    
    if (!data.documents || data.documents.length === 0) {
        container.innerHTML = '<p class="no-documents">No hay documentos almacenados</p>';
        return;
    }
    
    let documentsHTML = `
        <div class="documents-header">
            <h4>📄 ${data.total_documents} documentos de ${companies[currentCompanyId].company_name}</h4>
            <span class="pagination-info">Página ${data.page} (mostrando ${data.documents.length})</span>
        </div>
    `;
    
    data.documents.forEach((doc, index) => {
        documentsHTML += `
            <div class="document-card">
                <div class="doc-content">
                    <h5>Documento ${index + 1}</h5>
                    <p class="doc-id">ID: ${doc.id}</p>
                    <p class="doc-preview">${doc.content}</p>
                    <div class="doc-meta">
                        <span class="chunk-count">📊 ${doc.chunk_count} chunks</span>
                        <span class="created-at">📅 ${formatDate(doc.created_at)}</span>
                        <span class="company-badge">🏢 ${companies[currentCompanyId].company_name}</span>
                    </div>
                </div>
                <div class="doc-actions">
                    <button onclick="viewDocumentVectors('${doc.id}')" class="btn-small">🔍 Ver Vectores</button>
                    <button onclick="deleteDocument('${doc.id}')" class="btn-small btn-danger">🗑️ Eliminar</button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = documentsHTML;
}

async function deleteDocument(docId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este documento?')) {
        return;
    }
    
    try {
        showLoading('Eliminando documento...');
        
        const response = await fetch(`${API_BASE}documents/${docId}`, {
            method: 'DELETE',
            headers: {
                'X-Company-ID': currentCompanyId
            }
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            showToast(`✅ Documento eliminado: ${data.vectors_deleted} vectores eliminados`, 'success');
            listDocuments(); // Refresh list
        } else {
            throw new Error(data.message || 'Error eliminando documento');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error eliminando documento: ' + error.message, 'error');
    }
}

// ==================== CONVERSATION MANAGEMENT ====================

async function listConversations() {
    try {
        showLoading(`Cargando conversaciones de ${companies[currentCompanyId].company_name}...`);
        
        const response = await fetch(`${API_BASE}conversations?company_id=${currentCompanyId}&page=1&page_size=20`);
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            displayConversationsList(data);
            showToast(`💬 ${data.total_conversations} conversaciones encontradas`, 'info');
        } else {
            throw new Error(data.message || 'Error listando conversaciones');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error listando conversaciones: ' + error.message, 'error');
    }
}

function displayConversationsList(data) {
    const container = document.getElementById('conversationsList');
    
    if (!data.conversations || data.conversations.length === 0) {
        container.innerHTML = '<p class="no-conversations">No hay conversaciones activas</p>';
        return;
    }
    
    let conversationsHTML = `
        <div class="conversations-header">
            <h4>💬 ${data.total_conversations} conversaciones de ${companies[currentCompanyId].company_name}</h4>
        </div>
    `;
    
    data.conversations.forEach((conv, index) => {
        const lastMessage = conv.messages && conv.messages.length > 0 ? 
            conv.messages[conv.messages.length - 1].content.substring(0, 100) + '...' : 
            'Sin mensajes';
        
        conversationsHTML += `
            <div class="conversation-card">
                <div class="conv-content">
                    <h5>👤 Usuario: ${conv.user_id}</h5>
                    <div class="conv-stats">
                        <span>💬 ${conv.message_count} mensajes</span>
                        <span>👤 ${conv.user_message_count} usuario</span>
                        <span>🤖 ${conv.assistant_message_count} asistente</span>
                    </div>
                    <p class="last-message">Último mensaje: ${lastMessage}</p>
                    <span class="company-badge">🏢 ${companies[currentCompanyId].company_name}</span>
                </div>
                <div class="conv-actions">
                    <button onclick="testConversation('${conv.user_id}')" class="btn-small">🧪 Probar</button>
                    <button onclick="deleteConversation('${conv.user_id}')" class="btn-small btn-danger">🗑️ Eliminar</button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = conversationsHTML;
}

async function testConversation(userId) {
    const testMessage = prompt('Ingresa un mensaje de prueba:');
    if (!testMessage) return;
    
    try {
        showLoading('Enviando mensaje de prueba...');
        
        const response = await fetch(`${API_BASE}conversations/${userId}/test?company_id=${currentCompanyId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: testMessage
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            showModal(`🧪 Respuesta de prueba para ${userId}`, `
                <div class="test-result">
                    <p><strong>👤 Usuario:</strong> ${data.user_message}</p>
                    <p><strong>🤖 Respuesta:</strong> ${data.bot_response}</p>
                    <p><strong>🎯 Agente usado:</strong> ${data.agent_used}</p>
                    <p><strong>🏢 Empresa:</strong> ${companies[currentCompanyId].company_name}</p>
                </div>
            `);
        } else {
            throw new Error(data.message || 'Error en prueba de conversación');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error en prueba: ' + error.message, 'error');
    }
}

async function deleteConversation(userId) {
    if (!confirm(`¿Estás seguro de que quieres eliminar la conversación con ${userId}?`)) {
        return;
    }
    
    try {
        showLoading('Eliminando conversación...');
        
        const response = await fetch(`${API_BASE}conversations/${userId}?company_id=${currentCompanyId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            showToast('✅ Conversación eliminada', 'success');
            listConversations(); // Refresh list
        } else {
            throw new Error(data.message || 'Error eliminando conversación');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error eliminando conversación: ' + error.message, 'error');
    }
}

// ==================== CHAT TESTING ====================

async function sendChatMessage(e) {
    e.preventDefault();
    
    const message = document.getElementById('userMessage').value.trim();
    const userId = document.getElementById('testUserId').value.trim() || 'test_user';
    
    if (!message) {
        showToast('❌ Ingresa un mensaje', 'error');
        return;
    }
    
    // Display user message
    displayChatMessage('user', message);
    document.getElementById('userMessage').value = '';
    
    try {
        const response = await fetch(`${API_BASE}conversations/${userId}/test?company_id=${currentCompanyId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayChatMessage('assistant', data.bot_response);
            // Show agent used in a subtle way
            displayChatMessage('system', `Agente usado: ${data.agent_used}`);
        } else {
            throw new Error(data.message || 'Error obteniendo respuesta');
        }
    } catch (error) {
        displayChatMessage('error', 'Error: ' + error.message);
        showToast('❌ Error en chat: ' + error.message, 'error');
    }
}

function displayChatMessage(role, message) {
    const chatContainer = document.getElementById('chatHistory');
    const messageElement = document.createElement('div');
    messageElement.className = `message ${role}-message`;
    
    if (role === 'system') {
        messageElement.innerHTML = `<small><em>${message}</em></small>`;
    } else if (role === 'error') {
        messageElement.innerHTML = `<span class="error-text">${message}</span>`;
    } else {
        messageElement.textContent = message;
    }
    
    chatContainer.appendChild(messageElement);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ==================== MULTIMEDIA ====================

async function startVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
            
            await processVoiceMessage(audioFile);
            
            // Limpiar stream
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        document.getElementById('recordingStatus').style.display = 'block';
        showToast('🎙️ Grabando audio...', 'info');
        
    } catch (error) {
        showToast('❌ Error accediendo al micrófono: ' + error.message, 'error');
    }
}

function stopVoiceRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        document.getElementById('recordingStatus').style.display = 'none';
        showToast('⏹️ Grabación detenida', 'info');
    }
}

async function handleVoiceFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    await processVoiceMessage(file);
    e.target.value = '';
}

async function processVoiceMessage(audioFile) {
    const userId = document.getElementById('testUserId').value.trim() || 'test_user';
    
    try {
        showLoading('Procesando audio...');
        
        const formData = new FormData();
        formData.append('audio', audioFile);
        formData.append('user_id', userId);
        formData.append('company_id', currentCompanyId);
        
        const response = await fetch(`${API_BASE}multimedia/process-voice`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            displayChatMessage('user', `🎤 ${data.transcript}`);
            displayChatMessage('assistant', data.response);
            displayChatMessage('system', `Agente: ${data.agent_used} | Empresa: ${companies[currentCompanyId].company_name}`);
            showToast('✅ Audio procesado correctamente', 'success');
        } else {
            throw new Error(data.message || 'Error procesando audio');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error procesando audio: ' + error.message, 'error');
        displayChatMessage('error', 'Error procesando audio: ' + error.message);
    }
}

async function startCameraCapture() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('cameraVideo');
        video.srcObject = cameraStream;
        
        document.getElementById('cameraModal').style.display = 'block';
        showToast('📸 Cámara activada', 'info');
        
    } catch (error) {
        showToast('❌ Error accediendo a la cámara: ' + error.message, 'error');
    }
}

async function takePicture() {
    const video = document.getElementById('cameraVideo');
    const canvas = document.getElementById('cameraCanvas');
    const context = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
        const imageFile = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
        await processImageMessage(imageFile);
        closeCameraModal();
    }, 'image/jpeg', 0.8);
}

function closeCameraModal() {
    document.getElementById('cameraModal').style.display = 'none';
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
}

async function handleImageFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    await processImageMessage(file);
    e.target.value = '';
}

async function processImageMessage(imageFile, question = '¿Qué hay en esta imagen?') {
    const userId = document.getElementById('testUserId').value.trim() || 'test_user';
    
    try {
        showLoading('Analizando imagen...');
        
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('user_id', userId);
        formData.append('question', question);
        formData.append('company_id', currentCompanyId);
        
        const response = await fetch(`${API_BASE}multimedia/process-image`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.status === 'success') {
            displayChatMessage('user', `📸 Imagen enviada: ${imageFile.name}`);
            displayChatMessage('assistant', data.response);
            displayChatMessage('system', `Análisis: ${data.image_description.substring(0, 100)}...`);
            displayChatMessage('system', `Agente: ${data.agent_used} | Empresa: ${companies[currentCompanyId].company_name}`);
            showToast('✅ Imagen analizada correctamente', 'success');
        } else {
            throw new Error(data.message || 'Error analizando imagen');
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error analizando imagen: ' + error.message, 'error');
        displayChatMessage('error', 'Error analizando imagen: ' + error.message);
    }
}

// ==================== SYSTEM ADMINISTRATION ====================

async function checkSystemHealth() {
    try {
        showLoading('Verificando salud del sistema...');
        
        const response = await fetch(`${API_BASE}health`);
        const data = await response.json();
        
        hideLoading();
        
        const isHealthy = data.status === 'healthy';
        let healthHTML = `
            <h3>${isHealthy ? '✅ Sistema Saludable' : '❌ Sistema con Problemas'}</h3>
            <div class="system-health">
                <p><strong>Tipo:</strong> ${data.system_type}</p>
                <p><strong>Empresas configuradas:</strong> ${data.companies?.total || 0}</p>
        `;
        
        if (data.companies?.configured) {
            healthHTML += `<p><strong>Empresas disponibles:</strong> ${data.companies.configured.join(', ')}</p>`;
        }
        
        if (data.basic_components) {
            healthHTML += '<h4>🔧 Componentes Básicos:</h4><ul>';
            Object.entries(data.basic_components).forEach(([component, status]) => {
                const icon = status === 'connected' ? '✅' : '❌';
                healthHTML += `<li>${icon} ${component}: ${status}</li>`;
            });
            healthHTML += '</ul>';
        }
        
        healthHTML += '</div>';
        
        showModal('🩺 Health Check del Sistema', healthHTML);
        
    } catch (error) {
        hideLoading();
        showToast('❌ Error verificando salud del sistema: ' + error.message, 'error');
    }
}

// ==================== UTILITY FUNCTIONS ====================

function showLoading(message = 'Cargando...') {
    document.getElementById('loadingMessage').textContent = message;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    const container = document.getElementById('toastContainer');
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (container.contains(toast)) {
            container.removeChild(toast);
        }
    }, 5000);
    
    // Remove on click
    toast.addEventListener('click', () => {
        if (container.contains(toast)) {
            container.removeChild(toast);
        }
    });
}

function showModal(title, content) {
    // Create modal dynamically
    const modal = document.createElement('div');
    modal.className = 'modal modal-info';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${title}</h3>
                <button class="btn-close" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
            <div class="modal-footer">
                <button onclick="this.closest('.modal').remove()" class="btn-secondary">Cerrar</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'block';
    
    // Remove on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        return new Date(dateString).toLocaleDateString('es-ES');
    } catch {
        return dateString;
    }
}

// Additional admin functions (simplified for space)
async function reloadConfiguration() {
    try {
        showLoading('Recargando configuración...');
        const response = await fetch(`${API_BASE}admin/companies/reload-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        hideLoading();
        
        if (data.status === 'success') {
            showToast('✅ Configuración recargada', 'success');
            await loadCompanies();
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error: ' + error.message, 'error');
    }
}

async function cleanupVectors() {
    if (!confirm('¿Limpiar vectores huérfanos? Esta acción no se puede deshacer.')) return;
    
    try {
        showLoading('Limpiando vectores huérfanos...');
        const response = await fetch(`${API_BASE}documents/cleanup`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Company-ID': currentCompanyId
            },
            body: JSON.stringify({ dry_run: false })
        });
        const data = await response.json();
        hideLoading();
        
        if (data.status === 'success') {
            showToast(`✅ ${data.orphaned_vectors_deleted} vectores eliminados`, 'success');
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        hideLoading();
        showToast('❌ Error: ' + error.message, 'error');
    }
}

// Placeholder functions for remaining admin features
async function viewSystemStats() { showToast('🚧 Función en desarrollo', 'info'); }
async function testMultimedia() { showToast('🚧 Función en desarrollo', 'info'); }
async function forceVectorRecovery() { showToast('🚧 Función en desarrollo', 'info'); }
async function checkProtectionStatus() { showToast('🚧 Función en desarrollo', 'info'); }
async function exportConfiguration() { showToast('🚧 Función en desarrollo', 'info'); }
async function showMigrationTool() { showToast('🚧 Función en desarrollo', 'info'); }
async function viewAllCompanies() { showModal('🏢 Todas las Empresas', JSON.stringify(companies, null, 2)); }
async function viewConversationStats() { showToast('🚧 Función en desarrollo', 'info'); }
async function runDiagnostics() { showToast('🚧 Función en desarrollo', 'info'); }
async function viewDocumentVectors(docId) { showToast(`🔍 Ver vectores de ${docId}`, 'info'); }
