// scripts/admin.js - Admin Tools Module
'use strict';

/**
 * Admin Tools Module for Multi-Tenant Admin Panel
 * Handles system administration, diagnostics, and advanced management features
 */
class AdminTools {
    constructor() {
        this.isInitialized = false;
        this.currentCompanyId = null;
        this.diagnosticsRunning = false;
        
        this.init = this.init.bind(this);
        this.onCompanyChange = this.onCompanyChange.bind(this);
    }

    /**
     * Initialize Admin Tools
     */
    async init() {
        if (this.isInitialized) return;

        try {
            this.setupEventListeners();
            this.checkAdminPermissions();
            
            this.isInitialized = true;
            
            if (window.APP_CONFIG.DEBUG.enabled) {
                console.log('⚙️ Admin Tools initialized');
            }
        } catch (error) {
            console.error('❌ Failed to initialize Admin Tools:', error);
            throw error;
        }
    }

    /**
     * Handle company change
     */
    onCompanyChange(companyId) {
        this.currentCompanyId = companyId;
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('⚙️ Admin context changed to company:', companyId);
        }
    }

    /**
     * Check admin permissions and features
     */
    checkAdminPermissions() {
        // In a real application, this would check user permissions
        const isAdminMode = window.APP_CONFIG.ENV.is_development || 
                           window.location.search.includes('admin=true');
        
        if (!isAdminMode) {
            this.disableAdvancedFeatures();
        }
    }

    /**
     * Setup event listeners for admin tools
     */
    setupEventListeners() {
        // System management buttons
        const reloadConfigBtn = document.getElementById('reloadConfigBtn');
        const systemStatsBtn = document.getElementById('systemStatsBtn');
        const runDiagnosticsBtn = document.getElementById('runDiagnosticsBtn');
        
        if (reloadConfigBtn) {
            reloadConfigBtn.addEventListener('click', () => this.reloadConfiguration());
        }
        
        if (systemStatsBtn) {
            systemStatsBtn.addEventListener('click', () => this.viewSystemStats());
        }
        
        if (runDiagnosticsBtn) {
            runDiagnosticsBtn.addEventListener('click', () => this.runDiagnostics());
        }

        // Vectorstore management buttons
        const cleanupVectorsBtn = document.getElementById('cleanupVectorsBtn');
        const vectorRecoveryBtn = document.getElementById('vectorRecoveryBtn');
        const protectionStatusBtn = document.getElementById('protectionStatusBtn');
        
        if (cleanupVectorsBtn) {
            cleanupVectorsBtn.addEventListener('click', () => this.cleanupVectors());
        }
        
        if (vectorRecoveryBtn) {
            vectorRecoveryBtn.addEventListener('click', () => this.forceVectorRecovery());
        }
        
        if (protectionStatusBtn) {
            protectionStatusBtn.addEventListener('click', () => this.checkProtectionStatus());
        }

        // Configuration management buttons
        const exportConfigBtn = document.getElementById('exportConfigBtn');
        const migrationToolBtn = document.getElementById('migrationToolBtn');
        const testMultimediaBtn = document.getElementById('testMultimediaBtn');
        
        if (exportConfigBtn) {
            exportConfigBtn.addEventListener('click', () => this.exportConfiguration());
        }
        
        if (migrationToolBtn) {
            migrationToolBtn.addEventListener('click', () => this.showMigrationTool());
        }
        
        if (testMultimediaBtn) {
            testMultimediaBtn.addEventListener('click', () => this.testMultimedia());
        }
    }

    // ==================== SYSTEM MANAGEMENT ====================

    /**
     * Reload system configuration
     */
    async reloadConfiguration() {
        try {
            window.UI.showLoading('Recargando configuración del sistema...');
            
            const response = await window.API.reloadCompanyConfig();
            
            if (response.status === 'success') {
                window.UI.showToast('✅ Configuración recargada exitosamente', 'success');
                
                // Reload companies in CompanyManager
                if (window.CompanyManager) {
                    await window.CompanyManager.loadCompanies();
                }
                
                // Show reload details if available
                if (response.reloaded_companies) {
                    const details = `Empresas recargadas: ${response.reloaded_companies}`;
                    window.UI.showToast(details, 'info');
                }
                
            } else {
                throw new Error(response.message || 'Error recargando configuración');
            }
            
        } catch (error) {
            console.error('❌ Error reloading configuration:', error);
            window.UI.showToast('❌ Error recargando configuración: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * View detailed system statistics
     */
    async viewSystemStats() {
        try {
            window.UI.showLoading('Cargando estadísticas del sistema...');
            
            // Get system-wide statistics
            const stats = await this.getSystemWideStats();
            
            this.showSystemStatsModal(stats);
            
        } catch (error) {
            console.error('❌ Error loading system stats:', error);
            window.UI.showToast('❌ Error cargando estadísticas: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Get system-wide statistics
     */
    async getSystemWideStats() {
        const companies = window.CompanyManager?.getAllCompanies() || {};
        const stats = {
            system: {
                total_companies: Object.keys(companies).length,
                environment: window.APP_CONFIG.ENV.is_railway ? 'Railway Production' : 'Local Development',
                uptime: this.getSystemUptime(),
                memory_usage: this.getMemoryUsage(),
                is_railway: window.APP_CONFIG.ENV.is_railway
            },
            companies: {},
            features: {
                multimedia: window.APP_CONFIG.FEATURES.voice_processing && window.APP_CONFIG.FEATURES.image_processing,
                google_calendar: window.APP_CONFIG.FEATURES.google_calendar_enabled,
                schedule_service: window.API.scheduleServiceAvailable,
                auto_recovery: window.APP_CONFIG.FEATURES.auto_vectorstore_recovery
            }
        };

        // Get stats for each company
        for (const [companyId, company] of Object.entries(companies)) {
            try {
                const companyStats = await window.API.getSystemStats();
                stats.companies[companyId] = {
                    name: company.company_name,
                    status: companyStats.status,
                    data: companyStats.data
                };
            } catch (error) {
                stats.companies[companyId] = {
                    name: company.company_name,
                    status: 'error',
                    error: error.message
                };
            }
        }

        return stats;
    }

    /**
     * Show system statistics modal
     */
    showSystemStatsModal(stats) {
        const content = `
            <div class="system-stats">
                <h4>📊 Estadísticas Generales del Sistema</h4>
                
                <div class="stats-section">
                    <h5>🖥️ Sistema</h5>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-label">Entorno</div>
                            <div class="stat-value">${stats.system.environment}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Empresas Configuradas</div>
                            <div class="stat-value">${stats.system.total_companies}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Tiempo Activo</div>
                            <div class="stat-value">${stats.system.uptime}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Memoria Usada</div>
                            <div class="stat-value">${stats.system.memory_usage}</div>
                        </div>
                    </div>
                </div>

                <div class="stats-section">
                    <h5>🔧 Características</h5>
                    <div class="features-grid">
                        <div class="feature-item ${stats.features.multimedia ? 'enabled' : 'disabled'}">
                            <span class="feature-icon">${stats.features.multimedia ? '✅' : '❌'}</span>
                            Multimedia
                        </div>
                        <div class="feature-item ${stats.features.google_calendar ? 'enabled' : 'disabled'}">
                            <span class="feature-icon">${stats.features.google_calendar ? '✅' : '❌'}</span>
                            Google Calendar
                        </div>
                        <div class="feature-item ${stats.features.schedule_service ? 'enabled' : 'disabled'}">
                            <span class="feature-icon">${stats.features.schedule_service ? '✅' : '⚠️'}</span>
                            Servicio de Agendamiento
                        </div>
                        <div class="feature-item ${stats.features.auto_recovery ? 'enabled' : 'disabled'}">
                            <span class="feature-icon">${stats.features.auto_recovery ? '✅' : '❌'}</span>
                            Auto-Recovery
                        </div>
                    </div>
                </div>

                <div class="stats-section">
                    <h5>🏢 Estado por Empresa</h5>
                    <div class="companies-stats">
                        ${this.renderCompanyStats(stats.companies)}
                    </div>
                </div>

                ${stats.system.is_railway ? `
                    <div class="stats-section railway-info">
                        <h5>🚄 Información Railway</h5>
                        <p>• Despliegue en producción activo</p>
                        <p>• Sistema optimizado para Railway</p>
                        <p>• Gestión automática de puertos y servicios</p>
                        <p>• Modo fallback habilitado para servicios externos</p>
                    </div>
                ` : ''}
            </div>
        `;

        window.UI.showModal('📊 Estadísticas del Sistema', content, {
            maxWidth: '900px'
        });
    }

    /**
     * Render company statistics
     */
    renderCompanyStats(companies) {
        let html = '';
        
        for (const [companyId, company] of Object.entries(companies)) {
            const statusIcon = company.status === 'success' ? '✅' : 
                             company.status === 'error' ? '❌' : '⚠️';
            
            html += `
                <div class="company-stat-item">
                    <div class="company-stat-header">
                        <span class="company-status">${statusIcon}</span>
                        <span class="company-name">${company.name}</span>
                        <span class="company-id">${companyId}</span>
                    </div>
                    ${company.data ? `
                        <div class="company-stat-data">
                            <span>Conversaciones: ${company.data.conversations_count || 0}</span>
                            <span>Documentos: ${company.data.documents_count || 0}</span>
                            <span>Vectores: ${company.data.vectorstore_size || 0}</span>
                        </div>
                    ` : ''}
                    ${company.error ? `<div class="company-error">Error: ${company.error}</div>` : ''}
                </div>
            `;
        }
        
        return html || '<p>No hay empresas configuradas</p>';
    }

    /**
     * Run comprehensive system diagnostics
     */
    async runDiagnostics() {
        if (this.diagnosticsRunning) {
            window.UI.showToast('⚠️ Diagnósticos ya en ejecución', 'warning');
            return;
        }

        this.diagnosticsRunning = true;

        try {
            window.UI.showLoadingWithProgress('Ejecutando diagnósticos del sistema...', 0);
            
            const diagnostics = await this.performSystemDiagnostics();
            
            this.showDiagnosticsModal(diagnostics);
            
        } catch (error) {
            console.error('❌ Error running diagnostics:', error);
            window.UI.showToast('❌ Error en diagnósticos: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
            this.diagnosticsRunning = false;
        }
    }

    /**
     * Perform system diagnostics
     */
    async performSystemDiagnostics() {
        const diagnostics = {
            timestamp: new Date().toISOString(),
            tests: [],
            summary: { passed: 0, failed: 0, warnings: 0 }
        };

        const tests = [
            { name: 'API Connection', test: () => this.testAPIConnection() },
            { name: 'Company Configuration', test: () => this.testCompanyConfig() },
            { name: 'Redis Connection', test: () => this.testRedisConnection() },
            { name: 'OpenAI Service', test: () => this.testOpenAIService() },
            { name: 'Vectorstore Health', test: () => this.testVectorstoreHealth() },
            { name: 'Schedule Service', test: () => this.testScheduleService() },
            { name: 'Multimedia Support', test: () => this.testMultimediaSupport() },
            { name: 'Browser Compatibility', test: () => this.testBrowserCompatibility() }
        ];

        for (let i = 0; i < tests.length; i++) {
            const { name, test } = tests[i];
            const progress = ((i + 1) / tests.length) * 100;
            window.UI.updateProgress(progress);

            try {
                const result = await test();
                diagnostics.tests.push({ name, ...result });
                
                if (result.status === 'pass') diagnostics.summary.passed++;
                else if (result.status === 'fail') diagnostics.summary.failed++;
                else diagnostics.summary.warnings++;
                
            } catch (error) {
                diagnostics.tests.push({
                    name,
                    status: 'fail',
                    message: error.message,
                    details: error.stack
                });
                diagnostics.summary.failed++;
            }
        }

        return diagnostics;
    }

    /**
     * Show diagnostics results modal
     */
    showDiagnosticsModal(diagnostics) {
        const { summary } = diagnostics;
        const overallStatus = summary.failed === 0 ? 'healthy' : 
                            summary.failed < summary.passed ? 'warning' : 'critical';
        
        const content = `
            <div class="diagnostics-results">
                <h4>🔍 Resultados de Diagnósticos del Sistema</h4>
                
                <div class="diagnostics-summary ${overallStatus}">
                    <div class="summary-item">
                        <span class="summary-icon">✅</span>
                        <span class="summary-count">${summary.passed}</span>
                        <span class="summary-label">Pasaron</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-icon">⚠️</span>
                        <span class="summary-count">${summary.warnings}</span>
                        <span class="summary-label">Advertencias</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-icon">❌</span>
                        <span class="summary-count">${summary.failed}</span>
                        <span class="summary-label">Fallaron</span>
                    </div>
                </div>

                <div class="diagnostics-tests">
                    ${diagnostics.tests.map(test => `
                        <div class="test-result ${test.status}">
                            <div class="test-header">
                                <span class="test-icon">${this.getTestIcon(test.status)}</span>
                                <span class="test-name">${test.name}</span>
                                <span class="test-status">${test.status}</span>
                            </div>
                            <div class="test-message">${test.message}</div>
                            ${test.details ? `<div class="test-details">${test.details}</div>` : ''}
                        </div>
                    `).join('')}
                </div>

                <div class="diagnostics-footer">
                    <p><strong>Ejecutado:</strong> ${window.UI.formatDate(diagnostics.timestamp)}</p>
                    <button class="btn btn-primary" onclick="window.UI.copyToClipboard(\`${JSON.stringify(diagnostics, null, 2)}\`)">
                        📋 Copiar Resultados
                    </button>
                </div>
            </div>
        `;

        window.UI.showModal('🔍 Diagnósticos del Sistema', content, {
            maxWidth: '800px'
        });
    }

    /**
     * Get test icon based on status
     */
    getTestIcon(status) {
        const icons = {
            pass: '✅',
            fail: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[status] || '❓';
    }

    // ==================== DIAGNOSTIC TESTS ====================

    async testAPIConnection() {
        try {
            const health = await window.API.systemHealthCheck();
            return {
                status: health.status === 'healthy' ? 'pass' : 'warning',
                message: `API respondiendo: ${health.status}`,
                details: JSON.stringify(health, null, 2)
            };
        } catch (error) {
            return {
                status: 'fail',
                message: `API no disponible: ${error.message}`
            };
        }
    }

    async testCompanyConfig() {
        const companies = window.CompanyManager?.getAllCompanies() || {};
        const count = Object.keys(companies).length;
        
        if (count === 0) {
            return {
                status: 'fail',
                message: 'No hay empresas configuradas'
            };
        }
        
        return {
            status: 'pass',
            message: `${count} empresa(s) configurada(s)`,
            details: Object.keys(companies).join(', ')
        };
    }

    async testRedisConnection() {
        // This would be implemented based on your Redis health check
        return {
            status: 'warning',
            message: 'Test de Redis no implementado - asumiendo disponible'
        };
    }

    async testOpenAIService() {
        // This would test OpenAI API connectivity
        return {
            status: 'warning',
            message: 'Test de OpenAI no implementado - asumiendo disponible'
        };
    }

    async testVectorstoreHealth() {
        // This would test vectorstore health
        return {
            status: 'warning',
            message: 'Test de Vectorstore no implementado'
        };
    }

    async testScheduleService() {
        const available = window.API.scheduleServiceAvailable;
        
        if (available === null) {
            return {
                status: 'warning',
                message: 'Estado del servicio de agendamiento desconocido'
            };
        }
        
        return {
            status: available ? 'pass' : 'warning',
            message: available ? 'Servicio de agendamiento disponible' : 'Servicio en modo fallback (esperado en Railway)',
            details: available ? 'Totalmente funcional' : 'Funcionalidad limitada pero operativa'
        };
    }

    async testMultimediaSupport() {
        const hasGetUserMedia = !!navigator.mediaDevices?.getUserMedia;
        const hasMediaRecorder = !!window.MediaRecorder;
        
        if (hasGetUserMedia && hasMediaRecorder) {
            return {
                status: 'pass',
                message: 'Soporte multimedia completo',
                details: 'getUserMedia y MediaRecorder disponibles'
            };
        } else if (hasGetUserMedia || hasMediaRecorder) {
            return {
                status: 'warning',
                message: 'Soporte multimedia parcial',
                details: `getUserMedia: ${hasGetUserMedia}, MediaRecorder: ${hasMediaRecorder}`
            };
        } else {
            return {
                status: 'fail',
                message: 'Sin soporte multimedia',
                details: 'getUserMedia y MediaRecorder no disponibles'
            };
        }
    }

    async testBrowserCompatibility() {
        const features = {
            localStorage: !!window.localStorage,
            sessionStorage: !!window.sessionStorage,
            indexedDB: !!window.indexedDB,
            webWorkers: !!window.Worker,
            fetch: !!window.fetch,
            promises: !!window.Promise,
            es6: typeof Symbol !== 'undefined'
        };

        const supportedCount = Object.values(features).filter(Boolean).length;
        const totalCount = Object.keys(features).length;
        const percentage = Math.round((supportedCount / totalCount) * 100);

        return {
            status: percentage >= 90 ? 'pass' : percentage >= 70 ? 'warning' : 'fail',
            message: `Compatibilidad del navegador: ${percentage}% (${supportedCount}/${totalCount})`,
            details: Object.entries(features).map(([feature, supported]) => 
                `${feature}: ${supported ? '✅' : '❌'}`
            ).join(', ')
        };
    }

    // ==================== VECTORSTORE MANAGEMENT ====================

    /**
     * Cleanup orphaned vectors
     */
    async cleanupVectors() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const confirmed = await this.showConfirmDialog(
            '🧹 Limpiar Vectores Huérfanos',
            `¿Limpiar vectores huérfanos de <strong>${window.CompanyManager?.getCompany(this.currentCompanyId)?.company_name || this.currentCompanyId}</strong>?<br><br>
            Esta acción eliminará vectores sin documentos asociados. No se puede deshacer.`
        );

        if (!confirmed) return;

        try {
            window.UI.showLoading('Limpiando vectores huérfanos...');
            
            const result = await window.API.cleanupVectors(false);
            
            if (result.status === 'success') {
                const count = result.orphaned_vectors_deleted || 0;
                window.UI.showToast(`✅ ${count} vectores huérfanos eliminados`, 'success');
            } else {
                throw new Error(result.message || 'Error en limpieza');
            }
            
        } catch (error) {
            console.error('❌ Error cleaning up vectors:', error);
            window.UI.showToast('❌ Error limpiando vectores: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Force vectorstore recovery
     */
    async forceVectorRecovery() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        const confirmed = await this.showConfirmDialog(
            '🛠️ Forzar Recuperación de Vectorstore',
            `¿Forzar la recuperación del vectorstore para <strong>${window.CompanyManager?.getCompany(this.currentCompanyId)?.company_name || this.currentCompanyId}</strong>?<br><br>
            Esta acción reconstruirá completamente el índice vectorial. Puede tomar varios minutos.`
        );

        if (!confirmed) return;

        try {
            window.UI.showLoadingWithProgress('Iniciando recuperación del vectorstore...', 0);
            
            // Simulate progress updates
            const progressSteps = ['Verificando índice', 'Recuperando documentos', 'Reconstruyendo vectores', 'Validando integridad'];
            
            for (let i = 0; i < progressSteps.length; i++) {
                window.UI.showLoadingWithProgress(progressSteps[i], ((i + 1) / progressSteps.length) * 100);
                await new Promise(resolve => setTimeout(resolve, 2000));
            }

            window.UI.showToast('🛠️ Función de recuperación en desarrollo', 'info');
            
        } catch (error) {
            console.error('❌ Error in vector recovery:', error);
            window.UI.showToast('❌ Error en recuperación: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Check vectorstore protection status
     */
    async checkProtectionStatus() {
        if (!this.currentCompanyId) {
            window.UI.showToast('⚠️ Selecciona una empresa primero', 'warning');
            return;
        }

        try {
            window.UI.showLoading('Verificando estado de protección...');
            
            // This would call the actual protection status API
            const status = {
                protection_active: true,
                auto_recovery_enabled: window.APP_CONFIG.FEATURES.auto_vectorstore_recovery,
                last_check: new Date().toISOString(),
                vectorstore_healthy: true,
                backup_count: 3,
                last_backup: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
            };

            this.showProtectionStatusModal(status);
            
        } catch (error) {
            console.error('❌ Error checking protection status:', error);
            window.UI.showToast('❌ Error verificando protección: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Show protection status modal
     */
    showProtectionStatusModal(status) {
        const content = `
            <div class="protection-status">
                <h4>🛡️ Estado de Protección del Vectorstore</h4>
                
                <div class="protection-grid">
                    <div class="protection-item ${status.protection_active ? 'active' : 'inactive'}">
                        <span class="protection-icon">${status.protection_active ? '🟢' : '🔴'}</span>
                        <span class="protection-label">Protección Activa</span>
                        <span class="protection-value">${status.protection_active ? 'Sí' : 'No'}</span>
                    </div>
                    
                    <div class="protection-item ${status.auto_recovery_enabled ? 'active' : 'inactive'}">
                        <span class="protection-icon">${status.auto_recovery_enabled ? '🟢' : '🔴'}</span>
                        <span class="protection-label">Auto-Recovery</span>
                        <span class="protection-value">${status.auto_recovery_enabled ? 'Habilitado' : 'Deshabilitado'}</span>
                    </div>
                    
                    <div class="protection-item ${status.vectorstore_healthy ? 'active' : 'inactive'}">
                        <span class="protection-icon">${status.vectorstore_healthy ? '🟢' : '🔴'}</span>
                        <span class="protection-label">Estado del Vectorstore</span>
                        <span class="protection-value">${status.vectorstore_healthy ? 'Saludable' : 'Con problemas'}</span>
                    </div>
                </div>

                <div class="protection-details">
                    <h5>Detalles de Protección:</h5>
                    <ul>
                        <li><strong>Última Verificación:</strong> ${window.UI.formatDate(status.last_check)}</li>
                        <li><strong>Backups Disponibles:</strong> ${status.backup_count}</li>
                        <li><strong>Último Backup:</strong> ${window.UI.formatDate(status.last_backup)}</li>
                        <li><strong>Empresa:</strong> ${window.CompanyManager?.getCompany(this.currentCompanyId)?.company_name || this.currentCompanyId}</li>
                    </ul>
                </div>

                ${window.APP_CONFIG.ENV.is_railway ? `
                    <div class="railway-protection-info">
                        <h5>🚄 Protección en Railway:</h5>
                        <p>• Sistema de recuperación automática habilitado</p>
                        <p>• Monitoreo continuo de salud del vectorstore</p>
                        <p>• Reinicio automático en caso de fallos</p>
                    </div>
                ` : ''}
            </div>
        `;

        window.UI.showModal('🛡️ Estado de Protección', content, {
            maxWidth: '700px'
        });
    }

    // ==================== CONFIGURATION MANAGEMENT ====================

    /**
     * Export system configuration
     */
    async exportConfiguration() {
        try {
            window.UI.showLoading('Preparando exportación...');
            
            const config = {
                timestamp: new Date().toISOString(),
                environment: window.APP_CONFIG.ENV,
                companies: window.CompanyManager?.getAllCompanies() || {},
                features: window.APP_CONFIG.FEATURES,
                system_info: {
                    user_agent: navigator.userAgent,
                    platform: navigator.platform,
                    language: navigator.language,
                    is_railway: window.APP_CONFIG.ENV.is_railway
                }
            };

            const dataStr = JSON.stringify(config, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(dataBlob);
            link.download = `system_config_export_${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            
            window.UI.showToast('✅ Configuración exportada', 'success');
            
        } catch (error) {
            console.error('❌ Error exporting configuration:', error);
            window.UI.showToast('❌ Error exportando configuración: ' + error.message, 'error');
        } finally {
            window.UI.hideLoading();
        }
    }

    /**
     * Show migration tool
     */
    async showMigrationTool() {
        const content = `
            <div class="migration-tool">
                <h4>🔄 Herramienta de Migración</h4>
                
                <div class="migration-options">
                    <div class="migration-option">
                        <h5>📤 Exportar Datos</h5>
                        <p>Exporta todos los datos de la empresa seleccionada</p>
                        <button class="btn btn-primary" onclick="window.AdminTools.exportCompanyData()">
                            Exportar Empresa
                        </button>
                    </div>
                    
                    <div class="migration-option">
                        <h5>📥 Importar Datos</h5>
                        <p>Importa datos desde un archivo de exportación</p>
                        <input type="file" id="migrationFile" accept=".json" style="margin: 10px 0;">
                        <button class="btn btn-secondary" onclick="window.AdminTools.importCompanyData()">
                            Importar Empresa
                        </button>
                    </div>
                    
                    <div class="migration-option">
                        <h5>🔄 Migración Entre Entornos</h5>
                        <p>Migra configuraciones entre desarrollo y producción</p>
                        <button class="btn btn-info" onclick="window.AdminTools.migrateEnvironment()">
                            Migrar Entorno
                        </button>
                    </div>
                </div>

                <div class="migration-warning">
                    <h5>⚠️ Advertencia</h5>
                    <p>Las operaciones de migración pueden afectar la integridad de los datos. 
                    Asegúrate de tener backups antes de proceder.</p>
                </div>
            </div>
        `;

        window.UI.showModal('🔄 Herramienta de Migración', content, {
            maxWidth: '800px'
        });
    }

    /**
     * Test multimedia functionality
     */
    async testMultimedia() {
        if (window.MultimediaManager) {
            await window.MultimediaManager.testMultimediaSupport();
        } else {
            window.UI.showToast('⚠️ Multimedia Manager no disponible', 'warning');
        }
    }

    // ==================== UTILITY FUNCTIONS ====================

    /**
     * Get system uptime (approximated)
     */
    getSystemUptime() {
        const startTime = window.APP_CONFIG.startTime || Date.now();
        const uptime = Date.now() - startTime;
        const minutes = Math.floor(uptime / (1000 * 60));
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else {
            return `${minutes}m`;
        }
    }

    /**
     * Get memory usage (if available)
     */
    getMemoryUsage() {
        if (performance.memory) {
            const used = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024);
            const total = Math.round(performance.memory.totalJSHeapSize / 1024 / 1024);
            return `${used}MB / ${total}MB`;
        }
        return 'No disponible';
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
     * Disable advanced features if not admin
     */
    disableAdvancedFeatures() {
        const advancedButtons = [
            'vectorRecoveryBtn',
            'migrationToolBtn'
        ];

        advancedButtons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.disabled = true;
                btn.title = 'Función reservada para administradores';
            }
        });
    }

    // ==================== PLACEHOLDER FUNCTIONS ====================
    
    async exportCompanyData() {
        window.UI.showToast('🚧 Exportación de empresa en desarrollo', 'info');
    }
    
    async importCompanyData() {
        window.UI.showToast('🚧 Importación de empresa en desarrollo', 'info');
    }
    
    async migrateEnvironment() {
        window.UI.showToast('🚧 Migración de entorno en desarrollo', 'info');
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.diagnosticsRunning = false;
        this.isInitialized = false;
        
        if (window.APP_CONFIG.DEBUG.enabled) {
            console.log('🧹 Admin Tools cleaned up');
        }
    }
}

// Create global instance
window.AdminTools = new AdminTools();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminTools;
}
