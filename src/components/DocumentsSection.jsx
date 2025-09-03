// src/components/DocumentsSection.jsx - Gestión de documentos corregida
import React, { useState, useEffect } from 'react';
import apiService from '../services/api';

const DocumentsSection = ({ currentCompanyId, companies }) => {
  const [documents, setDocuments] = useState([]};

export default DocumentsSection;
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadDescription, setUploadDescription] = useState('');
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (currentCompanyId) {
      apiService.setCompanyId(currentCompanyId);
      loadDocuments();
      loadDocumentStats();
    }
  }, [currentCompanyId]);

  const loadDocuments = async () => {
    if (!currentCompanyId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('🔍 Loading documents for company:', currentCompanyId);
      const response = await apiService.getDocuments();
      
      console.log('📁 Documents response:', response);
      
      if (response && response.status === 'success') {
        setDocuments(response.documents || []);
      } else if (response && Array.isArray(response)) {
        setDocuments(response);
      } else {
        throw new Error(response?.message || 'Formato de respuesta inválido');
      }
      
    } catch (error) {
      console.error('❌ Error loading documents:', error);
      setError(`Error cargando documentos: ${error.message}`);
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocumentStats = async () => {
    if (!currentCompanyId) return;
    
    try {
      const response = await apiService.getDocumentStats();
      console.log('📊 Document stats:', response);
      setStats(response);
    } catch (error) {
      console.error('❌ Error loading document stats:', error);
      // No mostrar error para stats, no es crítico
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validar tamaño (máximo 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError('El archivo no puede ser mayor a 10MB');
        return;
      }
      
      // Validar tipo de archivo
      const allowedTypes = [
        'application/pdf',
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/csv'
      ];
      
      if (!allowedTypes.includes(file.type)) {
        setError('Tipo de archivo no soportado. Use PDF, TXT, DOC, DOCX o CSV');
        return;
      }
      
      setSelectedFile(file);
      setError(null);
    }
  };

  const uploadDocument = async () => {
    if (!selectedFile || !currentCompanyId) return;
    
    setIsLoading(true);
    setUploadProgress(0);
    setError(null);
    
    try {
      console.log('📤 Uploading document:', selectedFile.name);
      
      // Simular progreso de subida
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 100);
      
      const response = await apiService.uploadDocument(selectedFile, uploadDescription);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      console.log('✅ Upload response:', response);
      
      if (response && response.status === 'success') {
        // Limpiar formulario
        setSelectedFile(null);
        setUploadDescription('');
        setUploadProgress(0);
        
        // Recargar documentos
        await loadDocuments();
        await loadDocumentStats();
        
        alert('✅ Documento subido exitosamente');
      } else {
        throw new Error(response?.message || 'Error subiendo documento');
      }
      
    } catch (error) {
      console.error('❌ Error uploading document:', error);
      setError(`Error subiendo documento: ${error.message}`);
      setUploadProgress(0);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteDocument = async (documentId, documentName) => {
    if (!window.confirm(`¿Estás seguro de eliminar "${documentName}"?`)) {
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('🗑️ Deleting document:', documentId);
      
      const response = await apiService.deleteDocument(documentId);
      console.log('✅ Delete response:', response);
      
      if (response && response.status === 'success') {
        // Recargar documentos
        await loadDocuments();
        await loadDocumentStats();
        
        alert(`✅ Documento "${documentName}" eliminado exitosamente`);
      } else {
        throw new Error(response?.message || 'Error eliminando documento');
      }
      
    } catch (error) {
      console.error('❌ Error deleting document:', error);
      setError(`Error eliminando documento: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/
