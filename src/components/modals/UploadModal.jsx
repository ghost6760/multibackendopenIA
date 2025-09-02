// src/components/modals/UploadModal.jsx
import React, { useState, useRef } from 'react';
import { X, Upload, CheckCircle, FileText } from 'lucide-react';

const UploadModal = ({ 
  onClose, 
  currentCompanyId, 
  companies, 
  onSuccess, 
  showToast, 
  showLoading, 
  hideLoading 
}) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [metadata, setMetadata] = useState({
    title: '',
    description: '',
    category: ''
  });
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragIn = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragOut = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      setSelectedFile(files[0]);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      showToast('❌ Selecciona un archivo primero', 'error');
      return;
    }

    try {
      showLoading('Subiendo documento...');

      const finalMetadata = {
        ...metadata,
        filename: selectedFile.name,
        file_size: selectedFile.size,
        file_type: selectedFile.type
      };

      // Simulación de upload - reemplazar con documentsService.upload cuando esté disponible
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      showToast(`✅ Documento subido exitosamente`, 'success');
      onSuccess(); // Recargar lista de documentos
      onClose();
    } catch (error) {
      showToast('❌ Error subiendo documento: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const validateFile = (file) => {
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'text/markdown'
    ];
    
    const maxSize = 50 * 1024 * 1024; // 50MB
    
    if (!allowedTypes.includes(file.type)) {
      showToast('❌ Tipo de archivo no soportado. Usa: PDF, DOC, DOCX, TXT, MD', 'error');
      return false;
    }
    
    if (file.size > maxSize) {
      showToast('❌ El archivo es demasiado grande. Máximo 50MB', 'error');
      return false;
    }
    
    return true;
  };

  const handleFileChange = (file) => {
    if (validateFile(file)) {
      setSelectedFile(file);
      // Auto-llenar título basado en el nombre del archivo
      if (!metadata.title) {
        const name = file.name.replace(/\.[^/.]+$/, ""); // Remover extensión
        setMetadata(prev => ({ ...prev, title: name }));
      }
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">
              Subir Documento
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Añadir nuevo documento para entrenar el chatbot
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Zona de arrastrar y soltar */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center mb-6 transition-all duration-200 cursor-pointer ${
            dragOver 
              ? 'border-blue-400 bg-blue-50 scale-105' 
              : selectedFile 
                ? 'border-green-400 bg-green-50' 
                : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }`}
          onDragEnter={handleDragIn}
          onDragLeave={handleDragOut}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={(e) => e.target.files[0] && handleFileChange(e.target.files[0])}
            accept=".pdf,.doc,.docx,.txt,.md"
            className="hidden"
          />

          {selectedFile ? (
            <div className="space-y-3">
              <CheckCircle className="h-12 w-12 text-green-600 mx-auto" />
              <div>
                <p className="text-green-600 font-medium">{selectedFile.name}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <p className="text-xs text-gray-400 mt-2">
                  Haz clic para cambiar archivo
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {dragOver ? (
                <Upload className="h-12 w-12 text-blue-600 mx-auto animate-bounce" />
              ) : (
                <FileText className="h-12 w-12 text-gray-400 mx-auto" />
              )}
              <div>
                <p className="text-gray-600 font-medium">
                  {dragOver ? 'Suelta el archivo aquí' : 'Arrastra un archivo aquí o haz clic'}
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  Soportados: PDF, DOC, DOCX, TXT, MD (máx. 50MB)
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Campos de metadata */}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Título del documento
            </label>
            <input
              type="text"
              value={metadata.title}
              onChange={(e) => setMetadata(prev => ({ ...prev, title: e.target.value }))}
              placeholder="Título descriptivo del documento"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descripción (opcional)
            </label>
            <textarea
              value={metadata.description}
              onChange={(e) => setMetadata(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Descripción breve del contenido"
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Categoría (opcional)
            </label>
            <select
              value={metadata.category}
              onChange={(e) => setMetadata(prev => ({ ...prev, category: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Seleccionar categoría</option>
              <option value="tratamientos">Tratamientos</option>
              <option value="precios">Precios</option>
              <option value="horarios">Horarios</option>
              <option value="politicas">Políticas</option>
              <option value="general">General</option>
            </select>
          </div>
        </div>

        {/* Información de la empresa */}
        <div className="bg-blue-50 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <FileText className="h-5 w-5 text-blue-600 mr-2" />
            <div>
              <p className="text-sm font-medium text-blue-700">
                Empresa: {companies[currentCompanyId]?.company_name}
              </p>
              <p className="text-xs text-blue-600">
                Este documento se asociará exclusivamente a esta empresa
              </p>
            </div>
          </div>
        </div>

        {/* Botones de acción */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selectedFile}
            className={`px-4 py-2 rounded-lg transition-colors ${
              selectedFile
                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Upload className="h-4 w-4 inline mr-2" />
            Subir Documento
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadModal;
