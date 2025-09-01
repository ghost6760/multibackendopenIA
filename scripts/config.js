// scripts/config.js - Configuration and Environment Setup
'use strict';

/**
 * Global Configuration for Multi-Tenant Chatbot Admin Panel
 * This file must be loaded FIRST before any other scripts
 */

// Detect environment
const isProduction = window.location.hostname !== 'localhost' && !window.location.hostname.startsWith('127.0.0.1');
const API_BASE = window.location.origin + '/';

// Global application configuration
window.APP_CONFIG = {
    // API Configuration
    API: {
        base_url: API_BASE,
        endpoints: {
            // Companies
            companies: 'companies',
            company_status: 'company/{id}/status',
            company_health: 'health/company/{id}',
            
            // Documents
            documents: 'documents',
            documents_search: 'documents/search',
            documents_bulk: 'documents/bulk',
            documents_cleanup: 'documents/cleanup',
            upload_document: 'upload-document',
            documents_vectors: 'documents/vectors',
            documents_vectors_orphaned: 'documents/vectors/orphaned',
            
            // Chat
            chat_message: 'chat/message',
            chat_history: 'chat/history/{userId}',
            conversations: 'conversations',
            conversation_test: 'conversations/{userId}/test',
            
            // Multimedia
            audio_transcribe: 'multimedia/audio/transcribe',
            image_analyze: 'multimedia/image/analyze',
            image_capture: 'multimedia/image/capture',
            process_voice: 'multimedia/process-voice',
            process_image: 'multimedia/process-image',
            
            // Configuration
            configuration: 'configuration',
            google_calendar_config: 'configuration/google-calendar',
            schedule_agent_config: 'configuration/schedule-agent',
            
            // Admin
            health: 'health',
            admin_status: 'admin/status',
            admin_reset: 'admin/system/reset',
            admin_reload_config: 'admin/companies/reload-config'
        },
        default_headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        timeout: 30000 // 30 seconds
    },
    
    // Upload Configuration
    UPLOAD: {
        max_file_size: 10 * 1024 * 1024, // 10MB
        allowed_types: {
            documents: ['.txt', '.pdf', '.docx', '.md'],
            audio: ['.mp3', '.wav', '.ogg', '.m4a', '.aac'],
            images: ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        },
        chunk_size: 1000, // For document chunking
        overlap: 200
    },
    
    // UI Configuration
    UI: {
        loading_delay: 300, // ms
        toast_duration: 5000, // ms
        animation_speed: 300, // ms
        debounce_delay: 500, // ms for search inputs
        pagination: {
            default_page_size: 20,
            max_page_size: 100
        }
    },
    
    // Chat Configuration
    CHAT: {
        max_message_length: 500,
        typing_indicator_delay: 1000,
        auto_scroll: true,
        save_history: true,
        default_user_id: 'test_user'
    },
    
    // Multimedia Configuration
    MULTIMEDIA: {
        audio: {
            max_duration: 300, // 5 minutes
            sample_rate: 44100,
            echo_cancellation: true,
            noise_suppression: true,
            formats: ['audio/wav', 'audio/mp3', 'audio/ogg', 'audio/m4a']
        },
        video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facing_mode: 'environment', // Use back camera if available
            formats: ['image/jpeg', 'image/png', 'image/webp']
        }
    },
    
    // Company Management
    COMPANIES: {
        default_company: 'benova',
        max_companies: 50,
        validation_pattern: /^[a-zA-Z0-9_-]+$/
    },
    
    // Debug and Development
    DEBUG: {
        enabled: !isProduction,
        log_level: isProduction ? 'warn' : 'debug',
        show_network_logs: !isProduction,
        show_timing_logs: !isProduction
    },
    
    // Feature Flags
    FEATURES: {
        file_upload: true,
        voice_recording: true,
        image_capture: true,
        google_calendar: true,
        schedule_agent: true,
        vector_management: true,
        admin_tools: true,
        export_import: true
    },
    
    // Error Messages
    MESSAGES: {
        errors: {
            network: 'Error de conexión. Verifica tu conexión a internet.',
            timeout: 'La operación tardó demasiado. Intenta nuevamente.',
            server: 'Error del servidor. Contacta al administrador.',
            validation: 'Datos inválidos. Verifica la información ingresada.',
            permission: 'No tienes permisos para realizar esta acción.',
            not_found: 'Recurso no encontrado.',
            file_size: 'El archivo es demasiado grande.',
            file_type: 'Tipo de archivo no soportado.'
        },
        success: {
            saved: 'Información guardada correctamente.',
            uploaded: 'Archivo subido exitosamente.',
            deleted: 'Elemento eliminado correctamente.',
            updated: 'Actualización completada.',
            processed: 'Procesamiento completado.'
        },
        info: {
            loading: 'Cargando...',
            processing: 'Procesando...',
            uploading: 'Subiendo archivo...',
            saving: 'Guardando...',
            searching: 'Buscando...'
        }
    }
};

// Utility functions available globally
window.APP_UTILS = {
    /**
     * Format URL with parameters
     */
    formatUrl(template, params = {}) {
        let url = template;
        Object.keys(params).forEach(key => {
            url = url.replace(`{${key}}`, encodeURIComponent(params[key]));
        });
        return url;
    },
    
    /**
     * Validate file size and type
     */
    validateFile(file, type = 'documents') {
        const config = window.APP_CONFIG.UPLOAD;
        
        // Check size
        if (file.size > config.max_file_size) {
            throw new Error(`Archivo demasiado grande. Máximo ${Math.round(config.max_file_size / 1024 / 1024)}MB`);
        }
        
        // Check type
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        const allowedTypes = config.allowed_types[type] || [];
        
        if (!allowedTypes.includes(extension)) {
            throw new Error(`Tipo de archivo no soportado. Permitidos: ${allowedTypes.join(', ')}`);
        }
        
        return true;
    },
    
    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Throttle function
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    /**
     * Format date for display
     */
    formatDate(dateString, locale = 'es-ES') {
        if (!dateString) return 'N/A';
        try {
            return new Date(dateString).toLocaleDateString(locale);
        } catch {
            return dateString;
        }
    },
    
    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Generate unique ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },
    
    /**
     * Safe JSON parse
     */
    parseJSON(str, fallback = null) {
        try {
            return JSON.parse(str);
        } catch {
            return fallback;
        }
    },
    
    /**
     * Deep clone object
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const clonedObj = {};
            Object.keys(obj).forEach(key => {
                clonedObj[key] = this.deepClone(obj[key]);
            });
            return clonedObj;
        }
    }
};

// Basic UI utilities available immediately
window.UI = {
    /**
     * Show loading overlay
     */
    showLoading(message = 'Cargando...') {
        const overlay = document.getElementById('loadingOverlay');
        const messageEl = document.getElementById('loadingMessage');
        
        if (overlay && messageEl) {
            messageEl.textContent = message;
            overlay.style.display = 'flex';
        }
    },
    
    /**
     * Hide loading overlay
     */
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    },
    
    /**
     * Show toast notification
     */
    showNotification(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">&times;</button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            if (container.contains(toast)) {
                toast.remove();
            }
        }, window.APP_CONFIG.UI.toast_duration);
        
        // Animation
        requestAnimationFrame(() => {
            toast.classList.add('toast-show');
        });
    }
};

// Environment setup
if (window.APP_CONFIG.DEBUG.enabled) {
    console.log('🔧 App configuration loaded:', window.APP_CONFIG);
    console.log('🌐 API Base URL:', API_BASE);
    console.log('🏭 Environment:', isProduction ? 'Production' : 'Development');
}

// Global error handler
window.addEventListener('error', (event) => {
    if (window.APP_CONFIG.DEBUG.enabled) {
        console.error('🚨 Global Error:', {
            message: event.error?.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            timestamp: new Date().toISOString()
        });
    }
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
    if (window.APP_CONFIG.DEBUG.enabled) {
        console.error('🚨 Unhandled Promise Rejection:', event.reason);
    }
});

console.log('✅ Config.js loaded successfully');
