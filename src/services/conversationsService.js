// src/services/conversationsService.js
import { apiClient } from './apiClient';

export const conversationsService = {
  async list(companyId) {
    const response = await apiClient.get(`/conversations?company_id=${companyId}`);
    return response.data;
  },

  async sendMessage(companyId, userId, message) {
    const response = await apiClient.withCompany(companyId).post('/conversations/message', {
      user_id: userId,
      question: message,
      company_id: companyId
    });
    return response.data;
  },

  async getById(companyId, conversationId) {
    const response = await apiClient.withCompany(companyId).get(`/conversations/${conversationId}`);
    return response.data;
  },

  async getHistory(companyId, userId, limit = 50) {
    const response = await apiClient.withCompany(companyId).get(`/conversations/history/${userId}?limit=${limit}`);
    return response.data;
  },

  async delete(companyId, conversationId) {
    const response = await apiClient.withCompany(companyId).delete(`/conversations/${conversationId}`);
    return response.data;
  },

  async clear(companyId, userId) {
    const response = await apiClient.withCompany(companyId).post(`/conversations/clear/${userId}`);
    return response.data;
  },

  async getStats(companyId) {
    const response = await apiClient.withCompany(companyId).get(`/conversations/stats?company_id=${companyId}`);
    return response.data;
  },

  async exportConversation(companyId, conversationId, format = 'json') {
    const response = await apiClient.withCompany(companyId).get(
      `/conversations/${conversationId}/export?format=${format}`
    );
    return response.data;
  }
};
