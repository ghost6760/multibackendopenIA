// src/components/DocumentsSection.jsx - Gestión de documentos corregida
import React, { useState, useEffect } from 'react';
import apiService from '../services/api';

const DocumentsSection = ({ currentCompanyId, companies }) => {
  const [documents, setDocuments] = useState([]);
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
      console.log('Loading documents for company:', currentCompanyId);
      const response = await apiService.getDocuments();
      
      console.log('Documents response:', response);
      
      if (response && response.status === 'success') {
        setDocuments(response.documents || []);
      } else if (response && Array.isArray(response)) {
        setDocuments(response);
      } else {
        throw new Error(response?.message || 'Formato de respuesta inválido');
      }
      
    } catch (error) {
      console.error('Error loading documents:', error);
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
      console.log('Document stats:', response);
      setStats(response);
    } catch (error) {
      console.error('Error loading document stats:', error);
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
      console.log('Uploading document:', selectedFile.name);
      
      // Simular progreso de subida
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 100);
      
      const response = await apiService.uploadDocument(selectedFile, uploadDescription);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      console.log('Upload response:', response);
      
      if (response && response.status === 'success') {
        // Limpiar formulario
        setSelectedFile(null);
        setUploadDescription('');
        setUploadProgress(0);
        
        // Recargar documentos
        await loadDocuments();
        await loadDocumentStats();
        
        alert('Documento subido exitosamente');
      } else {
        throw new Error(response?.message || 'Error subiendo documento');
      }
      
    } catch (error) {
      console.error('Error uploading document:', error);
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
      console.log('Deleting document:', documentId);
      
      const response = await apiService.deleteDocument(documentId);
      console.log('Delete response:', response);
      
      if (response && response.status === 'success') {
        // Recargar documentos
        await loadDocuments();
        await loadDocumentStats();
        
        alert(`Documento "${documentName}" eliminado exitosamente`);
      } else {
        throw new Error(response?.message || 'Error eliminando documento');
      }
      
    } catch (error) {
      console.error('Error deleting document:', error);
      setError(`Error eliminando documento: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('es-ES');
  };

  if (!currentCompanyId) {
    return (
      <div className="bg-white/90 backdrop-blur rounded-lg p-6 text-center">
        <div className="text-gray-500">
          <div className="text-4xl mb-4">📄</div>
          <h3 className="text-lg font-semibold mb-2">Gestión de Documentos</h3>
          <p>Selecciona una empresa para gestionar sus documentos</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">
              📄 Documentos de {companies[currentCompanyId]?.company_name}
            </h2>
            <p className="text-gray-600 mt-1">
              Sube y gestiona los documentos de conocimiento para el chatbot
            </p>
          </div>
          
          {stats && (
            <div className="bg-blue-50 rounded-lg p-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="font-semibold text-blue-800">Total Documentos</div>
                  <div className="text-blue-600">{stats.total_documents || 0}</div>
                </div>
                <div>
                  <div className="font-semibold text-blue-800">Total Vectores</div>
                  <div className="text-blue-600">{stats.total_vectors || 0}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <div className="flex">
              <span className="text-red-500 mr-2">❌</span>
              {error}
            </div>
          </div>
        )}
      </div>

      {/* Upload Section */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">📤 Subir Nuevo Documento</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Seleccionar Archivo
            </label>
            <input
              type="file"
              onChange={handleFileSelect}
              accept=".pdf,.txt,.doc,.docx,.csv"
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              disabled={isLoading}
            />
            <p className="mt-1 text-xs text-gray-500">
              Formatos soportados: PDF, TXT, DOC, DOCX, CSV (máximo 10MB)
            </p>
          </div>

          {selectedFile && (
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-blue-800">{selectedFile.name}</div>
                  <div className="text-sm text-blue-600">
                    {formatFileSize(selectedFile.size)} • {selectedFile.type}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-red-500 hover:text-red-700"
                  disabled={isLoading}
                >
                  ❌
                </button>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descripción (Opcional)
            </label>
            <textarea
              value={uploadDescription}
              onChange={(e) => setUploadDescription(e.target.value)}
              placeholder="Descripción del documento..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:border-blue-500"
              rows={2}
              disabled={isLoading}
            />
          </div>

          {uploadProgress > 0 && (
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          )}

          <button
            onClick={uploadDocument}
            disabled={!selectedFile || isLoading}
            className={`w-full py-2 px-4 rounded-lg font-medium transition-all ${
              selectedFile && !isLoading
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Subiendo...
              </span>
            ) : (
              '📤 Subir Documento'
            )}
          </button>
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">📋 Documentos Existentes</h3>
          <button
            onClick={loadDocuments}
            disabled={isLoading}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            🔄 Actualizar
          </button>
        </div>

        {isLoading && documents.length === 0 ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Cargando documentos...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">📄</div>
            <p>No hay documentos cargados</p>
            <p className="text-sm mt-1">Sube tu primer documento para comenzar</p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id || doc.document_id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center mb-2">
                      <span className="text-xl mr-2">
                        {doc.file_type === 'pdf' ? '📄' : 
                         doc.file_type === 'txt' ? '📝' : 
                         doc.file_type === 'doc' || doc.file_type === 'docx' ? '📘' : 
                         doc.file_type === 'csv' ? '📊' : '📄'}
                      </span>
                      <div>
                        <h4 className="font-medium text-gray-800">
                          {doc.filename || doc.name || 'Documento sin nombre'}
                        </h4>
                        <p className="text-sm text-gray-600">
                          {formatFileSize(doc.file_size)} • 
                          Subido el {formatDate(doc.created_at || doc.upload_date)}
                        </p>
                      </div>
                    </div>
                    
                    {doc.description && (
                      <p className="text-sm text-gray-700 mb-2">{doc.description}</p>
                    )}
                    
                    <div className="flex items-center text-xs text-gray-500 space-x-4">
                      <span>🔤 {doc.chunks_count || doc.vectors || 0} vectores</span>
                      <span>🏷️ {doc.file_type?.toUpperCase() || 'N/A'}</span>
                      {doc.status && (
                        <span className={`px-2 py-1 rounded-full ${
                          doc.status === 'processed' ? 'bg-green-100 text-green-700' :
                          doc.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {doc.status}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="ml-4 flex flex-col space-y-2">
                    <button
                      onClick={() => deleteDocument(
                        doc.id || doc.document_id, 
                        doc.filename || doc.name || 'Documento'
                      )}
                      disabled={isLoading}
                      className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors disabled:opacity-50"
                    >
                      🗑️ Eliminar
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Debug Info */}
      <div className="bg-white/90 backdrop-blur rounded-lg p-4">
        <details>
          <summary className="cursor-pointer font-medium text-sm">🔧 Debug Info</summary>
          <div className="mt-2 text-xs space-y-1 text-gray-600">
            <div><strong>Company ID:</strong> {currentCompanyId}</div>
            <div><strong>Documents Count:</strong> {documents.length}</div>
            <div><strong>API Endpoint:</strong> GET/POST /api/documents</div>
            <div><strong>Loading:</strong> {isLoading ? 'Sí' : 'No'}</div>
            <div><strong>Selected File:</strong> {selectedFile?.name || 'Ninguno'}</div>
            <div><strong>Last Error:</strong> {error || 'Ninguno'}</div>
          </div>
        </details>
      </div>
    </div>
  );
};

export default DocumentsSection;
