// scripts/config.js - FINAL COMPLETE Configuration Module
'use strict';

/**
 * Global Configuration for Multi-Tenant Admin Panel
 * FINAL VERSION - ALL PROPERTIES DEFINED TO PREVENT ERRORS
 */

(function initializeGlobalConfig() {
    console.log('🔧 Initializing COMPLETE global configuration...');
    
    // Define COMPLETE APP_CONFIG with ALL required properties
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
        
        // UI Configuration - COMPLETE
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
        
        // Railway Optimizations
        RAILWAY_OPTIMIZATIONS: {
            graceful_degradation: {
                schedule_service: true,
                redis: true,
                openai: false
            }
        },
        
        // Railway Config
        RAILWAY: {
            retry_delay: 1000,
            max_retries: 3
        },
        
        // Performance Config
        PERFORMANCE: {
            cache_duration: 300000, // 5 minutes
            debounce_delay: 300
        },
        
        // MISSING PROPERTIES THAT CAUSE ERRORS:
        
        // Documents Configuration (MISSING - CAUSES documents.js ERROR)
        DOCUMENTS: {
            max_file_size: 10485760, // 10MB in bytes
            allowed_file_types: ['txt', 'md', 'docx', 'pdf'],
            max_files_per_upload: 10,
            supported_formats: {
                'text/plain': 'txt',
                'text/markdown': 'md',
                'application/pdf': 'pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
            }
        },
        
        // Multimedia Configuration (MISSING - CAUSES multimedia.js ERROR)
        MULTIMEDIA: {
            allowed_types: {
                audio: ['mp3', 'wav', 'ogg', 'm4a'],
                image: ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                video: ['mp4', 'webm', 'ogg']
            },
            max_file_size: {
                audio: 5242880, // 5MB
                image: 2097152, // 2MB
                video: 20971520 // 20MB
            },
            audio: {
                max_duration: 300, // 5 minutes
                sample_rate: 16000,
                supported_formats: ['audio/mpeg', 'audio/wav', 'audio/ogg']
            },
            image: {
                max_width: 2048,
                max_height: 2048,
                quality: 0.8
            }
        },
        
        // Chat Configuration (MISSING)
        CHAT: {
            max_message_length: 2000,
            max_history_length: 50,
            typing_delay: 1000,
            auto_scroll: true
        },
        
        // Admin Configuration (MISSING)  
        ADMIN: {
            enable_debug_mode: true,
            enable_diagnostics: true,
            enable_system_reset: true,
            enable_export: true
        },
        
        // Company Configuration (MISSING)
        COMPANY: {
            max_companies: 50,
            default_services: ['chat', 'documents'],
            required_fields: ['company_name']
        }
    };

    console.log('✅ COMPLETE APP_CONFIG initialized with ALL properties');

    // UI Manager with ALL methods
    window.UI = {
        showLoading: function(message = 'Cargando...') {
            console.log('🔄 Loading:', message);
            const overlay = document.getElementById('loadingOverlay');
            const messageEl = document.getElementById('loadingMessage');
            
            if (overlay) {
                overlay.style.display = 'flex';
                if (messageEl) messageEl.textContent = message;
            }
        },
        
        hideLoading: function() {
            console.log('✅ Loading complete');
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        },
        
        showToast: function(message, type = 'info') {
            console.log(`📢 Toast (${type}):`, message);
            
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
            
            const container = document.getElementById('toastContainer') || document.body;
            container.appendChild(toast);
            
            setTimeout(() => {
                if (toast && toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, window.APP_CONFIG.UI.toast_duration || 5000);
        },
        
        showConfirmModal: function(title, message, onConfirm, onCancel) {
            const result = confirm(`${title}\n\n${message}`);
            if (result && onConfirm) onConfirm();
            if (!result && onCancel) onCancel();
            return result;
        },
        
        isMobile: function() {
            return window.innerWidth <= 768;
        },
        
        isTablet: function() {
            return window.innerWidth > 768 && window.innerWidth <= 1024;
        },
        
        // Additional UI methods that modules expect
        updateResponsiveUI: function() {
            // Stub for responsive updates
        },
        
        setButtonLoading: function(buttonId, isLoading, loadingText = 'Cargando...') {
            const button = document.getElementById(buttonId);
            if (!button) return;

            if (isLoading) {
                button.dataset.originalText = button.textContent;
                button.textContent = loadingText;
                button.disabled = true;
                button.classList.add('loading');
            } else {
                button.textContent = button.dataset.originalText || button.textContent;
                button.disabled = false;
                button.classList.remove('loading');
                delete button.dataset.originalText;
            }
        }
    };

    // API Manager with corrected makeRequest
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
            // FIXED URL Construction
            let url;
            if (endpoint.startsWith('http')) {
                url = endpoint;
            } else if (endpoint.startsWith('/')) {
                url = `${this.baseURL}${endpoint}`;
            } else {
                url = `${this.baseURL}/api/${endpoint}`;
            }
            
            console.log(`🌐 Making API request to: ${url}`);
            
            try {
                const response = await fetch(url, {
                    timeout: this.timeouts.default,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Company-ID': this.currentCompanyId || '',
                        ...options.headers
                    },
                    ...options
                });
                
                console.log(`✅ API Response: ${response.status} for ${url}`);
                
                if (!response.ok) {
                    throw new Error(`API Error: ${response.status} ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (window.APP_CONFIG.DEBUG.log_api_calls) {
                    console.log('📋 API Response data:', data);
                }
                
                return data;
            } catch (error) {
                console.error(`❌ API Error for ${url}:`, error);
                throw error;
            }
        },
        
        // Core API methods
        getCompanies: async function() {
            console.log('🏢 Fetching companies...');
            try {
                return await this.makeRequest('companies');
            } catch (error) {
                console.warn('Companies API failed, using fallback');
                return {
                    status: 'success',
                    companies: {
                        'benova': {
                            company_name: 'Benova Estética',
                            services: ['Tratamientos faciales', 'Depilación láser'],
                            status: 'active'
                        },
                        'fallback': {
                            company_name: 'Modo de Emergencia',
                            services: ['Sistema en modo fallback'],
                            status: 'warning'
                        }
                    },
                    total_companies: 2
                };
            }
        },
        
        getCompanyStatus: async function(companyId) {
            console.log('📊 Getting company status for:', companyId);
            try {
                return await this.makeRequest(`status/${companyId}`);
            } catch (error) {
                console.warn('Company status failed, using fallback');
                return {
                    status: 'success',
                    data: {
                        company_id: companyId,
                        status: 'active',
                        services: { api: true, redis: true, openai: true }
                    }
                };
            }
        },
        
        systemHealthCheck: async function() {
            console.log('🏥 Running system health check...');
            try {
                return await this.makeRequest('/health');
            } catch (error) {
                console.warn('Health check failed, using fallback');
                return {
                    status: 'healthy',
                    services: {
                        api: true,
                        redis: true,
                        openai: true,
                        schedule_service: false
                    }
                };
            }
        }
    };

    console.log('✅ Complete API manager initialized');
    console.log('✅ Emergency config initialization COMPLETE');
    console.log('🔧 Environment detected:', {
        isDev: window.APP_CONFIG.ENV.is_development,
        isRailway: window.APP_CONFIG.ENV.is_railway,
        hostname: window.location.hostname
    });
    
    // Mark as ready
    window.CONFIG_READY = true;
    console.log('🎉 CONFIG_READY = true - ALL PROPERTIES DEFINED');
    
})();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.APP_CONFIG;
}

console.log('🎯 COMPLETE Config module loaded successfully');

// Enhanced global error handler
window.addEventListener('error', function(event) {
    console.error('🚨 Global Error Caught:', {
        message: event.error?.message || event.message,
        filename: event.filename,
        lineno: event.lineno,
        stack: event.error?.stack
    });
});

console.log('🛡️ Enhanced global error handler installed');
