// src/services/documentsService.js
import { apiClient } from './apiClient';

export const documentsService = {
  async list(companyId) {
    const response = await apiClient.get(`/documents/list?company_id=${companyId}`);
    return response.data;
  },

  async upload(companyId, file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('company_id', companyId);
    
    // Añadir metadata
    Object.keys(metadata).forEach(key => {
      if (metadata[key] !== null && metadata[key] !== undefined) {
        formData.append(key, metadata[key]);
      }
    });

    const response = await apiClient.post('/documents/upload', formData);
    return response.data;
  },

  async addText(companyId, content, metadata = {}) {
    const response = await apiClient.withCompany(companyId).post('/documents', {
      content,
      metadata,
      company_id: companyId
    });
    return response.data;
  },

  async delete(companyId, docId) {
    const response = await apiClient.withCompany(companyId).delete(`/documents/${docId}`);
    return response.data;
  },

  async cleanup(companyId, dryRun = false) {
    const response = await apiClient.withCompany(companyId).post('/documents/cleanup', {
      dry_run: dryRun,
      company_id: companyId
    });
    return response.data;
  },

  async getVectors(companyId, docId) {
    const response = await apiClient.withCompany(companyId).get(`/documents/${docId}/vectors`);
    return response.data;
  },

  async search(companyId, query, limit = 10) {
    const response = await apiClient.withCompany(companyId).post('/documents/search', {
      query,
      limit,
      company_id: companyId
    });
    return response.data;
  },

  async getStats(companyId) {
    const response = await apiClient.withCompany(companyId).get(`/documents/stats?company_id=${companyId}`);
    return response.data;
  }
};
