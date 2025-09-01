// scripts/config.js - Configuration Module
'use strict';

/**
 * Global Configuration for Multi-Tenant Chatbot Admin Panel
 */
window.APP_CONFIG = {
    // API Configuration
    API: {
        // Use relative URL for Railway compatibility
        BASE_URL: window.location.origin + '/api/',
        ENDPOINTS: {
            companies: 'companies',
            health: 'health',
            status: 'status',
            documents: 'documents',
            chat: 'chat',
            multimedia: 'multimedia',
            admin: 'admin'
        },
        TIMEOUTS: {
            default: 30000,
            upload: 120000,
            health_check: 10000
        }
    },

    // Railway Production Configuration
    RAILWAY: {
        // Railway assigns dynamic ports, use environment detection
        is_production: window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1',
        health_check_url: '/health', // Relative URL for Railway
        max_retries: 3,
        retry_delay: 2000
    },

    // Google Calendar Integration
    GOOGLE_CALENDAR: {
        enabled: true,
        scopes: ['https://www.googleapis.com/auth/calendar'],
        discovery_doc: 'https://www.googleapis.com/discovery/v1/apis/calendar/v3/rest',
        timezone: 'America/Bogota'
    },

    // Extended Configuration Support
    EXTENDED_FEATURES: {
        scheduling: true,
        multimedia: true,
        voice_recognition: true,
        image_analysis: true,
        advanced_analytics: true,
        auto_recovery: true
    },

    // UI Configuration
    UI: {
        toast_duration: 5000,
        loading_timeout: 60000,
        animation_duration: 300,
        max_toast_count: 5,
        debounce_delay: 300
    },

    // File Upload Configuration
    UPLOAD: {
        max_file_size: 10 * 1024 * 1024, // 10MB
        allowed_types: {
            documents: ['.txt', '.md', '.docx', '.pdf'],
            images: ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            audio: ['.mp3', '.wav', '.ogg', '.m4a']
        },
        chunk_size: 1024 * 1024 // 1MB chunks for large files
    },

    // Multi-tenant Configuration
    TENANT: {
        default_company_id: null,
        company_context_header: 'X-Company-ID',
        company_switching_enabled: true
    },

    // Error Handling
    ERROR: {
        retry_attempts: 3,
        retry_delay: 1000,
        show_stack_trace: false, // Set to true for development
        log_errors: true
    },

    // Performance Configuration
    PERFORMANCE: {
        enable_caching: true,
        cache_duration: 5 * 60 * 1000, // 5 minutes
        lazy_loading: true,
        debounce_search: true
    },

    // Security Configuration
    SECURITY: {
        csrf_protection: true,
        sanitize_inputs: true,
        validate_file_types: true
    }
};

/**
 * Environment Detection and Configuration Adjustment
 */
window.APP_CONFIG.ENV = {
    is_development: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
    is_railway: window.location.hostname.includes('railway.app') || window.location.hostname.includes('up.railway.app'),
    is_production: window.location.protocol === 'https:' && !window.location.hostname.includes('localhost'),
    
    // Dynamic port detection for Railway
    get_api_base() {
        if (this.is_railway || this.is_production) {
            return window.location.origin + '/api/';
        } else {
            // Development - check if custom port is being used
            const port = window.location.port || '8080';
            return `${window.location.protocol}//${window.location.hostname}:${port}/api/`;
        }
    }
};

// Update API base URL based on environment
window.APP_CONFIG.API.BASE_URL = window.APP_CONFIG.ENV.get_api_base();

/**
 * Feature Flags for Extended Configurations
 */
window.APP_CONFIG.FEATURES = {
    // Google Calendar Integration
    google_calendar_enabled: true,
    
    // Schedule Service Integration 
    schedule_service_enabled: true,
    schedule_service_fallback: true, // Fallback when service is unavailable
    
    // Extended Company Configuration
    extended_config_enabled: true,
    treatment_scheduling: true,
    agenda_management: true,
    
    // Advanced Features
    auto_vectorstore_recovery: true,
    real_time_notifications: true,
    advanced_analytics: true,
    
    // Multimedia Features
    voice_processing: true,
    image_processing: true,
    camera_capture: true,
    
    // Admin Features
    system_diagnostics: true,
    configuration_export: true,
    migration_tools: true,
    
    // Railway Specific Features
    railway_health_checks: true,
    dynamic_port_handling: true,
    production_error_handling: true
};

/**
 * Railway Production Optimizations
 */
window.APP_CONFIG.RAILWAY_OPTIMIZATIONS = {
    // Handle Railway's health check endpoint
    health_check_path: '/health',
    
    // Use Railway's assigned PORT environment variable
    use_dynamic_port: true,
    
    // Optimize for Railway's resource constraints
    reduce_polling_frequency: true,
    
    // Enable production error tracking
    enhanced_error_logging: true,
    
    // Railway-specific timeouts
    connection_timeout: 15000,
    request_timeout: 30000,
    
    // Graceful degradation when services are unavailable
    graceful_degradation: {
        schedule_service: true, // Continue working if schedule service (port 4040) is down
        vectorstore: true,      // Handle vectorstore connection issues
        external_apis: true     // Handle external API failures
    }
};

/**
 * Google Calendar Extended Configuration
 */
window.APP_CONFIG.GOOGLE_CALENDAR_CONFIG = {
    // Service Account Configuration
    service_account: {
        enabled: true,
        credentials_path: '/app/credentials/google_service_account.json'
    },
    
    // Calendar Settings
    calendar_settings: {
        primary_calendar_id: 'primary',
        timezone: 'America/Bogota',
        default_event_duration: 60, // minutes
        reminder_settings: {
            email: 24 * 60, // 24 hours in minutes
            popup: 60       // 1 hour in minutes
        }
    },
    
    // Booking Configuration
    booking_settings: {
        advance_booking_days: 30,
        business_hours: {
            start: '08:00',
            end: '18:00'
        },
        blocked_days: ['sunday'], // Days when no appointments are allowed
        minimum_booking_notice: 24 // hours
    }
};

/**
 * Debug Configuration
 */
window.APP_CONFIG.DEBUG = {
    enabled: window.APP_CONFIG.ENV.is_development,
    log_api_calls: window.APP_CONFIG.ENV.is_development,
    show_performance_metrics: false,
    verbose_errors: window.APP_CONFIG.ENV.is_development,
    
    // Railway Production Debugging
    railway_debug: {
        log_health_checks: true,
        log_port_detection: true,
        log_service_failures: true
    }
};

/**
 * Initialize Configuration Based on Environment
 */
function initializeConfig() {
    // Log configuration in development
    if (window.APP_CONFIG.DEBUG.enabled) {
        console.group('🔧 App Configuration');
        console.log('Environment:', window.APP_CONFIG.ENV);
        console.log('API Base URL:', window.APP_CONFIG.API.BASE_URL);
        console.log('Features Enabled:', Object.keys(window.APP_CONFIG.FEATURES).filter(key => window.APP_CONFIG.FEATURES[key]));
        console.log('Railway Mode:', window.APP_CONFIG.ENV.is_railway);
        console.groupEnd();
    }

    // Railway-specific adjustments
    if (window.APP_CONFIG.ENV.is_railway || window.APP_CONFIG.ENV.is_production) {
        // Reduce polling frequency for production
        window.APP_CONFIG.UI.debounce_delay = 500;
        
        // Increase timeouts for Railway
        window.APP_CONFIG.API.TIMEOUTS.default = 45000;
        window.APP_CONFIG.API.TIMEOUTS.upload = 180000;
        
        // Enable graceful degradation
        window.APP_CONFIG.RAILWAY_OPTIMIZATIONS.graceful_degradation.schedule_service = true;
    }

    // Configure error handling based on environment
    if (window.APP_CONFIG.ENV.is_production) {
        window.APP_CONFIG.ERROR.show_stack_trace = false;
        window.APP_CONFIG.DEBUG.enabled = false;
        window.APP_CONFIG.DEBUG.log_api_calls = false;
    }
}

/**
 * Railway Health Check Configuration
 * Handles the connection refused error on port 4040
 */
window.APP_CONFIG.HEALTH_CHECK = {
    // Primary health check (main app)
    primary: {
        endpoint: '/health',
        timeout: 10000,
        retry_attempts: 3
    },
    
    // Schedule service health check (optional)
    schedule_service: {
        endpoint: '/health', // Will try to connect to schedule service
        timeout: 5000,
        retry_attempts: 1,
        optional: true, // Don't fail if this service is unavailable
        fallback_enabled: true
    },
    
    // Component health checks
    components: {
        redis: { timeout: 3000, critical: true },
        openai: { timeout: 5000, critical: true },
        vectorstore: { timeout: 8000, critical: true },
        schedule_service: { timeout: 2000, critical: false } // Not critical - can continue without it
    }
};

/**
 * Extended Company Configuration Schema
 */
window.APP_CONFIG.COMPANY_SCHEMA = {
    basic: {
        company_id: 'string',
        company_name: 'string',
        services: 'array',
        vectorstore_index: 'string',
        redis_prefix: 'string'
    },
    
    extended: {
        integration_type: 'string', // 'google_calendar', 'calendly', 'webhook'
        integration_config: 'object',
        treatments: 'array',
        agendas: 'array',
        business_settings: 'object'
    },
    
    google_calendar: {
        credentials_path: 'string',
        calendar_id: 'string',
        calendar_timezone: 'string',
        service_account_email: 'string'
    }
};

// Initialize configuration on load
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeConfig);
    } else {
        initializeConfig();
    }
}

// Export for Node.js environments (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.APP_CONFIG;
}
