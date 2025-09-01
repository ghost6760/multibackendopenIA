// src/services/multimediaService.js
import { apiClient } from './apiClient';

export const multimediaService = {
  async processVoice(companyId, audioBlob, userId, question = '') {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice_message.wav');
    formData.append('user_id', userId);
    formData.append('company_id', companyId);
    if (question) {
      formData.append('question', question);
    }

    const response = await apiClient.post('/multimedia/process-voice', formData);
    return response.data;
  },

  async processImage(companyId, imageFile, userId, question = '') {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('user_id', userId);
    formData.append('company_id', companyId);
    formData.append('question', question || 'Analiza esta imagen');

    const response = await apiClient.post('/multimedia/process-image', formData);
    return response.data;
  },

  async processVideo(companyId, videoFile, userId, question = '') {
    const formData = new FormData();
    formData.append('video', videoFile);
    formData.append('user_id', userId);
    formData.append('company_id', companyId);
    if (question) {
      formData.append('question', question);
    }

    const response = await apiClient.post('/multimedia/process-video', formData);
    return response.data;
  },

  async transcribeAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.wav');

    const response = await apiClient.post('/multimedia/transcribe', formData);
    return response.data;
  },

  async synthesizeVoice(text, voice = 'es-ES-Standard-A') {
    const response = await apiClient.post('/multimedia/synthesize', {
      text,
      voice
    });
    return response.data;
  },

  async analyzeImage(imageFile) {
    const formData = new FormData();
    formData.append('image', imageFile);

    const response = await apiClient.post('/multimedia/analyze-image', formData);
    return response.data;
  }
};
