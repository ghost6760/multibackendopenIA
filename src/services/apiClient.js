// src/services/apiClient.js - Cliente API básico
export const apiClient = {
  get: async (url) => {
    const response = await fetch(url);
    return { data: await response.json() };
  },
  post: async (url, data) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return { data: await response.json() };
  },
  withCompany: (companyId) => ({
    get: (url) => apiClient.get(`${url}?company_id=${companyId}`),
    post: (url, data) => apiClient.post(url, { ...data, company_id: companyId })
  })
};

// src/services/companiesService.js - Servicio de empresas básico  
export const companiesService = {
  async list() {
    const response = await apiClient.get('/api/companies');
    return response.data;
  },
  
  async getById(companyId) {
    const response = await apiClient.get(`/api/companies/${companyId}`);
    return response.data;
  }
};

// src/services/documentsService.js - Servicio de documentos básico
export const documentsService = {
  async list(companyId) {
    const response = await apiClient.get(`/api/documents?company_id=${companyId}`);
    return response.data;
  },

  async upload(companyId, file, description) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);
    formData.append('company_id', companyId);
    
    const response = await fetch('/api/documents', {
      method: 'POST',
      body: formData
    });
    
    return { data: await response.json() };
  },

  async delete(companyId, documentId) {
    const response = await apiClient.withCompany(companyId).delete(`/documents/${documentId}`);
    return response.data;
  }
};

// src/services/conversationsService.js - Servicio de conversaciones básico  
export const conversationsService = {
  async list(companyId) {
    const response = await apiClient.get(`/api/conversations?company_id=${companyId}`);
    return response.data;
  },

  async sendMessage(companyId, userId, message) {
    const response = await apiClient.post('/api/conversations/message', {
      user_id: userId,
      message: message,
      company_id: companyId
    });
    return response.data;
  }
};

// src/services/multimediaService.js - Servicio multimedia básico
export const multimediaService = {
  async uploadImage(companyId, file) {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('company_id', companyId);
    
    const response = await fetch('/api/multimedia/image', {
      method: 'POST', 
      body: formData
    });
    
    return { data: await response.json() };
  }
};
