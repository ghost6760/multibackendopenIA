// src/services/api.js - Servicio de API corregido y robusto

class APIService {
  constructor() {
    // Detectar entorno automáticamente
    this.baseURL = this.detectEnvironment();
    this.companyId = null;
    this.defaultTimeout = 15000; // 15 segundos
    
    console.log(`🔗 API Service initialized with baseURL: ${this.baseURL}`);
  }

  detectEnvironment() {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    const port = window.location.port;

    // Railway production
    if (hostname.includes('railway.app') || hostname.includes('.up.railway.app')) {
      return `${protocol}//${hostname}`;
    }
    
    // Desarrollo local
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      // Si estamos en el puerto del frontend, usar el puerto del backend
      if (port === '3000') {
        return `${protocol}//${hostname}:8080`;
      }
      return `${protocol}//${hostname}:${port || 8080}`;
    }
    
    // Por defecto, usar la misma origin
    return `${protocol}//${hostname}${port ? ':' + port : ''}`;
  }

  setCompanyId(companyId) {
    this.companyId = companyId;
    console.log(`🏢 Company ID set to: ${companyId}`);
  }

  getHeaders(includeCompany = true) {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (includeCompany && this.companyId) {
      headers['X-Company-ID'] = this.companyId;
    }

    return headers;
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const requestOptions = {
      timeout: this.defaultTimeout,
      headers: this.getHeaders(options.includeCompany !== false),
      ...options
    };

    // Si hay company_id y es una petición GET, añadirlo como query param también
    if (this.companyId && (!options.method || options.method === 'GET')) {
      const separator = endpoint.includes('?') ? '&' : '?';
      const urlWithCompany = `${url}${separator}company_id=${this.companyId}`;
      
      console.log(`📡 Making request to: ${urlWithCompany}`);
      
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), requestOptions.timeout);
        
        const response = await fetch(urlWithCompany, {
          ...requestOptions,
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`✅ Request successful:`, data);
        return data;
        
      } catch (error) {
        console.error(`❌ Request failed for ${urlWithCompany}:`, error);
        throw this.handleError(error);
      }
    } else {
      console.log(`📡 Making request to: ${url}`);
      
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), requestOptions.timeout);
        
        const response = await fetch(url, {
          ...requestOptions,
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`✅ Request successful:`, data);
        return data;
        
      } catch (error) {
        console.error(`❌ Request failed for ${url}:`, error);
        throw this.handleError(error);
      }
    }
  }

  handleError(error) {
    if (error.name === 'AbortError') {
      return new Error('La petición tardó demasiado en responder');
    }
    
    if (error.message.includes('Failed to fetch')) {
      return new Error('Error de conexión. Verifica tu conexión a internet.');
    }
    
    if (error.message.includes('HTTP 404')) {
      return new Error('El recurso solicitado no fue encontrado');
    }
    
    if (error.message.includes('HTTP 500')) {
      return new Error('Error interno del servidor');
    }
    
    return error;
  }

  // ============================================================================
  // ENDPOINTS DE EMPRESAS
  // ============================================================================
  
  async getCompanies() {
    try {
      return await this.makeRequest('/api/companies', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error getting companies:', error);
      throw error;
    }
  }

  async getCompanyDetails(companyId) {
    try {
      const originalCompanyId = this.companyId;
      this.companyId = companyId;
      
      const result = await this.makeRequest(`/api/companies/${companyId}`);
      
      this.companyId = originalCompanyId;
      return result;
    } catch (error) {
      console.error(`Error getting company details for ${companyId}:`, error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE SALUD Y SISTEMA
  // ============================================================================
  
  async getSystemHealth() {
    try {
      return await this.makeRequest('/api/health', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error getting system health:', error);
      // No lanzar error para health check, devolver estado de error
      return {
        status: 'error',
        message: 'No se pudo conectar con el sistema',
        error: error.message
      };
    }
  }

  async getSystemInfo() {
    try {
      return await this.makeRequest('/api/system/info', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error getting system info:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE DOCUMENTOS
  // ============================================================================
  
  async getDocuments() {
    if (!this.companyId) {
      throw new Error('Company ID is required to get documents');
    }
    
    try {
      return await this.makeRequest('/api/documents/list');
    } catch (error) {
      console.error('Error getting documents:', error);
      throw error;
    }
  }

  async uploadDocument(file, metadata = {}) {
    if (!this.companyId) {
      throw new Error('Company ID is required to upload documents');
    }
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('company_id', this.companyId);
      
      if (metadata && Object.keys(metadata).length > 0) {
        formData.append('metadata', JSON.stringify(metadata));
      }

      const response = await fetch(`${this.baseURL}/api/documents/upload`, {
        method: 'POST',
        headers: {
          'X-Company-ID': this.companyId
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
      
    } catch (error) {
      console.error('Error uploading document:', error);
      throw error;
    }
  }

  async deleteDocument(documentId) {
    if (!this.companyId) {
      throw new Error('Company ID is required to delete documents');
    }
    
    try {
      return await this.makeRequest(`/api/documents/delete/${documentId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      console.error(`Error deleting document ${documentId}:`, error);
      throw error;
    }
  }

  async searchDocuments(query, options = {}) {
    if (!this.companyId) {
      throw new Error('Company ID is required to search documents');
    }
    
    try {
      return await this.makeRequest('/api/documents/search', {
        method: 'POST',
        body: JSON.stringify({
          query,
          k: options.k || 5,
          filter: options.filter || {}
        })
      });
    } catch (error) {
      console.error('Error searching documents:', error);
      throw error;
    }
  }

  async getDocumentStats() {
    if (!this.companyId) {
      throw new Error('Company ID is required to get document stats');
    }
    
    try {
      return await this.makeRequest('/api/documents/stats');
    } catch (error) {
      console.error('Error getting document stats:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE CONVERSACIONES
  // ============================================================================
  
  async getConversations() {
    if (!this.companyId) {
      throw new Error('Company ID is required to get conversations');
    }
    
    try {
      return await this.makeRequest('/api/conversations');
    } catch (error) {
      console.error('Error getting conversations:', error);
      throw error;
    }
  }

  async getConversation(conversationId) {
    if (!this.companyId) {
      throw new Error('Company ID is required to get conversation');
    }
    
    try {
      return await this.makeRequest(`/api/conversations/${conversationId}`);
    } catch (error) {
      console.error(`Error getting conversation ${conversationId}:`, error);
      throw error;
    }
  }

  async sendMessage(message, conversationId = null, userId = 'web-user') {
    if (!this.companyId) {
      throw new Error('Company ID is required to send message');
    }
    
    try {
      const payload = {
        message: message.trim(),
        user_id: userId,
        company_id: this.companyId
      };

      if (conversationId) {
        payload.conversation_id = conversationId;
      }

      return await this.makeRequest('/api/conversations/message', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  // ============================================================================
  // ENDPOINTS DE ADMIN
  // ============================================================================
  
  async runDiagnostics() {
    try {
      return await this.makeRequest('/api/admin/diagnostics', {
        includeCompany: false
      });
    } catch (error) {
      console.error('Error running diagnostics:', error);
      throw error;
    }
  }

  async reloadCompaniesConfig() {
    try {
      return await this.makeRequest('/api/admin/reload-companies', {
        method: 'POST',
        includeCompany: false
      });
    } catch (error) {
      console.error('Error reloading companies config:', error);
      throw error;
    }
  }

  async testMultimedia() {
    if (!this.companyId) {
      throw new Error('Company ID is required to test multimedia');
    }
    
    try {
      return await this.makeRequest('/api/admin/multimedia/test', {
        method: 'POST'
      });
    } catch (error) {
      console.error('Error testing multimedia:', error);
      throw error;
    }
  }

  // ============================================================================
  // UTILIDADES
  // ============================================================================
  
  async testConnection() {
    try {
      const response = await this.getSystemHealth();
      return {
        success: true,
        status: response.status,
        message: 'Conexión exitosa'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        message: 'Error de conexión'
      };
    }
  }

  // Método para verificar si una empresa específica está disponible
  async verifyCompanyAccess(companyId) {
    try {
      const originalCompanyId = this.companyId;
      this.companyId = companyId;
      
      const response = await this.getDocuments();
      
      this.companyId = originalCompanyId;
      return {
        success: true,
        accessible: true
      };
    } catch (error) {
      return {
        success: false,
        accessible: false,
        error: error.message
      };
    }
  }

  // Método para obtener configuración completa de una empresa
  async getFullCompanyConfig(companyId) {
    try {
      const originalCompanyId = this.companyId;
      this.companyId = companyId;
      
      const [details, documents, conversations] = await Promise.allSettled([
        this.getCompanyDetails(companyId),
        this.getDocuments(),
        this.getConversations()
      ]);
      
      this.companyId = originalCompanyId;
      
      return {
        success: true,
        company: details.status === 'fulfilled' ? details.value : null,
        documents_available: documents.status === 'fulfilled',
        conversations_available: conversations.status === 'fulfilled',
        documents_count: documents.status === 'fulfilled' ? 
          (documents.value?.documents_count || 0) : 0,
        conversations_count: conversations.status === 'fulfilled' ? 
          (conversations.value?.conversations?.length || 0) : 0
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
}

// Crear instancia singleton
export const apiService = new APIService();

// Export default para compatibilidad
export default apiService;
