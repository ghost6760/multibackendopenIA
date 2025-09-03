// src/components/DocumentManager.js - Gestor de documentos

import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const DocumentManager = ({ company }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);

  useEffect(() => {
    if (company) {
      loadDocuments();
    }
  }, [company]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiService.getDocuments();
      if (response.success && response.documents) {
        setDocuments(response.documents);
      } else {
        setDocuments([]);
      }
    } catch (err) {
      console.error('Error loading documents:', err);
      setError('Error al cargar documentos: ' + err.message);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      setUploading(true);
      setError(null);

      const response = await apiService.uploadDocument(file, {
        uploaded_at: new Date().toISOString(),
        company_id: company.company_id
      });

      if (response.success) {
        await loadDocuments(); // Recargar lista
        event.target.value = ''; // Limpiar input
      } else {
        throw new Error(response.error || 'Error al subir documento');
      }
    } catch (err) {
      console.error('Error uploading document:', err);
      setError('Error al subir documento: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!confirm('¿Estás seguro de que quieres eliminar este documento?')) {
      return;
    }

    try {
      const response = await apiService.deleteDocument(documentId);
      if (response.success) {
        await loadDocuments(); // Recargar lista
      } else {
        throw new Error(response.error || 'Error al eliminar documento');
      }
    } catch (err) {
      console.error('Error deleting document:', err);
      setError('Error al eliminar documento: ' + err.message);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await apiService.searchDocuments(searchQuery, { k: 10 });
      if (response.success && response.results) {
        setSearchResults(response.results);
      } else {
        setSearchResults([]);
      }
    } catch (err) {
      console.error('Error searching documents:', err);
      setError('Error en la búsqueda: ' + err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Gestión de Documentos
            </h2>
            <p className="text-gray-600 mt-1">
              {company?.company_name} - {documents.length} documentos
            </p>
          </div>
          <button
            onClick={loadDocuments}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            disabled={loading}
          >
            {loading ? <LoadingSpinner size="small" /> : null}
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Actualizar</span>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <p className="text-red-800">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-600"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Subir Nuevo Documento
        </h3>
        <div className="flex items-center space-x-4">
          <input
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
            accept=".pdf,.doc,.docx,.txt,.md"
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
          />
          {uploading && (
            <div className="flex items-center space-x-2 text-blue-600">
              <LoadingSpinner size="small" />
              <span className="text-sm">Subiendo...</span>
            </div>
          )}
        </div>
        <p className="mt-2 text-sm text-gray-500">
          Formatos soportados: PDF, DOC, DOCX, TXT, MD (máximo 16MB)
        </p>
      </div>

      {/* Search Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Buscar en Documentos
        </h3>
        <div className="flex space-x-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Escribe tu búsqueda..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Buscar
          </button>
        </div>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="mt-6">
            <h4 className="font-medium text-gray-900 mb-3">
              Resultados de búsqueda ({searchResults.length})
            </h4>
            <div className="space-y-3">
              {searchResults.map((result, index) => (
                <div key={index} className="p-4 border border-gray-200 rounded-lg">
                  <p className="text-sm text-gray-800">{result.content}</p>
                  {result.metadata && (
                    <div className="mt-2 text-xs text-gray-500">
                      Score: {result.relevance_score?.toFixed(3) || 'N/A'}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Documentos ({documents.length})
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          {loading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="large" />
            </div>
          ) : documents.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Título
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vista Previa
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {doc.title || 'Sin título'}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-500 max-w-xs truncate">
                        {doc.content_preview || 'Sin vista previa'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handleDeleteDocument(doc.id)}
                        className="text-red-600 hover:text-red-900 transition-colors"
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-8">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No hay documentos</h3>
              <p className="mt-1 text-sm text-gray-500">
                Comienza subiendo tu primer documento.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentManager;
