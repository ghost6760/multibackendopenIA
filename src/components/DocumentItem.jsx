// src/components/DocumentItem.jsx
import React, { useState } from 'react';
import { FileText, Eye, Trash2, Calendar, Database, Tag, ChevronDown, ChevronRight } from 'lucide-react';

const DocumentItem = ({ document, onDelete, onViewVectors, showToast }) => {
  const [expanded, setExpanded] = useState(false);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileIcon = (fileType) => {
    if (!fileType) return <FileText className="h-5 w-5 text-gray-500" />;
    
    if (fileType.includes('pdf')) return <FileText className="h-5 w-5 text-red-500" />;
    if (fileType.includes('doc')) return <FileText className="h-5 w-5 text-blue-500" />;
    if (fileType.includes('text')) return <FileText className="h-5 w-5 text-green-500" />;
    
    return <FileText className="h-5 w-5 text-gray-500" />;
  };

  const copyDocumentId = () => {
    if (document.id) {
      navigator.clipboard.writeText(document.id);
      showToast('📋 ID copiado al portapapeles', 'success');
    }
  };

  return (
    <div className="hover:bg-gray-50 transition-colors">
      <div className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-3">
              {getFileIcon(document.metadata?.file_type)}
              
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 truncate">
                  {document.title || document.filename || 'Sin título'}
                </h4>
                <div className="flex items-center space-x-4 mt-1">
                  <p className="text-xs text-gray-500">
                    ID: <button 
                      onClick={copyDocumentId}
                      className="hover:text-blue-600 underline cursor-pointer"
                    >
                      {document.id ? document.id.substring(0, 8) + '...' : 'N/A'}
                    </button>
                  </p>
                  <p className="text-xs text-gray-500 flex items-center">
                    <Database className="h-3 w-3 mr-1" />
                    {document.chunks || document.chunk_count || 0} chunks
                  </p>
                  <p className="text-xs text-gray-500 flex items-center">
                    <Calendar className="h-3 w-3 mr-1" />
                    {formatDate(document.created_at || document.upload_date)}
                  </p>
                </div>
              </div>
              
              <button
                onClick={() => setExpanded(!expanded)}
                className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
              >
                {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
            </div>
          </div>
          
          <div className="flex items-center space-x-2 ml-4">
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

        {/* Información expandida */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Información del archivo */}
              <div className="space-y-2">
                <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Archivo
                </h5>
                <div className="space-y-1 text-xs text-gray-600">
                  <p>Nombre: {document.filename || 'N/A'}</p>
                  <p>Tipo: {document.metadata?.file_type || 'N/A'}</p>
                  <p>Tamaño: {formatFileSize(document.metadata?.file_size)}</p>
                </div>
              </div>

              {/* Metadata */}
              <div className="space-y-2">
                <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Metadata
                </h5>
                <div className="space-y-1 text-xs text-gray-600">
                  <p>Descripción: {document.description || document.metadata?.description || 'N/A'}</p>
                  <p className="flex items-center">
                    <Tag className="h-3 w-3 mr-1" />
                    Categoría: {document.metadata?.category || 'General'}
                  </p>
                </div>
              </div>

              {/* Estadísticas */}
              <div className="space-y-2">
                <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Procesamiento
                </h5>
                <div className="space-y-1 text-xs text-gray-600">
                  <p>Chunks: {document.chunks || document.chunk_count || 0}</p>
                  <p>Estado: {document.status || 'Procesado'}</p>
                  <p>Vectorizado: {document.vectorized ? '✅ Sí' : '❌ No'}</p>
                </div>
              </div>

              {/* Acciones adicionales */}
              <div className="space-y-2">
                <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Acciones
                </h5>
                <div className="space-y-1">
                  <button
                    onClick={() => showToast(`📄 Documento: ${document.title || document.filename}`, 'info')}
                    className="text-xs text-blue-600 hover:text-blue-800 block"
                  >
                    Ver detalles completos
                  </button>
                  <button
                    onClick={() => onViewVectors(document.id)}
                    className="text-xs text-green-600 hover:text-green-800 block"
                  >
                    Inspeccionar vectores
                  </button>
                  <button
                    onClick={() => showToast(`🔄 Reprocesar ${document.title || document.filename}`, 'info')}
                    className="text-xs text-purple-600 hover:text-purple-800 block"
                  >
                    Reprocesar
                  </button>
                </div>
              </div>
            </div>

            {/* Contenido preview (si está disponible) */}
            {document.content_preview && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                  Vista Previa del Contenido
                </h5>
                <div className="bg-gray-50 rounded-md p-3 text-xs text-gray-700 max-h-32 overflow-y-auto">
                  {document.content_preview}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentItem;
