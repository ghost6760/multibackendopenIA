// scripts/companies.js - Company Management Module
'use strict';

/**
 * Company Management for Multi-Tenant Admin Panel
 * Handles company selection, status, and context switching
 */
class CompaniesManager {
    constructor() {
        this.companies = {};
        this.currentCompanyId = null;
        this.isInitialized = false;
        
        this.init = this.init.bind(this);
        this.onCompanyChange = this.onCompanyChange.bind(this);
    }
    
    /**
     * Initialize Companies Manager
     */
    async init() {
        if (this.isInitialized) return;
        
        try {
            this.setupEventListeners();
            
            // Load companies on initialization
            await this.loadCompanies();
            
            this.isInitialized = true;
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('🏢 Companies Manager initialized');
            }
            
        } catch (error) {
            console.error('❌ Failed to initialize Companies Manager:', error);
            throw error;
        }
    }
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Company selector change
        const companySelect = document.getElementById('currentCompany');
        if (companySelect) {
            companySelect.addEventListener('change', (e) => {
                const newCompanyId = e.target.value;
                if (newCompanyId !== this.currentCompanyId) {
                    this.selectCompany(newCompanyId);
                }
            });
        }
        
        // Refresh companies button
        const refreshBtn = document.getElementById('refreshCompanies');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadCompanies();
            });
        }
        
        // Company action buttons
        const checkHealthBtn = document.getElementById('checkHealthBtn');
        if (checkHealthBtn) {
            checkHealthBtn.addEventListener('click', () => {
                this.checkCompanyHealth();
            });
        }
        
        const viewStatsBtn = document.getElementById('viewStatsBtn');
        if (viewStatsBtn) {
            viewStatsBtn.addEventListener('click', () => {
                this.viewCompanyStats();
            });
        }
        
        const resetCacheBtn = document.getElementById('resetCacheBtn');
        if (resetCacheBtn) {
            resetCacheBtn.addEventListener('click', () => {
                this.resetCompanyCache();
            });
        }
        
        const viewAllBtn = document.getElementById('viewAllCompanies');
        if (viewAllBtn) {
            viewAllBtn.addEventListener('click', () => {
                this.showAllCompanies();
            });
        }
    }
    
    /**
     * Load companies from API
     */
    async loadCompanies() {
        try {
            window.UI.showLoading('Cargando empresas configuradas...');
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('🔄 Loading companies...');
            }
            
            const response = await window.API.getCompanies();
            
            if (response.status === 'success' && response.companies) {
                this.companies = response.companies;
                
                this.populateCompanySelector();
                
                // Set default company if none selected
                if (!this.currentCompanyId || !this.companies[this.currentCompanyId]) {
                    const defaultCompany = window.APP_CONFIG.COMPANIES.default_company;
                    const firstCompany = Object.keys(this.companies)[0];
                    
                    this.currentCompanyId = this.companies[defaultCompany] ? 
                        defaultCompany : firstCompany;
                }
                
                if (this.currentCompanyId) {
                    this.selectCompany(this.currentCompanyId, false);
                }
                
                await this.loadSystemOverview();
                
                window.UI.showNotification(
                    `✅ ${Object.keys(this.companies).length} empresas cargadas`,
                    'success'
                );
                
                if (window.APP_CONFIG.DEBUG.enabled) {
                    console.log('🏢 Companies loaded:', Object.keys(this.companies));
                }
                
            } else {
                throw new Error(response.message || 'Error cargando empresas');
            }
            
        } catch (error) {
            console.error('Error loading companies:', error);
            window.UI.showNotification(
                'Error cargando empresas: ' + error.message,
                'error'
            );
        } finally {
            window.UI.hideLoading();
        }
    }
    
    /**
     * Populate company selector dropdown
     */
    populateCompanySelector() {
        const selector = document.getElementById('currentCompany');
        if (!selector) return;
        
        // Clear existing options
        selector.innerHTML = '';
        
        if (Object.keys(this.companies).length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No hay empresas configuradas';
            selector.appendChild(option);
            return;
        }
        
        // Add companies
        Object.entries(this.companies).forEach(([companyId, company]) => {
            const option = document.createElement('option');
            option.value = companyId;
            option.textContent = `${company.company_name} (${companyId})`;
            selector.appendChild(option);
        });
        
        // Set selected value
        if (this.currentCompanyId) {
            selector.value = this.currentCompanyId;
        }
    }
    
    /**
     * Select a company
     */
    async selectCompany(companyId, showNotification = true) {
        if (!companyId || !this.companies[companyId]) {
            console.warn('Invalid company ID:', companyId);
            return;
        }
        
        const previousCompanyId = this.currentCompanyId;
        this.currentCompanyId = companyId;
        
        // Update API context
        window.API.setCompanyContext(companyId);
        
        // Update UI
        const selector = document.getElementById('currentCompany');
        if (selector) {
            selector.value = companyId;
        }
        
        // Update company indicators
        this.updateCompanyIndicators();
        
        // Load company information
        await this.loadCompanyInfo();
        
        // Notify other modules about company change
        await this.notifyCompanyChange(companyId, previousCompanyId);
        
        if (showNotification) {
            const company = this.companies[companyId];
            window.UI.showNotification(
                `Empresa cambiada a: ${company.company_name}`,
                'info'
            );
        }
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🏢 Company selected:', companyId);
        }
    }
    
    /**
     * Update company indicators throughout the UI
     */
    updateCompanyIndicators() {
        const company = this.companies[this.currentCompanyId];
        if (!company) return;
        
        const indicators = [
            'docCompanyIndicator',
            'searchCompanyIndicator',
            'chatCompanyName',
            'cameraCompany'
        ];
        
        indicators.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = company.company_name;
            }
        });
        
        // Update chat services
        const servicesElement = document.getElementById('chatCompanyServices');
        if (servicesElement && company.services) {
            servicesElement.textContent = `Servicios: ${company.services}`;
        }
    }
    
    /**
     * Load company information and update display
     */
    async loadCompanyInfo() {
        if (!this.currentCompanyId) return;
        
        try {
            const response = await window.API.getCompanyStatus(this.currentCompanyId);
            
            const infoDiv = document.getElementById('companyInfo');
            if (!infoDiv) return;
            
            if (response.status === 'success' && response.data) {
                const info = response.data;
                
                infoDiv.innerHTML = `
                    <div class="company-details">
                        <h3>${info.company_name} <span class="company-id">(${info.company_id})</span></h3>
                        <div class="company-stats">
                            <div class="stat-item">
                                <span class="stat-icon">📍</span>
                                <span class="stat-text">Servicios: ${info.services}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-icon">🤖</span>
                                <span class="stat-text ${info.orchestrator_ready ? 'status-healthy' : 'status-error'}">
                                    Orquestador: ${info.orchestrator_ready ? 'Listo' : 'No disponible'}
                                </span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-icon">🩺</span>
                                <span class="stat-text ${info.system_healthy ? 'status-healthy' : 'status-warning'}">
                                    Estado: ${info.system_healthy ? 'Saludable' : 'Requiere atención'}
                                </span>
                            </div>
                        </div>
                        <div class="technical-info">
                            <small>📊 Índice: ${info.vectorstore_index}</small>
                            <small>🔑 Prefijo: ${info.redis_prefix}</small>
                        </div>
                    </div>
                `;
                
                // Update company status section
                const statusContent = document.getElementById('companyStatusContent');
                if (statusContent) {
                    statusContent.innerHTML = `
                        <div class="status-grid">
                            <div class="status-card">
                                <h4>Estado General</h4>
                                <span class="status-badge ${info.system_healthy ? 'success' : 'warning'}">
                                    ${info.system_healthy ? 'Saludable' : 'Requiere atención'}
                                </span>
                            </div>
                            <div class="status-card">
                                <h4>Orquestador</h4>
                                <span class="status-badge ${info.orchestrator_ready ? 'success' : 'error'}">
                                    ${info.orchestrator_ready ? 'Activo' : 'Inactivo'}
                                </span>
                            </div>
                            <div class="status-card">
                                <h4>Vectorstore</h4>
                                <span class="status-badge ${info.vectorstore_connected ? 'success' : 'error'}">
                                    ${info.vectorstore_connected ? 'Conectado' : 'Desconectado'}
                                </span>
                            </div>
                        </div>
                    `;
                }
                
            } else {
                infoDiv.innerHTML = `
                    <div class="error-info">
                        <span class="error-icon">❌</span>
                        <span>Error cargando información de ${this.currentCompanyId}</span>
                    </div>
                `;
            }
            
        } catch (error) {
            console.error('Error loading company info:', error);
            const infoDiv = document.getElementById('companyInfo');
            if (infoDiv) {
                infoDiv.innerHTML = `
                    <div class="error-info">
                        <span class="error-icon">❌</span>
                        <span>Error de conexión</span>
                    </div>
                `;
            }
        }
    }
    
    /**
     * Load system overview
     */
    async loadSystemOverview() {
        try {
            const response = await window.API.getSystemHealth();
            
            const overviewDiv = document.getElementById('systemOverview');
            if (!overviewDiv) return;
            
            if (response.companies) {
                const healthData = response.companies.health || {};
                const statsData = response.companies.stats || {};
                
                let overviewHTML = '';
                
                Object.entries(this.companies).forEach(([companyId, company]) => {
                    const health = healthData[companyId] || {};
                    const stats = statsData[companyId] || {};
                    
                    const isHealthy = health.system_healthy || false;
                    const isActive = companyId === this.currentCompanyId;
                    const conversations = stats.conversations || 0;
                    const documents = stats.documents || 0;
                    
                    overviewHTML += `
                        <div class="company-overview-card ${isActive ? 'active' : ''}" 
                             data-company="${companyId}">
                            <div class="card-header">
                                <h4>${company.company_name}</h4>
                                <span class="company-id">${companyId}</span>
                            </div>
                            <div class="card-body">
                                <div class="overview-stats">
                                    <div class="stat-item">
                                        <span class="stat-icon ${isHealthy ? 'success' : 'error'}">
                                            ${isHealthy ? '✅' : '❌'}
                                        </span>
                                        <span class="stat-text">${isHealthy ? 'Saludable' : 'Error'}</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-icon">💬</span>
                                        <span class="stat-text">${conversations} conversaciones</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-icon">📄</span>
                                        <span class="stat-text">${documents} documentos</span>
                                    </div>
                                </div>
                            </div>
                            <div class="card-actions">
                                <button onclick="window.CompaniesManager.selectCompany('${companyId}')" 
                                        class="btn ${isActive ? 'btn-success' : 'btn-secondary'}">
                                    ${isActive ? '✓ Activa' : 'Seleccionar'}
                                </button>
                            </div>
                        </div>
                    `;
                });
                
                overviewDiv.innerHTML = overviewHTML;
                
            } else {
                overviewDiv.innerHTML = `
                    <div class="overview-placeholder">
                        <span class="placeholder-icon">⚠️</span>
                        <p>No se pudo cargar la vista general del sistema</p>
                    </div>
                `;
            }
            
        } catch (error) {
            console.error('Error loading system overview:', error);
            const overviewDiv = document.getElementById('systemOverview');
            if (overviewDiv) {
                overviewDiv.innerHTML = `
                    <div class="overview-placeholder error">
                        <span class="placeholder-icon">❌</span>
                        <p>Error cargando vista general</p>
                    </div>
                `;
            }
        }
    }
    
    /**
     * Notify other modules about company change
     */
    async notifyCompanyChange(newCompanyId, previousCompanyId) {
        const modules = [
            'DocumentsManager',
            'ChatManager',
            'MultimediaManager',
            'ConfigurationManager'
        ];
        
        for (const moduleName of modules) {
            if (window[moduleName] && typeof window[moduleName].onCompanyChange === 'function') {
                try {
                    await window[moduleName].onCompanyChange(newCompanyId, previousCompanyId);
                } catch (error) {
                    console.warn(`Error notifying ${moduleName} about company change:`, error);
                }
            }
        }
    }
    
    /**
     * Check company health
     */
    async checkCompanyHealth() {
        if (!this.currentCompanyId) {
            window.UI.showNotification('Selecciona una empresa primero', 'warning');
            return;
        }
        
        try {
            const company = this.companies[this.currentCompanyId];
            window.UI.showLoading(`Verificando salud de ${company.company_name}...`);
            
            const response = await window.API.getCompanyHealth(this.currentCompanyId);
            
            const isHealthy = response.system_healthy;
            const statusText = isHealthy ? '✅ Sistema saludable' : '❌ Sistema con problemas';
            
            let detailsHTML = `
                <div class="health-check-result">
                    <h3>${statusText}</h3>
                    <div class="health-details">
                        <p><strong>Empresa:</strong> ${response.company_name} (${response.company_id})</p>
                        <p><strong>Vectorstore:</strong> ${response.vectorstore_connected ? '✅ Conectado' : '❌ Desconectado'}</p>
            `;
            
            if (response.agents_status) {
                detailsHTML += '<h4>Estado de Agentes:</h4><ul>';
                Object.entries(response.agents_status).forEach(([agent, status]) => {
                    const icon = status === 'healthy' ? '✅' : '❌';
                    detailsHTML += `<li>${icon} ${agent}: ${status}</li>`;
                });
                detailsHTML += '</ul>';
            }
            
            if (response.rag_status) {
                detailsHTML += `
                    <h4>Estado RAG:</h4>
                    <p><strong>RAG Disponible:</strong> ${response.rag_status.rag_available ? '✅' : '❌'}</p>
                    <p><strong>Agentes con RAG:</strong> ${response.rag_status.rag_enabled_agents.join(', ')}</p>
                `;
            }
            
            detailsHTML += '</div></div>';
            
            this.showModal(`🩺 Health Check - ${company.company_name}`, detailsHTML);
            
        } catch (error) {
            window.UI.showNotification('Error verificando salud: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }
    
    /**
     * View company statistics
     */
    async viewCompanyStats() {
        if (!this.currentCompanyId) {
            window.UI.showNotification('Selecciona una empresa primero', 'warning');
            return;
        }
        
        try {
            window.UI.showLoading('Cargando estadísticas...');
            
            const response = await window.API.getAdminStatus();
            
            if (response.status === 'success') {
                const stats = response.statistics || {};
                const company = this.companies[this.currentCompanyId];
                
                let statsHTML = `
                    <div class="company-stats-result">
                        <h3>📊 Estadísticas de ${company.company_name}</h3>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-value">${stats.conversations || 0}</div>
                                <div class="stat-label">Conversaciones</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${stats.documents || 0}</div>
                                <div class="stat-label">Documentos</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${stats.bot_statuses || 0}</div>
                                <div class="stat-label">Estados Bot</div>
                            </div>
                        </div>
                `;
                
                if (response.configuration) {
                    statsHTML += `
                        <div class="config-section">
                            <h4>⚙️ Configuración</h4>
                            <p><strong>Servicios:</strong> ${response.configuration.services}</p>
                            <p><strong>Índice Vectorstore:</strong> ${response.configuration.vectorstore_index}</p>
                            <p><strong>URL Agendamiento:</strong> ${response.configuration.schedule_service_url}</p>
                        </div>
                    `;
                }
                
                statsHTML += '</div>';
                
                this.showModal('📊 Estadísticas', statsHTML);
                
            } else {
                throw new Error(response.message || 'Error cargando estadísticas');
            }
            
        } catch (error) {
            window.UI.showNotification('Error cargando estadísticas: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }
    
    /**
     * Reset company cache
     */
    async resetCompanyCache() {
        if (!this.currentCompanyId) {
            window.UI.showNotification('Selecciona una empresa primero', 'warning');
            return;
        }
        
        const company = this.companies[this.currentCompanyId];
        
        if (!confirm(`¿Estás seguro de que quieres limpiar el cache de ${company.company_name}?`)) {
            return;
        }
        
        try {
            window.UI.showLoading('Limpiando cache...');
            
            const response = await window.API.resetSystemCache(false);
            
            if (response.status === 'success') {
                window.UI.showNotification(
                    `✅ Cache limpiado: ${response.keys_cleared} claves eliminadas`,
                    'success'
                );
            } else {
                throw new Error(response.message || 'Error limpiando cache');
            }
            
        } catch (error) {
            window.UI.showNotification('Error limpiando cache: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }
    
    /**
     * Show all companies in a modal
     */
    showAllCompanies() {
        const companiesData = Object.entries(this.companies).map(([id, company]) => ({
            id,
            name: company.company_name,
            services: company.services,
            active: id === this.currentCompanyId
        }));
        
        let companiesHTML = `
            <div class="all-companies-view">
                <h3>🏢 Todas las Empresas (${companiesData.length})</h3>
                <div class="companies-list">
        `;
        
        companiesData.forEach(company => {
            companiesHTML += `
                <div class="company-item ${company.active ? 'active' : ''}">
                    <div class="company-info">
                        <h4>${company.name}</h4>
                        <p>ID: ${company.id}</p>
                        <p>Servicios: ${company.services}</p>
                    </div>
                    <div class="company-actions">
                        ${company.active ? 
                            '<span class="active-badge">✓ Activa</span>' : 
                            `<button onclick="window.CompaniesManager.selectCompany('${company.id}'); document.querySelector('.modal').remove();" class="btn btn-primary">Seleccionar</button>`
                        }
                    </div>
                </div>
            `;
        });
        
        companiesHTML += '</div></div>';
        
        this.showModal('🏢 Todas las Empresas', companiesHTML);
    }
    
    /**
     * Show modal dialog
     */
    showModal(title, content) {
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
                    <button onclick="this.closest('.modal').remove()" class="btn btn-secondary">Cerrar</button>
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
        
        // Focus trap
        const closeBtn = modal.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.focus();
        }
    }
    
    /**
     * Get current company ID
     */
    getCurrentCompanyId() {
        return this.currentCompanyId;
    }
    
    /**
     * Get current company data
     */
    getCurrentCompany() {
        return this.companies[this.currentCompanyId];
    }
    
    /**
     * Get all companies
     */
    getAllCompanies() {
        return this.companies;
    }
    
    /**
     * Handle company change event from external source
     */
    onCompanyChange(companyId) {
        return this.selectCompany(companyId);
    }
}

// Create global instance
window.CompaniesManager = new CompaniesManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CompaniesManager;
}

console.log('✅ Companies module loaded successfully');
