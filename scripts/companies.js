// scripts/companies.js - Company Management Module
'use strict';

/**
 * Company Management Module for Multi-Tenant Admin Panel
 * Handles company selection, status monitoring, and company-specific operations
 */
class CompanyManager {
    constructor() {
        this.companies = {};
        this.currentCompanyId = null;
        this.statusCache = new Map();
        this.statusRefreshInterval = null;
        this.isInitialized = false;
        
        this.init = this.init.bind(this);
        this.refreshCompanyStatus = this.refreshCompanyStatus.bind(this);
    }

    /**
     * Initialize Company Manager
     */
    async init() {
        if (this.isInitialized) return;

        try {
            await this.loadCompanies();
            this.setupEventListeners();
            this.startStatusMonitoring();
            
            this.isInitialized = true;
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('🏢 Company Manager initialized');
            }
        } catch (error) {
            console.error('❌ Failed to initialize Company Manager:', error);
            throw error;
        }
    }

    /**
     * Load all companies from API
     */
    async loadCompanies() {
        try {
            window.UI.showLoading('Cargando empresas...');
            
            const response = await window.API.getCompanies();
            
            if (response && response.companies) {
                this.companies = response.companies;
                this.updateCompanySelector();
                this.updateSystemOverview();
                
                // Auto-select first company if none selected
                if (!this.currentCompanyId && Object.keys(this.companies).length > 0) {
                    const firstCompanyId = Object.keys(this.companies)[0];
                    await this.selectCompany(firstCompanyId);
                }
                
                window.UI.showToast(`✅ ${Object.keys(this.companies).length} empresas cargadas`, 'success');
                
                if (window.APP_CONFIG.DEBUG.enabled) {
                    console.log('🏢 Companies loaded:', Object.keys(this.companies));
                }
            } else {
                throw new Error('No companies data received');
            }
            
        } catch (error) {
            console.error('❌ Error loading companies:', error);
            window.UI.showToast('❌ Error cargando empresas: ' + error.message, 'error');
            this.showFallbackCompanies();
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Update company selector dropdown
     */
    updateCompanySelector() {
        const select = document.getElementById('currentCompany');
        if (!select) return;

        // Clear existing options
        select.innerHTML = '<option value="">Selecciona una empresa...</option>';

        // Add company options
        Object.entries(this.companies).forEach(([id, company]) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${company.company_name || id} (${company.services?.length || 0} servicios)`;
            select.appendChild(option);
        });

        // Set current selection
        if (this.currentCompanyId) {
            select.value = this.currentCompanyId;
        }
    }

    /**
     * Select a company and update context
     */
    async selectCompany(companyId) {
        if (!companyId || companyId === this.currentCompanyId) return;

        if (!this.companies[companyId]) {
            window.UI.showToast('❌ Empresa no encontrada', 'error');
            return;
        }

        try {
            const company = this.companies[companyId];
            window.UI.showLoading(`Seleccionando empresa: ${company.company_name || companyId}...`);

            // Update current context
            this.currentCompanyId = companyId;
            window.API.setCompanyId(companyId);

            // Update UI
            this.updateCompanyIndicators(company.company_name || companyId);
            this.updateCompanySelector();

            // Load company-specific data
            await this.loadCompanyData(companyId);

            // Notify other modules
            this.notifyCompanyChange(companyId);

            window.UI.showToast(`✅ Empresa seleccionada: ${company.company_name || companyId}`, 'success');
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('🏢 Company selected:', { id: companyId, company });
            }

        } catch (error) {
            console.error('❌ Error selecting company:', error);
            window.UI.showToast('❌ Error seleccionando empresa: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Load company-specific data
     */
    async loadCompanyData(companyId) {
        try {
            // Load company status
            const status = await this.getCompanyStatus(companyId);
            this.updateCompanyInfo(status);

            // Cache the status
            this.statusCache.set(companyId, {
                data: status,
                timestamp: Date.now()
            });

        } catch (error) {
            console.warn('⚠️ Failed to load some company data:', error.message);
            // Don't show error to user for partial failures
        }
    }

    /**
     * Get company status with caching
     */
    async getCompanyStatus(companyId) {
        // Check cache first
        const cached = this.statusCache.get(companyId);
        const cacheAge = Date.now() - (cached?.timestamp || 0);
        const cacheValid = cacheAge < (window.APP_CONFIG.PERFORMANCE.cache_duration || 300000); // 5 minutes

        if (cached && cacheValid) {
            return cached.data;
        }

        try {
            const status = await window.API.getCompanyStatus(companyId);
            
            // Update cache
            this.statusCache.set(companyId, {
                data: status,
                timestamp: Date.now()
            });
            
            return status;
        } catch (error) {
            console.error('❌ Error getting company status:', error);
            
            // Return cached data if available, even if stale
            if (cached) {
                console.warn('⚠️ Using stale cached data for company status');
                return cached.data;
            }
            
            throw error;
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

        const isHealthy = statusData.data?.system_healthy;
        const agentsCount = statusData.data?.agents_available?.length || 0;

        const html = `
            <div class="company-status">
                <div class="status-item">
                    <div class="status-label">Nombre</div>
                    <div class="status-value">${company.company_name || this.currentCompanyId}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">ID</div>
                    <div class="status-value">${this.currentCompanyId}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Servicios</div>
                    <div class="status-value">${this.formatServices(company.services)}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Estado</div>
                    <div class="status-value" style="color: ${isHealthy ? 'var(--success-color)' : 'var(--danger-color)'}">
                        ${isHealthy ? '🟢 Saludable' : '🔴 Con problemas'}
                    </div>
                </div>
                <div class="status-item">
                    <div class="status-label">Vectorstore</div>
                    <div class="status-value">${company.vectorstore_index || 'N/A'}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Agentes</div>
                    <div class="status-value">${agentsCount} disponibles</div>
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
        const healthyCompanies = this.getHealthyCompaniesCount();
        const isRailway = window.APP_CONFIG.ENV.is_railway;

        const html = `
            <div class="status-item">
                <div class="status-label">Total de Empresas</div>
                <div class="status-value">${totalCompanies}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Empresas Activas</div>
                <div class="status-value" style="color: var(--success-color)">${healthyCompanies}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Entorno</div>
                <div class="status-value">${isRailway ? '🚄 Railway' : '🖥️ Local'}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Última Actualización</div>
                <div class="status-value">${window.UI.formatDate(new Date())}</div>
            </div>
        `;

        overviewEl.innerHTML = html;
    }

    /**
     * Get count of healthy companies
     */
    getHealthyCompaniesCount() {
        let healthyCount = 0;
        
        this.statusCache.forEach((cache, companyId) => {
            if (cache.data?.data?.system_healthy) {
                healthyCount++;
            }
        });
        
        // If no status data cached, assume all are healthy
        return healthyCount || Object.keys(this.companies).length;
    }

    /**
     * Format services array for display
     */
    formatServices(services) {
        if (!services || !Array.isArray(services)) return 'N/A';
        if (services.length === 0) return 'Ninguno';
        
        return services.slice(0, 3).join(', ') + 
               (services.length > 3 ? ` y ${services.length - 3} más` : '');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Company selector change
        const companySelect = document.getElementById('currentCompany');
        if (companySelect) {
            companySelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.selectCompany(e.target.value);
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

        // Health check button
        const healthBtn = document.getElementById('checkHealthBtn');
        if (healthBtn) {
            healthBtn.addEventListener('click', () => {
                this.performHealthCheck();
            });
        }

        // Statistics button
        const statsBtn = document.getElementById('viewStatsBtn');
        if (statsBtn) {
            statsBtn.addEventListener('click', () => {
                this.viewCompanyStatistics();
            });
        }

        // Reset cache button
        const resetBtn = document.getElementById('resetCacheBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetCompanyCache();
            });
        }
    }

    /**
     * Start status monitoring
     */
    startStatusMonitoring() {
        // Refresh status every 5 minutes
        const interval = window.APP_CONFIG.PERFORMANCE.cache_duration || 300000;
        
        this.statusRefreshInterval = setInterval(() => {
            if (this.currentCompanyId) {
                this.refreshCompanyStatus(this.currentCompanyId);
            }
        }, interval);
    }

    /**
     * Stop status monitoring
     */
    stopStatusMonitoring() {
        if (this.statusRefreshInterval) {
            clearInterval(this.statusRefreshInterval);
            this.statusRefreshInterval = null;
        }
    }

    /**
     * Refresh company status in background
     */
    async refreshCompanyStatus(companyId) {
        try {
            const status = await window.API.getCompanyStatus(companyId);
            
            // Update cache
            this.statusCache.set(companyId, {
                data: status,
                timestamp: Date.now()
            });

            // Update UI if this is the current company
            if (companyId === this.currentCompanyId) {
                this.updateCompanyInfo(status);
            }

            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log(`🔄 Status refreshed for company: ${companyId}`);
            }

        } catch (error) {
            console.warn(`⚠️ Failed to refresh status for ${companyId}:`, error.message);
        }
    }

    /**
     * Notify other modules of company change
     */
    notifyCompanyChange(companyId) {
        // Notify Documents Manager
        if (window.DocumentsManager) {
            window.DocumentsManager.onCompanyChange(companyId);
        }

        // Notify Chat Tester
        if (window.ChatTester) {
            window.ChatTester.onCompanyChange(companyId);
        }

        // Notify Multimedia Manager
        if (window.MultimediaManager) {
            window.MultimediaManager.onCompanyChange(companyId);
        }

        // Notify Admin Tools
        if (window.AdminTools) {
            window.AdminTools.onCompanyChange(companyId);
        }

        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('companyChange', {
            detail: { companyId, company: this.companies[companyId] }
        }));
    }

    /**
     * Perform health check for current company
     */
    async performHealthCheck() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        try {
            window.UI.showLoading('Verificando salud del sistema...');

            const health = await window.API.companyHealthCheck(this.currentCompanyId);
            const company = this.companies[this.currentCompanyId];
            
            this.showHealthCheckModal(health, company);

        } catch (error) {
            console.error('❌ Health check failed:', error);
            window.UI.showToast('❌ Error verificando salud: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Show health check results in modal
     */
    showHealthCheckModal(health, company) {
        let healthHTML = '<div class="health-results">';
        
        if (health.status === 'healthy' || health.status === 'partial') {
            const statusColor = health.status === 'healthy' ? 'var(--success-color)' : 'var(--warning-color)';
            const statusIcon = health.status === 'healthy' ? '✅' : '⚠️';
            const statusText = health.status === 'healthy' ? 'Sistema Saludable' : 'Sistema Parcialmente Funcional';
            
            healthHTML += `
                <h4 style="color: ${statusColor}">${statusIcon} ${statusText}</h4>
                <div class="health-info">
                    <p><strong>Empresa:</strong> ${company.company_name}</p>
                    <p><strong>ID:</strong> ${this.currentCompanyId}</p>
                    <p><strong>Timestamp:</strong> ${window.UI.formatDate(new Date())}</p>
                </div>
            `;

            if (health.components) {
                healthHTML += '<h5>Estado de Componentes:</h5><ul class="component-list">';
                Object.entries(health.components).forEach(([component, status]) => {
                    const icon = status === 'healthy' || status === 'connected' ? '✅' : '❌';
                    const displayName = this.getComponentDisplayName(component);
                    healthHTML += `<li>${icon} <strong>${displayName}:</strong> ${status}</li>`;
                });
                healthHTML += '</ul>';
            }

            // Show Railway-specific information
            if (window.APP_CONFIG.ENV.is_railway) {
                healthHTML += `
                    <div class="railway-info">
                        <h5>🚄 Información Railway:</h5>
                        <p>• Entorno de producción detectado</p>
                        <p>• Servicio de agendamiento en modo fallback (esperado)</p>
                        <p>• Todas las funciones principales operativas</p>
                    </div>
                `;
            }

        } else {
            healthHTML += `
                <h4 style="color: var(--danger-color)">❌ Sistema con Problemas</h4>
                <div class="error-info">
                    <p><strong>Error:</strong> ${health.error || health.message}</p>
                    <p><strong>Empresa:</strong> ${company.company_name}</p>
                </div>
            `;
        }
        
        healthHTML += '</div>';
        
        window.UI.showModal('🩺 Health Check del Sistema', healthHTML, {
            icon: '🩺',
            maxWidth: '600px'
        });
    }

    /**
     * Get display name for component
     */
    getComponentDisplayName(component) {
        const componentNames = {
            'redis': 'Redis Cache',
            'openai': 'OpenAI API',
            'vectorstore': 'Base de Datos Vectorial',
            'schedule_service': 'Servicio de Agendamiento',
            'companies': 'Gestor de Empresas'
        };
        
        return componentNames[component] || component;
    }

    /**
     * View company statistics
     */
    async viewCompanyStatistics() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        try {
            window.UI.showLoading('Cargando estadísticas...');

            const stats = await window.API.getSystemStats();
            const company = this.companies[this.currentCompanyId];
            
            this.showStatisticsModal(stats, company);

        } catch (error) {
            console.error('❌ Error loading statistics:', error);
            window.UI.showToast('❌ Error cargando estadísticas: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Show statistics in modal
     */
    showStatisticsModal(stats, company) {
        let statsHTML = '<div class="stats-results">';
        statsHTML += `<h4>📊 Estadísticas de ${company.company_name}</h4>`;
        
        if (stats.status === 'success' && stats.data) {
            const data = stats.data;
            
            statsHTML += '<div class="stats-grid">';
            
            // Main statistics
            if (data.conversations_count !== undefined) {
                statsHTML += `<div class="stat-item">
                    <div class="stat-label">💬 Conversaciones</div>
                    <div class="stat-value">${data.conversations_count.toLocaleString()}</div>
                </div>`;
            }
            
            if (data.documents_count !== undefined) {
                statsHTML += `<div class="stat-item">
                    <div class="stat-label">📄 Documentos</div>
                    <div class="stat-value">${data.documents_count.toLocaleString()}</div>
                </div>`;
            }
            
            if (data.vectorstore_size !== undefined) {
                statsHTML += `<div class="stat-item">
                    <div class="stat-label">🗄️ Vectores</div>
                    <div class="stat-value">${data.vectorstore_size.toLocaleString()}</div>
                </div>`;
            }
            
            if (data.cache_keys !== undefined) {
                statsHTML += `<div class="stat-item">
                    <div class="stat-label">🗂️ Cache Keys</div>
                    <div class="stat-value">${data.cache_keys.toLocaleString()}</div>
                </div>`;
            }
            
            statsHTML += '</div>';
            
            // Additional information
            if (data.last_activity) {
                statsHTML += `<p><strong>Última Actividad:</strong> ${window.UI.formatDate(data.last_activity)}</p>`;
            }
            
        } else {
            statsHTML += '<p>No hay estadísticas disponibles en este momento.</p>';
        }
        
        statsHTML += '</div>';
        
        window.UI.showModal('📊 Estadísticas del Sistema', statsHTML, {
            icon: '📊',
            maxWidth: '700px'
        });
    }

    /**
     * Reset company cache
     */
    async resetCompanyCache() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const company = this.companies[this.currentCompanyId];
        const companyName = company.company_name || this.currentCompanyId;
        
        const confirmed = await this.showConfirmDialog(
            '🗑️ Limpiar Cache',
            `¿Estás seguro de que quieres limpiar el cache de <strong>${companyName}</strong>?<br><br>
            Esta acción eliminará datos temporales y puede afectar el rendimiento temporalmente.`
        );
        
        if (!confirmed) return;

        try {
            window.UI.showLoading('Limpiando cache...');

            const result = await window.API.resetCompanyCache();
            
            if (result.status === 'success') {
                // Clear local cache
                this.statusCache.delete(this.currentCompanyId);
                
                // Reload company data
                await this.loadCompanyData(this.currentCompanyId);
                
                window.UI.showToast(`✅ Cache limpiado: ${result.keys_cleared || 0} claves eliminadas`, 'success');
            } else {
                throw new Error(result.message || 'Error limpiando cache');
            }

        } catch (error) {
            console.error('❌ Error resetting cache:', error);
            window.UI.showToast('❌ Error limpiando cache: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Show confirmation dialog
     */
    showConfirmDialog(title, message) {
        return new Promise((resolve) => {
            const modal = window.UI.showConfirmModal(
                title,
                message,
                () => resolve(true),
                () => resolve(false)
            );
        });
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
        
        // Show fallback system overview
        const overviewEl = document.getElementById('systemOverview');
        if (overviewEl) {
            overviewEl.innerHTML = `
                <div class="grid-placeholder">
                    <span class="placeholder-icon">⚠️</span>
                    <p>Error cargando información del sistema</p>
                    <small>Intenta recargar las empresas</small>
                </div>
            `;
        }
        
        window.UI.showToast('⚠️ Usando configuración de emergencia', 'warning');
    }

    /**
     * Get current company
     */
    getCurrentCompany() {
        return this.currentCompanyId ? this.companies[this.currentCompanyId] : null;
    }

    /**
     * Get all companies
     */
    getAllCompanies() {
        return this.companies;
    }

    /**
     * Check if company is selected
     */
    hasCompanySelected() {
        return !!this.currentCompanyId;
    }

    /**
     * Get company by ID
     */
    getCompany(companyId) {
        return this.companies[companyId] || null;
    }

    /**
     * Clear status cache
     */
    clearStatusCache() {
        this.statusCache.clear();
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🗑️ Company status cache cleared');
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopStatusMonitoring();
        this.clearStatusCache();
        this.isInitialized = false;
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🧹 Company Manager cleaned up');
        }
    }
}

// Create global instance
window.CompanyManager = new CompanyManager();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CompanyManager;
}
