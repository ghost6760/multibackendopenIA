// src/components/ChatSection.jsx - Chat corregido con endpoints del backend
import React, { useState, useEffect, useRef } from 'react';
import apiService from '../services/api';

const ChatSection = ({ currentCompanyId, companies }) => {
  const [chatMessages, setChatMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [testUserId] = useState('web-test-user');
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (currentCompanyId) {
      apiService.setCompanyId(currentCompanyId);
      // Limpiar mensajes al cambiar de empresa
      setChatMessages([]);
      setConversationId(null);
    }
  }, [currentCompanyId]);

  useEffect(() => {
    // Scroll automático al final del chat
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || !currentCompanyId) return;

    const userMessage = {
      id: Date.now(),
      text: inputMessage,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString()
    };

    setChatMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // CORRECCIÓN: Usar el método corregido del API service
      const response = await apiService.sendMessage(
        inputMessage,
        conversationId,
        testUserId
      );

      // Extraer la respuesta del formato del backend
      const botResponse = {
        id: Date.now() + 1,
        text: response.response || response.message || 'Sin respuesta',
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString()
      };

      setChatMessages(prev => [...prev, botResponse]);

      // Guardar el conversation_id si viene en la respuesta
      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = {
        id: Date.now() + 1,
        text: `❌ Error: ${error.message}`,
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString(),
        isError: true
      };

      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setChatMessages([]);
    setConversationId(null);
  };

  const loadSampleQuestions = () => {
    const sampleQuestions = [
      'Hola, ¿cómo estás?',
      '¿Qué servicios ofrecen?',
      'Quiero agendar una cita',
      '¿Cuáles son sus precios?',
      '¿Cuál es su horario de atención?',
      'Necesito más información'
    ];
    
    setInputMessage(sampleQuestions[Math.floor(Math.random() * sampleQuestions.length)]);
  };

  if (!currentCompanyId) {
    return (
      <div className="bg-white/90 backdrop-blur rounded-lg p-6 text-center">
        <div className="text-gray-500">
          <div className="text-4xl mb-4">💬</div>
          <h3 className="text-lg font-semibold mb-2">Chat de Prueba</h3>
          <p>Selecciona una empresa para comenzar a chatear</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/90 backdrop-blur rounded-lg overflow-hidden flex flex-col h-[600px]">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 flex justify-between items-center">
        <div>
          <h3 className="font-semibold">Chat con {companies[currentCompanyId]?.company_name}</h3>
          <p className="text-blue-200 text-sm">
            {conversationId ? `Conversación: ${conversationId.slice(-8)}` : 'Nueva conversación'}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadSampleQuestions}
            className="px-3 py-1 bg-blue-700 rounded text-sm hover:bg-blue-800 transition-colors"
            disabled={isLoading}
          >
            📝 Pregunta Random
          </button>
          <button
            onClick={clearChat}
            className="px-3 py-1 bg-red-600 rounded text-sm hover:bg-red-700 transition-colors"
            disabled={isLoading}
          >
            🗑️ Limpiar
          </button>
        </div>
      </div>

      {/* Messages Container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 p-4 overflow-y-auto space-y-4"
      >
        {chatMessages.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <div className="text-3xl mb-2">👋</div>
            <p>¡Escribe un mensaje para comenzar!</p>
            <p className="text-sm mt-2">Prueba preguntando sobre servicios, precios o agenda una cita</p>
          </div>
        )}

        {chatMessages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.sender === 'user'
                  ? 'bg-blue-600 text-white'
                  : message.isError
                  ? 'bg-red-100 text-red-800 border border-red-300'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.text}</p>
              <p
                className={`text-xs mt-1 ${
                  message.sender === 'user' 
                    ? 'text-blue-200' 
                    : message.isError
                    ? 'text-red-600'
                    : 'text-gray-500'
                }`}
              >
                {message.timestamp}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 px-4 py-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-gray-600">Escribiendo...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Escribe tu mensaje aquí..."
            className="flex-1 resize-none border rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 max-h-20"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 ${
              inputMessage.trim() && !isLoading
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <span className="flex items-center gap-2">
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Enviando...
                </>
              ) : (
                <>
                  <span>📤</span>
                  Enviar
                </>
              )}
            </span>
          </button>
        </div>
        
        {/* Quick action buttons */}
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => setInputMessage('Hola, ¿cómo estás?')}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
            disabled={isLoading}
          >
            👋 Saludo
          </button>
          <button
            onClick={() => setInputMessage('¿Qué servicios ofrecen?')}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
            disabled={isLoading}
          >
            🔍 Servicios
          </button>
          <button
            onClick={() => setInputMessage('Quiero agendar una cita')}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
            disabled={isLoading}
          >
            📅 Cita
          </button>
          <button
            onClick={() => setInputMessage('¿Cuáles son sus precios?')}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
            disabled={isLoading}
          >
            💰 Precios
          </button>
        </div>
      </div>

      {/* Debug info */}
      <div className="bg-gray-50 border-t p-3 text-xs text-gray-600">
        <details>
          <summary className="cursor-pointer font-medium">🔧 Debug Info</summary>
          <div className="mt-2 space-y-1">
            <div><strong>Company ID:</strong> {currentCompanyId}</div>
            <div><strong>User ID:</strong> {testUserId}</div>
            <div><strong>Conversation ID:</strong> {conversationId || 'No iniciada'}</div>
            <div><strong>Messages Count:</strong> {chatMessages.length}</div>
            <div><strong>API Endpoint:</strong> POST /api/conversations/message</div>
            <div><strong>Loading:</strong> {isLoading ? 'Sí' : 'No'}</div>
          </div>
        </details>
      </div>
    </div>
  );
};

export default ChatSection;
