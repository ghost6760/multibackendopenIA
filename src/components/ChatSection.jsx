// src/components/ChatSection.jsx
import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Settings, Camera, Mic, MicOff, Send } from 'lucide-react';
import { conversationsService } from '../services/conversationsService';
import { multimediaService } from '../services/multimediaService';
import ChatMessage from './ChatMessage';

const ChatSection = ({
  currentCompanyId,
  companies,
  showToast,
  showLoading,
  hideLoading,
  setShowCameraModal
}) => {
  const [chatMessages, setChatMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [testUserId, setTestUserId] = useState('test_user');
  const [isRecording, setIsRecording] = useState(false);
  
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const sendMessage = async (message = currentMessage) => {
    if (!message.trim() || !currentCompanyId) return;

    const userMessage = { role: 'user', content: message, timestamp: new Date() };
    setChatMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');

    try {
      showLoading('Enviando mensaje...');
      
      const data = await conversationsService.sendMessage(currentCompanyId, testUserId, message);
      
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        agent: data.agent_used,
        timestamp: new Date()
      };
      setChatMessages(prev => [...prev, assistantMessage]);

      if (data.agent_used) {
        const systemMessage = {
          role: 'system',
          content: `Agente: ${data.agent_used} | Empresa: ${companies[currentCompanyId]?.company_name || currentCompanyId}`,
          timestamp: new Date()
        };
        setChatMessages(prev => [...prev, systemMessage]);
      }
    } catch (error) {
      const errorMessage = {
        role: 'error',
        content: 'Error: ' + error.message,
        timestamp: new Date()
      };
      setChatMessages(prev => [...prev, errorMessage]);
      showToast('❌ Error enviando mensaje: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await processVoiceMessage(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      showToast('🎤 Grabando...', 'info');
    } catch (error) {
      showToast('❌ Error accediendo al micrófono: ' + error.message, 'error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processVoiceMessage = async (audioBlob) => {
    try {
      showLoading('Procesando audio...');
      
      const data = await multimediaService.processVoice(currentCompanyId, audioBlob, testUserId);
      
      const userMessage = {
        role: 'user',
        content: `🎤 Audio: "${data.transcription}"`,
        timestamp: new Date()
      };
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date()
      };

      setChatMessages(prev => [...prev, userMessage, assistantMessage]);
      showToast('✅ Audio procesado correctamente', 'success');
    } catch (error) {
      showToast('❌ Error procesando audio: ' + error.message, 'error');
    } finally {
      hideLoading();
    }
  };

  const clearChat = () => {
    setChatMessages([]);
    showToast('💬 Chat limpiado', 'info');
  };

  if (!currentCompanyId) {
    return (
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-8 text-center">
        <MessageSquare className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-700 mb-2">
          Selecciona una empresa
        </h3>
        <p className="text-gray-500">
          Para comenzar a probar el chat, selecciona una empresa en el header.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Configuración del chat */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <Settings className="h-5 w-5 mr-2" />
          Configuración de Pruebas
        </h3>
        
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center space-x-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Usuario de Prueba
              </label>
              <input
                type="text"
                value={testUserId}
                onChange={(e) => setTestUserId(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="test_user"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Empresa Actual
              </label>
              <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-gray-700">
                {companies[currentCompanyId]?.company_name || currentCompanyId}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={clearChat}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm"
            >
              Limpiar Chat
            </button>
            <div className="text-sm text-gray-500">
              {chatMessages.length} mensajes
            </div>
          </div>
        </div>
      </div>

      {/* Chat interface */}
      <div className="bg-white/95 backdrop-blur-sm rounded-xl overflow-hidden shadow-lg">
        {/* Messages area */}
        <div className="h-96 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {chatMessages.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <MessageSquare className="h-12 w-12 mx-auto mb-3 text-gray-400" />
              <p>Envía un mensaje para comenzar la conversación</p>
              <p className="text-sm mt-2">
                Puedes escribir, grabar audio o capturar una imagen
              </p>
            </div>
          ) : (
            chatMessages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <div className="flex items-end space-x-3">
            <div className="flex-1 relative">
              <textarea
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Escribe tu mensaje aquí..."
                rows="2"
                className="w-full px-4 py-2 pr-24 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>
            
            {/* Action buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowCameraModal(true)}
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                title="Capturar imagen"
              >
                <Camera className="h-5 w-5" />
              </button>
              
              <button
                onClick={isRecording ? stopRecording : startRecording}
                className={`p-2 rounded-lg transition-colors ${
                  isRecording
                    ? 'text-red-600 hover:text-red-700 bg-red-50 animate-pulse'
                    : 'text-gray-500 hover:text-blue-600 hover:bg-blue-50'
                }`}
                title={isRecording ? 'Parar grabación' : 'Grabar audio'}
              >
                {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
              </button>
              
              <button
                onClick={() => sendMessage()}
                disabled={!currentMessage.trim()}
                className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Enviar mensaje"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </div>
          
          {isRecording && (
            <div className="mt-2 text-center">
              <span className="text-red-600 text-sm flex items-center justify-center space-x-2">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                <span>Grabando... Haz clic en el micrófono para detener</span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatSection;
