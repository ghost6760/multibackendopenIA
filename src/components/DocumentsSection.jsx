// src/components/DocumentsSection.jsx
import React from 'react';
import { FileText, Upload, Trash2, RefreshCw, Eye, Database, Search } from 'lucide-react';

const DocumentsSection = ({
  documents,
  currentCompanyId,
  companies,
  loadDocuments,
  showToast,
  showLoading,
  hideLoading,
  setShowUploadModal
}) => {
  const deleteDocument = async (docId) => {
    // Reemplazar confirm por implementación segura
    const userConfirmed = window.confirm('¿Eliminar documento? Esta acción no se puede deshacer.');
    if (!userConfirmed) return;

    try {
      showLoading('Eliminando documento...');
      
      // Simulación de API call - reemplazar con documentsService.delete cuando esté disponible
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      showToast('✅ Documento eliminado', 'success');
      loadDocuments();
    } catch (error) {
      showToast('❌ Error eliminando documento: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const cleanupVectors = async () => {
    const userConfirmed = window.confirm('¿Limpiar vectores huérfanos? Esta acción no se puede deshacer.');
    if (!userConfirmed) return;

    try {
      showLoading('Limpiando vectores...');
      
      // Simulación de API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      showToast('✅ Vectores limpiados exitosamente', 'success');
    } catch (error) {
      showToast('❌ Error limpiando vectores: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const viewVectors = async (docId) => {
    try {
      showLoading('Cargando vectores...');
      
      // Simulación de API call
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const vectorCount = Math.floor(Math.random() * 50) + 10; // Simulado
      showToast(`📊 ${vectorCount} vectores encontrados para el documento`, 'info');
    } catch (error) {
      showToast('❌ Error cargando vectores: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const getDocumentStats = async () => {
    try {
      showLoading('Obteniendo estadísticas...');
      
      // Simulación de API call
      await new Promise(resolve => setTimeout(resolve, 800));
      
      const totalChunks = documents.reduce((sum, doc) => sum + (doc.chunks || doc.chunk_count || 0), 0);
      const message = `📊 Estadísticas: ${documents.length} docs, ${totalChunks} chunks`;
      showToast(message, 'info');
    } catch (error) {
      showToast('❌ Error obteniendo estadísticas: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  // Componente simplificado para item de documento
  const DocumentItem = ({ document, onDelete, onViewVectors }) => (
    <div className="px-6 py-4 hover:bg-gray-50 transition-colors">
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <FileText className="h-8 w-8 text-blue-600" />
          <div>
            <h4 className="font-medium text-gray-800">
              {document.title || document.filename || 'Documento sin título'}
            </h4>
            <p className="text-sm text-gray-500">
              {document.description || 'Sin descripción'}
            </p>
            <div className="flex space-x-4 text-xs text-gray-400 mt-1">
              <span>📄 {document.chunks || document.chunk_count || 0} chunks</span>
              <span>🔍 {document.vectors || 'N/A'} vectores</span>
              <span>📅 {document.created_at ? new Date(document.created_at).toLocaleDateString() : 'N/A'}</span>
            </div>
          </div>
        </div>
        
        <div className="flex space-x-2">
          <button
            onClick={() => onViewVectors(document.id)}
            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            title="Ver vectores"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={() => onDelete(document.id)}
            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Eliminar documento"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );

  if (!currentCompanyId) {
    return (
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-8 text-center">
        <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-700 mb-2">
          Selecciona una empresa
        </h3>
        <p className="text-gray-500">
          Para gestionar documentos, selecciona una empresa en el header.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header de documentos */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 flex items-center">
              <FileText className="h-5 w-5 mr-2" />
              Gestión de Documentos - {companies[currentCompanyId]?.company_name || currentCompanyId}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Administra los documentos que entrenan el chatbot de tu empresa
            </p>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={() => setShowUploadModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
              <Upload className="h-4 w-4" />
              <span>Subir Documento</span>
            </button>
            
            <button
              onClick={getDocumentStats}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center space-x-2"
            >
              <Database className="h-4 w-4" />
              <span>Estadísticas</span>
            </button>
            
            <button
              onClick={cleanupVectors}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2"
            >
              <Trash2 className="h-4 w-4" />
              <span>Limpiar Vectores</span>
            </button>
            
            <button
              onClick={loadDocuments}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center space-x-2"
            >
              <RefreshCw className="h-4 w-4" />
              <span>Actualizar</span>
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-blue-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Documentos</p>
                <p className="text-lg font-semibold text-blue-600">
                  {documents.length}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center">
              <Database className="h-8 w-8 text-green-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Total Chunks</p>
                <p className="text-lg font-semibold text-green-600">
                  {documents.reduce((sum, doc) => sum + (doc.chunks || doc.chunk_count || 0), 0)}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-purple-50 rounded-lg p-4">
            <div className="flex items-center">
              <Search className="h-8 w-8 text-purple-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Empresa</p>
                <p className="text-sm font-semibold text-purple-600">
                  {companies[currentCompanyId]?.company_name || currentCompanyId}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-orange-50 rounded-lg p-4">
            <div className="flex items-center">
              <Eye className="h-8 w-8 text-orange-600 mr-3" />
              <div>
                <p className="text-sm font-medium text-gray-600">Estado</p>
                <p className="text-sm font-semibold text-orange-600">
                  {documents.length > 0 ? 'Activo' : 'Sin datos'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lista de documentos */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl overflow-hidden shadow-lg">
        {documents.length === 0 ? (
          <div className="p-8 text-center">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <h4 className="text-lg font-medium text-gray-700 mb-2">
              No hay documentos
            </h4>
            <p className="text-gray-500 mb-4">
              Sube tu primer documento para comenzar a entrenar el chatbot.
            </p>
            <div className="space-y-2">
              <button
                onClick={() => setShowUploadModal(true)}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Subir Primer Documento
              </button>
              <p className="text-xs text-gray-400">
                Formatos soportados: PDF, DOC, DOCX, TXT, MD
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">
                  {documents.length} documentos encontrados
                </span>
                <div className="flex space-x-2 text-xs text-gray-500">
                  <span>Última actualización: {new Date().toLocaleTimeString('es-ES')}</span>
                </div>
              </div>
            </div>
            
            {documents.map((doc, index) => (
              <DocumentItem
                key={doc.id || `doc-${index}`}
                document={doc}
                onDelete={deleteDocument}
                onViewVectors={viewVectors}
                showToast={showToast}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentsSection;
