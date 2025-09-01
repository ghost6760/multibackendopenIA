// src/components/modals/UploadModal.jsx
import React, { useState, useRef } from 'react';
import { X, Upload, CheckCircle, Building, FileText } from 'lucide-react';
import { documentsService } from '../../services/documentsService';

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

      const data = await documentsService.upload(currentCompanyId, selectedFile, finalMetadata);
      
      showToast(`✅ Documento subido: ${data.chunks_created || 0} chunks creados`, 'success');
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
              value={metadata.title
