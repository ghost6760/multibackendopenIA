// scripts/config.js - Configuration Module (COMPLETE DEBUG VERSION)
'use strict';

/**
 * Global Configuration for Multi-Tenant Admin Panel
 * COMPLETE VERSION - Ensures all required objects are defined
 */

// Ensure this loads first and defines all required global objects
(function initializeGlobalConfig() {
    console.log('🔧 Initializing global configuration...');
    
    // Define APP_CONFIG first
    window.APP_CONFIG = {
        // Environment Configuration
        ENV: {
            is_development: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
            is_railway: window.location.hostname.includes('railway') || window.location.hostname.includes('.app') || window.location.hostname.includes('up.railway'),
            is_production: window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
        },
        
        // API Configuration
        API: {
            BASE_URL: window.location.origin,
            TIMEOUTS: {
                default: 10000,
                upload: 30000,
                health_check: 5000
            }
        },
        
        // Debug Configuration
        DEBUG: {
            enabled: window.location.hostname === 'localhost' || window.location.search.includes('debug=true'),
            verbose_errors: window.location.search.includes('verbose=true'),
            log_api_calls: window.location.search.includes('debug=true'),
            railway_debug: {
                log_health_checks: true,
                log_service_failures: true
            }
        },
        
        // UI Configuration
        UI: {
            max_toast_count: 5,
            toast_duration: 5000,
            loading_timeout: 30000
        },
        
        // Multi-tenant Configuration
        TENANT: {
            company_context_header: 'X-Company-ID',
            auto_select_first_company: true
        },
        
        // Railway Optimizations (MISSING IN ORIGINAL)
        RAILWAY_OPTIMIZATIONS: {
            graceful_degradation: {
                schedule_service: true
            }
        },
        
        // Railway Config (MISSING IN ORIGINAL)
        RAILWAY: {
            retry_delay: 1000
        },
        
        // Performance Config (MISSING IN ORIGINAL)
        PERFORMANCE: {
            cache_duration: 300000 // 5 minutes
        }
    };

    console.log('✅ APP_CONFIG initialized:', window.APP_CONFIG);

    // Basic UI Manager (simplified version to prevent errors)
    window.UI = {
        showLoading: function(message = 'Cargando...') {
            console.log('🔄 Loading:', message);
            const overlay = document.getElementById('loadingOverlay');
            const messageEl = document.getElementById('loadingMessage');
            
            if (overlay) {
                overlay.style.display = 'flex';
                if (messageEl) messageEl.textContent = message;
            } else {
                console.warn('⚠️ Loading overlay element not found');
            }
        },
        
        hideLoading: function() {
            console.log('✅ Loading complete');
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            } else {
                console.warn('⚠️ Loading overlay element not found');
            }
        },
        
        showToast: function(message, type = 'info') {
            console.log(`📢 Toast (${type}):`, message);
            
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 20px;
                background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : type === 'warning' ? '#ffc107' : '#007bff'};
                color: ${type === 'warning' ? '#000' : '#fff'};
                border-radius: 4px;
                z-index: 10000;
                max-width: 300px;
                word-wrap: break-word;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;
            `;
            
            // Add to container or body
            const container = document.getElementById('toastContainer') || document.body;
            container.appendChild(toast);
            
            // Auto remove
            setTimeout(() => {
                if (toast && toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 5000);
        },
        
        // Additional UI methods that might be called
        showConfirmModal: function(title, message, onConfirm, onCancel) {
            const result = confirm(`${title}\n\n${message}`);
            if (result && onConfirm) onConfirm();
            if (!result && onCancel) onCancel();
            return result;
        },
        
        // Mobile/Tablet detection methods
        isMobile: function() {
            return window.innerWidth <= 768;
        },
        
        isTablet: function() {
            return window.innerWidth > 768 && window.innerWidth <= 1024;
        }
    };

    console.log('✅ UI manager initialized');

    // Basic API Manager (simplified version to prevent errors)
    window.API = {
        baseURL: window.location.origin,
        currentCompanyId: null,
        scheduleServiceAvailable: false,
        timeouts: window.APP_CONFIG.API.TIMEOUTS,
        
        setCompanyId: function(companyId) {
            this.currentCompanyId = companyId;
            console.log('🏢 Company context set to:', companyId);
        },
        
        makeRequest: async function(endpoint, options = {}) {
            // FIX: Construir URL correctamente
            let url;
            if (endpoint.startsWith('http')) {
                url = endpoint;
            } else if (endpoint.startsWith('/')) {
                // Para rutas absolutas como '/health'
                url = `${this.baseURL}${endpoint}`;
            } else {
                // Para rutas relativas como 'companies' -> '/api/companies'
                url = `${this.baseURL}/api/${endpoint}`;
            }
            
            console.log(`🌐 Making API request to: ${url}`);
            
            try {
                const response = await fetch(url, {
                    timeout: this.timeouts.default,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Company-ID': this.currentCompanyId || ''
                    },
                    ...options
                });
                
                console.log(`✅ API Response: ${response.status} for ${url}`);
                
                if (!response.ok) {
                    throw new Error(`API Error: ${response.status} ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('📋 API Response data:', data);
                
                return data;
            } catch (error) {
                console.error(`❌ API Error for ${url}:`, error);
                throw error;
            }
        },
        
        getCompanies: async function() {
            console.log('🏢 Fetching companies...');
            try {
                return await this.makeRequest('companies');
            } catch (error) {
                console.warn('Companies API failed, using fallback');
                return {
                    status: 'success',
                    companies: {
                        'fallback': {
                            company_name: 'Modo de Emergencia',
                            services: ['Sistema en modo fallback'],
                            status: 'warning'
                        }
                    },
                    total_companies: 1
                };
            }
        },
        
        getCompanyStatus: async function(companyId) {
            console.log('📊 Getting company status for:', companyId);
            try {
                return await this.makeRequest(`status/${companyId}`);
            } catch (error) {
                console.warn('Company status failed');
                return {
                    status: 'warning',
                    data: {
                        company_id: companyId,
                        status: 'unknown'
                    }
                };
            }
        },
        
        systemHealthCheck: async function() {
            console.log('🏥 Running system health check...');
            try {
                return await this.makeRequest('/health');
            } catch (error) {
                console.warn('Health check failed');
                return {
                    status: 'degraded',
                    message: 'Health check unavailable'
                };
            }
        }
    };

    console.log('✅ API manager initialized');

    // Create empty CompanyManager if not defined elsewhere
    if (!window.CompanyManager) {
        window.CompanyManager = {
            companies: {},
            currentCompanyId: null,
            init: async function() {
                console.log('🏢 CompanyManager stub initialized');
            },
            loadCompanies: async function() {
                console.log('🏢 Loading companies via CompanyManager');
                return window.API.getCompanies();
            }
        };
        console.log('✅ CompanyManager stub created');
    }

    // Create empty AdminTools if not defined elsewhere  
    if (!window.AdminTools) {
        window.AdminTools = {
            init: async function() {
                console.log('⚙️ AdminTools stub initialized');
            }
        };
        console.log('✅ AdminTools stub created');
    }

    // Log successful config initialization
    console.log('✅ Emergency config initialization complete');
    console.log('🔧 Environment detected:', {
        isDev: window.APP_CONFIG.ENV.is_development,
        isRailway: window.APP_CONFIG.ENV.is_railway,
        isProd: window.APP_CONFIG.ENV.is_production,
        hostname: window.location.hostname
    });
    
    // Mark as ready
    window.CONFIG_READY = true;
    console.log('🎉 CONFIG_READY = true');
    
})();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.APP_CONFIG;
}

console.log('🎯 Config module loaded successfully');

// Add a global error handler to catch any remaining issues
window.addEventListener('error', function(event) {
    console.error('🚨 Global Error Caught:', {
        message: event.error?.message || event.message,
        filename: event.filename,
        lineno: event.lineno,
        error: event.error
    });
});

console.log('🛡️ Global error handler installed');
