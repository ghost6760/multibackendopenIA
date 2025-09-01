// scripts/main.js - Main Application Controller
'use strict';

/**
 * Main Application Controller for Multi-Tenant Chatbot Admin Panel
 * Railway Production Ready with Enhanced Error Handling
 */
class AdminPanelApp {
    constructor() {
        this.currentCompanyId = null;
        this.companies = {};
        this.initialized = false;
        this.isRailway = window.APP_CONFIG.ENV.is_railway;
        this.scheduleServiceAvailable = null;
        
        // Bind methods
        this.init = this.init.bind(this);
        this.handleError = this.handleError.bind(this);
        
        // Railway-specific initialization
        if (this.isRailway) {
            this.initializeRailwayOptimizations();
        }
    }

    /**
     * Initialize Railway-specific optimizations
     */
    initializeRailwayOptimizations() {
        // Handle Railway's health check endpoints
        this.setupRailwayHealthChecks();
        
        // Handle graceful degradation for unavailable services
        this.setupGracefulDegradation();
        
        // Enhanced error logging for production
        this.setupProductionErrorLogging();
    }

    /**
     * Setup Railway health checks
     */
    setupRailwayHealthChecks() {
        // Check main application health
        this.checkApplicationHealth();
        
        // Check schedule service availability (handle port 4040 error)
        this.checkScheduleServiceHealth();
    }

    /**
     * Check main application health
     */
    async checkApplicationHealth() {
        try {
            const health = await window.API.systemHealthCheck();
            if (window.APP_CONFIG.DEBUG.railway_debug.log_health_checks) {
                console.log('🏥 Application Health Check:', health);
            }
        } catch (error) {
            console.warn('⚠️ Application health check failed:', error.message);
            // Continue initialization even if health check fails
        }
    }

    /**
     * Check schedule service health (handles port 4040 connection refused)
     */
    async checkScheduleServiceHealth() {
        try {
            const response = await fetch('/health/schedule-service', {
                method: 'GET',
                timeout: 3000
            });
            
            this.scheduleServiceAvailable = response.ok;
            
            if (!this.scheduleServiceAvailable && window.APP_CONFIG.DEBUG.railway_debug.log_service_failures) {
                console.warn('📅 Schedule service unavailable - using fallback mode');
                window.UI.showToast('📅 Servicio de agendamiento en modo fallback', 'warning');
            }
        } catch (error) {
            this.scheduleServiceAvailable = false;
            if (window.APP_CONFIG.DEBUG.railway_debug.log_service_failures) {
                console.warn('⚠️ Schedule service connection failed (expected in Railway):', error.message);
            }
        }
    }

    /**
     * Setup graceful degradation for unavailable services
     */
    setupGracefulDegradation() {
        // Handle schedule service failures gracefully
        window.addEventListener('unhandledrejection', (event) => {
            if (event.reason?.message?.includes('4040') || event.reason?.message?.includes('Connection refused')) {
                event.preventDefault(); // Prevent error from propagating
                
                if (window.APP_CONFIG.DEBUG.railway_debug.log_service_failures) {
                    console.warn('🔄 Handled schedule service connection error gracefully');
                }
                
                // Show user-friendly message
                window.UI.showToast('📅 Algunas funciones de agendamiento están temporalmente no disponibles', 'info');
            }
        });
    }

    /**
     * Setup production error logging
     */
    setupProductionErrorLogging() {
        if (this.isRailway) {
            window.addEventListener('error', (event) => {
                console.error('🚨 Production Error:', {
                    message: event.error?.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent,
                    url: window.location.href
                });
            });
        }
    }

    /**
     * Initialize the application
     */
    async init() {
        try {
            window.UI.showLoading('Inicializando aplicación...');
            
            // Log initialization in development
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.group('🚀 Initializing Admin Panel App');
                console.log('Environment:', window.APP_CONFIG.ENV);
                console.log('Railway Mode:', this.isRailway);
                console.log('API Base URL:', window.API.baseURL);
                console.groupEnd();
            }

            // Initialize UI components
            this.initializeUIComponents();

            // Load companies
            await this.loadCompanies();

            // Setup event listeners
            this.setupEventListeners();

            // Initialize modules
            await this.initializeModules();

            this.initialized = true;
            window.UI.hideLoading();
            
            window.UI.showToast('✅ Aplicación inicializada correctamente', 'success');
            
            // Log successful initialization
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('✅ Admin Panel App initialized successfully');
            }

        } catch (error) {
            window.UI.hideLoading();
            this.handleError(error, 'Error inicializando aplicación');
            
            // Show fallback UI
            this.showFallbackUI();
        }
    }

    /**
     * Initialize UI components
     */
    initializeUIComponents() {
        // Initialize company selector
        const companySelect = document.getElementById('currentCompany');
        if (companySelect) {
            companySelect.addEventListener('change', (e) => {
                this.selectCompany(e.target.value);
            });
        }

        // Initialize refresh button
        const refreshBtn = document.getElementById('refreshCompanies');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadCompanies();
            });
        }

        // Update company indicators initially
        this.updateCompanyIndicators('-');
    }

    /**
     * Load companies from API
     */
    async loadCompanies() {
        try {
            window.UI.showLoading('Cargando empresas...');
            
            const response = await window.API.getCompanies();
            
            if (response.companies) {
                this.companies = response.companies;
                this.populateCompanySelector();
                this.updateSystemOverview();
                
                // Auto-select first company if none selected
                if (!this.currentCompanyId && Object.keys(this.companies).length > 0) {
                    const firstCompanyId = Object.keys(this.companies)[0];
                    this.selectCompany(firstCompanyId);
                }
                
                window.UI.showToast(`✅ ${Object.keys(this.companies).length} empresas cargadas`, 'success');
            }
            
            window.UI.hideLoading();
            
        } catch (error) {
            window.UI.hideLoading();
            this.handleError(error, 'Error cargando empresas');
            
            // Show fallback companies if available
            this.showFallbackCompanies();
        }
    }

    /**
     * Populate company selector dropdown
     */
    populateCompanySelector() {
        const select = document.getElementById('currentCompany');
        if (!select) return;

        // Clear existing options
        select.innerHTML = '<option value="">Selecciona una empresa...</option>';

        // Add company options
        Object.entries(this.companies).forEach(([id, company]) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = company.company_name || id;
            select.appendChild(option);
        });
    }

    /**
     * Select a company
     */
    async selectCompany(companyId) {
        if (!companyId || companyId === this.currentCompanyId) return;

        try {
            window.UI.showLoading(`Seleccionando empresa: ${this.companies[companyId]?.company_name || companyId}...`);

            this.currentCompanyId = companyId;
            window.API.setCompanyId(companyId);

            // Update UI
            this.updateCompanyIndicators(this.companies[companyId]?.company_name || companyId);
            
            // Update company selector
            const select = document.getElementById('currentCompany');
            if (select) {
                select.value = companyId;
            }

            // Load company data
            await this.loadCompanyData(companyId);

            // Update modules
            if (window.DocumentsManager) {
                window.DocumentsManager.onCompanyChange(companyId);
            }
            
            if (window.ChatTester) {
                window.ChatTester.onCompanyChange(companyId);
            }

            window.UI.hideLoading();
            window.UI.showToast(`✅ Empresa seleccionada: ${this.companies[companyId]?.company_name || companyId}`, 'success');

        } catch (error) {
            window.UI.hideLoading();
            this.handleError(error, `Error seleccionando empresa ${companyId}`);
        }
    }

    /**
     * Load company-specific data
     */
    async loadCompanyData(companyId) {
        try {
            // Load company status
            const status = await window.API.getCompanyStatus(companyId);
            this.updateCompanyInfo(status);

            // Load documents list if documents manager is available
            if (window.DocumentsManager) {
                await window.DocumentsManager.loadDocuments();
            }

        } catch (error) {
            console.warn('⚠️ Failed to load some company data:', error.message);
            // Don't show error to user for partial failures
        }
    }

    /**
     * Update company indicators across the UI
     */
    updateCompanyIndicators(companyName) {
        const indicators = [
            'docCompanyIndicator',
            'bulkCompanyIndicator', 
            'searchCompanyIndicator',
            'cameraCompany'
        ];

        indicators.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = companyName;
            }
        });
    }

    /**
     * Update company info display
     */
    updateCompanyInfo(statusData) {
        const companyInfoEl = document.getElementById('companyInfo');
        if (!companyInfoEl || !statusData) return;

        const company = this.companies[this.currentCompanyId];
        if (!company) return;

        const html = `
            <div class="company-status">
                <div class="status-item">
                    <div class="status-label">Nombre</div>
                    <div class="status-value">${company.company_name}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">ID</div>
                    <div class="status-value">${this.currentCompanyId}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Servicios</div>
                    <div class="status-value">${company.services?.join(', ') || 'N/A'}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Estado</div>
                    <div class="status-value" style="color: ${statusData.data?.system_healthy ? 'var(--success-color)' : 'var(--danger-color)'}">
                        ${statusData.data?.system_healthy ? '🟢 Saludable' : '🔴 Con problemas'}
                    </div>
                </div>
                <div class="status-item">
                    <div class="status-label">Vectorstore</div>
                    <div class="status-value">${company.vectorstore_index}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Agentes Disponibles</div>
                    <div class="status-value">${statusData.data?.agents_available?.length || 0}</div>
                </div>
            </div>
        `;

        companyInfoEl.innerHTML = html;
    }

    /**
     * Update system overview
     */
    updateSystemOverview() {
        const overviewEl = document.getElementById('systemOverview');
        if (!overviewEl) return;

        const totalCompanies = Object.keys(this.companies).length;
        const healthyCompanies = Object.values(this.companies).filter(c => c.status !== 'error').length;

        const html = `
            <div class="status-item">
                <div class="status-label">Total de Empresas</div>
                <div class="status-value">${totalCompanies}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Empresas Saludables</div>
                <div class="status-value" style="color: var(--success-color)">${healthyCompanies}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Modo Railway</div>
                <div class="status-value">${this.isRailway ? '🚄 Sí' : '🖥️ No'}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Servicio de Agendamiento</div>
                <div class="status-value" style="color: ${this.scheduleServiceAvailable ? 'var(--success-color)' : 'var(--warning-color)'}">
                    ${this.scheduleServiceAvailable === null ? '❓ Desconocido' : 
                      this.scheduleServiceAvailable ? '🟢 Disponible' : '🟡 Fallback'}
                </div>
            </div>
        `;

        overviewEl.innerHTML = html;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Health check button
        const healthBtn = document.getElementById('checkHealthBtn');
        if (healthBtn) {
            healthBtn.addEventListener('click', () => this.performHealthCheck());
        }

        // Statistics button
        const statsBtn = document.getElementById('viewStatsBtn');
        if (statsBtn) {
            statsBtn.addEventListener('click', () => this.viewStatistics());
        }

        // Reset cache button
        const resetBtn = document.getElementById('resetCacheBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetCache());
        }

        // Admin tool buttons
        this.setupAdminEventListeners();
    }

    /**
     * Setup admin event listeners
     */
    setupAdminEventListeners() {
        const adminButtons = [
            { id: 'reloadConfigBtn', handler: () => this.reloadConfiguration() },
            { id: 'systemStatsBtn', handler: () => this.viewSystemStats() },
            { id: 'runDiagnosticsBtn', handler: () => this.runDiagnostics() },
            { id: 'cleanupVectorsBtn', handler: () => this.cleanupVectors() },
            { id: 'vectorRecoveryBtn', handler: () => this.forceVectorRecovery() },
            { id: 'protectionStatusBtn', handler: () => this.checkProtectionStatus() },
            { id: 'exportConfigBtn', handler: () => this.exportConfiguration() },
            { id: 'migrationToolBtn', handler: () => this.showMigrationTool() },
            { id: 'testMultimediaBtn', handler: () => this.testMultimedia() },
            { id: 'viewAllCompanies', handler: () => this.viewAllCompanies() }
        ];

        adminButtons.forEach(({ id, handler }) => {
            const button = document.getElementById(id);
            if (button) {
                button.addEventListener('click', handler);
            }
        });
    }

    /**
     * Initialize modules
     */
    async initializeModules() {
        // Initialize UI utilities
        if (window.UI) {
            window.UI.init();
        }

        // Initialize Documents Manager
        if (window.DocumentsManager) {
            await window.DocumentsManager.init();
        }

        // Initialize Chat Tester
        if (window.ChatTester) {
            await window.ChatTester.init();
        }

        // Initialize Multimedia Manager
        if (window.MultimediaManager) {
            await window.MultimediaManager.init();
        }

        // Initialize Admin Tools
        if (window.AdminTools) {
            await window.AdminTools.init();
        }
    }

    /**
     * Perform system health check
     */
    async performHealthCheck() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        try {
            window.UI.showLoading('Verificando salud del sistema...');

            const health = await window.API.companyHealthCheck(this.currentCompanyId);
            
            let healthHTML = '<div class="health-results">';
            
            if (health.status === 'healthy' || health.status === 'partial') {
                healthHTML += `<h4 style="color: var(--success-color)">✅ Estado del Sistema</h4>`;
                healthHTML += `<p><strong>Empresa:</strong> ${this.companies[this.currentCompanyId]?.company_name}</p>`;
                healthHTML += `<p><strong>Estado General:</strong> ${health.status === 'healthy' ? 'Saludable' : 'Parcialmente funcional'}</p>`;

                if (health.components) {
                    healthHTML += '<h5>Componentes:</h5><ul>';
                    Object.entries(health.components).forEach(([component, status]) => {
                        const icon = status === 'healthy' || status === 'connected' ? '✅' : '❌';
                        healthHTML += `<li>${icon} ${component}: ${status}</li>`;
                    });
                    healthHTML += '</ul>';
                }

                // Show schedule service status
                if (this.scheduleServiceAvailable !== null) {
                    const scheduleIcon = this.scheduleServiceAvailable ? '✅' : '⚠️';
                    const scheduleStatus = this.scheduleServiceAvailable ? 'Disponible' : 'Modo Fallback';
                    healthHTML += `<p>${scheduleIcon} <strong>Servicio de Agendamiento:</strong> ${scheduleStatus}</p>`;
                }

            } else {
                healthHTML += `<h4 style="color: var(--danger-color)">❌ Sistema con Problemas</h4>`;
                healthHTML += `<p><strong>Error:</strong> ${health.error || health.message}</p>`;
            }
            
            healthHTML += '</div>';
            
            window.UI.showModal('🩺 Health Check del Sistema', healthHTML);

        } catch (error) {
            this.handleError(error, 'Error verificando salud del sistema');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * View system statistics
     */
    async viewStatistics() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        try {
            window.UI.showLoading('Cargando estadísticas...');

            const stats = await window.API.getSystemStats();
            
            if (stats.status === 'success') {
                let statsHTML = '<div class="stats-results">';
                statsHTML += `<h4>📊 Estadísticas de ${this.companies[this.currentCompanyId]?.company_name}</h4>`;
                
                if (stats.data) {
                    const data = stats.data;
                    statsHTML += `<div class="stats-grid">`;
                    
                    if (data.conversations_count !== undefined) {
                        statsHTML += `<div class="stat-item"><strong>Conversaciones:</strong> ${data.conversations_count}</div>`;
                    }
                    
                    if (data.documents_count !== undefined) {
                        statsHTML += `<div class="stat-item"><strong>Documentos:</strong> ${data.documents_count}</div>`;
                    }
                    
                    if (data.vectorstore_size !== undefined) {
                        statsHTML += `<div class="stat-item"><strong>Vectores:</strong> ${data.vectorstore_size}</div>`;
                    }
                    
                    if (data.cache_keys !== undefined) {
                        statsHTML += `<div class="stat-item"><strong>Cache Keys:</strong> ${data.cache_keys}</div>`;
                    }
                    
                    statsHTML += `</div>`;
                }
                
                statsHTML += '</div>';
                
                window.UI.showModal('📊 Estadísticas del Sistema', statsHTML);
            } else {
                throw new Error(stats.message || 'Error cargando estadísticas');
            }

        } catch (error) {
            this.handleError(error, 'Error cargando estadísticas');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Reset company cache
     */
    async resetCache() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const companyName = this.companies[this.currentCompanyId]?.company_name || this.currentCompanyId;
        
        if (!confirm(`¿Estás seguro de que quieres limpiar el cache de ${companyName}?`)) {
            return;
        }

        try {
            window.UI.showLoading('Limpiando cache...');

            const result = await window.API.resetCompanyCache();
            
            if (result.status === 'success') {
                window.UI.showToast(`✅ Cache limpiado: ${result.keys_cleared} claves eliminadas`, 'success');
            } else {
                throw new Error(result.message || 'Error limpiando cache');
            }

        } catch (error) {
            this.handleError(error, 'Error limpiando cache');
        } finally {
            window.UI.hideLoading();
        }
    }

    // ==================== ADMIN FUNCTIONS ====================

    /**
     * Reload configuration
     */
    async reloadConfiguration() {
        try {
            window.UI.showLoading('Recargando configuración...');
            
            const response = await window.API.reloadCompanyConfig();
            
            if (response.status === 'success') {
                window.UI.showToast('✅ Configuración recargada', 'success');
                await this.loadCompanies();
            } else {
                throw new Error(response.message);
            }
        } catch (error) {
            this.handleError(error, 'Error recargando configuración');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * View system stats (placeholder)
     */
    async viewSystemStats() {
        window.UI.showToast('🚧 Función en desarrollo - Vista de estadísticas del sistema', 'info');
    }

    /**
     * Run diagnostics (placeholder)
     */
    async runDiagnostics() {
        window.UI.showToast('🚧 Función en desarrollo - Diagnósticos del sistema', 'info');
    }

    /**
     * Cleanup vectors
     */
    async cleanupVectors() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        if (!confirm('¿Limpiar vectores huérfanos? Esta acción no se puede deshacer.')) {
            return;
        }

        try {
            window.UI.showLoading('Limpiando vectores huérfanos...');
            
            const result = await window.API.cleanupVectors(false);
            
            if (result.status === 'success') {
                window.UI.showToast(`✅ ${result.orphaned_vectors_deleted} vectores eliminados`, 'success');
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.handleError(error, 'Error limpiando vectores');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Force vector recovery (placeholder)
     */
    async forceVectorRecovery() {
        window.UI.showToast('🚧 Función en desarrollo - Recuperación forzada de vectorstore', 'info');
    }

    /**
     * Check protection status (placeholder)
     */
    async checkProtectionStatus() {
        window.UI.showToast('🚧 Función en desarrollo - Estado de protección', 'info');
    }

    /**
     * Export configuration (placeholder)
     */
    async exportConfiguration() {
        window.UI.showToast('🚧 Función en desarrollo - Exportar configuración', 'info');
    }

    /**
     * Show migration tool (placeholder)
     */
    async showMigrationTool() {
        window.UI.showToast('🚧 Función en desarrollo - Herramienta de migración', 'info');
    }

    /**
     * Test multimedia (placeholder)
     */
    async testMultimedia() {
        window.UI.showToast('🚧 Función en desarrollo - Test multimedia', 'info');
    }

    /**
     * View all companies
     */
    viewAllCompanies() {
        const companiesData = JSON.stringify(this.companies, null, 2);
        window.UI.showModal('🏢 Todas las Empresas', `<pre style="max-height: 400px; overflow: auto;">${companiesData}</pre>`);
    }

    // ==================== ERROR HANDLING ====================

    /**
     * Handle application errors
     */
    handleError(error, context = '') {
        const errorMessage = this.getErrorMessage(error, context);
        
        // Log error details in development
        if (window.APP_CONFIG.DEBUG.verbose_errors) {
            console.error('Application Error:', {
                context,
                error: error.message,
                stack: error.stack,
                timestamp: new Date().toISOString()
            });
        }

        // Show user-friendly error message
        window.UI.showToast(`❌ ${errorMessage}`, 'error');
        
        // Log error in Railway production
        if (this.isRailway) {
            console.error(`🚨 ${context}:`, error.message);
        }
    }

    /**
     * Get user-friendly error message
     */
    getErrorMessage(error, context) {
        if (!error || !error.message) {
            return `${context}: Error desconocido`;
        }

        const message = error.message.toLowerCase();
        
        if (message.includes('4040') || message.includes('connection refused')) {
            return `${context}: Servicio temporalmente no disponible`;
        } else if (message.includes('fetch')) {
            return `${context}: Error de conexión`;
        } else if (message.includes('timeout')) {
            return `${context}: Tiempo de espera agotado`;
        } else if (message.includes('404')) {
            return `${context}: Recurso no encontrado`;
        } else if (message.includes('403')) {
            return `${context}: Sin permisos`;
        } else if (message.includes('500')) {
            return `${context}: Error del servidor`;
        } else {
            return `${context}: ${error.message}`;
        }
    }

    /**
     * Show fallback UI when initialization fails
     */
    showFallbackUI() {
        const companyInfo = document.getElementById('companyInfo');
        if (companyInfo) {
            companyInfo.innerHTML = `
                <div class="info-placeholder">
                    <span class="placeholder-icon">⚠️</span>
                    <p>Error cargando información del sistema</p>
                    <p><small>Algunas funciones pueden no estar disponibles</small></p>
                </div>
            `;
        }

        const systemOverview = document.getElementById('systemOverview');
        if (systemOverview) {
            systemOverview.innerHTML = `
                <div class="grid-placeholder">
                    <span class="placeholder-icon">🚧</span>
                    <p>Sistema en modo de recuperación</p>
                </div>
            `;
        }
    }

    /**
     * Show fallback companies when API fails
     */
    showFallbackCompanies() {
        const select = document.getElementById('currentCompany');
        if (select) {
            select.innerHTML = `
                <option value="">Error cargando empresas</option>
                <option value="fallback">Modo de emergencia</option>
            `;
        }
        
        window.UI.showToast('⚠️ Usando configuración de emergencia', 'warning');
    }
}

// ==================== APPLICATION STARTUP ====================

/**
 * Initialize application when DOM is ready
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Create global app instance
        window.AdminApp = new AdminPanelApp();
        
        // Initialize the application
        await window.AdminApp.init();
        
        // Log successful startup in development
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🎉 Multi-Tenant Admin Panel initialized successfully');
        }
        
    } catch (error) {
        console.error('💥 Failed to initialize Admin Panel:', error);
        
        // Show critical error message
        document.body.innerHTML = `
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 400px;
            ">
                <h2 style="color: #e74c3c; margin-bottom: 1rem;">⚠️ Error Crítico</h2>
                <p>No se pudo inicializar la aplicación.</p>
                <p><small>Verifica tu conexión e intenta recargar la página.</small></p>
                <button onclick="window.location.reload()" style="
                    margin-top: 1rem;
                    padding: 0.5rem 1rem;
                    background: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                ">🔄 Recargar</button>
            </div>
        `;
    }
});

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminPanelApp;
}
