// src/components/modals/ConfigModal.jsx
import React, { useState } from 'react';
import { X, Calendar, Save, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react';
import { companiesService } from '../../services/companiesService';

const ConfigModal = ({ 
  onClose, 
  currentCompanyId, 
  googleCalendarUrl, 
  setGoogleCalendarUrl, 
  showToast, 
  showLoading, 
  hideLoading 
}) => {
  const [localUrl, setLocalUrl] = useState(googleCalendarUrl);
  const [isValidUrl, setIsValidUrl] = useState(true);

  const validateUrl = (url) => {
    if (!url.trim()) {
      setIsValidUrl(true);
      return true;
    }

    try {
      const urlObj = new URL(url);
      const isValid = urlObj.protocol === 'https:' && 
                     (urlObj.hostname.includes('calendar.google.com') || 
                      urlObj.hostname.includes('googleapis.com'));
      setIsValidUrl(isValid);
      return isValid;
    } catch {
      setIsValidUrl(false);
      return false;
    }
  };

  const handleUrlChange = (e) => {
    const url = e.target.value;
    setLocalUrl(url);
    validateUrl(url);
  };

  const handleSave = async () => {
    if (!localUrl.trim()) {
      showToast('❌ Ingresa una URL válida', 'error');
      return;
    }

    if (!isValidUrl) {
      showToast('❌ La URL debe ser de Google Calendar (https://calendar.google.com/...)', 'error');
      return;
    }

    try {
      showLoading('Guardando configuración...');
      
      await companiesService.updateGoogleCalendar(currentCompanyId, localUrl);
      
      setGoogleCalendarUrl(localUrl);
      showToast('✅ Configuración de Google Calendar guardada', 'success');
      onClose();
    } catch (error) {
      showToast('❌ Error guardando configuración: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const handleTestUrl = () => {
    if (localUrl && isValidUrl) {
      window.open(localUrl, '_blank');
    } else {
      showToast('❌ Ingresa una URL válida primero', 'error');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center space-x-2">
            <Calendar className="h-6 w-6 text-orange-600" />
            <h3 className="text-lg font-semibold text-gray-800">
              Configuración Google Calendar
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Información */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <Calendar className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="text-blue-800 font-medium mb-1">
                Integración con Google Calendar
              </p>
              <p className="text-blue-700 text-xs leading-relaxed">
                Esta URL será utilizada por el agente scheduler para gestionar citas automáticamente. 
                Debe ser una URL válida de Google Calendar.
              </p>
            </div>
          </div>
        </div>

        {/* Campo URL */}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              URL de conexión Google Calendar
            </label>
            <div className="relative">
              <input
                type="url"
                value={localUrl}
                onChange={handleUrlChange}
                className={`w-full px-3 py-2 pr-10 border rounded-md focus:outline-none focus:ring-2 transition-colors ${
                  isValidUrl 
                    ? 'border-gray-300 focus:ring-blue-500 focus:border-transparent' 
                    : 'border-red-300 focus:ring-red-500 focus:border-transparent bg-red-50'
                }`}
                placeholder="https://calendar.google.com/calendar/..."
              />
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                {localUrl && (
                  isValidUrl ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  )
                )}
              </div>
            </div>
            
            {!isValidUrl && localUrl && (
              <p className="text-red-600 text-xs mt-1 flex items-center">
                <AlertCircle className="h-3 w-3 mr-1" />
                La URL debe ser de Google Calendar (https://calendar.google.com/...)
              </p>
            )}
            
            <p className="text-gray-500 text-xs mt-2">
              Ejemplo: https://calendar.google.com/calendar/u/0/r
            </p>
          </div>

          {/* Botón de prueba */}
          {localUrl && isValidUrl && (
            <button
              onClick={handleTestUrl}
              className="w-full px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center space-x-2 text-sm"
            >
              <ExternalLink className="h-4 w-4" />
              <span>Probar URL (abrir en nueva ventana)</span>
            </button>
          )}
        </div>

        {/* Instrucciones */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <div className="flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="text-yellow-800 font-medium mb-2">
                Instrucciones para obtener la URL:
              </p>
              <ol className="text-yellow-700 text-xs space-y-1 list-decimal list-inside">
                <li>Ve a Google Calendar en tu navegador</li>
                <li>Copia la URL completa de la página principal</li>
                <li>Pégala en el campo superior</li>
                <li>El sistema la utilizará para integraciones de agenda</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Empresa actual */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-6">
          <p className="text-sm text-gray-700">
            <span className="font-medium">Configurando para:</span>
            <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
              {currentCompanyId}
            </span>
          </p>
        </div>

        {/* Botones */}
        <div className="flex space-x-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={!localUrl.trim() || !isValidUrl}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            <Save className="h-4 w-4" />
            <span>Guardar</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfigModal;
