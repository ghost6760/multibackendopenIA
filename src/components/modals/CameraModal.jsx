// src/components/modals/CameraModal.jsx
import React, { useState, useEffect, useRef } from 'react';
import { X, Camera, Send, RotateCcw, Zap } from 'lucide-react';
import { multimediaService } from '../../services/multimediaService';

const CameraModal = ({ 
  onClose, 
  currentCompanyId, 
  companies, 
  showToast, 
  showLoading, 
  hideLoading 
}) => {
  const [stream, setStream] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [cameraError, setCameraError] = useState(null);
  const [question, setQuestion] = useState('Analiza esta imagen capturada desde la cámara');
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    startCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startCamera = async () => {
    try {
      setCameraError(null);
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user' 
        } 
      });
      
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (error) {
      console.error('Error accediendo a la cámara:', error);
      setCameraError(error.message);
      showToast('❌ Error accediendo a la cámara: ' + error.message, 'error');
    }
  };

  const takePicture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (video && canvas) {
      const ctx = canvas.getContext('2d');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      // Dibujar la imagen del video en el canvas
      ctx.drawImage(video, 0, 0);

      // Convertir a blob
      canvas.toBlob((blob) => {
        setCapturedImage(blob);
        showToast('📸 Imagen capturada correctamente', 'success');
        
        // Detener el stream de video para ahorrar recursos
        if (stream) {
          stream.getTracks().forEach(track => track.stop());
          setStream(null);
        }
      }, 'image/jpeg', 0.8);
    }
  };

  const retakePhoto = () => {
    setCapturedImage(null);
    startCamera(); // Reiniciar la cámara
  };

  const sendImage = async () => {
    if (!capturedImage) return;

    try {
      showLoading('Procesando imagen...');

      const data = await multimediaService.processImage(
        currentCompanyId, 
        capturedImage, 
        'camera_user', 
        question
      );

      if (data.status === 'success') {
        showToast('✅ Imagen procesada correctamente', 'success');
        
        // Mostrar resultado en un toast más detallado
        setTimeout(() => {
          showToast(`🤖 Respuesta: ${data.response.substring(0, 100)}...`, 'info');
        }, 1000);
        
        onClose();
      } else {
        throw new Error(data.message || 'Error procesando imagen');
      }
    } catch (error) {
      showToast('❌ Error procesando imagen: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const handleClose = () => {
    // Limpiar recursos antes de cerrar
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[95vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-800 flex items-center">
              <Camera className="h-5 w-5 mr-2" />
              Capturar Imagen
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Para empresa: <strong>{companies[currentCompanyId]?.company_name || currentCompanyId}</strong>
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Error de cámara */}
        {cameraError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <Camera className="h-5 w-5 text-red-600 mr-2" />
              <div>
                <p className="text-red-800 font-medium">Error de cámara</p>
                <p className="text-red-700 text-sm mt-1">{cameraError}</p>
              </div>
            </div>
            <button
              onClick={startCamera}
              className="mt-3 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
            >
              Reintentar
            </button>
          </div>
        )}

        <div className="space-y-4">
          {/* Vista de la cámara o imagen capturada */}
          <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
            {!capturedImage ? (
              // Vista en vivo de la cámara
              <>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
                <canvas ref={canvasRef} className="hidden" />
                
                {/* Overlay con información */}
                <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1 rounded-full text-sm">
                  {stream ? '🔴 En vivo' : '⏸️ Detenido'}
                </div>
                
                {/* Grid de ayuda para encuadre */}
                <div className="absolute inset-0 pointer-events-none">
                  <div className="w-full h-full grid grid-cols-3 grid-rows-3">
                    {[...Array(9)].map((_, i) => (
                      <div key={i} className="border border-white/20" />
                    ))}
                  </div>
                </div>
              </>
            ) : (
              // Imagen capturada
              <div className="relative w-full h-full">
                <img
                  src={URL.createObjectURL(capturedImage)}
                  alt="Imagen capturada"
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-4 left-4 bg-green-600 text-white px-3 py-1 rounded-full text-sm">
                  📸 Capturada
                </div>
              </div>
            )}
          </div>

          {/* Campo de pregunta para la imagen */}
          {capturedImage && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Pregunta sobre la imagen
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows="2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                placeholder="¿Qué quieres saber sobre esta imagen?"
              />
            </div>
          )}

          {/* Controles */}
          <div className="flex justify-center space-x-4">
            {!capturedImage ? (
              // Botones para capturar
              <>
                <button
                  onClick={takePicture}
                  disabled={!stream}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  <Camera className="h-5 w-5" />
                  <span>Tomar Foto</span>
                </button>
                <button
                  onClick={handleClose}
                  className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
              </>
            ) : (
              // Botones para imagen capturada
              <>
                <button
                  onClick={sendImage}
                  className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
                >
                  <Send className="h-5 w-5" />
                  <span>Procesar Imagen</span>
                </button>
                <button
                  onClick={retakePhoto}
                  className="px-4 py-3 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors flex items-center space-x-2"
                >
                  <RotateCcw className="h-5 w-5" />
                  <span>Tomar Otra</span>
                </button>
                <button
                  onClick={handleClose}
                  className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancelar
                </button>
              </>
            )}
          </div>

          {/* Información adicional */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-start space-x-2">
              <Zap className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="text-blue-800 font-medium">Procesamiento con IA</p>
                <p className="text-blue-700 text-xs mt-1">
                  La imagen será analizada por el sistema de IA de la empresa {companies[currentCompanyId]?.company_name || currentCompanyId} 
                  y recibirás una respuesta contextualizada.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CameraModal;
