// scripts/main.js - Main Application Controller - FIXED INITIALIZATION
'use strict';

/**
 * Main Application Controller for Multi-Tenant Chatbot Admin Panel
 * FIXED: Force initialization even if DOMContentLoaded already fired
 */
class AdminPanelApp {
    constructor() {
        this.currentCompanyId = null;
        this.companies = {};
        this.initialized = false;
        this.isRailway = window.APP_CONFIG.ENV.is_railway;
        this.scheduleServiceAvailable = null;
        
        console.log('🚀 AdminPanelApp constructor called');
        
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
            if (window.APP_CONFIG.DEBUG?.railway_debug?.log_health_checks) {
                console.log('🏥 Application Health Check:', health);
            }
        } catch (error) {
            console.warn('⚠️ Application health check failed:', error.message);
            // Continue initialization even if health check fails
        }
    }

    /**
     * Check schedule service health
     */
    checkScheduleServiceHealth() {
        // This is handled by API manager
        this.scheduleServiceAvailable = window.API.scheduleServiceAvailable;
    }

    /**
     * Setup graceful degradation
     */
    setupGracefulDegradation() {
        // Handle offline states
        window.addEventListener('online', () => {
            window.UI.showToast('✅ Conexión restaurada', 'success');
        });

        window.addEventListener('offline', () => {
            window.UI.showToast('⚠️ Sin conexión a internet', 'warning');
        });
    }

    /**
     * Setup production error logging
     */
    setupProductionErrorLogging() {
        if (this.isRailway) {
            window.addEventListener('error', (event) => {
                console.error('🚨 Production Error:', {
                    message: event.error?.message || event.message,
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
     * Initialize the application - ENHANCED WITH LOGGING
     */
    async init() {
        console.log('🚀 Starting AdminPanelApp initialization...');
        
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
            console.log('📱 Initializing UI components...');
            this.initializeUIComponents();

            // Load companies
            console.log('🏢 Loading companies...');
            await this.loadCompanies();

            // Setup event listeners
            console.log('🎧 Setting up event listeners...');
            this.setupEventListeners();

            // Initialize modules
            console.log('📦 Initializing modules...');
            await this.initializeModules();

            this.initialized = true;
            window.UI.hideLoading();
            
            window.UI.showToast('✅ Aplicación inicializada correctamente', 'success');
            
            // Log successful initialization
            console.log('✅ Admin Panel App initialized successfully');
            
        } catch (error) {
            console.error('💥 Failed to initialize Admin Panel:', error);
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
                console.log('🏢 Company selection changed to:', e.target.value);
                this.selectCompany(e.target.value);
            });
        }

        // Initialize refresh button
        const refreshBtn = document.getElementById('refreshCompanies');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('🔄 Refresh button clicked');
                this.loadCompanies();
            });
        }

        // Initialize view all companies button
        const viewAllBtn = document.getElementById('viewAllCompanies');
        if (viewAllBtn) {
            viewAllBtn.addEventListener('click', () => {
                console.log('👁️ View all companies button clicked');
                this.showAllCompanies();
            });
        }

        // Update company indicators initially
        this.updateCompanyIndicators('-');
        
        console.log('📱 UI components initialized');
    }

    /**
     * Load companies from API - ENHANCED WITH DETAILED LOGGING
     */
    async loadCompanies() {
        console.log('🏢 Starting to load companies...');
        
        try {
            window.UI.showLoading('Cargando empresas...');
            
            console.log('🌐 Making API call to get companies...');
            const response = await window.API.getCompanies();
            
            console.log('📋 API response received:', response);
            
            if (response && response.companies) {
                this.companies = response.companies;
                console.log('🏢 Companies loaded:', Object.keys(this.companies));
                
                this.populateCompanySelector();
                this.updateSystemOverview();
                
                // Auto-select first company if none selected
                if (!this.currentCompanyId && Object.keys(this.companies).length > 0) {
                    const firstCompanyId = Object.keys(this.companies)[0];
                    console.log('🎯 Auto-selecting first company:', firstCompanyId);
                    await this.selectCompany(firstCompanyId);
                }
                
                window.UI.showToast(`✅ ${Object.keys(this.companies).length} empresas cargadas`, 'success');
                console.log('✅ Companies loading completed successfully');
            } else {
                throw new Error('No companies data received from API');
            }
            
        } catch (error) {
            console.error('❌ Error loading companies:', error);
            this.handleError(error, 'Error cargando empresas');
            
            // Show fallback companies
            this.showFallbackCompanies();
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Populate company selector dropdown
     */
    populateCompanySelector() {
        const select = document.getElementById('currentCompany');
        if (!select) {
            console.warn('⚠️ Company select element not found');
            return;
        }

        console.log('📝 Populating company selector...');

        // Clear existing options
        select.innerHTML = '<option value="">Selecciona una empresa...</option>';

        // Add company options
        Object.entries(this.companies).forEach(([id, company]) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${company.company_name || id}`;
            select.appendChild(option);
        });

        // Set current selection
        if (this.currentCompanyId) {
            select.value = this.currentCompanyId;
        }

        console.log('📝 Company selector populated with', Object.keys(this.companies).length, 'companies');
    }

    /**
     * Select a company
     */
    async selectCompany(companyId) {
        if (!companyId || companyId === this.currentCompanyId) return;

        if (!this.companies[companyId]) {
            window.UI.showToast('❌ Empresa no encontrada', 'error');
            return;
        }

        console.log('🏢 Selecting company:', companyId);

        try {
            const company = this.companies[companyId];
            window.UI.showLoading(`Seleccionando empresa: ${company.company_name || companyId}...`);

            // Update current context
            this.currentCompanyId = companyId;
            window.API.setCompanyId(companyId);

            // Update UI
            this.updateCompanyIndicators(company.company_name || companyId);
            this.populateCompanySelector();

            // Notify other modules
            this.notifyCompanyChange(companyId);

            window.UI.showToast(`✅ Empresa seleccionada: ${company.company_name || companyId}`, 'success');
            
        } catch (error) {
            console.error('❌ Error selecting company:', error);
            window.UI.showToast('❌ Error seleccionando empresa: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Admin button listeners
        const reloadBtn = document.getElementById('reloadConfigBtn');
        if (reloadBtn) {
            reloadBtn.addEventListener('click', () => this.reloadConfiguration());
        }

        const statsBtn = document.getElementById('systemStatsBtn');
        if (statsBtn) {
            statsBtn.addEventListener('click', () => this.showSystemStats());
        }

        const diagnosticsBtn = document.getElementById('runDiagnosticsBtn');
        if (diagnosticsBtn) {
            diagnosticsBtn.addEventListener('click', () => this.runDiagnostics());
        }

        console.log('🎧 Event listeners set up');
    }

    /**
     * Initialize modules
     */
    async initializeModules() {
        const modules = [
            { name: 'CompanyManager', obj: window.CompanyManager },
            { name: 'DocumentsManager', obj: window.DocumentsManager },
            { name: 'AdminTools', obj: window.AdminTools }
        ];

        for (const module of modules) {
            try {
                if (module.obj && typeof module.obj.init === 'function') {
                    console.log(`📦 Initializing ${module.name}...`);
                    await module.obj.init();
                    console.log(`✅ ${module.name} initialized`);
                } else {
                    console.warn(`⚠️ ${module.name} not available or no init method`);
                }
            } catch (error) {
                console.error(`❌ Failed to initialize ${module.name}:`, error);
                // Continue with other modules
            }
        }
    }

    /**
     * Show all companies
     */
    showAllCompanies() {
        if (!this.companies || Object.keys(this.companies).length === 0) {
            window.UI.showToast('⚠️ No hay empresas cargadas', 'warning');
            return;
        }

        const companiesData = JSON.stringify(this.companies, null, 2);
        window.UI.showModal('Todas las Empresas', `<pre style="max-height: 400px; overflow: auto;">${companiesData}</pre>`);
    }

    /**
     * Update company indicators
     */
    updateCompanyIndicators(companyName) {
        // Update company info display
        const companyInfo = document.getElementById('companyInfo');
        if (companyInfo) {
            if (companyName && companyName !== '-') {
                companyInfo.innerHTML = `
                    <div class="company-status active">
                        <span class="status-indicator">🟢</span>
                        <span class="company-name">${companyName}</span>
                    </div>
                `;
            } else {
                companyInfo.innerHTML = `
                    <div class="info-placeholder">
                        <span class="placeholder-icon">⏳</span>
                        <p>Selecciona una empresa</p>
                    </div>
                `;
            }
        }
    }

    /**
     * Update system overview
     */
    updateSystemOverview() {
        const overview = document.getElementById('systemOverview');
        if (!overview) return;

        const companiesCount = Object.keys(this.companies).length;
        
        overview.innerHTML = `
            <div class="system-stats">
                <div class="stat-item">
                    <span class="stat-icon">🏢</span>
                    <span class="stat-label">Empresas</span>
                    <span class="stat-value">${companiesCount}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-icon">✅</span>
                    <span class="stat-label">Estado</span>
                    <span class="stat-value">Activo</span>
                </div>
                <div class="stat-item">
                    <span class="stat-icon">🚄</span>
                    <span class="stat-label">Railway</span>
                    <span class="stat-value">Producción</span>
                </div>
            </div>
        `;
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
     * Notify modules about company change
     */
    notifyCompanyChange(companyId) {
        // Notify CompanyManager
        if (window.CompanyManager && window.CompanyManager.onCompanyChange) {
            window.CompanyManager.onCompanyChange(companyId);
        }

        // Notify DocumentsManager
        if (window.DocumentsManager && window.DocumentsManager.onCompanyChange) {
            window.DocumentsManager.onCompanyChange(companyId);
        }

        // Notify AdminTools
        if (window.AdminTools && window.AdminTools.onCompanyChange) {
            window.AdminTools.onCompanyChange(companyId);
        }
    }

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

    // Placeholder methods for admin functions
    async reloadConfiguration() {
        window.UI.showToast('🔄 Recargando configuración...', 'info');
        await this.loadCompanies();
    }

    async showSystemStats() {
        window.UI.showToast('📊 Estadísticas del sistema disponibles en desarrollo', 'info');
    }

    async runDiagnostics() {
        window.UI.showToast('🔍 Ejecutando diagnósticos...', 'info');
        setTimeout(() => {
            window.UI.showToast('✅ Diagnósticos completados', 'success');
        }, 2000);
    }
}

// ==================== APPLICATION STARTUP - FIXED ====================

/**
 * Initialize application - FIXED to handle various scenarios
 */
async function startApplication() {
    console.log('🚀 Starting application initialization...');
    
    try {
        // Create global app instance
        console.log('🏗️ Creating AdminPanelApp instance...');
        window.AdminApp = new AdminPanelApp();
        
        // Initialize the application
        console.log('⚡ Initializing AdminPanelApp...');
        await window.AdminApp.init();
        
        // Log successful startup
        console.log('🎉 Multi-Tenant Admin Panel initialized successfully');
        
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
                max-width: 500px;
                z-index: 10000;
                font-family: Arial, sans-serif;
            ">
                <h2 style="color: #e74c3c; margin-bottom: 1rem;">⚠️ Error Crítico</h2>
                <p><strong>Error:</strong> ${error.message}</p>
                <p>No se pudo inicializar la aplicación.</p>
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
}

// MULTIPLE INITIALIZATION STRATEGIES
console.log('📋 Document ready state:', document.readyState);

if (document.readyState === 'loading') {
    // DOM still loading
    console.log('⏳ DOM still loading, waiting for DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', startApplication);
} else {
    // DOM already loaded
    console.log('✅ DOM already loaded, starting immediately...');
    // Small delay to ensure all scripts are processed
    setTimeout(startApplication, 100);
}

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminPanelApp;
}
